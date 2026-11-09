"""Répète chaque stratégie depuis plusieurs dates de départ, sur 2018-2024 uniquement.

10 000 USD au départ de chaque test, durée identique dans une même comparaison.
Depuis la racine : venv/bin/python reports/run_rolling_starts.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import DEV_END, INITIAL_CAPITAL, LAB_DIR, TARGETS, buy_hold_weights, load_panel, window_final_capital
from price_lab import MEGACAPS, ROTATIONS, SINGLE_RULES, equal_weight, ml_strategy, rule_sma, single_asset, single_strategy
from social_lab import TRIALS, strategy_weights

OUT = LAB_DIR / "rolling"
OUT.mkdir(parents=True, exist_ok=True)
panel = load_panel()
LAST = pd.Timestamp(DEV_END)


def windows(years, months_step):
    """Départs réguliers depuis janvier 2018, en gardant seulement les fenêtres complètes."""
    result = []
    start = pd.Timestamp("2018-01-01")
    while start + pd.DateOffset(years=years) <= LAST + pd.Timedelta(days=1):
        result.append((start, start + pd.DateOffset(years=years) - pd.Timedelta(days=1)))
        start += pd.DateOffset(months=months_step)
    return result


def final_capitals(weights, spans):
    return np.array([window_final_capital(weights, panel, start, end) for start, end in spans])


# Toutes les stratégies : (poids, référence). Le contrôle moitié TSLA reste inclus.
strategies = {}
for symbol in TARGETS:
    for rule in SINGLE_RULES:
        strategies[f"{symbol}__{rule}"] = (single_strategy(rule, symbol)(panel), symbol)
    for kind in ("logistic", "boosting"):
        strategies[f"{symbol}__ml_{kind}"] = (ml_strategy(symbol, kind)(panel), symbol)
for name, fn in ROTATIONS.items():
    strategies[name] = (fn(panel), "SPY")
for variant in TRIALS:
    strategies[f"social__{variant}"] = (strategy_weights(panel, variant), "TSLA")
strategies["megacap_top3_vs_equal"] = (ROTATIONS["megacap_top3_mom"](panel), "megacap_equal")
references = {s: buy_hold_weights(panel, s) for s in TARGETS}
references["megacap_equal"] = equal_weight(MEGACAPS)(panel)

rows, details = [], []
for years, step in ((1, 6), (3, 6), (5, 6), (3, 1)):
    spans = windows(years, step)
    base = {name: final_capitals(w, spans) for name, w in references.items()}
    for name, (weights, reference) in strategies.items():
        caps = final_capitals(weights, spans)
        ref = base[reference]
        rows.append({
            "strategy": name, "reference": reference, "years": years, "step_months": step, "tests": len(spans),
            "median_final": np.median(caps), "mean_final": caps.mean(), "worst_final": caps.min(), "best_final": caps.max(),
            "ref_median_final": np.median(ref), "ref_mean_final": ref.mean(), "ref_worst_final": ref.min(), "ref_best_final": ref.max(),
            "share_beats_ref": (caps > ref).mean(), "share_loses_money": (caps < INITIAL_CAPITAL).mean(), "ref_share_loses_money": (ref < INITIAL_CAPITAL).mean(),
        })
        details.extend({"strategy": name, "reference": reference, "years": years, "step_months": step, "start": s.date(), "end": e.date(), "final": c, "ref_final": r} for (s, e), c, r in zip(spans, caps, ref))
    print("fait", years, step, len(spans), flush=True)

table = pd.DataFrame(rows)
table["beats_median"] = table.median_final > table.ref_median_final
table["beats_mean"] = table.mean_final > table.ref_mean_final
table.to_csv(OUT / "rolling_summary.csv", index=False)
pd.DataFrame(details).to_csv(OUT / "rolling_details.csv", index=False)

pd.set_option("display.width", 230, "display.max_columns", 30, "display.max_rows", 300)
cols = ["strategy", "reference", "tests", "median_final", "ref_median_final", "mean_final", "ref_mean_final", "worst_final", "ref_worst_final", "share_beats_ref", "share_loses_money", "ref_share_loses_money"]
focus = ["TSLA__market_filter_qqq", "TSLA__vol_target_30", "social__news_finbert_exit_5", "megacap_top3_vs_equal", "megacap_top3_mom", "social__musk_jev_exit_5", "TSLA__ml_boosting", "TSLA__sma200"]
for years, step in ((1, 6), (3, 6), (5, 6), (3, 1)):
    part = table[(table.years == years) & (table.step_months == step)]
    print(f"\n=== Durée {years} an(s), un départ tous les {step} mois, {part.tests.iloc[0]} tests ===")
    print(part[part.strategy.isin(focus)][cols].round(2).to_string(index=False))
    print("Stratégies battant leur référence en médiane :", int(part.beats_median.sum()), "/", len(part), "| en moyenne :", int(part.beats_mean.sum()))
    print(part.sort_values("share_beats_ref", ascending=False).head(10)[["strategy", "reference", "share_beats_ref", "median_final", "ref_median_final", "worst_final", "ref_worst_final"]].round(2).to_string(index=False))
