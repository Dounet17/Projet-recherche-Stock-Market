"""Importe le CSV produit sur le Pi dans `data/events/eight_k_times/`, au format de `download_8k_times.py`.

Ne garde que les dépôts absents des lots existants, et écarte les échecs, qu'une relance pourra retenter.
Relancer ce script sur le même fichier n'ajoute donc rien.

    scp 192.168.1.22:stock-market-news/eight_k_times/results.csv /tmp/results.csv
    venv/bin/python reports/import_8k_times_pi.py /tmp/results.csv
"""

import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "events" / "eight_k_times"
COLUMNS = ["accession", "accepted_new_york", "status"]

results = pd.read_csv(sys.argv[1], names=COLUMNS, dtype=str, keep_default_na=False)
failed = results[results.status == "failed"].accession.nunique()
results = results[results.status != "failed"].drop_duplicates("accession")
paths = sorted(OUT.glob("batch_*.parquet"))
done = set()
for path in paths:
    done |= set(pd.read_parquet(path, columns=["accession"]).accession)
new = results[~results.accession.isin(done)].copy()
new["accepted_new_york"] = new.accepted_new_york.where(new.accepted_new_york != "", None)
if len(new):
    new[COLUMNS].to_parquet(OUT / f"batch_{len(paths):05d}.parquet", index=False)
print(f"{len(new):,} dépôts ajoutés, {len(done) + len(new):,} au total, {failed:,} en échec à retenter")
print(new.status.value_counts().to_dict())
