"""Liste des fenêtres de prix à la minute autour des publications : séance d'avant, séance de la dépêche, séance d'après.

Ne lit aucun cours. Écrit une ligne « date<TAB>symboles » par séance, avec SPY, QQQ et DIA chaque jour comme repères.
Le symbole est celui du titre à la publication dans la table nettoyée ; les alias ne servent pas. Une séance hors des dates
de cotation du titre n'est pas demandée : le même symbole pourrait alors désigner une autre société.

Avec DEJA.tsv, une liste déjà téléchargée, seuls les couples absents sont écrits, sans les repères.

Depuis la racine : venv/bin/python reports/list_minute_windows.py SORTIE.tsv [DEJA.tsv]
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ["SPY", "QQQ", "DIA"]


def main():
    surprises = pd.read_parquet(ROOT / "data" / "news" / "earnings_surprise.parquet", columns=["event_security", "available_at"])
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["security_id", "symbol", "first_trade", "last_trade"]).set_index("security_id")
    for column in ("first_trade", "last_trade"):
        securities[column] = securities[column].dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    calendar = pd.read_parquet(ROOT / "data" / "calendar.parquet")
    column = next(c for c in calendar.columns if "date" in c.lower())
    sessions = pd.DatetimeIndex(sorted(pd.to_datetime(calendar[column]).dt.tz_localize(None).dt.normalize().unique()))
    sessions = sessions[(sessions >= "2017-12-01") & (sessions <= "2024-12-31")]
    days = surprises.available_at.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    position = sessions.searchsorted(days)
    symbols = surprises.event_security.map(securities.symbol).to_numpy()
    listed = surprises.event_security.map(securities.first_trade).to_numpy()
    last = surprises.event_security.map(securities.last_trade).to_numpy()
    rows = []
    for shift in (-1, 0, 1):
        at = np.clip(position + shift, 0, len(sessions) - 1)
        rows.append(pd.DataFrame({"date": sessions[at], "symbol": symbols, "listed": listed, "last": last}))
    table = pd.concat(rows)
    outside = (table.date < table.listed) | (table.date > table["last"])
    print(f"{outside.sum():,} séances hors cotation écartées, sur {len(table):,}")
    table = table[~outside][["date", "symbol"]].drop_duplicates()
    assert table.date.max() <= pd.Timestamp("2024-12-31")
    references = set(REFERENCES)
    if len(sys.argv) > 2:
        known = {(pd.Timestamp(day), symbol) for day, names in (line.rstrip("\n").split("\t") for line in open(sys.argv[2]) if line.strip()) for symbol in names.split(",")}
        table = table[[pair not in known for pair in zip(table.date, table.symbol)]]
        references = set()
    grouped = table.groupby("date").symbol.agg(lambda s: ",".join(sorted(set(s) | references)))
    grouped.to_csv(sys.argv[1], sep="\t", header=False, date_format="%Y-%m-%d")
    print(f"{len(table):,} couples titre et séance, {len(grouped):,} séances, {table.symbol.nunique():,} symboles, {grouped.index.min():%Y-%m-%d} à {grouped.index.max():%Y-%m-%d}")


if __name__ == "__main__":
    main()
