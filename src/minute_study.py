"""Étude des dépêches de résultats à la minute : règles du protocole figé `PROTOCOLE_RESULTATS_MINUTE.md`.

Fonctions pures, testées sur des données inventées (`tests/test_minute_study.py`). Le lancement est dans
`reports/run_minute_study.py`. Les heures sont des entiers en nanosecondes UTC. Une barre est datée par son début :
elle couvre [t, t + 1 min). Les prix d'un titre sont multipliés par le facteur d'ajustement de leur séance, pour
comparer deux séances malgré un split ; dans une même séance, le facteur se simplifie.
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

from events import newey_west_t, two_sided_p

MINUTE = 60 * 10**9
LATENCY = 5 * MINUTE          # délai entre la dépêche et la première décision possible
OPEN_WAIT = 6 * MINUTE        # première minute de séance, puis 5 minutes de plus ; sinon pas d'entrée
LATE_START = 5 * MINUTE       # variante : entrée à 9 h 35
EXTENDED_WAIT = 60 * MINUTE   # heures étendues : barre d'entrée au plus 60 minutes après le délai
SHORT_WINDOWS = (30, 60)      # fenêtres secondaires après l'ouverture, en minutes
WIRE_POINTS = (5, 30, 60)     # décomposition : minutes après la dépêche
EXTREME_MOVE = 0.5            # variation d'une minute à l'autre à lister avant interprétation
LIQUID = 100_000_000.0        # titres retenus pour les heures étendues
LAST_DAY = pd.Timestamp("2024-12-31")


# ---------------------------------------------------------------- empreintes

def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def folder_sha256(folder, pattern="bars_*.csv.gz"):
    """Empreinte de la liste triée « empreinte  nom » des fichiers, comme `sha256sum` puis `sha256sum` du tout."""
    lines = "".join(f"{file_sha256(path)}  {path.name}\n" for path in sorted(Path(folder).glob(pattern), key=lambda p: p.name))
    return hashlib.sha256(lines.encode()).hexdigest()


def check_hashes(expected, root):
    """Arrêt si une donnée diffère de celle du gel. `expected` : chemin relatif -> empreinte."""
    for relative, wanted in expected.items():
        path = Path(root) / relative
        found = folder_sha256(path) if path.is_dir() else file_sha256(path)
        if found != wanted:
            raise RuntimeError(f"{relative} a changé depuis le gel du protocole : {found} au lieu de {wanted}")


# ---------------------------------------------------------------- horloge

def session_table(calendar, start="2017-12-01", end=LAST_DAY):
    """Séances régulières avec ouverture et clôture en ns UTC. `calendar` : date, open, close en heure de New York."""
    table = calendar[(calendar.date >= start) & (calendar.date <= end)].sort_values("date").reset_index(drop=True)
    utc = lambda column: table[column].dt.tz_localize("America/New_York").dt.tz_convert("UTC").dt.as_unit("ns").astype("int64").to_numpy()
    return pd.DataFrame({"date": table.date.dt.normalize(), "open_ns": utc("open"), "close_ns": utc("close")})


def entry_sessions(available_ns, opens_ns):
    """Indice de la première séance ouverte au moins 5 minutes après la dépêche (9 h 25 pile entre le jour même)."""
    return np.searchsorted(opens_ns, np.asarray(available_ns) + LATENCY, side="left")


def placebo_sessions(available_ns, closes_ns):
    """Indice de la dernière séance terminée au moment de la dépêche : la séance témoin, entièrement antérieure."""
    return np.searchsorted(closes_ns, np.asarray(available_ns), side="right") - 1


# ---------------------------------------------------------------- lecture d'une série de barres

class Bars:
    """Barres d'un titre triées par heure : t (ns UTC), o et c ajustés."""

    def __init__(self, t, o, c):
        order = np.argsort(t, kind="stable")
        self.t, self.o, self.c = np.asarray(t, dtype=np.int64)[order], np.asarray(o, dtype=float)[order], np.asarray(c, dtype=float)[order]

    def first_open(self, start, stop):
        """Première barre qui commence dans [start, stop) : (heure, ouverture), sinon (None, nan)."""
        i = np.searchsorted(self.t, start, side="left")
        if i < len(self.t) and self.t[i] < stop:
            return int(self.t[i]), float(self.o[i])
        return None, np.nan

    def last_close(self, start, stop):
        """Dernière barre qui commence dans [start, stop) : (heure, clôture), sinon (None, nan)."""
        j = np.searchsorted(self.t, stop, side="left") - 1
        if j >= 0 and self.t[j] >= start:
            return int(self.t[j]), float(self.c[j])
        return None, np.nan

    def known_at(self, when):
        """Dernier prix connu à l'instant `when` : clôture de la dernière barre déjà terminée."""
        return self.last_close(np.iinfo(np.int64).min, when - MINUTE + 1)[1]

    def largest_move(self, start, stop):
        inside = (self.t >= start) & (self.t < stop)
        closes = self.c[inside]
        if len(closes) < 2:
            return np.nan
        with np.errstate(divide="ignore", invalid="ignore"):
            return float(np.nanmax(np.abs(closes[1:] / closes[:-1] - 1))) if np.isfinite(closes).sum() > 1 else np.nan


