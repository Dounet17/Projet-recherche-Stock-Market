"""Complète le dataset quotidien : opérations sur titres, symboles absents, prix bruts manquants.

Cause établie le 06/11/2026 : par défaut l'API suit les changements de symbole (paramètre
asof). Si l'ancien et le nouveau symbole sont dans le même lot, elle ne renvoie que le
nouveau, sans erreur : FRC et BBBY ne sont pas perdus, ils sont déjà là sous FRCB et BBBYQ.
Avec asof="-", chaque symbole répond pour lui-même, ce qui permet de tout réénumérer.

Étapes (chacune reprend après coupure) :
1. opérations sur titres jusqu'au 31/12/2024 -> data/universe/corporate_actions_dev.parquet ;
2. liste complète des actifs Alpaca, OTC compris -> data/universe/assets_all.parquet ;
3. symboles absents du panel -> data/universe/gap_dev_{all,raw}/ et gap_holdout_{all,raw}/ ;
4. prix bruts et séries "split" des cas particuliers -> data/universe/fix_dev/.

Les dossiers *holdout_* sont écrits mais jamais lus ici.
Depuis la racine : venv/bin/python reports/download_universe_gaps.py
"""

import itertools
import os
import string
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import collect
from lab import DEV_END, HOLDOUT_END, HOLDOUT_START, WARMUP_START

collect.ALPACA_MIN_INTERVAL_S = 0.31
OUT = ROOT / "data" / "universe"
BATCH = 100
COLUMNS = ["symbol", "ts_utc", "open", "high", "low", "close", "volume", "vwap"]
ACTION_TYPES = "forward_split,reverse_split,unit_split,stock_dividend,spin_off,cash_merger,stock_merger,stock_and_cash_merger,redemption,name_change,worthless_removal"
HEADERS = {"APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"], "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"]}


def download_actions():
    path = OUT / "corporate_actions_dev.parquet"
    if path.exists():
        return pd.read_parquet(path)
    rows = []
    # Fenêtres trimestrielles : la coupure à DEV_END exclut toute information de la validation.
    for start in pd.date_range(WARMUP_START, DEV_END, freq="QS"):
        end = min(start + pd.offsets.QuarterEnd(0), pd.Timestamp(DEV_END))
        params = {"start": start.date().isoformat(), "end": end.date().isoformat(), "types": ACTION_TYPES, "limit": 1000}
        while True:
            page = collect._alpaca_get(f"{collect.ALPACA_DATA_URL}/v1/corporate-actions", params)
            for kind, items in (page.get("corporate_actions") or {}).items():
                rows.extend({"kind": kind, **item} for item in items)
            token = page.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
        print("actions", start.date(), "| total", len(rows), flush=True)
    actions = pd.DataFrame(rows)
    actions.to_parquet(path, index=False)
    print(actions.kind.value_counts().to_string(), flush=True)
    return actions


def download_assets():
    path = OUT / "assets_all.parquet"
    if path.exists():
        return pd.read_parquet(path)
    frames = []
    for status in ("active", "inactive"):
        response = requests.get(f"{collect.ALPACA_TRADING_URL}/v2/assets", headers=HEADERS, params={"status": status, "asset_class": "us_equity"}, timeout=120)
        response.raise_for_status()
        frames.append(pd.DataFrame(response.json()))
    assets = pd.concat(frames, ignore_index=True)[["symbol", "name", "exchange", "status", "class"]]
    assets = assets.sort_values("status").drop_duplicates("symbol")
    assets.to_parquet(path, index=False)
    return assets


def fetch(symbols, adjustment, start, end, asof="-"):
    params = {"symbols": ",".join(symbols), "timeframe": "1Day", "adjustment": adjustment, "feed": "sip", "limit": 10000, "start": f"{start}T00:00:00Z", "end": f"{end}T23:59:59Z", "sort": "asc", "asof": asof}
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
        return fetch(symbols[:middle], adjustment, start, end, asof) + fetch(symbols[middle:], adjustment, start, end, asof)


