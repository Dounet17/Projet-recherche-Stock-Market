"""Construit la table de référence du buy and hold, 2016-2024, et la compare aux données de French.

Depuis la racine : venv/bin/python reports/build_reference.py
Résultat : data/reference/ (détail, non versionné) et reports/lab_2026-11/reference/ (synthèses).
"""

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from reference import TIERS, annualized, rolling_annual, benchmark_multiple, buy_hold_table, cohort_statistics, parse_french_csv, parse_sic_definitions, sector_of, tier_mask
from universe_data import load_universe

DATA = ROOT / "data" / "reference"
FRENCH = ROOT / "data" / "french"
OUT = ROOT / "reports" / "lab_2026-11" / "reference"
BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FILES = {"ind49": "49_Industry_Portfolios_daily_CSV.zip", "ind12": "12_Industry_Portfolios_daily_CSV.zip", "factors": "F-F_Research_Data_Factors_daily_CSV.zip", "sic49": "Siccodes49.zip", "sic12": "Siccodes12.zip"}
for folder in (DATA, FRENCH, OUT):
    folder.mkdir(parents=True, exist_ok=True)


def fetch(name):
    """Télécharge un fichier de French. Les données sont coupées à fin 2024 avant d'être gardées."""
    request = urllib.request.Request(BASE_URL + FILES[name], headers={"User-Agent": "research-script"})
    with urllib.request.urlopen(request, timeout=120) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))
    return archive.read(archive.namelist()[0]).decode("latin-1")


def load_french():
    sections = {}
    for name in ("ind49", "ind12", "factors"):
        for section, frame in parse_french_csv(fetch(name)).items():
            frame.to_parquet(FRENCH / f"{name}_{section}.parquet")
            sections[f"{name}_{section}"] = frame
    definitions = {name: fetch(name) for name in ("sic49", "sic12")}
    for name, text in definitions.items():
        (FRENCH / f"{name}.txt").write_text(text)
    return sections, definitions


print("Données de French...", flush=True)
french, definitions = load_french()
assert max(frame.index.max() for frame in french.values()) <= pd.Timestamp("2024-12-31")

print("Univers...", flush=True)
market = load_universe()
data = market.data
companies = pd.read_parquet(ROOT / "data" / "sec" / "dev_companies.parquet", columns=["cik", "sic"]).drop_duplicates("cik").set_index("cik").sic
securities = market.securities
sic = securities.cik.map(companies)
ranges49, _ = parse_sic_definitions(definitions["sic49"])
ranges12, _ = parse_sic_definitions(definitions["sic12"])
sectors = pd.DataFrame({"sector49": sector_of(sic.to_numpy(), ranges49), "sector12": sector_of(sic.to_numpy(), ranges12)}, index=securities.index)
defense = {f"{s}#0" for s in pd.read_csv(ROOT / "reports" / "lab_2026-11" / "defense_securities.csv").symbol}
missing = defense - set(securities.index)
assert not missing, missing
sectors["defense_list"] = sectors.index.isin(defense)
sectors.assign(symbol=securities.symbol, sic=sic, security_type=securities.security_type, exited=securities.exit_return_base.notna()).to_parquet(DATA / "sectors.parquet")

print("Table du buy and hold...", flush=True)
table = buy_hold_table(market)
table.to_parquet(DATA / "buy_hold_by_cohort.parquet", index=False)
print(f"{len(table):,} lignes, {table.start.nunique()} dates d'achat, de {table.start.min().date()} à {table.start.max().date()}", flush=True)
# Toutes les actions cotées, sans filtre de prix ni de liquidité : surtout de très petites valeurs.
listed_market = load_universe(min_price=0.0, min_dollar_volume=0.0)
listed = buy_hold_table(listed_market)
listed.to_parquet(DATA / "buy_hold_all_listed.parquet", index=False)
del listed_market
spy = benchmark_multiple(market.benchmarks, "SPY")
qqq = benchmark_multiple(market.benchmarks, "QQQ")
table = table.merge(sectors[["sector49", "sector12", "defense_list"]], left_on="security_id", right_index=True)

