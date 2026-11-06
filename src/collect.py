"""Téléchargement des données : tweets d'Elon Musk, prix et news via l'API Alpaca."""

import io
import os
import re
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from timeutils import tweet_time_utc

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
load_dotenv(ROOT / ".env")

ALPACA_DATA_URL = "https://data.alpaca.markets"
ALPACA_TRADING_URL = "https://paper-api.alpaca.markets"
# Plan gratuit : 200 appels par minute
ALPACA_MIN_INTERVAL_S = 0.31

MUSK_KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/dadalyndell/elon-musk-tweets-2010-to-2025-march"
MUSK_HF_URL = "https://huggingface.co/datasets/fdaudens/musk-tweets/resolve/main/elonmusk_data_fixed%20-%20Sheet1.csv"

_last_call = 0.0
_throttle = threading.Lock()


def _alpaca_get(url: str, params: dict) -> dict:
    """GET sur l'API Alpaca avec respect du quota et nouvelles tentatives (erreur 429, 5xx ou réseau)."""
    global _last_call
    headers = {
        "APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
    }
    for attempt in range(8):
        with _throttle:
            wait = ALPACA_MIN_INTERVAL_S - (time.monotonic() - _last_call)
            if wait > 0:
                time.sleep(wait)
            _last_call = time.monotonic()
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=120)
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"API Alpaca injoignable après plusieurs tentatives : {url}")


def _year_chunks(start: str, end: str) -> list[tuple[str, str]]:
    """Découpe [start, end] en tranches d'un an, téléchargées en parallèle."""
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    chunks = []
    while start_ts <= end_ts:
        stop = min(pd.Timestamp(year=start_ts.year + 1, month=1, day=1, tz=start_ts.tz) - pd.Timedelta(seconds=1), end_ts)
        chunks.append((start_ts.strftime("%Y-%m-%dT%H:%M:%SZ"), stop.strftime("%Y-%m-%dT%H:%M:%SZ")))
        start_ts = stop + pd.Timedelta(seconds=1)
    return chunks


def _paginate(url: str, params: dict, key: str, symbol: str | None = None) -> list:
    params = dict(params)
    rows = []
    while True:
        page = _alpaca_get(url, params)
        items = page.get(key) or ({} if symbol else [])
        rows += items.get(symbol, []) if symbol else items
        token = page.get("next_page_token")
        if not token:
            return rows
        params["page_token"] = token


def alpaca_bars(symbol: str, timeframe: str, start: str, end: str, adjustment: str = "split") -> pd.DataFrame:
    """Barres OHLCV d'un symbole (flux SIP consolidé, heures étendues comprises pour l'intraday).

    Chaque barre est étiquetée par son début, en UTC.
    adjustment : 'raw' (prix bruts), 'split' (corrigés des divisions d'actions) ou 'all' (+ dividendes).
    """
    params = {"symbols": symbol, "timeframe": timeframe, "adjustment": adjustment, "feed": "sip", "limit": 10000}
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = pool.map(lambda c: _paginate(f"{ALPACA_DATA_URL}/v2/stocks/bars",
                                             {**params, "start": c[0], "end": c[1]}, "bars", symbol),
                         _year_chunks(start, end))
        rows = [row for part in parts for row in part]
    df = pd.DataFrame(rows).rename(columns={"t": "ts_utc", "o": "open", "h": "high", "l": "low",
                                            "c": "close", "v": "volume", "n": "trade_count", "vw": "vwap"})
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df.insert(0, "symbol", symbol)
    return df.sort_values("ts_utc").reset_index(drop=True)


def alpaca_news(symbol: str, start: str, end: str) -> pd.DataFrame:
    """News Benzinga d'un symbole (titre et résumé, sans le texte complet), horodatées à la seconde."""
    params = {"symbols": symbol, "limit": 50, "sort": "asc"}
    with ThreadPoolExecutor(max_workers=4) as pool:
        parts = pool.map(lambda c: _paginate(f"{ALPACA_DATA_URL}/v1beta1/news",
                                             {**params, "start": c[0], "end": c[1]}, "news"),
                         _year_chunks(start, end))
        rows = [row for part in parts for row in part]
    df = pd.DataFrame(rows).drop_duplicates("id")
    # L'API filtre sur la date de mise à jour : on retire les news créées hors de la période
    created = pd.to_datetime(df["created_at"], utc=True)
    df = df[(created >= pd.Timestamp(start)) & (created <= pd.Timestamp(end))][["id", "created_at", "updated_at", "headline", "summary", "author", "source", "url", "symbols"]]
    for col in ["created_at", "updated_at"]:
        df[col] = pd.to_datetime(df[col], utc=True)
    df["symbols"] = df["symbols"].apply(lambda s: ",".join(s))
    return df


