"""Couverture des news Alpaca (Benzinga) sur l'univers, 2018-2024 : mesure seule, aucun rendement n'est regardé.

Échantillon figé (graine 20261107) : 30 titres par strate, 4 tranches de liquidité x vivants ou disparus.
Plus 2 semaines de tout le marché par an, pour estimer le volume total et le temps de téléchargement.
Reprise possible : chaque titre déjà téléchargé est gardé dans data/news_coverage/.

Depuis la racine : venv/bin/python reports/measure_news_coverage.py
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from collect import ALPACA_DATA_URL, _paginate, _year_chunks

OUT = ROOT / "data" / "news_coverage"
BY_SECURITY = OUT / "by_security"
BY_SECURITY.mkdir(parents=True, exist_ok=True)
START, END = "2018-01-01", "2024-12-31"
PER_STRATUM = 30
SEED = 20261107
TIERS = ((1, 500, "top500"), (501, 1000, "501_1000"), (1001, 3000, "1001_3000"), (3001, 10**9, "rest"))
FIELDS = ["id", "created_at", "updated_at", "headline", "summary", "author", "source", "symbols"]


def fetch_news(symbol, start=START, end=END):
    """News d'un symbole. L'API filtre sur la mise à jour : on reprend ensuite la date de création."""
    begin, stop = pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=59, seconds=59)
    rows = []
    for first, last in _year_chunks(begin, stop):
        rows += _paginate(f"{ALPACA_DATA_URL}/v1beta1/news", {"symbols": symbol, "limit": 50, "sort": "asc", "start": first, "end": last}, "news")
    if not rows:
        return pd.DataFrame(columns=FIELDS)
    frame = pd.DataFrame(rows).drop_duplicates("id")
    frame["created_at"] = pd.to_datetime(frame.created_at, utc=True)
    frame["updated_at"] = pd.to_datetime(frame.updated_at, utc=True)
    frame["symbols"] = frame.symbols.apply(lambda items: ",".join(items) if isinstance(items, (list, np.ndarray)) else "")
    return frame[(frame.created_at >= begin) & (frame.created_at <= stop)].reindex(columns=FIELDS)


if __name__ != "__main__":
    raise SystemExit("à lancer comme script")

securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet")
stocks = securities[securities.security_type.isin(["common", "adr"]) & ~securities.too_short].copy()
# Présents au moins en partie sur la période. Le classement sert à stratifier, jamais de signal.
stocks = stocks[stocks.last_trade >= pd.Timestamp(START, tz="UTC")].copy()
stocks["rank"] = stocks.mean_dollar_volume.rank(ascending=False)
rng = np.random.default_rng(SEED)
chosen = []
for low, high, label in TIERS:
    for alive in (True, False):
        stratum = stocks[(stocks["rank"] >= low) & (stocks["rank"] <= high) & (stocks.alive_at_end == alive)].sort_values("security_id")
        picks = rng.choice(len(stratum), min(PER_STRATUM, len(stratum)), replace=False)
        chosen.append(stratum.iloc[np.sort(picks)].assign(tier=label, population=len(stratum)))
sample = pd.concat(chosen, ignore_index=True)
sample[["security_id", "symbol", "tier", "alive_at_end", "population", "first_trade", "last_trade", "mean_dollar_volume"]].to_parquet(OUT / "sample.parquet", index=False)
print(f"{len(sample)} titres tirés", sample.groupby(["tier", "alive_at_end"]).size().to_dict(), flush=True)

begun = time.monotonic()
for k, row in enumerate(sample.itertuples()):
    path = BY_SECURITY / f"{row.security_id.replace('/', '_')}.parquet"
    if path.exists():
        continue
    # Le symbole et ses anciens noms : une news peut citer l'ancien ou le nouveau.
    symbols = [row.symbol] + [s for s in (row.alias_symbols if row.alias_symbols is not None else []) if s != row.symbol]
    news = pd.concat([fetch_news(symbol) for symbol in symbols], ignore_index=True).drop_duplicates("id")
    # Un symbole réutilisé par une autre société : on ne garde que la vie de ce titre, marge de 5 jours.
    created = pd.to_datetime(news.created_at, utc=True)
    news = news[(created >= row.first_trade - pd.Timedelta(days=5)) & (created <= row.last_trade + pd.Timedelta(days=5))]
    news.assign(created_at=pd.to_datetime(news.created_at, utc=True), updated_at=pd.to_datetime(news.updated_at, utc=True)).astype({"id": "int64", "headline": "string", "summary": "string", "author": "string", "source": "string", "symbols": "string"}).to_parquet(path, index=False)
    if (k + 1) % 10 == 0:
        print(f"{k + 1}/{len(sample)} titres, {time.monotonic() - begun:.0f} s", flush=True)

weeks = []
for year in range(2018, 2025):
    state = np.random.default_rng(SEED + year)
    for day in state.choice(pd.bdate_range(f"{year}-01-08", f"{year}-12-15"), 2, replace=False):
        monday = pd.Timestamp(day) - pd.Timedelta(days=pd.Timestamp(day).weekday())
        begin, stop = monday.strftime("%Y-%m-%d"), (monday + pd.Timedelta(days=6)).strftime("%Y-%m-%d")
        path = OUT / f"market_week_{begin}.parquet"
        if not path.exists():
            items = _paginate(f"{ALPACA_DATA_URL}/v1beta1/news", {"start": begin, "end": stop, "limit": 50, "sort": "asc", "include_content": "false"}, "news")
            frame = pd.DataFrame(items)
            frame["symbols"] = frame.symbols.apply(lambda items: ",".join(items) if isinstance(items, list) else "")
            frame.reindex(columns=FIELDS).to_parquet(path, index=False)
        weeks.append(begin)
(OUT / "weeks.json").write_text(json.dumps(sorted(weeks)))
print("terminé", round(time.monotonic() - begun), "s", flush=True)
