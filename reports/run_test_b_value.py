"""Test B : valeur par le P/E sur le grand univers, 2018-2024.

Paramètres figés avant le premier calcul de performance, une seule variante : chaque premier jour
de bourse du mois, parmi les 1 000 actions ordinaires achetables les plus liquides, poids égaux sur
les 50 plus bas P/E. Le P/E est le cours brut divisé par le bénéfice par action des 12 derniers mois,
connu le lendemain de sa publication. Le bénéfice doit être positif et le P/E d'au moins 3 : en
dessous, le contrôle des données montre surtout des plus-values ponctuelles et des erreurs.

Depuis la racine : venv/bin/python reports/run_test_b_value.py
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from experiment import run_experiment, top_n
from universe_data import load_universe


def low_pe(data, liquid=1000, top=50, min_pe=3.0):
    pe = data.raw_close / data.eps_ttm.where(data.eps_ttm > 0)
    in_universe = data.dollar_volume.where(data.tradable).rank(axis=1, ascending=False) <= liquid
    return top_n(-pe.where(pe >= min_pe), n=top, tradable=in_universe)


if __name__ == "__main__":
    market = load_universe(types=("common",), fundamentals=True)
    table = run_experiment(low_pe, market, name="test_b_low_pe", family="heuristic", n_random=20, liquid=[1000], top=[50], min_pe=[3.0])
    pd.set_option("display.width", 200)
    print(table.T.to_string())