def alpaca_calendar(start: str, end: str) -> pd.DataFrame:
    """Jours de bourse américains avec heures d'ouverture et de fermeture (heure de New York)."""
    headers = {
        "APCA-API-KEY-ID": os.environ["ALPACA_API_KEY"],
        "APCA-API-SECRET-KEY": os.environ["ALPACA_SECRET_KEY"],
    }
    resp = requests.get(f"{ALPACA_TRADING_URL}/v2/calendar", params={"start": start, "end": end},
                        headers=headers, timeout=60)
    resp.raise_for_status()
    cal = pd.DataFrame(resp.json())
    cal["date"] = pd.to_datetime(cal["date"])
    cal["open"] = pd.to_datetime(cal["date"].dt.strftime("%Y-%m-%d") + " " + cal["open"])
    cal["close"] = pd.to_datetime(cal["date"].dt.strftime("%Y-%m-%d") + " " + cal["close"])
    return cal[["date", "open", "close"]]


def _download(url: str, dest: Path) -> Path:
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        resp = requests.get(url, timeout=300)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
    return dest


def musk_posts() -> pd.DataFrame:
    """Posts d'Elon Musk : fusion de Kaggle dadalyndell et Hugging Face fdaudens sur l'identifiant.

    dadalyndell sert de base (types de posts fiables) ; fdaudens ajoute surtout des réponses de
    2023-2024 et des retweets que dadalyndell n'a pas. L'heure est toujours recalculée depuis l'identifiant.
    """
    zip_path = _download(MUSK_KAGGLE_URL, RAW / "musk_dadalyndell.zip")
    with zipfile.ZipFile(zip_path) as z:
        dada = pd.read_csv(io.BytesIO(z.read("all_musk_posts.csv")), dtype=str)
    dada = dada[dada["id"].str.fullmatch(r"\d+", na=False)]
    is_true = lambda col: dada[col].str.lower().eq("true")
    dada_kind = pd.Series("original", index=dada.index)
    dada_kind[is_true("isQuote")] = "quote"
    dada_kind[is_true("isReply")] = "reply"
    dada_kind[is_true("isRetweet") | dada["fullText"].str.startswith("RT @", na=False)] = "retweet"
    a = pd.DataFrame({
        "id": dada["id"],
        "text": dada["fullText"],
        "kind": dada_kind,
        "reply_to": dada["inReplyToUsername"],
        "like_count": pd.to_numeric(dada["likeCount"], errors="coerce"),
        "retweet_count": pd.to_numeric(dada["retweetCount"], errors="coerce"),
    })

    hf = pd.read_csv(_download(MUSK_HF_URL, RAW / "musk_fdaudens.csv"), dtype=str)
    hf["id"] = hf["Permalink"].str.extract(r"status/(\d+)", expand=False)
    hf = hf.dropna(subset=["id"]).drop_duplicates("id")
    hf_kind = hf["MessageType"].map({"X Reply": "reply", "X Repost": "retweet"}).fillna("original")
    b = pd.DataFrame({
        "id": hf["id"],
        "text": hf["Message"].str.strip(),
        "kind": hf_kind,
        "reply_to": None,
        "like_count": pd.to_numeric(hf["Favorites"], errors="coerce"),
        "retweet_count": pd.to_numeric(hf["Retweets"], errors="coerce"),
    })

    a["source"] = "dadalyndell"
    b["source"] = "fdaudens"
    b = b[~b["id"].isin(a["id"])]
    posts = pd.concat([a, b], ignore_index=True).drop_duplicates("id")
    posts["id"] = posts["id"].astype("int64")
    posts.insert(1, "ts_utc", tweet_time_utc(posts["id"]))
    return posts.sort_values("ts_utc").reset_index(drop=True)


# Mots-clés d'un post qui parle de Tesla (filtre simple, à compléter par un classifieur)
TESLA_PATTERN = re.compile(
    r"\b(?:tesla|tsla|model ?[3ysx]|cybertruck|gigafactory|giga ?(?:texas|berlin|shanghai|nevada)|"
    r"autopilot|fsd|full self.driving|robotaxi|cybercab|powerwall|megapack|supercharger)\b",
    re.IGNORECASE,
)


def mentions_tesla(text: pd.Series) -> pd.Series:
    return text.fillna("").str.contains(TESLA_PATTERN)
