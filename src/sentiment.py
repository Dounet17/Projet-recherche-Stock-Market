"""Classifieurs de sentiment : FinBERT (local) et Jev (API TypeSafe)."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

FINBERT_MODEL = "ProsusAI/finbert"
JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"
# Tarif public de Jev 1.13 : 0,042 $ par million de tokens d'entrée
JEV_USD_PER_M_INPUT_TOKENS = 0.042
# Codes HTTP temporaires (dont 499 : connexion interrompue côté serveur) : on réessaie
RETRY_STATUSES = {408, 409, 425, 429, 499}


@lru_cache(maxsize=1)
def _load_finbert():
    """Charge FinBERT une seule fois par session (environ 440 Mo, téléchargé au premier appel)."""
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(FINBERT_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(FINBERT_MODEL).eval()
    return tokenizer, model


def finbert_classify(texts: list[str], batch_size: int = 32) -> pd.DataFrame:
    """Sentiment financier de chaque texte selon FinBERT : positive / negative / neutral."""
    import torch

    tokenizer, model = _load_finbert()
    labels = [model.config.id2label[i] for i in range(model.config.num_labels)]

    rows = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        t0 = time.perf_counter()
        enc = tokenizer(batch, padding=True, truncation=True, max_length=128, return_tensors="pt")
        with torch.no_grad():
            probs = model(**enc).logits.softmax(dim=-1).numpy()
        per_text = (time.perf_counter() - t0) / len(batch)
        for p in probs:
            row = {f"p_{lab}": float(v) for lab, v in zip(labels, p)}
            row["label"] = labels[int(p.argmax())]
            row["latency_s"] = per_text
            rows.append(row)
    return pd.DataFrame(rows)


def _jev_request(text: str) -> dict:
    body = {
        "model": JEV_MODEL,
        "state": {"author": "Elon Musk", "platform": "X (Twitter)", "post": text},
        "questions": {
            # Même question que FinBERT, pour comparer à armes égales
            "sentiment": {
                "type": "choice",
                "instructions": "What is the financial sentiment expressed in this post?",
                "criteria": {"positive": None, "negative": None, "neutral": None},
            },
            # Question propre au projet : l'effet attendu sur l'action Tesla
            "impact": {
                "type": "choice",
                "instructions": ("If a trader reads this post at the moment it is published, what is the "
                                 "likely short-term effect on Tesla (TSLA) stock price?"),
                "criteria": {"up": "TSLA likely to rise", "down": "TSLA likely to fall",
                             "none": "No clear effect on TSLA"},
            },
            "relevant": {"type": "noul", "instructions": "Could this post move Tesla (TSLA) stock price?"},
        },
    }
    headers = {"Authorization": f"Bearer {os.environ['TYPESAFE_API_KEY']}", "Content-Type": "application/json"}
    for attempt in range(6):
        t0 = time.perf_counter()
        try:
            resp = requests.post(JEV_URL, data=json.dumps(body), headers=headers, timeout=60)
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
            continue
        latency = time.perf_counter() - t0
        if resp.status_code in RETRY_STATUSES or resp.status_code >= 500:
            time.sleep(2 ** attempt)
            continue
        resp.raise_for_status()
        out = resp.json()
        ans = out["answers"]
        row = {f"sent_p_{k}": v for k, v in ans["sentiment"]["probabilities"].items()}
        row["sent_label"] = ans["sentiment"]["choice"]
        row.update({f"impact_p_{k}": v for k, v in ans["impact"]["probabilities"].items()})
        row["impact_label"] = ans["impact"]["choice"]
        row["relevant_p"] = ans["relevant"]["noul"]
        row["input_tokens"] = out["usage"]["input_tokens"]
        row["latency_s"] = latency
        row["model"] = out["model"]
        return row
    raise RuntimeError("API Jev injoignable après plusieurs tentatives")


def _jev_request_safe(text: str) -> dict:
    try:
        return _jev_request(text)
    except Exception as exc:  # un échec isolé ne doit pas perdre tout le lot
        return {"error": str(exc)[:200]}


def jev_classify(texts: list[str], max_workers: int = 4) -> pd.DataFrame:
    """Classe chaque texte avec Jev : sentiment (comme FinBERT), effet attendu sur TSLA, pertinence.

    Les textes en échec ont une colonne `error` remplie et des probabilités vides.
    """
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        rows = list(pool.map(_jev_request_safe, texts))
    df = pd.DataFrame(rows)
    if "error" not in df:
        df["error"] = None
    return df
