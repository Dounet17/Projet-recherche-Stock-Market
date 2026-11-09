"""Évalue toutes les stratégies de prix sur la période de développement 2018-2024.

Depuis la racine : venv/bin/python reports/run_price_lab.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import DEV_START, DEV_END, LAB_DIR, TARGETS, backtest, buy_hold_weights, check_no_lookahead, compare, load_panel, record_trial, summarize
from price_lab import ROTATIONS, SINGLE_RULES, ml_strategy, single_strategy

OUT = LAB_DIR / "price"
OUT.mkdir(parents=True, exist_ok=True)
panel = load_panel()
bench = {s: backtest(buy_hold_weights(panel, s), panel) for s in TARGETS}
bench10 = {s: backtest(buy_hold_weights(panel, s), panel, cost_bps=10) for s in TARGETS}
cash = panel.open["BIL"].shift(-1) / panel.open["BIL"] - 1
SPLIT = pd.Timestamp("2022-01-01")

trials = []
for symbol in TARGETS:
    for rule in SINGLE_RULES:
        trials.append((f"{symbol}__{rule}", "single_rule", {"symbol": symbol, "rule": rule}, single_strategy(rule, symbol), symbol))
    for kind in ("logistic", "boosting"):
        trials.append((f"{symbol}__ml_{kind}", "ml", {"symbol": symbol, "model": kind, "horizon": 5}, ml_strategy(symbol, kind), symbol))
for name, fn in ROTATIONS.items():
    trials.append((name, "rotation", {"rule": name}, fn, "SPY"))

for rule in SINGLE_RULES:
    check_no_lookahead(single_strategy(rule, "TSLA"), panel)
for name, fn in ROTATIONS.items():
    check_no_lookahead(fn, panel)
for kind in ("logistic", "boosting"):
    check_no_lookahead(ml_strategy("TSLA", kind), panel)
print("Contrôle anti-fuite réussi pour toutes les familles", flush=True)

rows = []
for name, family, params, fn, reference in trials:
    weights = fn(panel)
    result = backtest(weights, panel)
    base = bench[reference].returns
    row = record_trial("claude", name, family, params, result, reference, base)
    high_cost = backtest(weights, panel, cost_bps=10)
    with_cash = backtest(weights, panel, cash_returns=cash)
    row["final_capital_cost10"] = summarize(high_cost)["final_capital"]
    row["benchmark_final_cost10"] = summarize(bench10[reference])["final_capital"]
    row["final_capital_bil"] = summarize(with_cash)["final_capital"]
    row["benchmark_final"] = summarize(bench[reference])["final_capital"]
    row["benchmark_sharpe"] = summarize(bench[reference])["sharpe"]
    row["benchmark_max_drawdown"] = summarize(bench[reference])["max_drawdown"]
    # Stabilité : le résultat tient-il sur les deux moitiés, ou une seule ?
    for label, mask in (("h1", result.returns.index < SPLIT), ("h2", result.returns.index >= SPLIT)):
        row[f"excess_{label}"] = float((np.log1p(result.returns[mask]) - np.log1p(base[mask])).sum())
    if family == "rotation":
        qqq = compare(result.returns, bench["QQQ"].returns, n_boot=1000)
        row["excess_vs_qqq"] = qqq["annual_log_excess"]
        row["sharpe_diff_vs_qqq"] = qqq["sharpe_difference"]
        row["alpha_vs_qqq"] = qqq["annual_alpha"]
    rows.append(row)
    print(name, round(row["final_capital"]), round(row["sharpe"], 2), flush=True)

table = pd.DataFrame(rows).set_index("name")
table["beats_final"] = table.final_capital > table.benchmark_final
table["beats_sharpe"] = table.sharpe > table.benchmark_sharpe
table["beats_cost10"] = table.final_capital_cost10 > table.benchmark_final_cost10
table["stable_excess"] = (table.excess_h1 > 0) & (table.excess_h2 > 0)
table.to_csv(OUT / "results.csv")

pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 300)
cols = ["benchmark", "final_capital", "benchmark_final", "sharpe", "benchmark_sharpe", "max_drawdown", "beta", "annual_alpha", "excess_h1", "excess_h2"]
print("\nBuy and hold :", json.dumps({s: {k: round(v, 3) for k, v in summarize(bench[s]).items() if k in ("final_capital", "sharpe", "max_drawdown")} for s in TARGETS}))
print("\nEssais :", len(table), "Battent le capital final :", int(table.beats_final.sum()), "Battent le Sharpe :", int(table.beats_sharpe.sum()), "Stables :", int(table.stable_excess.sum()))
print("\nPar famille de règle, part des actifs où le buy and hold est battu :")
single = table[table.family != "rotation"].copy()
single["rule"] = [n.split("__")[1] for n in single.index]
print(single.groupby("rule")[["beats_final", "beats_sharpe", "beats_cost10", "stable_excess"]].mean().round(2).to_string())
print("\nMeilleurs écarts de capital, p corrigées dans reports/run_family_correction.py :")
print(table.sort_values("annual_log_excess", ascending=False).head(15)[cols].round(3).to_string())
print("\nRotations :")
print(table[table.family == "rotation"][cols + ["excess_vs_qqq", "sharpe_diff_vs_qqq", "alpha_vs_qqq", "final_capital_bil"]].round(3).to_string())
print("\nTSLA :")
print(table[table.index.str.startswith("TSLA__")][cols + ["final_capital_cost10", "final_capital_bil"]].round(3).to_string())
