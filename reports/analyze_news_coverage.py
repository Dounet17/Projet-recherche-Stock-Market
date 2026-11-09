"""Analyse de l'échantillon de couverture des news. Aucun rendement n'est lu.

Depuis la racine : venv/bin/python reports/analyze_news_coverage.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import LAB_DIR

IN = ROOT / "data" / "news_coverage"
OUT = LAB_DIR / "news"
OUT.mkdir(parents=True, exist_ok=True)
START = pd.Timestamp("2018-01-01", tz="UTC")
END = pd.Timestamp("2025-01-01", tz="UTC")
pd.set_option("display.width", 220, "display.max_columns", 30)

sample = pd.read_parquet(IN / "sample.parquet")
articles = {}
for row in sample.itertuples():
    frame = pd.read_parquet(IN / "by_security" / f"{row.security_id.replace('/', '_')}.parquet")
    frame["created_at"] = pd.to_datetime(frame.created_at, utc=True)
    frame["updated_at"] = pd.to_datetime(frame.updated_at, utc=True)
    articles[row.security_id] = frame

sample["begin"] = sample.first_trade.clip(lower=START)
sample["stop"] = sample.last_trade.clip(upper=END)
sample["listed_years"] = ((sample.stop - sample.begin).dt.days / 365.25).clip(lower=1 / 12)
sample["articles"] = [len(articles[s]) for s in sample.security_id]
sample["per_year"] = sample.articles / sample.listed_years
sample["weekly_share"] = [articles[s].created_at.dt.to_period("W").nunique() for s in sample.security_id] / (sample.listed_years * 52.18)


def weighted_rate(frame, column):
    """Moyenne par strate, repondérée par la taille réelle de la strate dans l'univers."""
    by = frame.groupby(["tier", "alive_at_end"]).agg(value=(column, "mean"), population=("population", "first"))
    return float((by.value * by.population).sum() / by.population.sum())


sample["covered"] = sample.articles > 0
sample["regular"] = sample.per_year >= 12
strata = sample.groupby(["tier", "alive_at_end"]).agg(stocks=("security_id", "count"), population=("population", "first"), covered=("covered", "mean"), regular=("regular", "mean"), median_per_year=("per_year", "median"), mean_per_year=("per_year", "mean"), median_weeks_with_news=("weekly_share", "median")).reset_index()
order = ["top500", "501_1000", "1001_3000", "rest"]
strata["tier"] = pd.Categorical(strata.tier, order, ordered=True)
strata = strata.sort_values(["tier", "alive_at_end"])
strata.to_csv(OUT / "coverage_by_stratum.csv", index=False)
print(strata.round(3).to_string(index=False))
estimates = {column: weighted_rate(sample, column) for column in ("covered", "regular", "per_year")}
print("univers, estimations repondérées :", {k: round(v, 3) for k, v in estimates.items()})
print("par statut :", {str(k): {c: round(weighted_rate(g, c), 3) for c in ("covered", "regular", "per_year")} for k, g in sample.groupby("alive_at_end")})

