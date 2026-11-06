"""Télécharge les archives complètes de la SEC (comptes publiés et liste des dépôts).

Le fichier partiel reprend là où il s'est arrêté. Ces archives contiennent aussi 2025-2026 :
toute extraction de recherche doit filtrer sur la date de dépôt, au plus tard le 31/12/2024.
Depuis la racine : venv/bin/python reports/download_sec_bulk.py
"""

import os
import zipfile
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
OUT = ROOT / "data" / "sec" / "raw"
OUT.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": f"Projet-recherche-Stock-Market {os.environ['SEC_CONTACT_EMAIL']}"}
FILES = {
    "companyfacts.zip": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
    "submissions.zip": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
}

for name, url in FILES.items():
    path = OUT / name
    partial = path.with_suffix(".part")
    if path.exists():
        print(name, "déjà présent", flush=True)
        continue
    for attempt in range(8):
        done = partial.stat().st_size if partial.exists() else 0
        headers = {**HEADERS, "Range": f"bytes={done}-"} if done else HEADERS
        try:
            with requests.get(url, headers=headers, stream=True, timeout=120) as response:
                if response.status_code == 416:
                    break
                response.raise_for_status()
                # Le serveur peut ignorer la reprise : on repart alors de zéro.
                mode = "ab" if response.status_code == 206 else "wb"
                with open(partial, mode) as handle:
                    for chunk in response.iter_content(1 << 20):
                        handle.write(chunk)
            break
        except requests.exceptions.RequestException as error:
            print(name, "nouvel essai après", type(error).__name__, flush=True)
    else:
        raise SystemExit(f"Échec du téléchargement de {name}")
    with zipfile.ZipFile(partial) as archive:
        members = len(archive.namelist())
    partial.rename(path)
    print(name, round(path.stat().st_size / 1e9, 2), "Go,", members, "fichiers", flush=True)
print("Terminé", flush=True)
