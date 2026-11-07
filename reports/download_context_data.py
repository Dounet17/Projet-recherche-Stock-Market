"""Données de contexte, gratuites et sans clé, coupées à fin 2024 avant d'être gardées.

- Facteurs quotidiens de Fama et French : marché, taille, valeur, rentabilité, investissement, momentum.
- Séries de marché FRED : volatilité implicite, taux, pétrole, dollar, écart de crédit. Ce sont des cours, peu
  révisés, à la différence de la macroéconomie (PIB, emploi), non téléchargée ici pour cette raison.

Depuis la racine : venv/bin/python reports/download_context_data.py
"""

import io
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from reference import parse_french_csv

FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
FRENCH_FILES = {"factors5": "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", "momentum": "F-F_Momentum_Factor_daily_CSV.zip"}
FRED_SERIES = {"VIXCLS": "vix", "DGS2": "treasury_2y", "DGS10": "treasury_10y", "DTB3": "tbill_3m", "T10Y2Y": "curve_10y_2y", "DCOILWTICO": "oil_wti", "DTWEXBGS": "dollar_broad", "BAMLH0A0HYM2": "high_yield_spread"}
START, END = "2015-01-01", "2024-12-31"

french_dir, fred_dir = ROOT / "data" / "french", ROOT / "data" / "fred"
fred_dir.mkdir(parents=True, exist_ok=True)


def get(url):
    """Par curl : FRED ne répond pas au client HTTP standard de Python depuis cette machine."""
    for attempt in range(5):
        result = subprocess.run(["curl", "-sS", "-L", "-m", "60", "--fail", url], capture_output=True)
        if result.returncode == 0:
            return result.stdout
        print("nouvel essai", url[-40:], result.returncode, flush=True)
        time.sleep(10 * (attempt + 1))
    raise RuntimeError(f"Téléchargement impossible : {url}")


for name, file in FRENCH_FILES.items():
    archive = zipfile.ZipFile(io.BytesIO(get(FRENCH_URL + file)))
    sections = parse_french_csv(archive.read(archive.namelist()[0]).decode("latin-1"))
    for section, frame in sections.items():
        assert frame.index.max() <= pd.Timestamp(END)
        frame.to_parquet(french_dir / f"{name}_{section}.parquet")
        print(name, section, frame.index.min().date(), frame.index.max().date(), frame.columns.tolist(), flush=True)

columns = {}
for series, label in FRED_SERIES.items():
    text = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={START}&coed={END}").decode()
    frame = pd.read_csv(io.StringIO(text))
    frame.columns = ["date", label]
    frame["date"] = pd.to_datetime(frame.date)
    values = pd.to_numeric(frame.set_index("date")[label], errors="coerce").loc[:END]
    columns[label] = values
    print(series, label, values.first_valid_index().date(), values.last_valid_index().date(), int(values.notna().sum()), flush=True)
pd.DataFrame(columns).sort_index().to_parquet(fred_dir / "market_context.parquet")
