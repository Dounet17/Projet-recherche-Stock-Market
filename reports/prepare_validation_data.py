"""Prépare les news et le calendrier 2025-2026 sans lire aucun cours de validation.

Écrit dans data/lab_holdout/ : news fusionnées, calendrier étendu, scores FinBERT.
Même modèle et mêmes réglages que le développement (titres seuls, 128 tokens, CPU).
Depuis la racine : venv/bin/python reports/prepare_validation_data.py
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from collect import alpaca_calendar, alpaca_news
from lab import HOLDOUT_END, HOLDOUT_START
from social_lab import NEWS_CACHE, headline_hash

DATA = ROOT / "data"
OUT = DATA / "lab_holdout"
OUT.mkdir(exist_ok=True)
for name in ("musk_posts", "finbert_musk_tesla", "jev_musk_tesla", "tsla_earnings"):
    link = OUT / f"{name}.parquet"
    if not link.exists():
        link.symlink_to(DATA / f"{name}.parquet")

raw_path = OUT / "news_2025_2026.parquet"
if raw_path.exists():
    fresh = pd.read_parquet(raw_path)
else:
    fresh = alpaca_news("TSLA", f"{HOLDOUT_START}T00:00:00Z", f"{HOLDOUT_END}T23:59:59Z")
    fresh.to_parquet(raw_path, index=False)
old = pd.read_parquet(DATA / "tsla_news.parquet")
news = pd.concat([old, fresh], ignore_index=True).sort_values("updated_at").drop_duplicates("id", keep="last")
news.to_parquet(OUT / "tsla_news.parquet", index=False)
print("News : développement", len(old), "| nouvelles", len(fresh), "| total", len(news), flush=True)

extra = alpaca_calendar("2018-01-01", HOLDOUT_END)
base = pd.read_parquet(DATA / "calendar.parquet")
if list(extra.columns) != list(base.columns):
    raise ValueError(f"Calendrier inattendu : {list(extra.columns)}")
merged = pd.concat([base, extra], ignore_index=True).drop_duplicates("date", keep="first").sort_values("date")
merged.to_parquet(OUT / "calendar.parquet", index=False)
print("Calendrier :", len(merged), "jours, dernier", merged.date.max(), flush=True)

news["headline_hash"] = news.headline.map(headline_hash)
news["available_at"] = news[["created_at", "updated_at"]].max(axis=1)
cache_path = OUT / "news_finbert.parquet"
cache = pd.read_parquet(cache_path if cache_path.exists() else NEWS_CACHE)
keys = pd.MultiIndex.from_frame(cache[["id", "headline_hash"]])
todo = news.loc[~pd.MultiIndex.from_frame(news[["id", "headline_hash"]]).isin(keys)]
print("Titres à classer :", len(todo), flush=True)

if len(todo):
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    torch.set_num_threads(6)
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert", local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert", local_files_only=True).to("cpu").eval()
    labels = {label.lower(): int(i) for i, label in model.config.id2label.items()}
    pending = []
    for first in range(0, len(todo), 32):
        batch = todo.iloc[first:first + 32]
        encoded = tokenizer(batch.headline.fillna("").tolist(), padding=True, truncation=True, max_length=128, return_tensors="pt")
        with torch.inference_mode():
            probabilities = model(**encoded).logits.softmax(dim=-1).numpy()
        rows = batch[["id", "headline_hash", "available_at"]].copy()
        rows["p_positive"] = probabilities[:, labels["positive"]]
        rows["p_negative"] = probabilities[:, labels["negative"]]
        rows["p_neutral"] = probabilities[:, labels["neutral"]]
        pending.append(rows)
        if len(pending) == 64 or first + 32 >= len(todo):
            cache = pd.concat([cache, *pending], ignore_index=True)
            cache.to_parquet(cache_path, index=False)
            pending = []
            print("classés", first + len(batch), "/", len(todo), flush=True)
else:
    cache.to_parquet(cache_path, index=False)
print("Terminé", flush=True)
