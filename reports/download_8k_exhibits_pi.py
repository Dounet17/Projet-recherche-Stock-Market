"""Texte des communiqués joints aux 8-K de résultats, version sans dépendance pour le Raspberry Pi.

Une seule requête par dépôt : le fichier complet de la soumission, dont on ne garde que le texte des pièces EX-99, ou
le corps du 8-K s'il n'y en a aucune. Reprise possible : un dépôt en échec est retenté à la relance. Le contact SEC
arrive sur l'entrée standard et n'est jamais écrit sur le disque. Aucun cours n'est lu.

    python3 -u download_8k_exhibits_pi.py liste.tsv dossier < contact
"""

import gzip
import html
import json
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
MAX_DOWNLOAD = 30_000_000
MAX_TEXT = 500_000
DOCUMENT = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.DOTALL)
TYPE = re.compile(r"<TYPE>([^\n<]+)")
TEXT = re.compile(r"<TEXT>(.*?)</TEXT>", re.DOTALL)


def plain_text(markup):
    """Texte lisible d'une pièce : balises retirées, cellules de tableau séparées pour garder les colonnes distinctes."""
    markup = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)</(td|th)>", " | ", markup)
    markup = re.sub(r"(?i)</(tr|p|div)>|<br\s*/?>", "\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t\xa0]+", " ", text)).strip()


def extract_exhibits(submission):
    """Pièces EX-99 d'une soumission, ou le corps du 8-K si aucune n'existe. Renvoie (types gardés, texte)."""
    documents = []
    for block in DOCUMENT.findall(submission):
        kind = TYPE.search(block)
        body = TEXT.search(block)
        if kind and body:
            documents.append((kind[1].strip().upper(), body[1]))
    kept = [d for d in documents if d[0].startswith("EX-99")] or [d for d in documents if d[0].startswith("8-K")]
    return [d[0] for d in kept], "\n\n".join(plain_text(d[1]) for d in kept)[:MAX_TEXT]


def main():
    list_path, folder = Path(sys.argv[1]), Path(sys.argv[2])
    contact = sys.stdin.readline().strip()
    if not contact:
        sys.exit("Contact SEC manquant sur l'entrée standard.")
    headers = {"User-Agent": f"Projet-recherche-Stock-Market {contact}"}
    folder.mkdir(parents=True, exist_ok=True)
    rows = [tuple(line.split("\t")) for line in list_path.read_text().splitlines() if line]
    done = set()
    parts = sorted(folder.glob("batch_*.jsonl.gz"))
    for path in parts:
        with gzip.open(path, "rt") as file:
            for line in file:
                record = json.loads(line)
                if record["status"] != "failed":
                    done.add(record["accession"])
    todo = [row for row in rows if row[1] not in done]
    print(f"{len(rows):,} dépôts, déjà faits {len(done):,}, à faire {len(todo):,}, durée estimée {len(todo) * MIN_INTERVAL / 3600:.1f} h", flush=True)
    lock = threading.Lock()
    next_slot = [time.monotonic()]

    def fetch(row):
        cik, accession = row
        url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{accession}.txt"
        for attempt in range(5):
            with lock:
                wait = next_slot[0] - time.monotonic()
                next_slot[0] = max(next_slot[0], time.monotonic()) + MIN_INTERVAL
            if wait > 0:
                time.sleep(wait)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
                    raw = response.read(MAX_DOWNLOAD)
                types, text = extract_exhibits(raw.decode("latin-1"))
                return {"accession": accession, "status": "ok" if text else "no_text", "types": types, "bytes": len(raw), "text": text}
            except urllib.error.HTTPError as error:
                if error.code == 404:
                    return {"accession": accession, "status": "not_found", "types": [], "bytes": 0, "text": ""}
                time.sleep(5 * (attempt + 1))
            except OSError:
                time.sleep(5 * (attempt + 1))
        return {"accession": accession, "status": "failed", "types": [], "bytes": 0, "text": ""}

    begun = time.monotonic()
    number = 1 + max((int(path.name[6:11]) for path in parts), default=-1)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for start in range(0, len(todo), BATCH):
            part = list(pool.map(fetch, todo[start:start + BATCH]))
            target = folder / f"batch_{number:05d}.jsonl.gz"
            with gzip.open(str(target) + ".partial", "wt") as output:
                for record in part:
                    output.write(json.dumps(record, ensure_ascii=False) + "\n")
            Path(str(target) + ".partial").rename(target)
            number += 1
            print(f"{time.strftime('%d/%m %H:%M:%S')} {start + len(part):,}/{len(todo):,}, {time.monotonic() - begun:.0f} s, échecs de ce lot {sum(r['status'] == 'failed' for r in part)}, sans texte {sum(r['status'] == 'no_text' for r in part)}, sans dépôt {sum(r['status'] == 'not_found' for r in part)}", flush=True)
    print("TERMINÉ", flush=True)


if __name__ == "__main__":
    main()
