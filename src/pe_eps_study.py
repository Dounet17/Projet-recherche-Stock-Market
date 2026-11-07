"""Stratégies EPS et P/E : règles du protocole figé `PROTOCOLE_PE_EPS.md`.

Une stratégie reçoit `market.data` (connu à chaque clôture) et renvoie des poids par date, une ligne vide signifiant
« aucun ordre » : le moteur du laboratoire exécute à l'ouverture suivante. Fonctions testées sur données inventées
(`tests/test_pe_eps_study.py`) ; lancement dans `reports/run_pe_eps_study.py`.
"""

import numpy as np
import pandas as pd

DECISION_MONTHS = (3, 6, 9, 12)
LIQUID = 1000
TOP = 100
YEAR = 252


def decision_days(index):
    """Vrai au premier jour de bourse de mars, juin, septembre et décembre. Ne dépend d'aucune date future."""
    months = index.month
    first = np.r_[True, months[1:] != months[:-1]]
    return pd.Series(first & np.isin(months, DECISION_MONTHS), index=index)


def growth(data):
    """Croissance de l'EPS sur 12 mois : EPS connu ce jour contre EPS connu 252 séances plus tôt."""
    past = data.eps_ttm.shift(YEAR)
    return (data.eps_ttm - past) / past.abs()


def eligible(data, liquid=LIQUID):
    """Achetable, parmi les `liquid` plus liquides du jour, EPS positif ce jour et 252 séances plus tôt."""
    rank = data.dollar_volume.where(data.tradable).rank(axis=1, ascending=False, method="first")
    eps, past = data.eps_ttm, data.eps_ttm.shift(YEAR)
    return data.tradable & (rank <= liquid) & (eps > 0) & (past > 0)


def _equal_weights(chosen, index):
    """Poids égaux sur les titres choisis aux jours de décision ; lignes vides les autres jours."""
    days = decision_days(index)
    weights = chosen.astype(float).div(chosen.sum(axis=1).clip(lower=1), axis=0)
    return weights.where(days, axis=0)


def _top(score, allowed, n):
    """Les `n` meilleurs scores parmi les titres permis, départage stable par ordre des colonnes."""
    return score.where(allowed).rank(axis=1, ascending=False, method="first") <= n


def growth_strategy(data, top=TOP, liquid=LIQUID):
    """E1 : les `top` plus fortes croissances de l'EPS dans l'univers éligible."""
    allowed = eligible(data, liquid)
    return _equal_weights(_top(growth(data), allowed, top), data.close.index)


def combined_score(data, sectors, liquid=LIQUID):
    """E2 : moyenne du rang en centiles de la croissance (univers éligible à secteur connu) et de celui de l'E/P
    au sein de son secteur. Calculé seulement aux jours de décision ; vide ailleurs."""
    days = decision_days(data.close.index)
    sector = pd.Series(sectors).reindex(data.close.columns)
    known = sector.notna() & (sector != "unknown")
    allowed = eligible(data, liquid) & known.to_numpy()
    g = growth(data)
    ep = data.eps_ttm / data.raw_close
    score = pd.DataFrame(np.nan, index=data.close.index, columns=data.close.columns)
    for day in data.close.index[days.to_numpy()]:
        mask = allowed.loc[day]
        if not mask.any():
            continue
        g_rank = g.loc[day].where(mask).rank(pct=True)
        ep_rank = ep.loc[day].where(mask).groupby(sector).rank(pct=True)
        score.loc[day] = (g_rank + ep_rank) / 2
    return score, allowed


def combined_strategy(data, sectors, top=TOP, liquid=LIQUID):
    """E2 : les `top` meilleurs scores combinés."""
    score, allowed = combined_score(data, sectors, liquid)
    return _equal_weights(_top(score, allowed, top), data.close.index)


def control_strategy(data, sectors=None, liquid=LIQUID):
    """Témoin : tout l'univers éligible à poids égaux (à secteur connu si `sectors` est donné)."""
    allowed = eligible(data, liquid)
    if sectors is not None:
        sector = pd.Series(sectors).reindex(data.close.columns)
        allowed = allowed & (sector.notna() & (sector != "unknown")).to_numpy()
    return _equal_weights(allowed, data.close.index)
