"""Retrouve les symboles disparus absents de la liste d'Alpaca, par énumération.

Essaie tous les symboles de 1 à 4 lettres, plus ceux de 5 lettres cités dans nos news.
Un symbole inconnu ne renvoie simplement aucune barre. Écrit dans data/universe/extra_*,
avec la même séparation entre développement et validation, et reprend après coupure.
Depuis la racine : venv/bin/python reports/download_universe_extra.py
"""

import itertools
import re
import string
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import collect
from lab import DEV_END, HOLDOUT_END, HOLDOUT_START, WARMUP_START

collect.ALPACA_MIN_INTERVAL_S = 0.45
OUT = ROOT / "data" / "universe"
BATCH = 100
known = set(pd.read_parquet(OUT / "assets.parquet").symbol)
candidates = {"".join(c) for size in range(1, 5) for c in itertools.product(string.ascii_uppercase, repeat=size)}
news = pd.read_parquet(ROOT / "data" / "tsla_news.parquet", columns=["symbols"])
candidates |= {s for value in news.symbols for s in value.split(",") if re.fullmatch(r"[A-Z]{5}", s)}
symbols = sorted(candidates - known)
batches = [symbols[i:i + BATCH] for i in range(0, len(symbols), BATCH)]
print("Candidats :", len(symbols), "| lots :", len(batches), flush=True)


def fetch(batch, adjustment, start, end):
    params = {"symbols": ",".join(batch), "timeframe": "1Day", "adjustment": adjustment, "feed": "sip", "limit": 10000, "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z", "sort": "asc"}
    rows = []
    try:
        while True:
            page = collect._alpaca_get(f"{collect.ALPACA_DATA_URL}/v2/stocks/bars", params)
            for symbol, bars in (page.get("bars") or {}).items():
                rows.extend({"symbol": symbol, "ts_utc": b["t"], "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"], "volume": b["v"], "vwap": b.get("vw")} for b in bars)
            token = page.get("next_page_token")
            if not token:
                return rows
            params["page_token"] = token
    except requests.exceptions.HTTPError as error:
        if len(batch) == 1:
            print("Symbole ignoré :", batch[0], error.response.status_code, flush=True)
            return []
        middle = len(batch) // 2
        return fetch(batch[:middle], adjustment, start, end) + fetch(batch[middle:], adjustment, start, end)


for label, adjustment, start, end in (("extra_dev_all", "all", WARMUP_START, DEV_END), ("extra_dev_raw", "raw", WARMUP_START, DEV_END), ("extra_holdout_all", "all", HOLDOUT_START, HOLDOUT_END), ("extra_holdout_raw", "raw", HOLDOUT_START, HOLDOUT_END)):
    folder = OUT / label
    folder.mkdir(exist_ok=True)
    found = set()
    if label != "extra_dev_all":
        # Les passes suivantes ne redemandent que les symboles qui existent vraiment.
        existing = sorted({s for p in (OUT / "extra_dev_all").glob("*.parquet") for s in pd.read_parquet(p, columns=["symbol"]).symbol.unique()})
        batches = [existing[i:i + BATCH] for i in range(0, len(existing), BATCH)]
        print(label, "symboles réels :", len(existing), "| lots :", len(batches), flush=True)
    for number, batch in enumerate(batches):
        path = folder / f"batch_{number:05d}.parquet"
        if path.exists():
            continue
        frame = pd.DataFrame(fetch(batch, adjustment, start, end), columns=["symbol", "ts_utc", "open", "high", "low", "close", "volume", "vwap"])
        frame["ts_utc"] = pd.to_datetime(frame.ts_utc, utc=True)
        temporary = path.with_suffix(".tmp")
        frame.to_parquet(temporary, index=False)
        temporary.rename(path)
        found |= set(frame.symbol)
        if number % 20 == 0:
            print(label, number + 1, "/", len(batches), "| symboles trouvés dans cette reprise", len(found), flush=True)
    print(label, "terminé", len(found), flush=True)
print("Terminé", flush=True)
