"""Barres à la minute autour des publications, pour le Raspberry Pi. Bibliothèque standard seule. Prix bruts, heures étendues.

Les clés arrivent sur l'entrée standard, deux lignes : elles restent en mémoire. Un fichier par séance : une séance
terminée n'est pas refaite. Aucune date après le 31/12/2024 n'est acceptée. Rien n'est calculé ici sur ces prix.

Première passe avec `asof=-` : chaque symbole répond pour lui-même à cette date, sans suivre ses changements de nom.
BHLB et BBT restent ainsi deux sociétés en 2018. Un titre renommé depuis n'a alors aucune barre sous son symbole actuel :
une seconde passe le demande seul sans `asof`, et ses lignes portent `mode=current` pour pouvoir les écarter.

    python3 -u download_minute_bars_pi.py liste.tsv dossier < clés
"""

import csv
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime

URL = "https://data.alpaca.markets/v2/stocks/bars"
MIN_INTERVAL = 0.31
BATCH = 200
MAX_WAIT = 900
FIELDS = ("t", "o", "h", "l", "c", "v", "n", "vw")


def log(message):
    print(datetime.now().strftime("%d/%m %H:%M:%S"), message, flush=True)


class Client:
    def __init__(self, key, secret):
        self.headers = {"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret, "User-Agent": "research-script"}
        self.last_call = 0.0
        self.calls = 0

    def get(self, params):
        """Renvoie la réponse, ou None si l'API refuse la demande elle-même (symbole invalide)."""
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
                if error.code in (400, 422):
                    return None
                log(f"erreur HTTP {error.code}, attente {wait} s")
            except (OSError, ValueError) as error:
                log(f"erreur réseau {type(error).__name__}, attente {wait} s")
            time.sleep(wait)
            wait = min(wait * 2, MAX_WAIT)


def fetch(client, symbols, day, asof, writer, requested=None):
    """Écrit toutes les pages d'une demande ; une demande refusée est coupée en deux. Renvoie les symboles reçus."""
    params = {"symbols": ",".join(symbols), "timeframe": "1Min", "adjustment": "raw", "feed": "sip", "limit": 10000, "sort": "asc", "start": f"{day}T08:00:00Z", "end": f"{day}T23:59:59Z"}
    if asof:
        params["asof"] = asof
    received = set()
    while True:
        page = client.get(params)
        if page is None:
            if len(symbols) == 1:
                log(f"{day} symbole refusé : {symbols[0]}")
                return received
            middle = len(symbols) // 2
            return received | fetch(client, symbols[:middle], day, asof, writer, requested) | fetch(client, symbols[middle:], day, asof, writer, requested)
        for symbol, bars in (page.get("bars") or {}).items():
            received.add(requested or symbol)
            for bar in bars:
                writer.writerow([requested or symbol, symbol, "self" if asof else "current", *[bar.get(k) for k in FIELDS]])
        token = page.get("next_page_token")
        if not token:
            return received
        params["page_token"] = token


def download_day(client, folder, day, symbols):
    path = os.path.join(folder, f"bars_{day}.csv.gz")
    if os.path.exists(path):
        return None
    temporary = path + ".partial"
    with gzip.open(temporary, "wt", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["requested", "returned", "mode", *FIELDS])
        received = set()
        for start in range(0, len(symbols), BATCH):
            received |= fetch(client, symbols[start:start + BATCH], day, "-", writer)
        missing = [symbol for symbol in symbols if symbol not in received]
        recovered = set()
        for symbol in missing:
            recovered |= fetch(client, [symbol], day, None, writer, requested=symbol)
    os.replace(temporary, path)
    return len(symbols), len(received), len(recovered)


def main():
    list_path, folder = sys.argv[1], sys.argv[2]
    os.makedirs(folder, exist_ok=True)
    key, secret = sys.stdin.readline().strip(), sys.stdin.readline().strip()
    if not key or not secret:
        raise SystemExit("Clés absentes de l'entrée standard")
    rows = [line.rstrip("\n").split("\t") for line in open(list_path) if line.strip()]
    if any(date.fromisoformat(day) > date(2024, 12, 31) for day, _ in rows):
        raise SystemExit("Période de validation 2025-2026 verrouillée")
    client = Client(key, secret)
    begun = time.monotonic()
    totals = [0, 0, 0]
    for number, (day, symbols) in enumerate(rows, 1):
        result = download_day(client, folder, day, symbols.split(","))
        if result:
            totals = [a + b for a, b in zip(totals, result)]
            if number % 25 == 0 or number == len(rows):
                log(f"{day} : séance {number}/{len(rows)}, demandés {totals[0]}, reçus {totals[1]}, retrouvés sans asof {totals[2]}, {client.calls} appels, {time.monotonic() - begun:.0f} s")
    log(f"Bilan : demandés {totals[0]}, reçus {totals[1]}, retrouvés sans asof {totals[2]}")
    log("TERMINÉ")


if __name__ == "__main__":
    main()