# 1. Par taille d'univers.
rows = []
for tier in TIERS:
    subset = table[tier_mask(table, tier)]
    stats = cohort_statistics(subset)
    for scenario in ("optimistic", "pessimistic", "gross_base"):
        stats[f"mean_{scenario}"] = subset.groupby(["start", "horizon"])[scenario].mean().to_numpy()
    merged = subset.merge(spy, on=["start", "horizon"])
    stats["share_beats_spy"] = merged.assign(win=merged.base > merged.SPY).groupby(["start", "horizon"]).win.mean().to_numpy()
    stats["tier"] = tier
    rows.append(stats)
stats = cohort_statistics(listed)
for scenario in ("optimistic", "pessimistic", "gross_base"):
    stats[f"mean_{scenario}"] = listed.groupby(["start", "horizon"])[scenario].mean().to_numpy()
merged = listed.merge(spy, on=["start", "horizon"])
stats["share_beats_spy"] = merged.assign(win=merged.base > merged.SPY).groupby(["start", "horizon"]).win.mean().to_numpy()
stats["tier"] = "all_listed"
rows.append(stats)
cohorts = pd.concat(rows, ignore_index=True).merge(spy, on=["start", "horizon"]).merge(qqq, on=["start", "horizon"])
cohorts["spy_annual"] = cohorts.SPY ** (1 / cohorts.nominal_years) - 1
cohorts.to_csv(OUT / "cohorts.csv", index=False)
# « Jusqu'à la fin » mélange des durées de 1 mois à 9 ans : on ne le moyenne pas entre dates d'achat.
horizon_summary = cohorts[cohorts.horizon != -1].groupby(["tier", "horizon"]).agg(cohorts=("start", "count"), mean_annual=("mean_annual", "mean"), median_annual=("median_annual", "mean"), spy_annual=("spy_annual", "mean"), share_loss=("share_loss", "mean"), share_beats_spy=("share_beats_spy", "mean"), worst_cohort=("mean_annual", "min"), best_cohort=("mean_annual", "max")).reset_index()
horizon_summary.to_csv(OUT / "summary_by_horizon.csv", index=False)

# 2. Par secteur, sur l'horizon de 5 ans et jusqu'à la fin.
sector_rows = []
for column, label in (("sector12", "french12"), ("sector49", "french49")):
    for tier in ("all", "top1000"):
        stats = cohort_statistics(table[tier_mask(table, tier)], by=(column,)).rename(columns={column: "sector"})
        stats["classification"], stats["tier"] = label, tier
        sector_rows.append(stats)
for tier in ("all", "top1000"):
    stats = cohort_statistics(table[tier_mask(table, tier) & table.defense_list.to_numpy()])
    stats["sector"], stats["classification"], stats["tier"] = "defense_list", "manual", tier
    sector_rows.append(stats)
sector_cohorts = pd.concat(sector_rows, ignore_index=True)
sector_cohorts.to_parquet(DATA / "sector_cohorts.parquet", index=False)
sector_summary = sector_cohorts[sector_cohorts.horizon.isin([-1, 60])].groupby(["classification", "tier", "sector", "horizon"]).agg(cohorts=("start", "count"), avg_titles=("count", "mean"), mean_annual=("mean_annual", "mean"), median_annual=("median_annual", "mean"), share_loss=("share_loss", "mean"), worst_cohort=("mean_annual", "min"), best_cohort=("mean_annual", "max")).reset_index()
sector_summary.to_csv(OUT / "summary_by_sector.csv", index=False)

# 3. Contrôle : notre moyenne quotidienne par secteur contre celle de French (CRSP).
common = securities.index[securities.security_type == "common"]
daily = data.close[common].pct_change(fill_method=None)
compare_rows = []
for name, column, section in (("french12", "sector12", "ind12_equal"), ("french49", "sector49", "ind49_equal")):
    reference = french[section].loc["2016-02-01":"2024-12-31"]
    for sector in reference.columns:
        members = sectors.index[(sectors[column] == sector) & sectors.index.isin(common)]
        ours = daily[members].mean(axis=1).reindex(reference.index) if len(members) else pd.Series(np.nan, index=reference.index)
        pair = pd.concat([ours, reference[sector]], axis=1).dropna()
        compare_rows.append({"classification": name, "sector": sector, "titles_ours": len(members), "days": len(pair), "correlation": pair.corr().iloc[0, 1] if len(pair) > 2 else np.nan, "annual_ours": annualized(pair.iloc[:, 0]), "annual_french": annualized(pair.iloc[:, 1])})
