"""Exécute un modèle avec reprise par lots : --family timesfm3 --device cuda."""

import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HSA_OVERRIDE_GFX_VERSION", "10.3.0")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import torch
from foundation_benchmark import OUT, ForecastAdapter, prepare_inputs, run_variant

parser = argparse.ArgumentParser()
parser.add_argument("--family", required=True, choices=["timesfm3", "chronos_synth", "chronos2", "kronos"])
parser.add_argument("--variants", nargs="+", default=["univariate", "market", "finbert", "jev"])
parser.add_argument("--device", default="cuda")
parser.add_argument("--batch-size", type=int, default=16)
parser.add_argument("--limit", type=int)
parser.add_argument("--sample-count", type=int, default=1)
args = parser.parse_args()
torch.set_num_threads(4)
if args.device == "cuda" and not torch.cuda.is_available():
    raise RuntimeError("GPU demandé mais indisponible")
reference, inputs = prepare_inputs()
adapter = ForecastAdapter(args.family, args.device, sample_count=args.sample_count)
runtime_path = OUT / f"runtime_{args.family}.json"
rows = json.loads(runtime_path.read_text()) if runtime_path.exists() else []
rows = [row for row in rows if row["variant"] not in args.variants]
for variant in args.variants:
    _, metadata = run_variant(adapter, variant, inputs["contexts"], inputs["timestamps"], args.batch_size, args.limit)
    rows.append(metadata)
    runtime_path.write_text(json.dumps(rows, indent=2) + "\n")
print(json.dumps(rows, indent=2), flush=True)
