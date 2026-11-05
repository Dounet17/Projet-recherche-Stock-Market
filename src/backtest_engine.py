import pandas as pd
import numpy as np
import os

def run_baseline_backtest(initial_budget=10000):
    # 1. Charger les données
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "..", "data", "raw", "dow_jones_2018_2024.csv")
    
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)

    # 2. Simulation d'achat au Jour 1
    prix_achat = df['Close'].iloc[0]
    nombre_actions = initial_budget / prix_achat

    # 3. Suivi quotidien du portefeuille 
    df['Portfolio_Value'] = df['Close'] * nombre_actions

    # --- CALCUL DU MAX DRAWDOWN ---
    df['Peak'] = df['Portfolio_Value'].cummax()
    df['Drawdown'] = ((df['Portfolio_Value'] - df['Peak']) / df['Peak']) * 100
    
    max_drawdown = df['Drawdown'].min() # La pire chute (valeur négative)
    date_pire_chute = df['Drawdown'].idxmin().strftime('%Y-%m-%d')
    valeur_au_plus_bas = df.loc[df['Drawdown'].idxmin(), 'Portfolio_Value']

    # --- CALCUL DU RATIO DE SHARPE
    daily_returns = df['Portfolio_Value'].pct_change().dropna()
    sharpe_ratio = np.sqrt(252) * (daily_returns.mean() / daily_returns.std())

    # 4. Résultats finaux au dernier jour
    valeur_finale = df['Portfolio_Value'].iloc[-1]
    profit = valeur_finale - initial_budget
    roi = (profit / initial_budget) * 100

    # 5. Affichage
    print("=== STRATÉGIE DE BASE : BUY AND HOLD ===")
    print(f"Budget initial : {initial_budget:.2f} €")
    print(f"Prix d'achat (Jan 2018) : {prix_achat:.2f} pts")
    print(f"Parts achetées : {nombre_actions:.4f}")
    print("-" * 45)
    print("PERFORMANCE FINALE (Déc 2024) :")
    print(f"Valeur finale : {valeur_finale:.2f} €")
    print(f"Profit net : +{profit:.2f} €")
    print(f"ROI : +{roi:.2f} %")
    print("-" * 45)
    print("ANALYSE DU RISQUE :")
    print(f"Max Drawdown : {max_drawdown:.2f} % (atteint le {date_pire_chute})")
    print(f"Valeur du portefeuille au plus bas : {valeur_au_plus_bas:.2f} €")
    print(f"Ratio de Sharpe : {sharpe_ratio:.2f} (Au-dessus de 1.0 = bon)")

if __name__ == "__main__":
    run_baseline_backtest()