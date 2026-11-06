"""Étape 4 : retour à la moyenne, action par action, contre le buy and hold de cette action.

Définitions reprises de `price_lab` et figées avant le premier lancement sur ce dataset, une variante
journalisée par règle : bandes de Bollinger (20 séances, 2 écarts-types) et RSI sur 2 séances (entrée
sous 10, sortie au-dessus de 70). Mêmes actions et mêmes dates que la moyenne mobile de l'étape 3.

Depuis la racine : venv/bin/python reports/run_step4_mean_reversion.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pandas as pd

import lab
from experiment import adjusted_p_values
from per_stock import OUT, evaluate_rule
from stock_rules import bollinger_reversion, rsi2_reversion
from universe_data import load_universe

if __name__ == "__main__":
    market = load_universe()
    evaluate_rule(bollinger_reversion, market, "step4_bollinger_by_stock", {"window": 20, "width": 2.0, "check": "daily", "mode": "per_stock", "history_min_valid": 180})
    evaluate_rule(rsi2_reversion, market, "step4_rsi2_by_stock", {"rsi_window": 2, "enter_below": 10, "leave_above": 70, "trend_window": 200, "check": "daily", "mode": "per_stock", "history_min_valid": 180})
    start = pd.Timestamp("2018-01-02")
    spy = lab.backtest(lab.buy_hold_weights(market.benchmarks, "SPY"), market.benchmarks, start=start, exits=pd.Series(dtype=float))
    adjusted = adjusted_p_values("universe", spy.returns)
    adjusted.round(4).to_csv(OUT / "adjusted_p_all_trials.csv")
    print(adjusted.round(4).to_string())
