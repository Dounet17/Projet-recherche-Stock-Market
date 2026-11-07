"""Confronte chaque ligne de `data/news/earnings_surprise.parquet` au communiqué joint au 8-K du même jour. Aucun cours.

Écrit `data/news/earnings_surprise_verified.parquet` et `reports/lab_2026-11/news/verification_8k.json`. Le contrôle
porte le nom `figure_position` ; il ne vérifie ni l'estimation citée, ni la première diffusion.

Depuis la racine : venv/bin/python reports/verify_surprise_exhibits.py [dossier des communiqués]
"""

import glob
import gzip
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from exhibit_check import locate_figure

DATA = ROOT / "data"
OUT = ROOT / "reports" / "lab_2026-11" / "news" / "verification_8k.json"
# Publications contrôlées à la main sur les pièces SEC par le second audit, hors chiffres de la table : repère de la règle.
AUDIT_WRONG = {"WSBF#0": "0,23 est le BPA du même trimestre un an plus tôt"}
AUDIT_NOT_EXPLICIT = {"MHO#0": "2,93 seulement reconstituable"}


def accessions_by_publication(surprises):
    """Tous les 8-K de résultats du jour de chaque publication : le communiqué peut être dans un autre dépôt du jour."""
    times = pd.concat(map(pd.read_parquet, sorted((DATA / "events" / "eight_k_times").glob("batch_*.parquet"))))
    times = times[times.status == "ok"]
    filings = pd.read_parquet(DATA / "sec" / "dev_filings.parquet", columns=["cik", "filing_date", "accession"])
    filings = filings[filings.accession.isin(times.accession)].merge(times[["accession", "accepted_new_york"]], on="accession")
    filings["accepted"] = pd.to_datetime(filings.accepted_new_york, format="%Y%m%d%H%M%S").dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC").astype("datetime64[ns, UTC]")
    keys = surprises[["id", "cik"]].assign(accepted=surprises.accepted_utc.astype("datetime64[ns, UTC]"))
    days = keys.merge(filings[["cik", "accepted", "filing_date"]].drop_duplicates(["cik", "accepted"]), on=["cik", "accepted"], how="left")
    return days.merge(filings[["cik", "filing_date", "accession"]], on=["cik", "filing_date"], how="left")[["id", "accession"]].dropna()


def read_batch(path):
    with gzip.open(path, "rt") as file:
        return [json.loads(line) for line in file]


def check(row):
    position, basis = locate_figure(row[1], row[2])
    return row[0], position, basis


def main():
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else DATA / "events" / "exhibits"
    surprises = pd.read_parquet(DATA / "news" / "earnings_surprise.parquet")
    assert surprises.accepted_utc.max() < pd.Timestamp("2025-01-01", tz="UTC")
    mapping = accessions_by_publication(surprises)
    texts, statuses = {}, {}
    with Pool(8) as pool:
        for batch in pool.imap_unordered(read_batch, sorted(glob.glob(str(folder / "batch_*.jsonl.gz")))):
            for record in batch:
                statuses[record["accession"]] = record["status"]
                if record["status"] == "ok":
                    texts[record["accession"]] = record["text"]
    print(f"{len(statuses):,} dépôts lus, {len(texts):,} avec texte", flush=True)
    mapping = mapping[mapping.accession.isin(statuses)]
    grouped = mapping.groupby("id").accession.agg(list)
    table = surprises[surprises.id.isin(grouped.index)].copy()
    work = [(row.id, "\n".join(texts.get(a, "") for a in grouped[row.id]), row.eps) for row in table[["id", "eps"]].itertuples(index=False)]
    del texts
    with Pool(8) as pool:
        found = pool.map(check, work, chunksize=500)
    del work
    results = pd.DataFrame(found, columns=["id", "figure_position", "exhibit_basis"])
    table = table.merge(results, on="id")
    table["verified"] = table.figure_position.eq("current")
    # La base du titre doit être explicite, et le communiqué ne doit pas contredire une étiquette ajustée.
    table["principal"] = table.verified & table.basis.isin(["adjusted", "gaap"])
    if len(table) == len(surprises):
        table.to_parquet(DATA / "news" / "earnings_surprise_verified.parquet", index=False)
    year = table.accepted_utc.dt.year
    securities = pd.read_parquet(DATA / "universe_clean" / "securities_dev.parquet", columns=["security_id", "alive_at_end"]).set_index("security_id").alive_at_end
    alive = table.event_security.map(securities)
    witnesses = {key: table[(table.event_security == key)].assign(p=lambda f: f.figure_position)[["period_end", "eps", "figure_position"]].astype(str).head(2).to_dict("records") for key in [*AUDIT_WRONG, *AUDIT_NOT_EXPLICIT]}
    summary = {
        "publications_in_table": len(surprises), "publications_checked": len(table), "complete": len(table) == len(surprises),
        "filing_status": pd.Series(statuses).value_counts().to_dict(),
        "figure_position": table.figure_position.value_counts().to_dict(),
        "verified_by_year": {str(y): {"checked": int((year == y).sum()), "verified": round(float(table.verified[year == y].mean()), 3), "principal": int(table.principal[year == y].sum())} for y in sorted(year.unique())},
        "verified_by_survival": {"alive": round(float(table.verified[alive.eq(True)].mean()), 3), "gone": round(float(table.verified[alive.eq(False)].mean()), 3)},
        "verified_by_basis": {k: round(float(v), 3) for k, v in table.groupby("basis").verified.mean().items()},
        "principal": int(table.principal.sum()), "unlabeled_verified": int((table.verified & table.basis.eq("unlabeled")).sum()),
        "exhibit_basis_when_unlabeled": table[table.verified & table.basis.eq("unlabeled")].exhibit_basis.value_counts().to_dict(),
        "audit_witnesses": witnesses,
    }
    if len(table) == len(surprises):
        OUT.write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
