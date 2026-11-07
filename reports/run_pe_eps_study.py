"""Lancement unique de l'étude figée dans `reports/lab_2026-11/PROTOCOLE_PE_EPS.md`.

Vérifie d'abord les empreintes des données du gel. Avec `--dry-run`, s'arrête après les effectifs aux jours de décision :
aucun rendement n'est lu (seuls les filtres de prix, de liquidité et les EPS, comme ailleurs dans le projet).

Écrit `reports/lab_2026-11/pe_eps_study/summary.json` et deux lignes au journal `ledger_universe.csv` (E1 et E2 ; les
témoins sont des références, non inscrites).

Depuis la racine : venv/bin/python reports/run_pe_eps_study.py [--dry-run]
"""

import argparse
import dataclasses
import json
import sys
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
import minute_study as ms
import pe_eps_study as pe
from events import holm
from experiment import adjusted_p_values, run_variant
from universe_data import DATA_PATH, _ttm_eps, load_universe

EXPECTED = {
    "data/universe_clean/prices_dev.parquet": "c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15",
    "data/universe_clean/securities_dev.parquet": "d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161",
    "data/universe_clean/fundamentals_quarterly_dev.parquet": "99ac5e83f4dbdf6e29f3a9691a16d0475f11fa07c1e8ff1d898a074a1c187e2d",
    "data/reference/sectors.parquet": "ce9cf466b59b6f12893b199a9450feb82e63673356d6e0d575cb288d5302f85e",
    "data/calendar.parquet": "87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03",
}
OUT = ROOT / "reports" / "lab_2026-11" / "pe_eps_study"
TRIALS = {"E1": "pe_eps_growth_top100_quarterly", "E2": "pe_eps_growth_sector_ep_top100_quarterly"}


def load_sectors():
    return pd.read_parquet(ROOT / "data" / "reference" / "sectors.parquet").sector12


def from_2018(fn):
    """Aucun ordre avant la première des 28 décisions : le portefeuille part en liquidités (relecture D4)."""
    def wrapped(data):
        weights = fn(data)
        return weights.where(pd.Series(weights.index >= pd.Timestamp(lab.DEV_START), index=weights.index), axis=0)
    return wrapped


def strategies(sectors):
    return {"E1": from_2018(pe.growth_strategy), "E2": from_2018(partial(pe.combined_strategy, sectors=sectors)),
            "control_E1": from_2018(pe.control_strategy), "control_E2": from_2018(partial(pe.control_strategy, sectors=sectors))}


def study_market():
    """Univers des actions ordinaires avec l'EPS causal de cette étude, et l'EPS de `universe_data` pour comparaison."""
    market = load_universe(types=("common",))
    dates, columns = market.data.close.index, market.data.close.columns
    prices = pd.read_parquet(DATA_PATH / "prices_dev.parquet", columns=["security_id", "ts_utc", "close", "adj_close", "suspect_print"],
                             filters=[("security_id", "in", list(columns)), ("ts_utc", "<", pd.Timestamp("2025-01-01", tz="UTC"))])
    prices["day"] = prices.ts_utc.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    prices["factor"] = (prices.adj_close / prices.close).where(~prices.suspect_print)
    factor = prices.pivot_table(index="day", columns="security_id", values="factor").reindex(index=dates, columns=columns)
    quarters = pd.read_parquet(DATA_PATH / "fundamentals_quarterly_dev.parquet", columns=["cik", "period_end", "filed", "eps", "eps_suspect"])
    quarters = quarters[quarters.filed <= ms.LAST_DAY]
    ciks = market.securities.cik.reindex(columns)
    causal = pe.causal_eps_matrix(quarters, ciks, dates, factor.to_numpy())
    multiplier = pd.DataFrame(pe.share_multiplier(factor.to_numpy()), index=dates, columns=columns)
    original = pd.DataFrame(_ttm_eps(DATA_PATH, columns, ciks, dates, factor.to_numpy()), index=dates, columns=columns)
    fields = {f.name: getattr(market.data, f.name) for f in dataclasses.fields(market.data) if f.name != "eps_ttm"}
    data = pe.StudyData(**fields, eps_ttm=causal, share_multiplier=multiplier)
    return dataclasses.replace(market, data=data), original


def decision_list(index):
    days = index[pe.decision_days(index).to_numpy()]
    return days[(days >= lab.DEV_START) & (days <= lab.DEV_END)]


def counts(market, original_eps, weights):
    """Effectifs aux 28 jours de décision, sans aucun rendement (relecture D7 : définitions nommées)."""
    import run_test_b_value
    data = market.data
    allowed = pe.eligible(data)
    low_pe = (data.raw_close / data.eps_ttm.where(data.eps_ttm > 0)).where(allowed)
    test_b = run_test_b_value.low_pe(dataclasses.replace(data, eps_ttm=original_eps))
    rows, previous = [], {}
    for day in decision_list(data.close.index):
        held = {k: set(w.loc[day][w.loc[day] > 0].index) for k, w in weights.items()}
        cheap = set(low_pe.loc[day].nsmallest(pe.TOP).index)
        b = set(test_b.loc[day][test_b.loc[day] > 0].index)
        # Parmi les 1 000 plus liquides : EPS présent d'un seul côté, ou écart de plus de 1 % entre les deux constructions.
        top = data.dollar_volume.loc[day].where(data.tradable.loc[day]).rank(ascending=False, method="first") <= pe.LIQUID
        new, old = data.eps_ttm.loc[day], original_eps.loc[day]
        changed = top & ((new.isna() != old.isna()) | ((new - old).abs() > 0.01 * old.abs()))
        rows.append({"date": str(day.date()), "eligible": int(allowed.loc[day].sum()), **{f"n_{k}": len(v) for k, v in held.items()},
                     "E2_lowest_pe_100_eligible_no_floor": len(held["E2"] & cheap), "E2_test_B_identities": len(held["E2"] & b),
                     "E1_E2_overlap": len(held["E1"] & held["E2"]),
                     "eps_differs_from_universe_data_top1000": int(changed.sum()),
                     **{f"{k}_kept": len(held[k] & previous[k]) for k in ("E1", "E2") if previous}})
        previous = held
    return pd.DataFrame(rows)


