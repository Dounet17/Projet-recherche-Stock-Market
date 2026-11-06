"""Télécharge les barres quotidiennes des titres américains cotés, vivants et disparus.

Écrit par lots dans data/universe/ et reprend là où il s'est arrêté. La période de
validation va dans des dossiers holdout_* séparés, à ne pas lire pendant la recherche.
Warrants, droits et unités sont exclus, ainsi que l'OTC (hors bourse réglementée).
Depuis la racine : venv/bin/python reports/download_universe.py
"""

import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import collect
from lab import DEV_END, HOLDOUT_END, HOLDOUT_START, WARMUP_START

# Plus prudent que le quota, car d'autres téléchargements peuvent tourner en parallèle.
collect.ALPACA_MIN_INTERVAL_S = 0.45
OUT = ROOT / "data" / "universe"
OUT.mkdir(parents=True, exist_ok=True)
EXCHANGES = {"NYSE", "NASDAQ", "ARCA", "AMEX", "BATS"}
EXCLUDED_NAME = re.compile(r"\b(warrants?|rights?|units?)\b", re.IGNORECASE)
BATCH = 100


def load_assets():
    path = OUT / "assets.parquet"
    if path.exists():
        return pd.read_parquet(path)
    headers = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}
    frames = []
    for status in ("active", "inactive"):
        response = requests.get(f"{collect.ALPACA_TRADING_URL}/v2/assets", headers=headers, params={"status": status, "asset_class": "us_equity"}, timeout=120)
        response.raise_for_status()
        frames.append(pd.DataFrame(response.json()))
    assets = pd.concat(frames, ignore_index=True)
    assets = assets[assets.exchange.isin(EXCHANGES) & ~assets.name.fillna("").str.contains(EXCLUDED_NAME)]
    assets = assets[["id", "symbol", "name", "exchange", "status", "tradable", "fractionable"]].drop_duplicates("symbol").sort_values("symbol")
    assets.to_parquet(path, index=False)
    return assets


def fetch(symbols, adjustment, start, end):
    """Toutes les pages d'un lot. Un lot refusé est coupé en deux pour isoler le symbole fautif."""
    params = {"symbols": ",".join(symbols), "timeframe": "1Day", "adjustment": adjustment, "feed": "sip", "limit": 10000, "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z", "sort": "asc"}
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
        if len(symbols) == 1:
            print("Symbole ignoré :", symbols[0], error.response.status_code, flush=True)
            return []
        middle = len(symbols) // 2
        return fetch(symbols[:middle], adjustment, start, end) + fetch(symbols[middle:], adjustment, start, end)


assets = load_assets()
symbols = assets.symbol.tolist()
batches = [symbols[i:i + BATCH] for i in range(0, len(symbols), BATCH)]
print("Titres :", len(symbols), "| lots :", len(batches), "|", assets.status.value_counts().to_dict(), flush=True)
began = time.time()
for label, adjustment, start, end in (("dev_all", "all", WARMUP_START, DEV_END), ("dev_raw", "raw", WARMUP_START, DEV_END), ("holdout_all", "all", HOLDOUT_START, HOLDOUT_END), ("holdout_raw", "raw", HOLDOUT_START, HOLDOUT_END)):
    folder = OUT / label
    folder.mkdir(exist_ok=True)
    total = 0
    for number, batch in enumerate(batches):
        path = folder / f"batch_{number:05d}.parquet"
        if path.exists():
            continue
        frame = pd.DataFrame(fetch(batch, adjustment, start, end), columns=["symbol", "ts_utc", "open", "high", "low", "close", "volume", "vwap"])
        frame["ts_utc"] = pd.to_datetime(frame.ts_utc, utc=True)
        temporary = path.with_suffix(".tmp")
        frame.to_parquet(temporary, index=False)
        temporary.rename(path)
        total += len(frame)
        if number % 10 == 0:
            print(label, number + 1, "/", len(batches), "| lignes de cette reprise", total, "|", round((time.time() - began) / 60, 1), "min", flush=True)
    print(label, "terminé", flush=True)
print("Téléchargement terminé", flush=True)
