"""Test A : momentum 12 mois sur le grand univers, 2018-2024.

Paramètres figés avant le premier lancement, une seule variante : chaque premier jour de bourse du
mois, poids égaux sur les 50 titres achetables dont le cours a le plus monté sur 252 séances.

Depuis la racine : venv/bin/python reports/run_test_a_momentum.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experiment import run_experiment, top_n
from universe_data import load_universe


def momentum(data, lookback=252, top=50):
    score = data.close.pct_change(lookback, fill_method=None)
    return top_n(score, n=top, tradable=data.tradable)


if __name__ == "__main__":
    market = load_universe()
    table = run_experiment(momentum, market, name="test_a_momentum", family="heuristic", n_random=20, lookback=[252], top=[50])
    pd.set_option("display.width", 200)
    print(table.T.to_string())
