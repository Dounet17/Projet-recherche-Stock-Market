"""Télécharge les noms de fichiers XBRL de la SEC : ils contiennent le symbole de l'époque.

Les « Financial Statement Data Sets » trimestriels (2015-2024) listent chaque dépôt avec son
fichier XBRL, par exemple twx-20171231.xml. Seul sub.txt est conservé, le reste est supprimé.
Écrit data/sec/dev_instances.parquet, sans aucun dépôt postérieur au 31/12/2024.
Depuis la racine : venv/bin/python -I reports/download_sec_instances.py
"""

import io
import os
import re
import zipfile
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path.cwd()
load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "sec" / "fsds"
OUT.mkdir(exist_ok=True)
HEADERS = {"User-Agent": f"Projet-recherche-Stock-Market {os.environ['SEC_CONTACT_EMAIL']}"}
URL = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/{}.zip"
COLUMNS = ["adsh", "cik", "name", "sic", "form", "filed", "period", "instance"]
PREFIX = re.compile(r"^([a-z]{1,6})[-_]\d{6,8}", re.IGNORECASE)

frames = []
for year in range(2015, 2025):
    for quarter in range(1, 5):
        label = f"{year}q{quarter}"
        path = OUT / f"{label}.parquet"
        if not path.exists():
            response = requests.get(URL.format(label), headers=HEADERS, timeout=600)
            response.raise_for_status()
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive, archive.open("sub.txt") as handle:
                table = pd.read_csv(handle, sep="\t", usecols=COLUMNS, dtype=str)
            table.to_parquet(path, index=False)
            print(label, len(table), flush=True)
        frames.append(pd.read_parquet(path))
table = pd.concat(frames, ignore_index=True)
table["filed"] = pd.to_datetime(table.filed, format="%Y%m%d", errors="coerce")
table = table[table.filed <= "2024-12-31"]
table["prefix"] = table.instance.fillna("").str.extract(PREFIX, expand=False).str.upper()
table["cik"] = table.cik.astype(int)
table.to_parquet(ROOT / "data" / "sec" / "dev_instances.parquet", index=False)
print("Dépôts :", len(table), "| avec préfixe :", table.prefix.notna().sum(), "| sociétés :", table.cik.nunique(), flush=True)
print("Terminé", flush=True)
