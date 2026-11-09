"""Extrait des archives SEC ce qui a été déposé au plus tard le 31/12/2024.

Produit dans data/sec/ :
- dev_facts.parquet : EPS, résultat net et nombre d'actions, au premier dépôt de chaque période ;
- dev_filings.parquet : dépôts 8-K, 10-K, 10-Q, 4 et S-1, avec leur heure d'acceptation ;
- dev_companies.parquet : numéro de société (CIK), nom, anciens noms et symboles.
Depuis la racine : venv/bin/python -I reports/extract_sec_dev.py
"""

import json
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "sec" / "raw"
OUT = ROOT / "data" / "sec"
CUTOFF = "2024-12-31"
CONCEPTS = {
    ("us-gaap", "EarningsPerShareDiluted"): "eps_diluted",
    ("us-gaap", "EarningsPerShareBasic"): "eps_basic",
    ("us-gaap", "NetIncomeLoss"): "net_income",
    ("dei", "EntityCommonStockSharesOutstanding"): "shares_outstanding",
}
FORMS = {"8-K", "8-K/A", "10-K", "10-K/A", "10-Q", "10-Q/A", "4", "S-1", "S-1/A"}

rows = []
with zipfile.ZipFile(RAW / "companyfacts.zip") as archive:
    names = [n for n in archive.namelist() if n.endswith(".json")]
    for position, name in enumerate(names):
        data = json.loads(archive.read(name))
        # Le CIK arrive parfois en texte : le nom du fichier fait référence pour toutes les sociétés.
        cik, facts = int(Path(name).name[3:13]), data.get("facts", {})
        for (taxonomy, concept), label in CONCEPTS.items():
            for unit, values in facts.get(taxonomy, {}).get(concept, {}).get("units", {}).items():
                for fact in values:
                    # Filtre posé avant tout stockage : rien de postérieur n'entre dans ce fichier.
                    if fact.get("filed", "9999") <= CUTOFF:
                        rows.append((cik, label, unit, fact.get("start"), fact["end"], fact["val"], fact["filed"], fact.get("form"), fact.get("accn")))
        if position % 2000 == 0:
            print("comptes", position, "/", len(names), "| lignes", len(rows), flush=True)
facts = pd.DataFrame(rows, columns=["cik", "concept", "unit", "start", "end", "value", "filed", "form", "accn"])
total = len(facts)
# Premier dépôt de chaque période : ni version corrigée, ni chiffre re-publié plus tard.
facts = facts.sort_values(["filed", "accn"]).drop_duplicates(["cik", "concept", "unit", "start", "end"], keep="first")
facts.to_parquet(OUT / "dev_facts.parquet", index=False)
print("Faits :", total, "lus,", len(facts), "gardés au premier dépôt", flush=True)

companies, filings = [], []
with zipfile.ZipFile(RAW / "submissions.zip") as archive:
    names = [n for n in archive.namelist() if n.endswith(".json")]
    for position, name in enumerate(names):
        data = json.loads(archive.read(name))
        if "-submissions-" in name:
            cik, block = int(Path(name).name[3:13]), data
        else:
            cik, block = int(data["cik"]), data.get("filings", {}).get("recent", {})
            companies.append({"cik": cik, "name": data.get("name"), "tickers": ",".join(t for t in (data.get("tickers") or []) if t), "exchanges": ",".join(e for e in (data.get("exchanges") or []) if e), "former_names": "|".join(f.get("name", "") for f in data.get("formerNames") or []), "sic": data.get("sic"), "entity_type": data.get("entityType")})
        for form, date, accepted, items, accession in zip(block.get("form", []), block.get("filingDate", []), block.get("acceptanceDateTime", []), block.get("items", []), block.get("accessionNumber", [])):
            if form in FORMS and date <= CUTOFF:
                filings.append((cik, form, date, accepted, items, accession))
        if position % 20000 == 0:
            print("dépôts", position, "/", len(names), "| lignes", len(filings), flush=True)
pd.DataFrame(companies).to_parquet(OUT / "dev_companies.parquet", index=False)
filings = pd.DataFrame(filings, columns=["cik", "form", "filing_date", "accepted", "items", "accession"]).drop_duplicates("accession")
filings.to_parquet(OUT / "dev_filings.parquet", index=False)
print("Sociétés :", len(companies), "| dépôts gardés :", len(filings), flush=True)
print(filings.form.value_counts().to_string(), flush=True)
print("Terminé", flush=True)