EMPTY = Bars([], [], [])


def trade(stock, spy, start, stop, wait=OPEN_WAIT):
    """Achat à l'ouverture de la première barre de [start, start + wait), vente à la clôture de la dernière barre
    avant `stop`. SPY sur exactement les mêmes minutes. Renvoie (rendement, rendement SPY, heure d'entrée)."""
    entry_time, entry = stock.first_open(start, min(start + wait, stop))
    if entry_time is None:
        return np.nan, np.nan, None
    exit_time, leave = stock.last_close(entry_time, stop)
    spy_time, spy_entry = spy.first_open(entry_time, entry_time + wait)
    spy_exit = spy.last_close(spy_time, exit_time + 1)[1] if spy_time is not None else np.nan
    return leave / entry - 1, spy_exit / spy_entry - 1, entry_time


def measure_event(stock, spy, available, entry_session, placebo_session):
    """Toutes les mesures à la minute d'un événement. Les séances sont des couples (ouverture, clôture) en ns UTC."""
    opening, closing = entry_session
    out = {}
    out["h1"], out["h1_spy"], entry_time = trade(stock, spy, opening, closing)
    out["entry_delay_s"] = np.nan if entry_time is None else (entry_time - opening) / 1e9
    for minutes in SHORT_WINDOWS:
        out[f"open_{minutes}m"], out[f"open_{minutes}m_spy"], _ = trade(stock, spy, opening, opening + minutes * MINUTE)
    out["late"], out["late_spy"], _ = trade(stock, spy, opening + LATE_START, closing)
    out["placebo"], out["placebo_spy"], _ = trade(stock, spy, placebo_session[0], placebo_session[1])

    # Heures étendues : achat au moins 5 minutes après la dépêche, revente à l'ouverture régulière.
    out["extended"] = out["extended_spy"] = np.nan
    start = available + LATENCY
    if start < opening:
        buy_time, buy = stock.first_open(start, min(start + EXTENDED_WAIT, opening))
        sell_time, sell = stock.first_open(opening, opening + OPEN_WAIT)
        if buy_time is not None and sell_time is not None:
            spy_buy_time, spy_buy = spy.first_open(buy_time, buy_time + OPEN_WAIT)
            spy_sell = spy.first_open(sell_time, sell_time + OPEN_WAIT)[1]
            out["extended"] = sell / buy - 1
            out["extended_spy"] = spy_sell / spy_buy - 1 if spy_buy_time is not None else np.nan

    # Décomposition : rendements cumulés depuis la clôture de la séance témoin, titre et SPY.
    base, spy_base = stock.last_close(*placebo_session)[1], spy.last_close(*placebo_session)[1]
    points = {f"wire_{m}m": available + m * MINUTE for m in WIRE_POINTS}
    points["open_30m_mark"] = opening + 30 * MINUTE
    for name, when in points.items():
        out[f"cum_{name}"] = stock.known_at(when) / base - 1
        out[f"cum_{name}_spy"] = spy.known_at(when) / spy_base - 1
    first_time, first = stock.first_open(opening, opening + OPEN_WAIT)
    spy_first = spy.first_open(first_time, first_time + OPEN_WAIT)[1] if first_time is not None else np.nan
    out["cum_open"], out["cum_open_spy"] = first / base - 1, spy_first / spy_base - 1
    out["cum_close"] = stock.last_close(opening, closing)[1] / base - 1
    out["cum_close_spy"] = spy.last_close(opening, closing)[1] / spy_base - 1
    out["largest_minute_move"] = stock.largest_move(opening, closing)
    return out


# ---------------------------------------------------------------- cours quotidiens

