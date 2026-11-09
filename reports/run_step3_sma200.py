"""Étape 3 : moyenne mobile sur 200 séances, action par action, contre le buy and hold de cette action.

Règle figée avant le premier lancement, une seule variante journalisée : investi si la clôture dépasse
la moyenne des 200 dernières séances (au moins 180 valides), sinon en liquidités à 0 %. Vérifiée chaque
jour. Achats les premiers jours de bourse des mois, de janvier 2018 à fin 2024, avec les mêmes titres
achetables que la table de référence. Le rapport principal porte sur « toutes achetables ».

Depuis la racine : venv/bin/python reports/run_step3_sma200.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from per_stock import evaluate_rule
from stock_rules import sma200
from universe_data import load_universe

if __name__ == "__main__":
    evaluate_rule(sma200, load_universe(), "step3_sma200_by_stock", {"window": 200, "min_valid": 180, "check": "daily", "mode": "per_stock"})
