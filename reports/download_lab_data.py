"""Télécharge les barres quotidiennes ajustées (splits et dividendes) de l'univers du laboratoire.

Depuis la racine : venv/bin/python reports/download_lab_data.py
"""

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from collect import alpaca_bars
from lab import DATA_FILE, HOLDOUT_END, UNIVERSE, WARMUP_START


def fetch(symbol):
    return alpaca_bars(symbol, "1Day", WARMUP_START + "T00:00:00Z", HOLDOUT_END + "T23:59:59Z", adjustment="all")


with ThreadPoolExecutor(8) as pool:
    frames = list(pool.map(fetch, UNIVERSE))
frame = pd.concat(frames, ignore_index=True)
frame["date"] = frame.ts_utc.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
frame = frame.drop(columns="ts_utc")
if frame.duplicated(["symbol", "date"]).any():
    raise ValueError("Doublons symbole/date")
frame.to_parquet(DATA_FILE, index=False)
print(frame.groupby("symbol").date.agg(["size", "min", "max"]).to_string())