comparison = pd.DataFrame(compare_rows)
comparison["gap"] = comparison.annual_ours - comparison.annual_french
comparison.to_csv(OUT / "french_comparison.csv", index=False)
spy_close = market.benchmarks.close["SPY"].pct_change(fill_method=None)
market_vw = french["factors_data"]["Mkt-RF"] + french["factors_data"]["RF"]
pair = pd.concat([spy_close, market_vw], axis=1, join="inner").loc["2016-02-01":].dropna()
check = {"spy_vs_crsp_correlation": float(pair.corr().iloc[0, 1]), "spy_annual": annualized(pair.iloc[:, 0]), "crsp_market_annual": annualized(pair.iloc[:, 1])}

# 4. Long terme : la période 2016-2024 est-elle représentative ?
windows = []
for years, label in ((9, "2016-2024"), (7, "2018-2024")):
    rolling = rolling_annual(market_vw, years)
    observed = float(rolling.iloc[-1])
    windows.append({"window": label, "years": years, "annual": observed, "percentile_since_1926": float((rolling < observed).mean()), "worst": float(rolling.min()), "median": float(rolling.median()), "best": float(rolling.max()), "share_negative": float((rolling < 0).mean())})
pd.DataFrame(windows).to_csv(OUT / "long_term_market.csv", index=False)
long_rows = []
for section, weight in (("ind49_value", "value"), ("ind49_equal", "equal")):
    for sector, series in french[section].items():
        long_rows.append({"sector": sector, "weight": weight, "first_date": series.first_valid_index(), "annual_full": annualized(series), "annual_2000_2015": annualized(series.loc["2000":"2015"]), "annual_2016_2024": annualized(series.loc["2016":"2024"])})
pd.DataFrame(long_rows).to_csv(OUT / "long_term_sectors.csv", index=False)

# Affichage.
pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 200)
print("\nDurée des horizons : -1 = jusqu'à fin 2024")
print(horizon_summary.round(3).to_string())
print("\nPlus gros multiples, achat du 02/01/2018 :")
for label, frame in (("achetables", table), ("toutes cotées", listed)):
    top = frame[(frame.horizon == -1) & (frame.start == pd.Timestamp("2018-01-02"))].nlargest(6, "base")
    print(label, [(s, round(m, 1)) for s, m in zip(top.security_id, top.base)])
print("\nDates d'achat fixes :")
keep = ["tier", "start", "count", "mean", "median", "p10", "p90", "share_loss", "share_wiped_90", "share_exited", "share_beats_spy", "mean_optimistic", "mean_pessimistic", "mean_gross_base", "SPY", "QQQ"]
print(cohorts[(cohorts.horizon == -1) & cohorts.start.isin(pd.to_datetime(["2016-02-01", "2018-01-02"]))][keep].round(3).to_string())
print("\nSecteurs French 12, tous titres, 5 ans :")
print(sector_summary[(sector_summary.classification == "french12") & (sector_summary.tier == "all") & (sector_summary.horizon == 60)].drop(columns=["classification", "tier", "horizon"]).round(3).sort_values("mean_annual", ascending=False).to_string())
pick = ["Guns", "Softw", "Hardw", "Chips", "Banks", "Oil", "Drugs", "Aero", "defense_list", "unknown"]
print("\nSecteurs ciblés, 5 ans :")
print(sector_summary[sector_summary.sector.isin(pick) & (sector_summary.horizon == 60)].drop(columns=["horizon"]).round(3).to_string())
print("\nContrôle marché :", {k: round(v, 4) for k, v in check.items()})
print("\nContrôle French, secteurs :")
print(comparison.groupby("classification")[["correlation", "gap"]].describe().round(3).T.to_string())
print(comparison[comparison.classification == "french12"].round(3).to_string())
print(comparison[comparison.classification == "french49"].sort_values("correlation").head(8).round(3).to_string())
print("\nLong terme :")
print(pd.DataFrame(windows).round(3).to_string())
print(pd.DataFrame(long_rows).query("sector in @pick and weight=='value'").round(3).to_string())
