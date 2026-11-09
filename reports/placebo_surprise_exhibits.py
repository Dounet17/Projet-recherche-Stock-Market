"""Test placebo du contrôle `figure_position` : à quelle fréquence un chiffre faux passe-t-il pour le bon ? Aucun cours.

On cherche dans les communiqués des chiffres qui ne devraient pas s'y trouver comme résultat du trimestre, sur un tirage
fixe de 6 000 publications. La part classée `current` estime la chance qu'un chiffre faux soit validé par hasard.

Écrit `reports/lab_2026-11/news/verification_8k_placebo.json`.

Depuis la racine, après `verify_surprise_exhibits.py` : venv/bin/python reports/placebo_surprise_exhibits.py [dossier]
"""

import glob
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent / "src"))
from exhibit_check import locate_figure
from verify_surprise_exhibits import DATA, accessions_by_publication, read_batch

OUT = ROOT / "lab_2026-11" / "news" / "verification_8k_placebo.json"
SAMPLE = 6000


def position(row):
    return locate_figure(row[0], row[1])[0]


def rates(texts, values):
    """Part de chaque réponse ; une valeur manquante est un cas où le placebo se confond avec le vrai chiffre."""
    keep = [(text, value) for text, value in zip(texts, values) if not np.isnan(value)]
    with Pool(8) as pool:
        found = pd.Series(pool.map(position, keep, chunksize=100))
    return {"n": len(keep), **{k: round(float(v), 3) for k, v in found.value_counts(normalize=True).items()}}


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "events" / "exhibits"
    table = pd.read_parquet(DATA / "news" / "earnings_surprise_verified.parquet")
    grouped = accessions_by_publication(table).groupby("id").accession.agg(list)
    sample = table[table.id.isin(grouped.index) & table.eps.notna() & table.eps_estimate.notna()].sample(SAMPLE, random_state=11)
    wanted = {a for i in sample.id for a in grouped[i]}
    filings = {}
    with Pool(8) as pool:
        for batch in pool.imap(read_batch, sorted(glob.glob(str(folder / "batch_*.jsonl.gz")))):
            for record in batch:
                if record["status"] == "ok" and record["accession"] in wanted:
                    filings[record["accession"]] = record["text"]
    texts = ["\n".join(filings.get(a, "") for a in grouped[i]) for i in sample.id]

    eps, estimate = sample.eps.to_numpy(), sample.eps_estimate.to_numpy()
    other = np.random.default_rng(3).permutation(eps)
    summary = {
        "true_eps": rates(texts, eps),
        "cited_estimate": rates(texts, np.where(np.isclose(np.round(estimate, 2), np.round(eps, 2)), np.nan, estimate)),
        "eps_plus_0.07": rates(texts, np.round(eps + .07, 2)),
        "eps_minus_0.13": rates(texts, np.round(eps - .13, 2)),
        "eps_of_another_publication": rates(texts, np.where(np.isclose(other, eps), np.nan, other)),
    }
    OUT.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
