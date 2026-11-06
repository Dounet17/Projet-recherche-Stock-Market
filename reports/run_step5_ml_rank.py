"""Étape 5 : modèle de classement des actions, famille adaptative, 2018-2024.

Figé avant le premier lancement, une seule variante journalisée : chaque premier jour de bourse du mois,
poids égaux sur les 50 titres achetables les mieux classés, exécution à l'ouverture suivante. Modèle et
indicateurs dans `src/ml_rank.py`, réentraînement chaque 1er janvier, aucun réglage des paramètres.

Depuis la racine : venv/bin/python reports/run_step5_ml_rank.py
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import lab
from experiment import REFERENCE, run_experiment
from ml_rank import MODEL_PARAMS, diagnose, make_strategy
from universe_data import load_universe

NAME = "step5_ml_rank"
OUT = lab.LAB_DIR / "ml"

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    market = load_universe()
    data = market.data
    last_dates = data.close.apply(lambda column: column.last_valid_index())
    keep = {}
    strategy = make_strategy(market.exits["base"], last_dates, keep=keep)
    table = run_experiment(strategy, market, name=NAME, family="adaptive", n_random=20, top=[50])
    diagnostics = diagnose(keep["scores"], data, market.exits["base"], last_dates)
    diagnostics.monthly.to_csv(OUT / f"{NAME}_monthly.csv")
    diagnostics.deciles.rename("mean_monthly_return").to_csv(OUT / f"{NAME}_deciles.csv")
    monthly = diagnostics.monthly
    # Détail non versionné, pour auditer le modèle sans le réentraîner.
    (lab.ROOT / "data" / "ml").mkdir(parents=True, exist_ok=True)
    keep["scores"].dropna(how="all").to_parquet(lab.ROOT / "data" / "ml" / f"{NAME}_scores.parquet")
    pd.set_option("display.width", 200)
    print(table.T.to_string())
    print("paramètres", MODEL_PARAMS)
    print("mois", len(monthly), "corrélation de rang moyenne", round(monthly.rank_correlation.mean(), 4), "t", round(monthly.rank_correlation.mean() / monthly.rank_correlation.std(ddof=1) * np.sqrt(len(monthly)), 2), "part positive", round((monthly.rank_correlation > 0).mean(), 3))
    print("décile 10 moins décile 1, par mois", round(monthly.top_minus_bottom.mean(), 4), "t", round(monthly.top_minus_bottom.mean() / monthly.top_minus_bottom.std(ddof=1) * np.sqrt(len(monthly)), 2))
    excess = monthly.top50_mean - monthly.universe_mean
    print("50 premiers moins univers, par mois, avant frais", round(excess.mean(), 4), "t", round(excess.mean() / excess.std(ddof=1) * np.sqrt(len(monthly)), 2))
    print("déciles", diagnostics.deciles.round(4).to_dict())
    print("corrélation par année", monthly.rank_correlation.groupby(monthly.index.year).mean().round(4).to_dict())
    print("50 premiers moins univers par année", excess.groupby(excess.index.year).mean().round(4).to_dict())
    returns = pd.read_parquet(lab.LAB_DIR / "trials" / "universe" / f"{table.index[0]}.parquet")["return"]
    print("par année", ((1 + returns).groupby(returns.index.year).prod() - 1).round(3).to_dict())
    benchmark = lab.backtest(lab.buy_hold_weights(market.benchmarks, REFERENCE), market.benchmarks, exits=pd.Series(dtype=float)).returns
    print("SPY", ((1 + benchmark).groupby(benchmark.index.year).prod() - 1).round(3).to_dict())