def save_batches(folder_name, symbols, adjustment, start, end):
    folder = OUT / folder_name
    folder.mkdir(exist_ok=True)
    batches = [symbols[i:i + BATCH] for i in range(0, len(symbols), BATCH)]
    for number, batch in enumerate(batches):
        path = folder / f"batch_{number:05d}.parquet"
        if path.exists():
            continue
        frame = pd.DataFrame(fetch(batch, adjustment, start, end), columns=COLUMNS)
        frame["ts_utc"] = pd.to_datetime(frame.ts_utc, utc=True)
        temporary = path.with_suffix(".tmp")
        # Les lots vides ne sont gardés que comme marque de reprise.
        frame.to_parquet(temporary, index=False)
        temporary.rename(path)
        if number % 100 == 0:
            print(folder_name, number + 1, "/", len(batches), flush=True)
    print(folder_name, "terminé", flush=True)


def panel_symbols():
    return {s for folder in ("dev_all", "extra_dev_all") for p in (OUT / folder).glob("*.parquet") for s in pd.read_parquet(p, columns=["symbol"]).symbol.unique()}


actions = download_actions()
assets = download_assets()
panel = panel_symbols()
extra_list = ROOT / "reports" / "lab_2026-11" / "sec_ticker_candidates.txt"
candidates = {"".join(c) for size in range(1, 5) for c in itertools.product(string.ascii_uppercase, repeat=size)}
candidates |= set(assets.symbol.dropna())
for column in ("old_symbol", "new_symbol", "acquiree_symbol", "acquirer_symbol", "symbol"):
    if column in actions:
        candidates |= set(actions[column].dropna())
tried = {s for p in (OUT / "gap_dev_raw").glob("*.parquet") for s in pd.read_parquet(p, columns=["symbol"]).symbol.unique()}
if extra_list.exists():
    # Seconde passe : uniquement les symboles lus dans les fichiers XBRL de la SEC.
    candidates = set(extra_list.read_text().split()) - {"".join(c) for size in range(1, 5) for c in itertools.product(string.ascii_uppercase, repeat=size)}
symbols = sorted(s for s in candidates - panel - tried if s)
print("Candidats absents du panel :", len(symbols), flush=True)
# Passe rapide en brut : un seul type d'ajustement suffit à savoir qui existe.
tag = "" if not extra_list.exists() else "_sec"
save_batches(f"gap{tag}_dev_raw", symbols, "raw", WARMUP_START, DEV_END)
found = sorted({s for p in (OUT / f"gap{tag}_dev_raw").glob("*.parquet") for s in pd.read_parquet(p, columns=["symbol"]).symbol.unique()})
print("Symboles trouvés :", len(found), flush=True)
save_batches(f"gap{tag}_dev_all", found, "all", WARMUP_START, DEV_END)
save_batches(f"gap{tag}_holdout_raw", found, "raw", HOLDOUT_START, HOLDOUT_END)
save_batches(f"gap{tag}_holdout_all", found, "all", HOLDOUT_START, HOLDOUT_END)

# Dix symboles n'ont aucun prix brut, trois ont un ajustement "all" invalide.
fix = OUT / "fix_dev"
fix.mkdir(exist_ok=True)
for name, wanted, adjustment, asof in (("raw_default", ["ABB", "ACAB", "CHAA", "DCRN", "EFHT", "ETE", "HCLP", "IMH", "NH", "OBNK"], "raw", None), ("raw_noasof", ["ABB", "ACAB", "CHAA", "DCRN", "EFHT", "ETE", "HCLP", "IMH", "NH", "OBNK"], "raw", "-"), ("split_invalid", ["JTAI", "LDTC", "PRSR"], "split", None)):
    path = fix / f"{name}.parquet"
    if path.exists():
        continue
    rows = []
    for symbol in wanted:
        params = {"symbols": symbol, "timeframe": "1Day", "adjustment": adjustment, "feed": "sip", "limit": 10000, "start": f"{WARMUP_START}T00:00:00Z", "end": f"{DEV_END}T23:59:59Z", "sort": "asc"}
        if asof:
            params["asof"] = asof
        while True:
            page = collect._alpaca_get(f"{collect.ALPACA_DATA_URL}/v2/stocks/bars", params)
            for key, bars in (page.get("bars") or {}).items():
                rows.extend({"symbol": key, "ts_utc": b["t"], "open": b["o"], "high": b["h"], "low": b["l"], "close": b["c"], "volume": b["v"], "vwap": b.get("vw")} for b in bars)
            token = page.get("next_page_token")
            if not token:
                params.pop("page_token", None)
                break
            params["page_token"] = token
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame["ts_utc"] = pd.to_datetime(frame.ts_utc, utc=True)
    frame.to_parquet(path, index=False)
    print(name, frame.groupby("symbol").size().to_dict(), flush=True)
print("Terminé", flush=True)
