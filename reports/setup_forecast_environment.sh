#!/usr/bin/env bash
# Prérequis : venv initial installé ; crée une surcouche isolée pour ROCm.
set -euo pipefail
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
if [[ ! -x .venv-forecast/bin/python ]]; then
    uv venv .venv-forecast --python venv/bin/python
fi
.venv-forecast/bin/python - <<'PY'
from pathlib import Path
import subprocess
import sysconfig
base_site = subprocess.check_output(['venv/bin/python', '-c', 'import sysconfig; print(sysconfig.get_paths()["purelib"])'], text=True).strip()
(Path(sysconfig.get_paths()['purelib']) / 'project_existing_environment.pth').write_text(base_site + '\n')
PY
uv pip install --python .venv-forecast/bin/python --no-deps \
    timesfm==3.0.2 chronos-forecasting==2.3.2 einops==0.8.2 accelerate==1.15.0
uv pip install --python .venv-forecast/bin/python --no-deps \
    'torch==2.6.0+rocm6.2.4' --index-url https://download.pytorch.org/whl/rocm6.2.4
.venv-forecast/bin/python reports/download_forecast_models.py
