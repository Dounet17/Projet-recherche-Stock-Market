"""Table d'événements datés et étude de la réaction des cours.

Vocabulaire :
- étude d'événement : mesure du rendement d'une action autour d'une date, comparé à celui du marché ;
- rendement anormal : rendement de l'action moins celui du marché (ici SPY) sur la même période ;
- surprise de résultats (SUE) : variation du bénéfice par action par rapport au même trimestre de l'année
  précédente, divisée par l'écart-type de ces variations passées. C'est une approximation : les prévisions
  des analystes, qui définissent la vraie surprise, ne sont pas disponibles.

Précaution : le champ `accepted` de `data/sec/dev_filings.parquet` est faux d'environ 4 à 5 heures dans 30 % des
8-K de résultats, malgré son suffixe Z : il ne sert jamais. Soit on prend `filing_date` et l'on achète à l'ouverture
de la séance suivante (`day_positions`), soit on prend l'heure lue dans l'en-tête SEC (`positions_after_time`).
"""

import numpy as np
import pandas as pd
from scipy import stats

ANNOUNCEMENT_MAX_DAYS = 150
RECENT_MAX_DAYS = 150
SUE_HISTORY = 8
SUE_MIN_HISTORY = 4


def match_announcements(quarters, announcements):
    """Date de publication de chaque trimestre : le dernier 8-K 2.02 jusqu'au dépôt des comptes inclus.

    Pas le premier après la fin du trimestre : TSLA dépose un 2.02 pour ses livraisons deux jours après.
    Cette règle se trompe parfois vers le tard (une transcription, comme NKE en juillet 2018) : l'entrée
    arrive alors après la réaction, ce qui est prudent, jamais avant.
    `quarters` : cik, period_end, filed. `announcements` : cik, date. Sans 8-K, `announced` reste vide.
    """
    left = quarters.reset_index(drop=True).copy()
    left["_order"] = np.arange(len(left))
    left["filed"] = pd.to_datetime(left.filed).astype("datetime64[ns]")
    right = announcements[["cik", "date"]].copy()
    right["date"] = pd.to_datetime(right.date).astype("datetime64[ns]")
    merged = pd.merge_asof(left.sort_values("filed"), right.sort_values("date"), left_on="filed", right_on="date", by="cik", direction="backward")
    begin = pd.to_datetime(merged.period_end)
    too_old = (merged.date <= begin) | (merged.date > begin + pd.Timedelta(days=ANNOUNCEMENT_MAX_DAYS))
    merged["announced"] = merged.date.mask(too_old)
    return merged.sort_values("_order").drop(columns=["_order", "date"]).reset_index(drop=True)


def day_positions(days, dates):
    """Pour un jour donné : dernière séance strictement avant, et première séance strictement après.

    L'heure du dépôt étant incertaine, on ne suppose jamais qu'il précède la clôture ou l'ouverture du jour.
    """
    days = pd.DatetimeIndex(days)
    positions = dates.searchsorted(days)
    in_range = positions < len(dates)
    trading = np.zeros(len(days), dtype=bool)
    trading[in_range] = dates[positions[in_range]] == days[in_range]
    return positions - 1, np.where(trading, positions + 1, positions)


def positions_after_time(times, dates, last_entry_second=(9 * 60 + 25) * 60):
    """Pour une heure d'acceptation SEC (New York, sans fuseau) : dernière clôture connue et première ouverture possible.

    Une acceptation au plus tard à 9 h 25 permet d'acheter à l'ouverture du jour, avec 5 minutes pour réagir.
    Sinon, l'ouverture de la séance suivante. La clôture du jour n'est connue qu'à partir de 16 h ; un jour de
    fermeture anticipée est traité comme un autre, ce qui recule seulement le point de départ de la réaction.
    """
    times = pd.DatetimeIndex(times)
    days = times.normalize()
    positions = dates.searchsorted(days)
    in_range = positions < len(dates)
    trading = np.zeros(len(times), dtype=bool)
    trading[in_range] = dates[positions[in_range]] == days[in_range]
    seconds = np.asarray(times.hour * 3600 + times.minute * 60 + times.second)
    in_time = trading & (seconds <= last_entry_second)
    after_close = trading & (seconds >= 16 * 3600)
    return np.where(after_close, positions, positions - 1), np.where(trading & ~in_time, positions + 1, positions)


def _prior_year_positions(ends):
    prior = np.full(len(ends), -1)
    for k in range(len(ends)):
        gap = (ends[k] - ends[:k]) / np.timedelta64(1, "D")
        hit = np.flatnonzero((gap >= 340) & (gap <= 390))
        if len(hit):
            prior[k] = hit[-1]
    return prior


