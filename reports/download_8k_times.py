"""Heures réelles des 8-K de résultats, lues dans l'en-tête SEC : répare le champ `accepted`, faux dans ~22 % des cas.

L'en-tête donne l'heure d'acceptation, en heure de New York. Elle n'est ni l'heure du communiqué ni celle de sa
première diffusion : elle n'est donc qu'une borne approximative. Limité aux 8-K 2.02 rattachés à une publication de
2018-2024 de `data/events/earnings_events.parquet`, à 8 requêtes par seconde (la SEC autorise 10). Reprise possible.

Depuis la racine : venv/bin/python reports/download_8k_times.py
"""

import os
import re
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
HEADERS = {"User-Agent": f"Projet-recherche-Stock-Market {os.environ['SEC_CONTACT_EMAIL']}"}
OUT = ROOT / "data" / "events" / "eight_k_times"
OUT.mkdir(parents=True, exist_ok=True)
MIN_INTERVAL = 1 / 8
BATCH = 2000
PATTERN = re.compile(r"<ACCEPTANCE-DATETIME>(\d{14})")

events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["cik", "announced"]).dropna().drop_duplicates()
events = events[(events.announced >= "2017-12-15") & (events.announced <= "2024-12-31")]
filings = pd.read_parquet(ROOT / "data" / "sec" / "dev_filings.parquet", columns=["cik", "form", "filing_date", "accepted", "items", "accession"])
wanted = filings[(filings.form == "8-K") & filings["items"].fillna("").str.contains(r"\b2\.02\b")].copy()
wanted["announced"] = pd.to_datetime(wanted.filing_date)
wanted = wanted.merge(events, on=["cik", "announced"]).drop_duplicates("accession").sort_values(["announced", "cik"]).reset_index(drop=True)
done = set()
for path in sorted(OUT.glob("batch_*.parquet")):
    done |= set(pd.read_parquet(path, columns=["accession"]).accession)
todo = wanted[~wanted.accession.isin(done)]
print(f"{len(wanted):,} 8-K, déjà faits {len(done):,}, à faire {len(todo):,}, durée estimée {len(todo) * MIN_INTERVAL / 3600:.1f} h", flush=True)

lock = threading.Lock()
next_slot = [time.monotonic()]


def fetch(row):
    cik, accession = row
    url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}.hdr.sgml"
    for attempt in range(5):
        with lock:
            wait = next_slot[0] - time.monotonic()
            next_slot[0] = max(next_slot[0], time.monotonic()) + MIN_INTERVAL
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=30) as response:
                match = PATTERN.search(response.read(4096).decode("latin-1"))
            return accession, match.group(1) if match else None, "ok" if match else "no_field"
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return accession, None, "not_found"
            time.sleep(5 * (attempt + 1))
        except OSError:
            time.sleep(5 * (attempt + 1))
    return accession, None, "failed"


begun = time.monotonic()
number = len(list(OUT.glob("batch_*.parquet")))
rows = list(zip(todo.cik, todo.accession))
with ThreadPoolExecutor(max_workers=8) as pool:
    for start in range(0, len(rows), BATCH):
        part = list(pool.map(fetch, rows[start:start + BATCH]))
        pd.DataFrame(part, columns=["accession", "accepted_new_york", "status"]).to_parquet(OUT / f"batch_{number:05d}.parquet", index=False)
        number += 1
        print(f"{start + len(part):,}/{len(rows):,}, {time.monotonic() - begun:.0f} s, échecs de ce lot {sum(p[2] != 'ok' for p in part)}", flush=True)
print("terminé", flush=True)
