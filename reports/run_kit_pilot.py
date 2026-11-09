"""Pilote KiT sur la première séance de chaque mois à midi (36 origines fixées).

Fenêtres natives 1200/120, huit trajectoires, seize étapes Euler ; évaluation
des ouvertures à t et t+15, comme les autres modèles. Ce pilote séparé ne
remplace pas une évaluation complète des 18 000 décisions.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", "10.3.0")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "data" / "vendor" / "KiT"))
import numpy as np
import pandas as pd
import torch
from foundation_benchmark import OUT, predicted_trade_return, prepare_inputs
from kit_v1.data.calendar import bars_per_day
from kit_v1.data.normalize import load_stats
from kit_v1.infer import (denormalize_paths, flow_sample, load_model_and_config,
                          paths_to_ohlcv, prepare_inference_window)

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int)
ap.add_argument("--paths", type=int, default=8)
ap.add_argument("--steps", type=int, default=16)
ap.add_argument("--device", default="cuda")
ap.add_argument("--precision", default="fp16", choices=["fp32", "fp16"])
args = ap.parse_args()
torch.set_num_threads(4)
reference, _ = prepare_inputs()
ny = reference.entry_ts.dt.tz_convert("America/New_York")
noon = reference[(ny.dt.hour == 12) & (ny.dt.minute == 0)].copy()
noon["month"] = noon.entry_ts.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.to_period("M")
selected = noon.groupby("month", sort=True).head(1)
if args.limit is not None:
    selected = selected.head(args.limit)
selected.to_parquet(OUT / "kit_pilot_origins.parquet")
manifest = json.loads((ROOT / "data" / "forecast_models.json").read_text())
bundle = Path(manifest["kit"]["local_path"]) / "step_market_284M"
model, cfg = load_model_and_config(str(bundle / "step_market_284M.pt"), "tiny", 0)
model.to(args.device).eval()
stats = load_stats(bundle / "stats.json")
inst = json.loads((bundle / "instruments.json").read_text())["TSLA"]
bars = pd.read_parquet(ROOT / "data" / "foundation_regular_bars.parquet")
# KiT horodate ses barres par leur FIN, et utilise des heures locales.
bars["datetime"] = (bars.ts_utc + pd.Timedelta(minutes=1)).dt.tz_convert("America/New_York").dt.tz_localize(None)
cal = pd.read_parquet(ROOT / "data" / "calendar.parquet")
trading_days = cal.date.to_numpy(dtype="datetime64[D]")
Lc, Lh = cfg.data.window_for("1m")
keep = Lc + int(np.ceil(12 * cfg.data.vol_ema_half_life_days * bars_per_day("us", "1m"))) + 8
folder = OUT / "chunks" / "kit_pilot"
folder.mkdir(parents=True, exist_ok=True)
paths_out, rows = [], []
for i, row in selected.iterrows():
    cache = folder / f"{i:06d}_k{args.paths}_s{args.steps}_{args.precision}.npz"
    if cache.exists():
        saved = np.load(cache)
        opens, seconds = saved["paths"], float(saved["seconds"])
    else:
        known_end = (row.entry_ts - pd.Timedelta(minutes=1)).tz_convert("America/New_York").tz_localize(None)
        hist = bars[bars.datetime <= known_end].tail(keep)
        win = prepare_inference_window(hist, "us", "1m", Lc=Lc, Lh=Lh, stats=stats, soft_clip_c=cfg.data.soft_clip_c, half_life_days=cfg.data.vol_ema_half_life_days, sector_id=inst["sector"], inst_id=inst["vocab_index"], trading_days=trading_days)
        if win["n_pad"] or win["future_timestamps"][1] - pd.Timedelta(minutes=1) != row.entry_ts.tz_convert("America/New_York").tz_localize(None):
            raise ValueError("Alignement KiT invalide")
        start = time.perf_counter()
        result = flow_sample(model, win["x_ctx"], win["cond"], Lh=Lh, steps=args.steps, n_paths=args.paths, solver="euler", generator=torch.Generator().manual_seed(20261025 + i), device=torch.device(args.device), chunk_size=args.paths, precision=args.precision)
        if args.device == "cuda":
            torch.cuda.synchronize()
        seconds = time.perf_counter() - start
        features = denormalize_paths(result, "us", "1m", stats, c=cfg.data.soft_clip_c)[0]
        prices = paths_to_ohlcv(features, win["prev_close"], win["prev_ema"], win["half_life_bars"])
        opens = prices["open"][:, :17]
        predicted_trade_return(opens)
        np.savez_compressed(cache, paths=opens, seconds=seconds)
    paths_out.append(opens)
    predicted = float(np.median(opens, axis=0)[16] / np.median(opens, axis=0)[1] - 1)
    rows.append({"reference_index": i, "entry_ts": str(row.entry_ts), "predicted_return": predicted, "actual_return": row.asset_return, "seconds": seconds})
    print(f"KiT pilote {len(rows)}/{len(selected)} : {seconds:.2f} s", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "kit_pilot.csv", index=False)
np.savez_compressed(OUT / "kit_pilot_paths.npz", paths=np.stack(paths_out), reference_indices=selected.index.to_numpy())
(OUT / "kit_pilot_metadata.json").write_text(json.dumps({"paths": args.paths, "euler_steps": args.steps, "precision": args.precision, "device": args.device, "context": Lc, "native_horizon": Lh, "evaluated_horizon_min": 15, "selection": "première séance de chaque mois à 12 h New York", "rows": len(rows), "training_cutoff": cfg.data.train_end, "tsla_embedding_id": inst["vocab_index"], "scope": "pilote descriptif séparé ; période antérieure à la borne de préentraînement"}, indent=2) + "\n")