def standardized_surprise(ends, base_eps, filed, decisions, current_known=False):
    """SUE de chaque trimestre, avec les seuls chiffres publiés avant sa date de décision.

    `base_eps` est exprimé dans une échelle d'actions commune. `filed` donne la publication de chaque
    chiffre : un terme déposé à partir de la date de décision est écarté, y compris dans l'historique.
    `current_known=True` admet le chiffre du trimestre lui-même avant son dépôt : il figure en général dans
    le communiqué, mais pas dans nos données. Le résultat est alors rétrospectif et doit être présenté ainsi.
    """
    n = len(ends)
    prior = _prior_year_positions(ends)
    changes = np.full(n, np.nan)
    available = np.full(n, np.datetime64("NaT", "ns"))
    for i in np.flatnonzero(prior >= 0):
        changes[i] = base_eps[i] - base_eps[prior[i]]
        available[i] = max(filed[i], filed[prior[i]])
    sue = np.full(n, np.nan)
    for k in np.flatnonzero(np.isfinite(changes)):
        decision = decisions[k]
        if filed[prior[k]] >= decision or (not current_known and filed[k] >= decision):
            continue
        earlier = np.arange(max(0, k - SUE_HISTORY), k)
        past = changes[earlier][np.isfinite(changes[earlier]) & (available[earlier] < decision)]
        if len(past) >= SUE_MIN_HISTORY:
            spread = past.std(ddof=1)
            if spread > 1e-9:
                sue[k] = changes[k] / spread
    return sue


def forward_multiple(marks, opens, closes, entry, cols, horizon, exit_values, last_rows):
    """Multiple de l'ouverture `entry` à l'ouverture `entry + horizon` ; disparu avant, dernier cours et sortie.

    L'horizon doit tenir dans les données pour tous, disparus compris : sinon la fin d'échantillon traiterait
    différemment les survivants et les autres.
    """
    multiple = np.full(len(entry), np.nan)
    end = entry + horizon
    inside = end < marks.shape[0]
    multiple[inside] = marks[end[inside], cols[inside]] / opens[entry[inside], cols[inside]]
    leaves = inside & np.isfinite(exit_values[cols]) & (last_rows[cols] < end)
    multiple[leaves] = closes[last_rows[cols[leaves]], cols[leaves]] / opens[entry[leaves], cols[leaves]] * (1 + exit_values[cols[leaves]])
    return multiple


def prior_quarter_groups(frame, value="sue", groups=5):
    """Groupe de 1 à `groups` selon les seuils du trimestre civil précédent : aucun chiffre futur n'entre."""
    quarter = frame.entry_date.dt.to_period("Q")
    result = pd.Series(np.nan, index=frame.index)
    probabilities = np.arange(1, groups) / groups
    for period in sorted(quarter.unique()):
        previous = frame.loc[quarter == period - 1, value].dropna()
        if len(previous) < groups * 10:
            continue
        thresholds = previous.quantile(probabilities).to_numpy()
        current = frame.loc[quarter == period, value]
        known = current.notna()
        result.loc[current.index[known]] = np.searchsorted(thresholds, current[known].to_numpy(), side="right") + 1
    return result


def quarterly_spread(frame, column, groups=5):
    """Écart entre groupe haut et bas par trimestre civil : chaque trimestre pèse autant, pas chaque action."""
    known = frame.dropna(subset=[column, "group"])
    means = known.groupby([known.entry_date.dt.to_period("Q"), "group"])[column].mean().unstack("group")
    return (means[groups] - means[1]).dropna()


def newey_west_t(values, lags=1):
    """t de la moyenne, en tenant compte de l'autocorrélation entre périodes voisines."""
    x = np.asarray(values, dtype=float)
    n = len(x)
    if n < 3:
        return float("nan")
    d = x - x.mean()
    variance = (d @ d) / n
    for lag in range(1, lags + 1):
        variance += 2 * (1 - lag / (lags + 1)) * (d[lag:] @ d[:-lag]) / n
    return float(x.mean() / np.sqrt(variance / n)) if variance > 0 else float("nan")


def two_sided_p(t_value, n):
    """p bilatérale de Student appliquée au t de Newey-West : une approximation prudente pour peu de trimestres."""
    return float(2 * stats.t.sf(abs(t_value), n - 1))


def block_bootstrap_p(values, block=2, n_boot=20_000, seed=0):
    """p bilatérale par blocs circulaires de trimestres : garde la dépendance dans le temps, jamais nulle."""
    x = np.asarray(values, dtype=float)
    centered = x - x.mean()
    n = len(x)
    rng = np.random.default_rng(seed)
    blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n, (n_boot, blocks))
    positions = (starts[:, :, None] + np.arange(block)) % n
    draws = centered[positions.reshape(n_boot, -1)[:, :n]].mean(axis=1)
    return float((1 + (np.abs(draws) >= abs(x.mean())).sum()) / (n_boot + 1))


def holm(p_values):
    """Correction de Holm pour tests multiples."""
    p = pd.Series(p_values, dtype=float).reset_index(drop=True)
    ordered = p.sort_values()
    adjusted = (ordered * (len(p) - np.arange(len(p)))).cummax().clip(upper=1.0)
    return adjusted.reindex(p.index)
