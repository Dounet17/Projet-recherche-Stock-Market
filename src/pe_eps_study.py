"""Stratégies EPS et P/E : règles du protocole figé `PROTOCOLE_PE_EPS.md`.

Une stratégie reçoit `market.data` (connu à chaque clôture) et renvoie des poids par date, une ligne vide signifiant
« aucun ordre » : le moteur du laboratoire exécute à l'ouverture suivante. Fonctions testées sur données inventées
(`tests/test_pe_eps_study.py`) ; lancement dans `reports/run_pe_eps_study.py`.
"""

from dataclasses import dataclass, fields

import numpy as np
import pandas as pd

from universe_data import Universe

DECISION_MONTHS = (3, 6, 9, 12)
LIQUID = 1000
TOP = 100
YEAR = 252
SAME_QUARTER_DAYS = 20            # deux fins de période plus proches que cela sont deux versions d'un même trimestre
GAP_DAYS = (70, 110)              # écart entre deux trimestres consécutifs, comme `universe_data`
MAX_AGE_DAYS = 200                # expiration après la fin du dernier trimestre, comme `universe_data`
SPLIT_BAND = (1 / 1.2, 1.2)       # un saut du facteur d'ajustement hors de cette bande est un fractionnement


@dataclass(frozen=True)
class StudyData(Universe):
    """Données d'une stratégie, avec le multiplicateur de fractionnement ; la troncature garde ce type."""

    share_multiplier: pd.DataFrame = None

    def truncate(self, last_date):
        last_date = pd.Timestamp(last_date)
        return StudyData(**{f.name: None if getattr(self, f.name) is None else getattr(self, f.name).loc[:last_date] for f in fields(self)})


# ---------------------------------------------------------------- EPS causal (relecture D1 à D3)

def share_multiplier(factor):
    """Nombre d'actions d'aujourd'hui pour une action du début de la série, d'après les seuls fractionnements.

    `factor` : cours ajusté / cours brut, par séance et par titre. Un fractionnement fait sauter ce facteur d'un
    coup (2 pour un fractionnement en deux) ; un dividende le fait glisser de quelques pour cent. Seuls les sauts
    hors de `SPLIT_BAND` sont gardés : les dividendes ne touchent plus l'EPS. Seul le rapport entre deux dates
    passées sert, si bien qu'une normalisation future du facteur se simplifie.
    """
    filled = pd.DataFrame(factor).ffill().to_numpy(dtype=float)
    ratio = np.ones_like(filled)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio[1:] = filled[1:] / filled[:-1]
    jump = np.where((ratio < SPLIT_BAND[0]) | (ratio > SPLIT_BAND[1]), ratio, 1.0)
    jump[~np.isfinite(jump)] = 1.0
    return np.cumprod(jump, axis=0)


def causal_ttm_column(quarters, dates, multiplier):
    """EPS sur 12 mois d'un titre, par séance, à l'échelle d'actions de cette séance, sans aucun dépôt futur.

    À chaque date de dépôt f, seuls les trimestres déposés au plus tard à f comptent. Il faut quatre trimestres
    consécutifs, le dernier étant le plus récent connu. Chaque EPS trimestriel est ramené en actions d'origine à sa
    date de dépôt, puis à l'échelle de chaque séance par le multiplicateur de fractionnement. Valeur utilisable à
    partir de la séance qui suit f, jusqu'au dépôt suivant ou à l'expiration de 200 jours après la fin de période.
    """
    out = np.full(len(dates), np.nan)
    quarters = quarters.sort_values(["filed", "period_end"], kind="stable")
    ends, filed, eps = quarters.period_end.to_numpy(), quarters.filed.to_numpy(), quarters.eps.to_numpy()
    units_at_filing = eps * multiplier[np.minimum(np.searchsorted(dates, filed), len(dates) - 1)]
    segments = []
    for f in np.unique(filed):
        n = np.searchsorted(filed, f, side="right")          # dépôts connus à f : un préfixe, triés par dépôt
        order = np.lexsort((filed[:n], ends[:n]))            # par fin de période, puis par dépôt
        e = ends[:n][order]
        group = np.r_[0, np.cumsum(np.diff(e) / np.timedelta64(1, "D") > SAME_QUARTER_DAYS)]
        last_of_group = np.r_[group[1:] != group[:-1], True]  # version la plus récente de chaque trimestre
        picked = order[last_of_group]
        begin = np.searchsorted(dates, f, side="right")
        value = np.nan
        if len(picked) >= 4:
            last = picked[-4:]
            gaps = np.diff(ends[last]) / np.timedelta64(1, "D")
            if ((gaps >= GAP_DAYS[0]) & (gaps <= GAP_DAYS[1])).all():
                expiry = np.searchsorted(dates, ends[last[-1]] + np.timedelta64(MAX_AGE_DAYS, "D"), side="right")
                value = (units_at_filing[last].sum(), expiry)
        segments.append((begin, value))
    for k, (begin, value) in enumerate(segments):
        end = segments[k + 1][0] if k + 1 < len(segments) else len(dates)
        if isinstance(value, tuple):
            units, expiry = value
            stop = min(end, expiry)
            if stop > begin:
                out[begin:stop] = units / multiplier[begin:stop]
    return out


def causal_eps_matrix(quarters, ciks, dates, factor):
    """Matrice dates x titres de l'EPS sur 12 mois causal. `ciks` : titre -> CIK ; `factor` : matrice cours ajusté /
    cours brut alignée sur `dates` et sur l'ordre de `ciks`."""
    quarters = quarters[~quarters.eps_suspect] if "eps_suspect" in quarters else quarters
    by_cik = dict(tuple(quarters.groupby("cik", sort=False)))
    multiplier = share_multiplier(factor)
    values = np.asarray(dates.to_numpy() if hasattr(dates, "to_numpy") else dates).astype(quarters.filed.dtype)
    out = np.full((len(values), len(ciks)), np.nan)
    for j, cik in enumerate(ciks.to_numpy()):
        if pd.notna(cik) and int(cik) in by_cik:
            out[:, j] = causal_ttm_column(by_cik[int(cik)], values, multiplier[:, j])
    return pd.DataFrame(out, index=dates, columns=ciks.index)


def decision_days(index):
    """Vrai au premier jour de bourse de mars, juin, septembre et décembre. Ne dépend d'aucune date future."""
    months = index.month
    first = np.r_[True, months[1:] != months[:-1]]
    return pd.Series(first & np.isin(months, DECISION_MONTHS), index=index)


def growth(data):
    """Croissance de l'EPS sur 12 mois : EPS connu ce jour contre EPS connu 252 séances plus tôt.

    `data.eps_ttm` est déjà à l'échelle d'actions de chaque séance ; l'EPS d'il y a un an est remis à l'échelle
    d'aujourd'hui quand `data` porte `share_multiplier` (relecture D2), sinon comparé tel quel.
    """
    past = data.eps_ttm.shift(YEAR)
    multiplier = getattr(data, "share_multiplier", None)
    if multiplier is not None:
        past = past * multiplier.shift(YEAR) / multiplier
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
