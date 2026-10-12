import yfinance as yf
import pandas as pd
import os

def fetch_dow_jones_data():
    ticker = "^DJI"
    start_date = "2018-01-01"
    end_date = "2024-12-31"

    print(f"Téléchargement des données pour {ticker}...")
    df = yf.download(ticker, start=start_date, end=end_date)

    if df.empty:
        print("Erreur de téléchargement.")
        return

    # Si yfinance a rajouté la double ligne d'en-tête, on l'aplatit.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
    # ---------------------------

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "..", "data", "raw")
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "dow_jones_2018_2024.csv")
    df.to_csv(output_file)

    print(f"Succès ! CSV propre sauvegardé ici : {os.path.abspath(output_file)}")

if __name__ == "__main__":
    fetch_dow_jones_data()