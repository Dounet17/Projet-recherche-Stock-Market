"""Premier contrôle qualité du grand dataset, sur 2016-2024 uniquement.

Depuis la racine : venv/bin/python reports/qc_universe.py
Les dossiers de validation ne sont jamais lus ici.
"""

import glob
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
U = ROOT / "data" / "universe"
COLUMNS = ["symbol", "ts_utc", "close", "volume"]


def load(*folders):
    return pd.concat([pd.read_parquet(p, columns=COLUMNS) for f in folders for p in sorted(glob.glob(str(U / f / "*.parquet")))], ignore_index=True)


b = load("dev_all", "extra_dev_all").drop_duplicates(["symbol", "ts_utc"]).sort_values(["symbol", "ts_utc"])
raw = load("dev_raw", "extra_dev_raw")
assets = pd.read_parquet(U / "assets.parquet")
listed = set(assets.symbol)
stats = b.groupby("symbol").agg(first=("ts_utc", "min"), last=("ts_utc", "max"), days=("close", "size"))
report = {"symbols": len(stats), "from_alpaca_list": int(stats.index.isin(listed).sum()), "found_by_enumeration": int((~stats.index.isin(listed)).sum()), "rows": len(b), "last_date": str(b.ts_utc.max())}

known = "TWTR ATVI SIVB FRC SBNY BBBY CELG XLNX ANTM RTN AGN ESRX RHT TIF ETFC CTXS NLSN CERN KSU MXIM PBCT VAR FLIR ALXN WORK COG HFC DISCA VIAC BLL ABMD SPLK PXD DWDP TFCF WP LB NBL APC CA MON SCG LLL GGP COL DPS EVHC BCR HCN WYN".split()
report["known_disappeared_found"] = f"{sum(s in stats.index for s in known)} / {len(known)}"
report["adjusted_without_raw"] = sorted(set(stats.index) - set(raw.symbol))

# Même société sous deux symboles : mêmes cours pendant les 60 premières séances communes.
heads = b.groupby("symbol").head(60)
counts = heads.groupby("symbol").close.size()
keys = heads[heads.symbol.isin(counts[counts == 60].index)].groupby("symbol").apply(lambda g: (str(g.ts_utc.iloc[0]), tuple(g.close.round(4))), include_groups=False)
groups = keys.groupby(keys).apply(lambda s: list(s.index))
aliases = [g for g in groups if len(g) > 1]
report["alias_groups"] = len(aliases)
report["alias_symbols_to_drop"] = sum(len(g) - 1 for g in aliases)
report["alias_examples"] = aliases[:15]
report["alias_contains_fb_meta"] = any({"FB", "META"} <= set(g) for g in aliases)

previous = b.groupby("symbol").close.shift().astype(float)
jumps = (b.close.astype(float) / previous.where(previous > 0) - 1).abs()
report["symbols_with_non_positive_close"] = sorted(b.loc[b.close <= 0, "symbol"].unique().tolist())[:20]
report["daily_moves_above_100pct"] = int((jumps > 1).sum())
report["symbols_with_such_moves"] = int(b.loc[jumps > 1, "symbol"].nunique())
report["non_positive_closes"] = int((b.close <= 0).sum())

# Symboles qu'on sait réutilisés : trous de cotation et niveau de prix.
gaps = b.assign(gap=b.groupby("symbol").ts_utc.diff().dt.days)
long_gap = gaps[gaps.gap > 30].groupby("symbol").size()
report["symbols_with_gap_over_30_days"] = int(len(long_gap))
report["suspects"] = {s: {"first": str(stats.loc[s, "first"])[:10], "last": str(stats.loc[s, "last"])[:10], "days": int(stats.loc[s, "days"]), "longest_gap_days": int(gaps[gaps.symbol == s].gap.max()), "first_close": float(b[b.symbol == s].close.iloc[0]), "last_close": float(b[b.symbol == s].close.iloc[-1])} for s in ("CA", "LB", "MON", "SBNY") if s in stats.index}

(ROOT / "reports" / "lab_2026-11" / "qc_universe.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(report, indent=1, ensure_ascii=False))
