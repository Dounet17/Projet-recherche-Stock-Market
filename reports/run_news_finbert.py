"""FinBERT sur les titres de news retenus par le tri, sur GPU. Aucun rendement n'est lu. Reprise possible.

Version figée du modèle, antérieure à l'ajout de poids sur Hugging Face en octobre 2026. Chaque titre différent n'est
classé qu'une fois. Les résumés ne servent pas : il n'y en a aucun en 2018-2019.

Depuis la racine :
HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_news_finbert.py
"""

import json
import sys
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

ROOT = Path(__file__).resolve().parents[1]
MODEL = "ProsusAI/finbert"
REVISION = "4556d13015211d73dccd3fdd39d39232506f3e43"  # 23/05/2023
WEIGHTS_SHA256 = "e15a7b5738df7f17553399b6d94c6e2ff69c89245d066e8e5d183f5803a554e3"
OUT = ROOT / "data" / "news" / "finbert"
BATCH = 512
PART = 100_000
MAX_LENGTH = 64


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    OUT.mkdir(parents=True, exist_ok=True)
    articles = pd.read_parquet(ROOT / "data" / "news" / "news_articles.parquet", columns=["headline", "category", "n_stocks"])
    keep = ~articles.category.isin(["market_commentary", "evergreen"]) & (articles.n_stocks >= 1) & articles.headline.str.strip().ne("")
    headlines = articles.loc[keep, "headline"].drop_duplicates()
    done = set()
    parts = sorted(OUT.glob("part_*.parquet"))
    manifest = OUT / "manifest.json"
    settings = {"model": MODEL, "revision": REVISION, "weights_sha256": WEIGHTS_SHA256, "max_length": MAX_LENGTH, "text": "headline"}
    if manifest.exists() and json.loads(manifest.read_text()) != settings:
        sys.exit("Ces parties viennent d'autres réglages : refus de les mélanger.")
    if parts and not manifest.exists():
        sys.exit("Parties sans manifeste : provenance inconnue, refus de les réutiliser.")
    manifest.write_text(json.dumps(settings, indent=1))
    for path in parts:
        done |= set(pd.read_parquet(path, columns=["headline"]).headline)
    # Du plus court au plus long : des lots de longueur voisine vont plus vite.
    todo = headlines[~headlines.isin(done)]
    todo = todo.iloc[todo.str.len().argsort(kind="stable").to_numpy()].tolist()
    if limit:
        todo = todo[:limit]
    print(f"{len(headlines):,} titres, déjà faits {len(done):,}, à faire {len(todo):,}", flush=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL, revision=REVISION, use_safetensors=False).eval().to(device)
    labels = [model.config.id2label[i] for i in range(model.config.num_labels)]
    print("appareil", device, "étiquettes", labels, flush=True)

    begun = time.monotonic()
    # Premier numéro libre : un numéro existant ne doit jamais être écrasé, même si une partie manque.
    number = 1 + max((int(path.stem.split("_")[1]) for path in parts), default=-1)
    for start in range(0, len(todo), PART):
        chunk = todo[start:start + PART]
        probabilities = []
        for first in range(0, len(chunk), BATCH):
            encoded = tokenizer(chunk[first:first + BATCH], padding=True, truncation=True, max_length=MAX_LENGTH, return_tensors="pt").to(device)
            with torch.inference_mode():
                probabilities.append(model(**encoded).logits.softmax(dim=-1).cpu())
        values = torch.cat(probabilities).numpy()
        frame = pd.DataFrame(values, columns=[f"p_{label}" for label in labels]).astype("float32")
        frame.insert(0, "headline", chunk)
        frame.to_parquet(OUT / f"part_{number:04d}.parquet", index=False)
        number += 1
        elapsed = time.monotonic() - begun
        print(f"{start + len(chunk):,}/{len(todo):,}, {elapsed:.0f} s, {(start + len(chunk)) / elapsed:.0f} titres/s", flush=True)
    print("TERMINÉ", flush=True)


if __name__ == "__main__":
    main()
