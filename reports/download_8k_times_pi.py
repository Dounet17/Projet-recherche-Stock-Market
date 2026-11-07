"""Heures réelles des 8-K, version sans dépendance pour le Raspberry Pi. Mêmes règles que `download_8k_times.py`.

Lit une liste « cik<TAB>accession », ajoute chaque résultat à un CSV et reprend là où il s'est arrêté. Un dépôt
en échec est retenté à la relance. Le contact SEC arrive sur l'entrée standard et n'est jamais écrit sur le disque.

    python3 -u download_8k_times_pi.py liste.tsv resultats.csv < contact
"""

import csv
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

MIN_INTERVAL = 1 / 8
BATCH = 2000
PATTERN = re.compile(r"<ACCEPTANCE-DATETIME>(\d{14})")

list_path, result_path = Path(sys.argv[1]), Path(sys.argv[2])
contact = sys.stdin.readline().strip()
if not contact:
    sys.exit("Contact SEC manquant sur l'entrée standard.")
headers = {"User-Agent": f"Projet-recherche-Stock-Market {contact}"}

rows = [tuple(line.split("\t")) for line in list_path.read_text().splitlines() if line]
done = set()
if result_path.exists():
    with result_path.open(newline="") as file:
        done = {row[0] for row in csv.reader(file) if row and row[2] != "failed"}
todo = [row for row in rows if row[1] not in done]
print(f"{len(rows):,} 8-K, déjà faits {len(done):,}, à faire {len(todo):,}, durée estimée {len(todo) * MIN_INTERVAL / 3600:.1f} h", flush=True)

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
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
                match = PATTERN.search(response.read(4096).decode("latin-1"))
            return accession, match.group(1) if match else "", "ok" if match else "no_field"
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return accession, "", "not_found"
            time.sleep(5 * (attempt + 1))
        except OSError:
            time.sleep(5 * (attempt + 1))
    return accession, "", "failed"


begun = time.monotonic()
with ThreadPoolExecutor(max_workers=8) as pool, result_path.open("a", newline="") as output:
    writer = csv.writer(output)
    for start in range(0, len(todo), BATCH):
        part = list(pool.map(fetch, todo[start:start + BATCH]))
        writer.writerows(part)
        output.flush()
        print(f"{time.strftime('%d/%m %H:%M:%S')} {start + len(part):,}/{len(todo):,}, {time.monotonic() - begun:.0f} s, échecs de ce lot {sum(p[2] != 'ok' for p in part)}", flush=True)
print("TERMINÉ", flush=True)
