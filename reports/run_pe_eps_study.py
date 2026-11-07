"""Lancement unique de l'étude figée dans `reports/lab_2026-11/PROTOCOLE_PE_EPS.md`.

Vérifie d'abord les empreintes des données du gel. Avec `--dry-run`, s'arrête après les effectifs aux jours de décision :
aucun rendement n'est lu (seuls les filtres de prix, de liquidité et les EPS, comme ailleurs dans le projet).

Écrit `reports/lab_2026-11/pe_eps_study/summary.json` et deux lignes au journal `ledger_universe.csv` (E1 et E2 ; les
témoins sont des références, non inscrites).

Depuis la racine : venv/bin/python reports/run_pe_eps_study.py [--dry-run]
"""

import argparse
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
from universe_data import load_universe

EXPECTED = {
    "data/universe_clean/prices_dev.parquet": "c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15",
    "data/universe_clean/securities_dev.parquet": "d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161",
    "data/universe_clean/fundamentals_quarterly_dev.parquet": "99ac5e83f4dbdf6e29f3a9691a16d0475f11fa07c1e8ff1d898a074a1c187e2d",
    "data/reference/sectors.parquet": "ce9cf466b59b6f12893b199a9450feb82e63673356d6e0d575cb288d5302f85e",
    "data/calendar.parquet": "87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03",
}
OUT = ROOT / "reports" / "lab_2026-11" / "pe_eps_study"
TRIALS = {"E1": "pe_eps_growth_top100_quarterly", "E2": "pe_eps_growth_sector_ep_top100_quarterly"}


def strategies(sectors):
    return {"E1": pe.growth_strategy, "E2": partial(pe.combined_strategy, sectors=sectors),
            "control_E1": pe.control_strategy, "control_E2": partial(pe.control_strategy, sectors=sectors)}


def counts(market, sectors, weights):
    """Effectifs aux jours de décision, sans aucun rendement."""
    data = market.data
    days = data.close.index[pe.decision_days(data.close.index).to_numpy()]
    days = days[(days >= lab.DEV_START) & (days <= lab.DEV_END)]
    allowed = pe.eligible(data)
    low_pe = (data.raw_close / data.eps_ttm.where(data.eps_ttm > 0)).where(allowed)
    rows = []
    previous = {}
    for day in days:
        held = {k: set(w.loc[day][w.loc[day] > 0].index) for k, w in weights.items()}
        cheap = set(low_pe.loc[day].nsmallest(pe.TOP).index)
        rows.append({"date": str(day.date()), "eligible": int(allowed.loc[day].sum()), **{f"n_{k}": len(v) for k, v in held.items()},
                     "E2_low_pe_overlap": len(held["E2"] & cheap), "E1_E2_overlap": len(held["E1"] & held["E2"]),
                     **{f"{k}_kept": len(held[k] & previous[k]) for k in ("E1", "E2") if previous}})
        previous = held
    return pd.DataFrame(rows)


def run_one(name, weights, market):
    result, benchmark, extra = run_variant(weights, market, lab.DEV_START, lab.DEV_END, n_random=20, seed=0)
    return result, benchmark, extra


def describe_portfolio(result, benchmark, cash):
    excess = lambda r: r - cash.reindex(r.index).fillna(0.0)
    sharpe = lambda r: float(excess(r).mean() / excess(r).std(ddof=1) * np.sqrt(lab.TRADING_DAYS))
    yearly = (1 + result.returns).groupby(result.returns.index.year).prod() - 1
    return {**lab.summarize(result), "sharpe_over_bil": sharpe(result.returns), "by_year": {str(k): float(v) for k, v in yearly.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    ms.check_hashes(EXPECTED, ROOT)
    print("Empreintes conformes au gel.", flush=True)
    market = load_universe(types=("common",), fundamentals=True)
    sectors = pd.read_parquet(ROOT / "data" / "reference" / "sectors.parquet").sector12
    funcs = strategies(sectors)
    weights = {k: f(market.data) for k, f in funcs.items()}
    table = counts(market, sectors, weights)
    funnel = {"decision_days": len(table), "eligible": table.eligible.describe()[["min", "50%", "max"]].to_dict(),
              "held": {k: table[f"n_{k}"].describe()[["min", "50%", "max"]].to_dict() for k in funcs},
              "E2_low_pe_overlap": table.E2_low_pe_overlap.describe()[["min", "50%", "max"]].to_dict(),
              "E1_E2_overlap": table.E1_E2_overlap.describe()[["min", "50%", "max"]].to_dict()}
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
                 "S3_control_vs_SPY": lab.compare(runs["control_E1"][0].returns, spy.returns)}
    for name, p in zip(secondary, holm([s["excess_p_one_sided"] for s in secondary.values()])):
        secondary[name]["p_holm_secondary"] = float(p)
    portfolios = {k: describe_portfolio(r, b, cash) | {"extra": e} for k, (r, b, e) in runs.items()}
    portfolios["SPY"] = describe_portfolio(spy, spy, cash)

    exits = market.exits["base"].reindex(market.data.close.columns)
    sectors_held = {}
    for name in ("E1", "E2", "control_E1"):
        w = weights[name].dropna(how="all")
        held = w[w > 0].stack().reset_index()
        held.columns = ["date", "security_id", "weight"]
        held["sector"] = held.security_id.map(sectors)
        sectors_held[name] = (held.groupby("sector").weight.sum() / held.weight.sum()).round(4).to_dict()
        portfolios[name]["share_later_delisted"] = float(held.security_id.map(exits).notna().mean())
    report = {"funnel": funnel, "confirmatory": confirm, "secondary": secondary, "portfolios": portfolios,
              "romano_wolf_ledger": adjusted_p_values("universe", spy.returns).reindex(list(TRIALS.values())).to_dict(),
              "sector_weights": sectors_held, "decision_table": table.to_dict("records")}
    (OUT / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    print(json.dumps({k: report[k] for k in ("confirmatory", "secondary")}, indent=1, default=float))
    return report


if __name__ == "__main__":
    main()
