"""Étude des notes d'analystes : règles du protocole figé `PROTOCOLE_NOTES_ANALYSTES.md`.

Fonctions pures, testées sur des données inventées (`tests/test_analyst_study.py`). Le lancement est dans
`reports/run_analyst_study.py`. Les fenêtres quotidiennes, l'horloge et les statistiques viennent de `minute_study`.
"""

import re

import numpy as np
import pandas as pd

RATING_UP = re.compile(r"\bupgrades?\b", re.IGNORECASE)
RATING_DOWN = re.compile(r"\bdowngrades?\b", re.IGNORECASE)
TARGET_PREFIX = re.compile(r"^(?:UPDATE:\s*)?[\w&.,' -]{2,40}\s(?:maintains|reiterates)\b", re.IGNORECASE)
TARGET_UP = re.compile(r"\b(?:raises|boosts|increases|lifts)\b.*\bprice target\b", re.IGNORECASE)
TARGET_DOWN = re.compile(r"\b(?:lowers|cuts|reduces|trims)\b.*\bprice target\b", re.IGNORECASE)
KINDS = ("upgrade", "downgrade", "target_up", "target_down")
HOLD = 20
CAP = 0.10
EARNINGS_BEFORE, EARNINGS_AFTER = 2, 1   # séances avant et après l'entrée où une publication exclut la note
PLACEBO_SHIFT = 60
EXTREME_HIGH, EXTREME_LOW = 2.0, -0.9


def classify(headline):
    """Type d'une note d'après son titre, ou None. Règles du protocole, sans tenir compte de la casse."""
    up, down = bool(RATING_UP.search(headline)), bool(RATING_DOWN.search(headline))
    if up and not down:
        return "upgrade"
    if down and not up:
        return "downgrade"
    if TARGET_PREFIX.search(headline):
        if TARGET_UP.search(headline):
            return "target_up"
        if TARGET_DOWN.search(headline):
            return "target_down"
    return None


def select_notes(articles, links, security_types):
    """Notes d'une seule action, sans correction ni relais tardif, liées directement à une action ordinaire ou un ADR."""
    notes = articles[(articles.category == "analyst") & (articles.n_stocks == 1) & ~articles.correction & ~articles.late_relay].copy()
    notes["kind"] = notes.headline.map(classify)
    notes = notes.dropna(subset=["kind"])
    stocks = links[(links.link == "direct") & ~links.conflict]
    stocks = stocks[stocks.security_id.map(security_types).isin(["common", "adr"])]
    return notes.merge(stocks[["id", "security_id"]], on="id")


def decision_sessions(available_ns, closes_ns):
    """Première séance dont la clôture suit la note : le moteur quotidien décide à cette clôture (portefeuille A3)."""
    return np.searchsorted(closes_ns, np.asarray(available_ns), side="right")


def collapse(notes, family_kinds, key="entry_idx"):
    """Un événement par titre et par séance d'entrée si toutes les notes d'une famille vont dans le même sens,
    aucun sinon. Garde la première note (heure, puis identifiant)."""
    part = notes[notes.kind.isin(family_kinds)].sort_values(["available_at", "id"])
    direction = part.kind.map({family_kinds[0]: 1, family_kinds[1]: -1})
    agree = direction.groupby([part.security_id, part[key]]).transform(lambda d: d.abs().sum() == abs(d.sum()))
    return part[agree.astype(bool)].drop_duplicates(["security_id", key]).copy()


def near_earnings(ciks, entry_positions, earnings_positions):
    """Vrai si une publication de la même société tombe entre 2 séances avant et 1 séance après l'entrée.

    `earnings_positions` : CIK -> indices de séance triés des publications.
    """
    out = np.zeros(len(entry_positions), dtype=bool)
    for k, (cik, p) in enumerate(zip(ciks, entry_positions)):
        if pd.isna(cik) or int(cik) not in earnings_positions:
            continue
        q = earnings_positions[int(cik)]
        i = np.searchsorted(q, p - EARNINGS_BEFORE, side="left")
        out[k] = i < len(q) and q[i] <= p + EARNINGS_AFTER
    return out


def earnings_inside(ciks, entry_positions, earnings_positions, hold=HOLD):
    """Vrai si une publication tombe pendant la fenêtre tenue, de l'entrée à la séance `hold` comprise."""
    out = np.zeros(len(entry_positions), dtype=bool)
    for k, (cik, p) in enumerate(zip(ciks, entry_positions)):
        if pd.isna(cik) or int(cik) not in earnings_positions:
            continue
        q = earnings_positions[int(cik)]
        i = np.searchsorted(q, p, side="left")
        out[k] = i < len(q) and q[i] <= p + hold - 1
    return out


def holding_intervals(decision_rows, securities, hold=HOLD):
    """Intervalles [début, fin) de lignes de décision où chaque titre est tenu ; un rachat pendant la tenue la prolonge."""
    intervals = []
    current = {}
    for row, security in sorted(zip((int(r) for r in decision_rows), securities)):
        if security in current and current[security][1] >= row:
            current[security][1] = row + hold
        else:
            if security in current:
                intervals.append((security, *current[security]))
            current[security] = [row, row + hold]
    intervals.extend((security, start, end) for security, (start, end) in current.items())
    return sorted(intervals, key=lambda x: (x[1], x[0]))


def portfolio_weights(decision_rows, securities, dates, hold=HOLD, cap=CAP):
    """Poids du portefeuille A3, une ligne seulement les jours où l'ensemble des positions change.

    Une décision à la clôture de la ligne d ouvre une position exécutée à l'ouverture d + 1, retirée par la décision
    de la ligne d + hold : elle est tenue `hold` séances. Poids égaux entre positions ouvertes, au plus `cap`
    chacune, le reste en liquidités. Les autres lignes restent vides : aucun ordre, les poids dérivent avec les prix.
    """
    columns = pd.Index(sorted(set(securities)))
    changes = {}
    for security, start, end in holding_intervals(decision_rows, securities, hold):
        changes.setdefault(start, []).append((security, True))
        changes.setdefault(end, []).append((security, False))
    weights = np.full((len(dates), len(columns)), np.nan)
    active = set()
    for row in sorted(changes):
        if row >= len(dates):
            break
        for security, opening in sorted(changes[row], key=lambda x: x[1]):
            (active.add if opening else active.discard)(security)
        weights[row] = 0.0
        if active:
            weights[row, columns.get_indexer(sorted(active))] = min(1.0 / len(active), cap)
    return pd.DataFrame(weights, index=dates, columns=columns)
