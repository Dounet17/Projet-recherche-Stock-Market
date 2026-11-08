"""Registre des hypothèses : toute idée est inscrite avant le moindre calcul de rendement.

Le fichier canonique est `reports/lab_2026-11/registre_hypotheses.csv` ; ses règles sont dans
`reports/lab_2026-11/REGISTRE_HYPOTHESES.md`. Un lanceur appelle `require(identifiant)` avant tout calcul : il
s'arrête si l'hypothèse n'est pas inscrite ou si son protocole n'est pas figé.

    venv/bin/python src/registry.py          # contrôle du registre et résumé par statut
"""

import sys
from pathlib import Path

import pandas as pd

PATH = Path(__file__).resolve().parents[1] / "reports" / "lab_2026-11" / "registre_hypotheses.csv"
COLUMNS = ("id", "inscrite_le", "titre", "famille", "hypothese", "source", "inspiree_de_resultats_vus", "donnees",
           "conception", "validation", "variantes_max", "statut", "protocole", "resultat")
FAMILIES = ("heuristique", "adaptative", "hybride", "evenement", "reference")
STATUSES = ("proposee", "protocole_fige", "lancee", "echec", "nulle", "reussie", "abandonnee")
LAUNCHABLE = ("protocole_fige",)
DONE = ("echec", "nulle", "reussie", "abandonnee")


def load(path=PATH):
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def check(table):
    """Liste des problèmes du registre ; vide si tout est conforme."""
    problems = []
    missing = [c for c in COLUMNS if c not in table.columns]
    if missing:
        return [f"colonnes manquantes : {missing}"]
    if table.id.duplicated().any():
        problems.append(f"identifiants en double : {sorted(table.id[table.id.duplicated()])}")
    for row in table.itertuples(index=False):
        if row.famille not in FAMILIES:
            problems.append(f"{row.id} : famille inconnue {row.famille!r}")
        if row.statut not in STATUSES:
            problems.append(f"{row.id} : statut inconnu {row.statut!r}")
        if row.inspiree_de_resultats_vus not in ("oui", "non"):
            problems.append(f"{row.id} : inspiree_de_resultats_vus doit valoir oui ou non")
        if pd.isna(pd.to_datetime(row.inscrite_le, format="%Y-%m-%d", errors="coerce")):
            problems.append(f"{row.id} : date d'inscription invalide")
        if not row.variantes_max.isdigit() or int(row.variantes_max) < 1:
            problems.append(f"{row.id} : variantes_max doit être un entier positif")
        if row.statut in DONE and not row.resultat:
            problems.append(f"{row.id} : résultat manquant pour un statut terminé")
        if row.statut in LAUNCHABLE + ("lancee",) + DONE[:3] and not row.protocole:
            problems.append(f"{row.id} : protocole manquant")
        # Une idée née de résultats déjà vus ne peut pas se valider sur la période qui l'a inspirée.
        if row.inspiree_de_resultats_vus == "oui" and "2018-2024" in row.validation:
            problems.append(f"{row.id} : inspirée de 2018-2024, elle doit se valider ailleurs")
    return problems


def require(hypothesis_id, path=PATH):
    """Arrêt si l'hypothèse n'est pas inscrite, si le registre est invalide ou si son protocole n'est pas figé."""
    table = load(path)
    problems = check(table)
    if problems:
        raise RuntimeError("Registre invalide : " + " ; ".join(problems))
    row = table[table.id == hypothesis_id]
    if row.empty:
        raise RuntimeError(f"{hypothesis_id} n'est pas inscrite au registre : l'inscrire avant tout calcul")
    status = row.statut.iloc[0]
    if status not in LAUNCHABLE:
        raise RuntimeError(f"{hypothesis_id} a le statut {status!r} : seul un protocole figé peut être lancé")
    return row.iloc[0].to_dict()


if __name__ == "__main__":
    table = load()
    problems = check(table)
    print(f"{len(table)} hypothèses ; {'aucun problème' if not problems else str(len(problems)) + ' problèmes'}")
    for problem in problems:
        print(" -", problem)
    print(table.groupby("statut").size().to_string())
    sys.exit(1 if problems else 0)
