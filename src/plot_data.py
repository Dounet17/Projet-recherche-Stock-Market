import pandas as pd
import matplotlib.pyplot as plt
import os

def plot_dow_jones():
    # 1. Retrouver le fichier CSV
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_path = os.path.join(script_dir, "..", "data", "raw", "dow_jones_2018_2024.csv")

    print("Chargement des données...")
    # On charge le CSV en disant que la colonne 'Date' est l'index temporel
    df = pd.read_csv(data_path, index_col=0, parse_dates=True)

    # 2. Création du graphique
    plt.figure(figsize=(12, 6))
    plt.plot(df.index, df['Close'], label='Dow Jones (Prix de clôture)', color='royalblue')
    
    # Esthétique du graphique
    plt.title('Évolution du Dow Jones (2018 - 2024)', fontsize=14)
    plt.xlabel('Année', fontsize=12)
    plt.ylabel('Points', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()

    # 3. Sauvegarde dans le dossier des résultats
    output_dir = os.path.join(script_dir, "..", "results", "figures")
    os.makedirs(output_dir, exist_ok=True) # Crée le dossier s'il n'existe pas
    output_file = os.path.join(output_dir, "dow_jones_history.png")
    
    plt.savefig(output_file, bbox_inches='tight')
    print(f"Graphique généré et sauvegardé ici : {os.path.abspath(output_file)}")

if __name__ == "__main__":
    plot_dow_jones()