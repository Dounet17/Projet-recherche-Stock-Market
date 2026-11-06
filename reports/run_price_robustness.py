"""Teste la robustesse des deux pistes issues du développement, sur 2018-2024.

Si une piste ne tient qu'avec un réglage ou un seul titre, elle n'est pas retenue.
Depuis la racine : venv/bin/python reports/run_price_robustness.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import LAB_DIR, backtest, buy_hold_weights, check_no_lookahead, compare, load_panel, record_trial, summarize
from price_lab import MEGACAPS, equal_weight, momentum_top, rule_sma, single_asset, single_strategy

panel = load_panel()
OUT = LAB_DIR / "price"
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)
bh = {s: backtest(buy_hold_weights(panel, s), panel) for s in ("TSLA", "SPY", "QQQ")}
equal = backtest(equal_weight(MEGACAPS)(panel), panel)
rows = []


def evaluate(name, fn, reference_name, reference):
    check_no_lookahead(fn, panel)
    result = backtest(fn(panel), panel)
    record_trial("claude", f"robust_{name}", "robustness", {"variant": name, "reference": reference_name}, result, reference_name, reference.returns)
    cmp_ = compare(result.returns, reference.returns)
    stats = summarize(result)
    rows.append({"name": name, "reference": reference_name, "final": stats["final_capital"], "ref_final": summarize(reference)["final_capital"], "sharpe": stats["sharpe"], "ref_sharpe": summarize(reference)["sharpe"], "max_dd": stats["max_drawdown"], "turnover": stats["turnover_per_year"], "excess": cmp_["annual_log_excess"], "p_excess": cmp_["excess_p_one_sided"], "alpha": cmp_["annual_alpha"], "p_alpha": cmp_["alpha_p_one_sided"]})
    return result


# Piste 1 : rotation mensuelle sur les grandes capitalisations.
# La vraie question : le momentum ajoute-t-il quelque chose au simple panier des mêmes titres ?
for top in (2, 3, 4):
    for lookback in (63, 126, 252):
        evaluate(f"mega_top{top}_lb{lookback}", momentum_top(MEGACAPS, top=top, lookback=lookback), "megacap_equal", equal)
for removed in MEGACAPS:
    subset = tuple(s for s in MEGACAPS if s != removed)
    reference = backtest(equal_weight(subset)(panel), panel)
    evaluate(f"mega_top3_without_{removed}", momentum_top(subset), f"equal_without_{removed}", reference)

# Piste 2 : TSLA détenue seulement si le marché est en tendance haussière.


def market_filter(symbol, market, window):
    def strategy(p):
        return single_asset(p, symbol, rule_sma(p.close[market], window).reindex(p.dates).fillna(0.0))

    return strategy


for market in ("QQQ", "SPY"):
    for window in (100, 150, 200, 250):
        evaluate(f"tsla_filter_{market}_{window}", market_filter("TSLA", market, window), "TSLA", bh["TSLA"])

table = pd.DataFrame(rows).set_index("name")
table.to_csv(OUT / "robustness.csv")
print(table.round(3).to_string())

# Résultats année par année des candidats, face à leurs références.
candidates = {"megacap_top3_mom": momentum_top(MEGACAPS), "megacap_equal": equal_weight(MEGACAPS), "tsla_filter_qqq_200": market_filter("TSLA", "QQQ", 200), "TSLA_vol_target_30": single_strategy("vol_target_30", "TSLA")}
series = {name: backtest(fn(panel), panel).returns for name, fn in candidates.items()}
series.update({f"bh_{s}": b.returns for s, b in bh.items()})
annual = (1 + pd.DataFrame(series)).groupby(lambda d: d.year).prod() - 1
annual.round(3).to_csv(OUT / "annual_candidates.csv")
print("\nRendement par année :\n", annual.round(3).to_string())

# Sensibilité à la date de départ : le résultat dépend-il d'un point d'entrée chanceux ?
print("\nCapital final selon l'année de départ :")
out = []
for year in range(2018, 2024):
    row = {"start": year}
    for name, fn in {"megacap_top3_mom": momentum_top(MEGACAPS), "megacap_equal": equal_weight(MEGACAPS), "tsla_filter_qqq_200": market_filter("TSLA", "QQQ", 200)}.items():
        row[name] = summarize(backtest(fn(panel), panel, start=f"{year}-01-02"))["final_capital"]
    for s in ("TSLA", "QQQ", "SPY"):
        row[f"bh_{s}"] = summarize(backtest(buy_hold_weights(panel, s), panel, start=f"{year}-01-02"))["final_capital"]
    out.append(row)
print(pd.DataFrame(out).set_index("start").round(0).to_string())