everything = pd.concat([frame.assign(sampled=s) for s, frame in articles.items()], ignore_index=True)
everything["count_symbols"] = everything.symbols.fillna("").str.split(",").str.len()
print("\narticles de l'échantillon", len(everything), "uniques", everything.id.nunique())
unique = everything.drop_duplicates("id").copy()
local = unique.created_at.dt.tz_convert("America/New_York")
minutes = local.dt.hour * 60 + local.dt.minute
weekday = local.dt.weekday < 5
quality = {
    "share_one_symbol": float((unique.count_symbols == 1).mean()),
    "share_up_to_3_symbols": float((unique.count_symbols <= 3).mean()),
    "median_symbols": float(unique.count_symbols.median()),
    "share_with_summary": float(unique.summary.fillna("").str.len().gt(0).mean()),
    "share_in_session": float((weekday & (minutes >= 570) & (minutes < 960)).mean()),
    "share_pre_market": float((weekday & (minutes >= 240) & (minutes < 570)).mean()),
    "share_after_close": float((weekday & (minutes >= 960) & (minutes < 1200)).mean()),
    "share_updated_over_1h_later": float(((unique.updated_at - unique.created_at) > pd.Timedelta(hours=1)).mean()),
    "share_updated_over_1d_later": float(((unique.updated_at - unique.created_at) > pd.Timedelta(days=1)).mean()),
    "share_seconds_zero": float((unique.created_at.dt.second == 0).mean()),
    "sources": unique.source.fillna("").value_counts().head(5).to_dict(),
}
print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in quality.items()})
by_year = unique.groupby(unique.created_at.dt.year).id.count()
print("articles uniques par année dans l'échantillon :", by_year.to_dict())
unique["headline_type"] = np.select([unique.headline.fillna("").str.contains(r"(?i)\b(EPS|earnings|Q[1-4]|quarter|revenue|sales)\b"), unique.headline.fillna("").str.contains(r"(?i)\b(price target|upgrade|downgrade|initiates|maintains|raises|lowers|analyst)\b"), unique.headline.fillna("").str.contains(r"(?i)\b(shares are|moving|moves|trading (higher|lower)|mid-day|session|movers|stocks that|why )\b")], ["earnings", "analysts", "market_comment"], "other")
print("types de titres (mots-clés approximatifs) :", unique.headline_type.value_counts(normalize=True).round(3).to_dict())
print("exemples :", unique.sample(6, random_state=1).headline.str.slice(0, 80).tolist())

# Les publications de résultats ont-elles une news datée dans la journée ? 8-K rattachés seulement.
events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["security_id", "announced", "days_to_filing"])
events = events[events.security_id.isin(sample.security_id) & events.announced.notna() & (events.days_to_filing <= 150)]
events = events[(events.announced >= "2018-01-01") & (events.announced <= "2024-12-31")].copy()
hits_any, hits_before = [], []
for row in events.itertuples():
    frame = articles[row.security_id]
    day = pd.Timestamp(row.announced, tz="America/New_York")
    created = frame.created_at.dt.tz_convert("America/New_York")
    hits_any.append(bool(((created >= day - pd.Timedelta(days=1)) & (created < day + pd.Timedelta(days=2))).any()))
    hits_before.append(bool(((created >= day) & (created < day + pd.Timedelta(days=1))).any()))
events["news_around"], events["news_same_day"] = hits_any, hits_before
merged = events.merge(sample[["security_id", "tier", "alive_at_end"]], on="security_id")
print("\npublications de résultats avec une news :", merged.groupby("tier", observed=True)[["news_around", "news_same_day"]].mean().round(3).reindex(order).to_dict(), "n", len(merged))

# Volume total : semaines de tout le marché.
weeks = [pd.read_parquet(path) for path in sorted(IN.glob("market_week_*.parquet"))]
volume = pd.DataFrame([{"week": path.stem[-10:], "articles": len(frame), "with_symbol": int(frame.symbols.fillna("").str.len().gt(0).sum())} for path, frame in zip(sorted(IN.glob("market_week_*.parquet")), weeks)])
volume["year"] = volume.week.str[:4]
yearly = volume.groupby("year").articles.mean() * 52.18
total = float(yearly.sum())
print("\nvolume hebdomadaire de tout le marché par année :", volume.groupby("year").articles.mean().round(0).to_dict(), "articles estimés sur 2018-2024 :", round(total))
print("part avec au moins un symbole :", round(volume.with_symbol.sum() / volume.articles.sum(), 3), "heures de téléchargement à 50 par page et 0,31 s :", round(total / 50 * 0.31 / 3600, 1))
symbols = pd.concat(weeks).symbols.fillna("").str.split(",").explode()
symbols = symbols[symbols != ""]
known = set(pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["symbol"]).symbol)
print("symboles cités, part dans nos titres :", round(symbols.isin(known).mean(), 3), "distincts", symbols.nunique())

(OUT / "coverage_summary.json").write_text(json.dumps({"estimates": estimates, "quality": quality, "weekly_volume": volume.to_dict("records"), "estimated_total": total}, indent=1, default=str))
