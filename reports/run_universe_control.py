"""Contrôle de bout en bout du cadre d'expérience sur le grand univers, période 2018-2024.

Témoin, pas une idée de stratégie : poids égaux sur les 500 titres les plus liquides, chaque mois.
Sert à vérifier la chaîne complète et donne un repère pour les tests suivants. L'essai est journalisé.

Depuis la racine : venv/bin/python reports/run_universe_control.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experiment import run_experiment, top_n
from universe_data import load_universe


def liquid_equal_weight(data, top=500):
    return top_n(data.dollar_volume, n=top, tradable=data.tradable)


market = load_universe()
table = run_experiment(liquid_equal_weight, market, name="control_liquid_equal_weight", family="control", n_random=10, top=[500])
pd.set_option("display.width", 200)
print(table.T.to_string())