def daily_window(opens, closes, entry, cols, sessions, exit_values, last_rows):
    """Multiple de l'ouverture `entry` à la clôture de la séance `entry + sessions - 1`.

    Un titre disparu avant la fin rapporte son dernier cours puis son rendement de sortie. Un trou de cotation garde le
    dernier cours connu. La fenêtre doit tenir dans les données pour tous les titres, disparus compris.
    """
    marks = pd.DataFrame(closes).ffill().to_numpy()
    multiple = np.full(len(entry), np.nan)
    end = entry + sessions - 1
    inside = end < closes.shape[0]
    start = opens[entry[inside], cols[inside]]
    multiple[inside] = marks[end[inside], cols[inside]] / start
    leaves = np.zeros(len(entry), dtype=bool)
    leaves[inside] = np.isfinite(exit_values[cols[inside]]) & (last_rows[cols[inside]] < end[inside])
    multiple[leaves] = closes[last_rows[cols[leaves]], cols[leaves]] / opens[entry[leaves], cols[leaves]] * (1 + exit_values[cols[leaves]])
    return multiple - 1


# ---------------------------------------------------------------- statistiques

def quarterly_spread(frame, value):
    """Par trimestre civil de l'entrée : moyenne des écarts positifs moins celle des négatifs."""
    known = frame.dropna(subset=[value])
    means = known.groupby([known.quarter, known.positive])[value].mean().unstack()
    if True not in means or False not in means:
        return pd.Series(dtype=float)
    return (means[True] - means[False]).dropna()


def quarterly_mean(frame, value):
    known = frame.dropna(subset=[value])
    return known.groupby(known.quarter)[value].mean()


def summarize(series):
    """Moyenne des trimestres, t de Newey-West, p bilatérale et intervalle à 95 %."""
    x = pd.Series(series, dtype=float).dropna()
    n = len(x)
    if n < 3:
        return {"quarters": n, "mean": np.nan, "t": np.nan, "p": np.nan, "ci_low": np.nan, "ci_high": np.nan}
    from scipy import stats
    t_value = newey_west_t(x.to_numpy())
    se = abs(x.mean() / t_value) if np.isfinite(t_value) and t_value != 0 else np.nan
    critical = stats.t.ppf(0.975, n - 1)
    return {"quarters": n, "mean": float(x.mean()), "t": t_value, "p": two_sided_p(t_value, n),
            "ci_low": float(x.mean() - critical * se), "ci_high": float(x.mean() + critical * se)}


def two_way_cluster(y, x, first, second):
    """Coefficient et t de `x` dans y = a + b x, erreurs regroupées dans deux dimensions (Cameron, Gelbach, Miller).

    Sans `x` (None), coefficient de la constante seule. Les dimensions sont par exemple la date et la société.
    """
    y = np.asarray(y, dtype=float)
    design = np.ones((len(y), 1)) if x is None else np.column_stack([np.ones(len(y)), np.asarray(x, dtype=float)])
    keep = np.isfinite(y)
    y, design = y[keep], design[keep]
    first, second = np.asarray(first)[keep], np.asarray(second)[keep]
    inverse = np.linalg.inv(design.T @ design)
    beta = inverse @ design.T @ y
    scores = design * (y - design @ beta)[:, None]

    def meat(groups):
        codes = pd.factorize(pd.Series(groups, dtype=object))[0]
        summed = np.zeros((codes.max() + 1, design.shape[1]))
        np.add.at(summed, codes, scores)
        return summed.T @ summed

    pairs = np.array([f"{a}|{b}" for a, b in zip(first, second)], dtype=object)
    variance = inverse @ (meat(first) + meat(second) - meat(pairs)) @ inverse
    k = design.shape[1] - 1
    return float(beta[k]), float(beta[k] / np.sqrt(variance[k, k])) if variance[k, k] > 0 else np.nan


def sign_placebo_p(frame, value, draws=1000, seed=0):
    """p bilatérale de l'écart moyen par trimestre quand les signes sont tirés au hasard au sein de chaque trimestre."""
    known = frame.dropna(subset=[value]).reset_index(drop=True)
    observed = quarterly_spread(known, value).mean()
    rng = np.random.default_rng(seed)
    quarters = [group.index.to_numpy() for _, group in known.groupby("quarter")]
    signs = known.positive.to_numpy().copy()
    exceed = 0
    for _ in range(draws):
        for rows in quarters:
            signs[rows] = rng.permutation(signs[rows])
        exceed += abs(quarterly_spread(known.assign(positive=signs), value).mean()) >= abs(observed)
    return float((1 + exceed) / (draws + 1))


def portfolio(daily_returns, sessions, capital=10_000.0):
    """Capital final quand chaque séance rapporte la moyenne de ses achats, et zéro sans achat ce jour-là."""
    by_day = pd.Series(daily_returns.to_numpy(), index=pd.DatetimeIndex(daily_returns.index)).groupby(level=0).mean()
    path = (1 + by_day.reindex(pd.DatetimeIndex(sessions)).fillna(0.0)).cumprod() * capital
    return float(path.iloc[-1]), path
