"""Extrait des archives SEC les indices qui relient un symbole boursier à une société.

Le champ "tickers" de la SEC ne donne que le symbole actuel, donc rien pour les sociétés
disparues. Les noms de documents déposés contiennent souvent le symbole de l'époque :
sbny-20221231.htm, fb-12312017x10k.htm. Écrit dans data/sec/ :
- dev_doc_prefixes.parquet : (cik, préfixe, premier et dernier dépôt, nombre de dépôts) ;
- dev_entities.parquet : formulaires annuels déposés et catégorie de chaque société.
Rien de postérieur au 31/12/2024 n'est conservé.
Depuis la racine : venv/bin/python -I reports/extract_sec_links.py
"""

import json
import multiprocessing as mp
import re
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path.cwd()
RAW = ROOT / "data" / "sec" / "raw" / "submissions.zip"
OUT = ROOT / "data" / "sec"
CUTOFF = "2024-12-31"
FORMS = {"10-K", "10-K/A", "10-Q", "10-Q/A", "8-K", "8-K/A", "20-F", "20-F/A", "40-F", "6-K", "N-CEN", "N-CSR", "NPORT-P", "10-KT"}
PREFIX = re.compile(r"^([a-z]{1,5})[-_]?(?:\d{6,8}|q\d|fy\d|10-?[kq]|8-?k|ex)", re.IGNORECASE)
NOT_TICKERS = {"form", "doc", "ex", "exh", "ek", "pr", "press", "d", "k", "q", "r", "rrd", "tv", "f", "g", "edgar", "filing", "report", "main", "html", "htm", "body", "file", "sec", "annual", "cover"}


def scan(names):
    prefixes, entities = {}, {}
    with zipfile.ZipFile(RAW) as archive:
        for name in names:
            data = json.loads(archive.read(name))
            if "-submissions-" in name:
                cik, block = int(Path(name).name[3:13]), data
            else:
                cik, block = int(data["cik"]), data.get("filings", {}).get("recent", {})
                entities.setdefault(cik, {}).update(entity_type=data.get("entityType"), category=data.get("category"), sic=data.get("sic"), name=data.get("name"), tickers=",".join(t for t in (data.get("tickers") or []) if t), former=json.dumps(data.get("formerNames") or []))
            for form, date, document in zip(block.get("form", []), block.get("filingDate", []), block.get("primaryDocument", [])):
                if form not in FORMS or date > CUTOFF:
                    continue
                record = entities.setdefault(cik, {})
                record[form.split("/")[0]] = record.get(form.split("/")[0], 0) + 1
                record["first_filing"] = min(record.get("first_filing", date), date)
                record["last_filing"] = max(record.get("last_filing", date), date)
                match = PREFIX.match(document or "")
                if match and form not in {"N-CEN", "N-CSR", "NPORT-P"}:
                    prefix = match.group(1).upper()
                    if prefix.lower() not in NOT_TICKERS:
                        key = (cik, prefix)
                        first, last, count = prefixes.get(key, (date, date, 0))
                        prefixes[key] = (min(first, date), max(last, date), count + 1)
    return prefixes, entities


if __name__ == "__main__":
    with zipfile.ZipFile(RAW) as archive:
        names = [n for n in archive.namelist() if n.endswith(".json")]
    chunks = [names[i:i + 5000] for i in range(0, len(names), 5000)]
    all_prefixes, all_entities = {}, {}
    with mp.Pool(8) as pool:
        for position, (prefixes, entities) in enumerate(pool.imap_unordered(scan, chunks)):
            for key, (first, last, count) in prefixes.items():
                old = all_prefixes.get(key, (first, last, 0))
                all_prefixes[key] = (min(old[0], first), max(old[1], last), old[2] + count)
            for cik, record in entities.items():
                target = all_entities.setdefault(cik, {})
                for field, value in record.items():
                    if field == "first_filing":
                        target[field] = min(target.get(field, value), value)
                    elif field == "last_filing":
                        target[field] = max(target.get(field, value), value)
                    elif isinstance(value, int) and field != "sic":
                        target[field] = target.get(field, 0) + value
                    else:
                        target[field] = value
            if position % 20 == 0:
                print(position, "/", len(chunks), flush=True)
    frame = pd.DataFrame([(c, p, *v) for (c, p), v in all_prefixes.items()], columns=["cik", "prefix", "first_filing", "last_filing", "filings"])
    frame.to_parquet(OUT / "dev_doc_prefixes.parquet", index=False)
    entities = pd.DataFrame.from_dict(all_entities, orient="index").rename_axis("cik").reset_index()
    entities = entities.astype({c: "string" for c in ("entity_type", "category", "sic", "name", "tickers", "former") if c in entities})
    entities.to_parquet(OUT / "dev_entities.parquet", index=False)
    print("Préfixes :", len(frame), "| sociétés avec dépôts :", entities.first_filing.notna().sum(), flush=True)
    print("Terminé", flush=True)
