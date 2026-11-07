"""Télécharge toutes les news Alpaca de 2018-2024, mois par mois. Bibliothèque standard seule, pour tourner sur le Pi.

Les clés arrivent sur l'entrée standard, deux lignes : elles restent en mémoire, sans jamais être écrites ni affichées.
Reprise : un mois terminé n'est pas refait. Aucun article créé après le 31/12/2024 n'est gardé.

    python3 download_all_news.py DOSSIER [AAAA-MM-JJ AAAA-MM-JJ] < clés
"""

import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

URL = "https://data.alpaca.markets/v1beta1/news"
MIN_INTERVAL = 0.31
LAST_ALLOWED = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
FIELDS = ("id", "created_at", "updated_at", "headline", "summary", "author", "source", "symbols", "url")
MAX_WAIT = 900


def log(message):
    print(datetime.now().strftime("%d/%m %H:%M:%S"), message, flush=True)


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def month_ranges(first, last):
    current = first
    while current <= last:
        following = date(current.year + (current.month == 12), current.month % 12 + 1, 1)
        yield current, min(following - timedelta(days=1), last)
        current = following


class Client:
    def __init__(self, key, secret):
        self.headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "User-Agent": "research-script"}
        self.last_call = 0.0
        self.calls = 0

    def get(self, params):
        wait = 5
        while True:
            pause = MIN_INTERVAL - (time.monotonic() - self.last_call)
            if pause > 0:
                time.sleep(pause)
            self.last_call = time.monotonic()
            request = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params), headers=self.headers)
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    self.calls += 1
                    return json.load(response)
            except urllib.error.HTTPError as error:
                if error.code in (401, 403):
                    log(f"ARRÊT : accès refusé ({error.code})")
                    raise SystemExit(2)
                log(f"erreur HTTP {error.code}, attente {wait} s")
            except (OSError, ValueError) as error:
                log(f"erreur réseau {type(error).__name__}, attente {wait} s")
            time.sleep(wait)
            wait = min(wait * 2, MAX_WAIT)


def download_month(client, folder, first, last):
    path = os.path.join(folder, f"news_{first:%Y-%m}.jsonl.gz")
    if os.path.exists(path):
        return 0
    begin = datetime(first.year, first.month, first.day, tzinfo=timezone.utc)
    params = {"start": f"{first}T00:00:00Z", "end": f"{last}T23:59:59Z", "limit": 50, "sort": "asc", "include_content": "false"}
    temporary = path + ".partial"
    kept = 0
    with gzip.open(temporary, "wt", encoding="utf-8") as output:
        while True:
            page = client.get(params)
            for item in page.get("news") or []:
                created = parse_time(item["created_at"])
                # L'API filtre sur la mise à jour : la création décide.
                if begin <= created <= LAST_ALLOWED:
                    output.write(json.dumps({k: item.get(k) for k in FIELDS}, ensure_ascii=False) + "\n")
                    kept += 1
            token = page.get("next_page_token")
            if not token:
                break
            params["page_token"] = token
    os.replace(temporary, path)
    return kept


def main():
    folder = sys.argv[1]
    first = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date(2018, 1, 1)
    last = date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else date(2024, 12, 31)
    if last > date(2024, 12, 31):
        raise SystemExit("Période de validation 2025-2026 verrouillée")
    os.makedirs(folder, exist_ok=True)
    key = sys.stdin.readline().strip()
    secret = sys.stdin.readline().strip()
    if not key or not secret:
        raise SystemExit("Clés absentes de l'entrée standard")
    client = Client(key, secret)
    begun = time.monotonic()
    total = 0
    for start, stop in month_ranges(first, last):
        kept = download_month(client, folder, start, stop)
        total += kept
        log(f"{start:%Y-%m} : {kept} articles, total {total}, {client.calls} appels, {time.monotonic() - begun:.0f} s")
    log("TERMINÉ")


if __name__ == "__main__":
    main()
