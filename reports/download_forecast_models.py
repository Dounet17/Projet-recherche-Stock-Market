"""Télécharge les révisions exactes du benchmark, sans changer les poids publiés."""

import json
import subprocess
from pathlib import Path

from huggingface_hub import snapshot_download

ROOT = Path(__file__).resolve().parents[1]
metadata = json.loads((ROOT / "reports" / "foundation_benchmark_2026-10-25" / "metadata.json").read_text())
manifest = {}
for name, record in metadata["model_revisions"].items():
    patterns = ["config.json", "README.md", "step_market_284M/*"] if name == "kit" else None
    local = snapshot_download(record["model_id"], revision=record["revision"], allow_patterns=patterns)
    manifest[name] = {**record, "local_path": local}
    print(name, record["revision"], flush=True)
(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "forecast_models.json").write_text(json.dumps(manifest, indent=2) + "\n")
sources = {"timesfm": "https://github.com/google-research/timesfm.git", "Kronos": "https://github.com/shiyu-coder/Kronos.git", "KiT": "https://github.com/Luciferbobo/KiT.git"}
for name, revision in metadata["source_revisions"].items():
    dest = ROOT / "data" / "vendor" / name
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--filter=blob:none", sources[name], str(dest)], check=True)
    current = subprocess.check_output(["git", "-C", str(dest), "rev-parse", "HEAD"], text=True).strip()
    if current != revision:
        dirty = subprocess.check_output(["git", "-C", str(dest), "status", "--porcelain"], text=True).strip()
        if dirty:
            raise RuntimeError(f"Sources modifiées localement, révision inchangée : {dest}")
        subprocess.run(["git", "-C", str(dest), "fetch", "origin", revision], check=True)
        subprocess.run(["git", "-C", str(dest), "checkout", "--detach", revision], check=True)
