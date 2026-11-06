"""Confronte les coupures de symboles réutilisés à une source indépendante : le paramètre asof.

Interrogé à une date antérieure à la coupure, Alpaca renvoie la société de l'époque. Si cette
série s'arrête avant la reprise, la règle est confirmée. Si elle continue, Alpaca ne distingue
pas les deux sociétés : le test ne tranche pas. Échantillon tiré au sort, graine fixe.
Depuis la racine : venv/bin/python -I reports/validate_universe_cuts.py
"""

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import collect
from lab import DEV_END, WARMUP_START

SAMPLE = 120
cuts = pd.read_parquet(ROOT / "data" / "universe_clean" / "cuts_dev.parquet")
# Une coupure antérieure à 2016 + 1 mois ne laisse pas de date asof exploitable.
cuts = cuts[pd.to_datetime(cuts.last_before, utc=True) >= "2016-03-01"]
sample = cuts.sample(min(SAMPLE, len(cuts)), random_state=2026)
rows = []
for cut in sample.itertuples():
    asof = (pd.Timestamp(cut.last_before) - pd.Timedelta(days=30)).date().isoformat()
    params = {"symbols": cut.symbol, "timeframe": "1Day", "adjustment": "raw", "feed": "sip", "limit": 10000, "start": f"{WARMUP_START}T00:00:00Z", "end": f"{DEV_END}T23:59:59Z", "sort": "asc", "asof": asof}
    last = None
    while True:
        page = collect._alpaca_get(f"{collect.ALPACA_DATA_URL}/v2/stocks/bars", params)
        for bars in (page.get("bars") or {}).values():
            if bars:
                last = bars[-1]["t"]
        token = page.get("next_page_token")
        if not token:
            break
        params["page_token"] = token
    gap = None if last is None else (pd.Timestamp(last) - pd.Timestamp(cut.last_before)).days
    rows.append({"symbol": cut.symbol, "last_before": str(cut.last_before)[:10], "first_after": str(cut.first_after)[:10], "sessions": int(cut.sessions), "asof_last": None if last is None else last[:10], "days_after_cut": gap})
frame = pd.DataFrame(rows)
# Alpaca recopie parfois quelques cours après la fin : seul compte que la seconde société soit absente.
last_seen = pd.to_datetime(frame.asof_last, utc=True)
second_begins = pd.to_datetime(frame.first_after, utc=True)
separated = last_seen < second_begins
result = {"tested": len(frame), "alpaca_separates_at_cut": int(separated.sum()), "alpaca_keeps_both_societies": int((last_seen >= second_begins).sum()), "no_answer": int(last_seen.isna().sum()), "median_days_between_end_and_cut": float(frame.loc[separated, "days_after_cut"].median()), "examples_kept_together": frame[last_seen >= second_begins].head(12).to_dict("records")}
(ROOT / "reports" / "lab_2026-11" / "validate_cuts.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(result, indent=1, ensure_ascii=False))