def run_one(name, weights, market):
    result, benchmark, extra = run_variant(weights, market, lab.DEV_START, lab.DEV_END, n_random=20, seed=0)
    return result, benchmark, extra


def describe_portfolio(result, spy, cash):
    """Mesures d'un portefeuille, dont bêta et alpha contre SPY pour chacun (relecture D6)."""
    excess = lambda r: r - cash.reindex(r.index).fillna(0.0)
    sharpe = lambda r: float(excess(r).mean() / excess(r).std(ddof=1) * np.sqrt(lab.TRADING_DAYS))
    yearly = (1 + result.returns).groupby(result.returns.index.year).prod() - 1
    versus = lab.compare(result.returns, spy.returns)
    return {**lab.summarize(result), "sharpe_over_bil": sharpe(result.returns), "by_year": {str(k): float(v) for k, v in yearly.items()},
            "beta_vs_spy": versus["beta"], "annual_alpha_vs_spy": versus["annual_alpha"], "alpha_ci95": versus["alpha_ci95"]}


def holdings(weights):
    """Couples titre et décision réellement détenus aux 28 décisions (relecture D5 : poids nuls et vides retirés)."""
    w = weights.loc[decision_list(weights.index)]
    held = w.stack().dropna().reset_index()
    held.columns = ["date", "security_id", "weight"]
    return held[held.weight > 0]


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    ms.check_hashes(EXPECTED, ROOT)
    print("Empreintes conformes au gel.", flush=True)
    market, original_eps = study_market()
    sectors = load_sectors()
    funcs = strategies(sectors)
    weights = {k: f(market.data) for k, f in funcs.items()}
    assert weights["E1"].dropna(how="all").index.min() >= pd.Timestamp(lab.DEV_START)
    table = counts(market, original_eps, weights)
    stat = lambda c: table[c].describe()[["min", "50%", "max"]].to_dict()
    funnel = {"decision_days": len(table), "eligible": stat("eligible"), "held": {k: stat(f"n_{k}") for k in funcs},
              **{c: stat(c) for c in ("E2_lowest_pe_100_eligible_no_floor", "E2_test_B_identities", "E1_E2_overlap", "eps_differs_from_universe_data_top1000")}}
    print(json.dumps(funnel, indent=1, default=float), flush=True)
    if args.dry_run:
        print("Essai à blanc : arrêt avant toute lecture de rendement.")
        return funnel

    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("E1", "E2", "control_E1", "control_E2"):
        lab.check_no_lookahead(funcs[name], market.data)
    runs = {k: run_one(k, w, market) for k, w in weights.items()}
    spy = runs["E1"][1]
    for name in ("E1", "E2"):
        result, benchmark, extra = runs[name]
        lab.record_trial("universe", TRIALS[name], "heuristic", {"top": pe.TOP, "liquid": pe.LIQUID, "months": list(pe.DECISION_MONTHS)}, result, "SPY", benchmark.returns, extra)
    bil_open = market.benchmarks.open["BIL"]
    cash = (bil_open.shift(-1) / bil_open - 1).fillna(0.0)

    confirm = {"P1": lab.compare(runs["E1"][0].returns, runs["control_E1"][0].returns),
               "P2": lab.compare(runs["E2"][0].returns, runs["control_E2"][0].returns)}
    for name, p in zip(confirm, holm([c["excess_p_one_sided"] for c in confirm.values()])):
        confirm[name]["p_holm"] = float(p)
    secondary = {"S1_E1_vs_SPY": lab.compare(runs["E1"][0].returns, spy.returns), "S2_E2_vs_SPY": lab.compare(runs["E2"][0].returns, spy.returns),
                 "S3_control_E1_vs_SPY": lab.compare(runs["control_E1"][0].returns, spy.returns)}
    for name, p in zip(secondary, holm([s["excess_p_one_sided"] for s in secondary.values()])):
        secondary[name]["p_holm_secondary"] = float(p)
    portfolios = {k: describe_portfolio(r, spy, cash) | {"extra": e} for k, (r, b, e) in runs.items()}
    portfolios["SPY"] = describe_portfolio(spy, spy, cash)

    exits = market.exits["base"].reindex(market.data.close.columns)
    sectors_held = {}
    for name in funcs:
        held = holdings(weights[name])
        held["sector"] = held.security_id.map(sectors)
        sectors_held[name] = (held.groupby("sector").weight.sum() / held.weight.sum()).round(4).to_dict()
        portfolios[name]["share_later_delisted_pairs"] = float(held.security_id.map(exits).notna().mean())
    report = {"funnel": funnel, "confirmatory": confirm, "secondary": secondary, "portfolios": portfolios,
              "romano_wolf_ledger": adjusted_p_values("universe", spy.returns).reindex(list(TRIALS.values())).to_dict(),
              "sector_weights": sectors_held, "decision_table": table.to_dict("records")}
    (OUT / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    print(json.dumps({k: report[k] for k in ("confirmatory", "secondary")}, indent=1, default=float))
    return report


if __name__ == "__main__":
    main()
