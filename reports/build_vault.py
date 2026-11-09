"""Génère un coffre Obsidian qui décrit le projet : sujet, données, stratégies, résultats, code.

Lancement : venv/bin/python -I reports/build_vault.py (quelques secondes), puis ouvrir `vault/`
dans Obsidian. Seules les métadonnées des fichiers sont lues (taille, nombre de lignes, noms de
colonnes), jamais les valeurs. Les dossiers dont le nom contient "holdout" ne sont pas parcourus.
Les liens du code sont relevés automatiquement ; descriptions et chiffres de synthèse sont écrits
ici à la main, depuis les rapports. Tout est régénéré, sauf `vault/Notes/` et `vault/.obsidian/`.
"""
import ast
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
VAULT = ROOT / "vault"
GENERATED = ["Sujet", "Données", "Stratégies", "Résultats", "Hypothèses", "Code", "Glossaire", "Annexes"]
ROOT_NOTE = "Projet"

# Une note = (dossier, étiquette, parent, corps). Le parent liste ses enfants automatiquement.
notes: dict[str, dict] = {}


def add(name, folder, tag, parent, body):
    if name in notes:
        raise ValueError(f"Note en double : {name}")
    notes[name] = {"folder": folder, "tag": tag, "parent": parent, "body": body.strip()}


# ---------------------------------------------------------------- Branches principales
add(ROOT_NOTE, "", "racine", None, """
Point de départ du coffre. Un modèle d'IA peut-il faire mieux qu'un placement passif ?

- [[Points ouverts]] : ce qui reste à faire ou à faire valider.
- La vue en graphe (Ctrl+G) montre tout le projet. Les flèches suivent le trajet réel :
  données → script → données produites → rapport.

Ce coffre est généré par `reports/build_vault.py`. Les notes personnelles vont dans `Notes/` :
c'est le seul dossier de notes conservé à la régénération.
""")
add("Sujet", "Sujet", "sujet", ROOT_NOTE, "Ce que le projet doit faire, et pourquoi.")
add("Données", "Données", "donnees", ROOT_NOTE, """
Tout ce qui est stocké dans `data/`, non versionné. Chaque fiche donne la taille mesurée, le nombre
de lignes et les colonnes, le script qui produit la donnée et ceux qui l'utilisent.
""")
add("Stratégies", "Stratégies", "strategie", ROOT_NOTE, """
Les stratégies testées, classées selon l'énoncé. Les colonnes ne se comparent pas d'une ligne à
l'autre si la période ou l'univers diffèrent : chaque stratégie se lit face à sa référence.

| Stratégie | Famille | Période | Capital final | Référence |
|---|---|---|---:|---:|
| [[Moyenne mobile 200]] | Heuristique | 2018-2024 | 12 487 | 16 490 (buy and hold moyen) |
| [[Momentum 12 mois]] | Heuristique | 2018-2024 | 18 160 | 24 531 (SPY) |
| [[P-E bas]] | Heuristique | 2018-2024 | 14 372 | 24 531 (SPY) |
| [[Classement par ML]] | Adaptative | 2018-2024 | 9 670 | 24 531 (SPY) |
| [[Rotation top 3]] | Heuristique | 2025-2026 | 10 050 | 13 274 (panier égal) |
| [[Filtre QQQ sur TSLA]] | Heuristique | 2025-2026 | 8 527 | 10 070 (TSLA) |
| [[Ciblage de volatilité]] | Heuristique | 2025-2026 | 10 178 | 10 070 (TSLA) |
| [[Sortie sur news]] | Hybride | 2025-2026 | 8 090 | 10 070 (TSLA) |

Départ de 10 000 USD partout. Conclusion à ce stade : rien ne bat le placement passif de façon
démontrée, ce qui est cohérent avec l'hypothèse de départ.
""")
add("Résultats", "Résultats", "resultat", ROOT_NOTE, """
Les rapports du projet, recopiés sans modification de leur texte. Une section « Liens dans le
projet » est ajoutée à la fin de chacun, d'après les fichiers qu'il cite.
""")
add("Code", "Code", "code", ROOT_NOTE, "Modules de `src/`, scripts de `reports/` et notebooks, avec leurs dépendances réelles.")
add("Glossaire", "Glossaire", "glossaire", ROOT_NOTE, "Les notions financières utilisées, expliquées simplement.")
add("Points ouverts", "", "racine", ROOT_NOTE, """
Repris de `CLAUDE.md` au 07/11/2026.

**À faire valider par le professeur**
- L'élargissement à un grand univers d'actions.
- L'usage de la période 2025-2026.
- L'usage de l'USD au lieu de l'euro.

**Données**
- Vérifier sur les sources les chiffres de [[data news]] avant l'étude de la surprise de résultats.
- Relire `known_securities.csv`, écrit de mémoire, et vérifier les références de Shumway.
- Reconstituer l'appartenance historique aux indices.
- Nettoyer 2025-2026 avec les mêmes règles, sans réglage.

**Stratégies**
- [[P-E]] et [[BPA]] restent insuffisamment traités alors que l'énoncé les demande.
- Les hypothèses de [[RAPPORT_VALIDATION]] sont closes : ne pas ajuster ces règles pour les retester sur 2025-2026.

**Binôme**
- La partie Trump / Dow Jones revient à Dounet17 : aucun résultat dans ce dossier.
""")

# ---------------------------------------------------------------- Sujet
add("Question de recherche", "Sujet", "sujet", "Sujet", """
Un modèle d'IA peut-il obtenir de bons résultats en prédisant le marché, mieux qu'un simple placement
passif (type ETF S&P 500 ou Nasdaq) ?

L'hypothèse de départ est que non : les résultats seront probablement proches du hasard. Le but est
de tout mettre en place pour maximiser le rendement, puis d'expliquer honnêtement pourquoi chaque
approche réussit ou échoue. Voir [[Hypothèse de l'équipe]].
""")
add("Énoncé officiel", "Sujet", "sujet", "Sujet", """
- Tester sur un indice : « the EURO STOXX 50, DOW JONES or similar ».
- Les publications du président américain peuvent faire bouger les marchés de façon imprévisible.
- Trois familles à comparer : **heuristics**, **adaptive**, **hybrid**. Voir [[Stratégies]].
- Objectifs : collection de données temporelles, implémentation des stratégies, évaluation sur un
  budget virtuel de 10 000 €, analyse des résultats.
- Livrables : une présentation orale et un article scientifique.
""")
add("Hypothèse de l'équipe", "Sujet", "sujet", "Sujet", """
Il ne s'agit pas d'être le premier à réagir à une annonce, mais de réagir **avant la masse des humains**.
Il y aurait une fenêtre exploitable entre les robots les plus rapides et les traders humains, qui
doit rester rentable après [[Frais de transaction]].

Pour la tester, il faut des prix à la minute et l'heure exacte de chaque publication : [[data tsla_1min]], [[data musk_posts]].
""")
add("Répartition du binôme", "Sujet", "sujet", "Sujet", """
- **DavidTom** : Elon Musk sur Tesla (TSLA). QQQ sert seulement de référence. Voir [[data musk_posts]].
- **Dounet17** : Dow Jones (DIA et composants), avec Trump comme personnalité naturelle, à confirmer.

Périmètre confirmé le 25/10/2026 : ce dossier reste sur Musk / Tesla.
""")
add("Règles de méthode", "Sujet", "sujet", "Sujet", """
- **Pas de look-ahead** : une décision n'utilise que ce qui est connu à ce moment. Voir [[Look-ahead]].
- Découpage chronologique, jamais de mélange aléatoire.
- Heure des posts toujours recalculée depuis l'identifiant. Voir [[src timeutils]].
- Toujours compter les [[Frais de transaction]].
- La période 2025-2026 est désormais connue : voir [[RAPPORT_VALIDATION]].
- Une référence pour juger : voir [[Buy and hold]].
""")

# ---------------------------------------------------------------- Données
for hub, text in {
    "Prix": "Cours de bourse, à la journée et à la minute. Source : API Alpaca.",
    "Réseaux sociaux": "Publications de Musk et leur classification. Les données Trump relèvent de la partie de Dounet17.",
    "News": "Dépêches Benzinga fournies par l'API News d'Alpaca.",
    "Fondamentaux et SEC": "Comptes publiés, dépôts officiels et publications de résultats.",
    "Contexte de marché": "Facteurs de French et séries macroéconomiques de la FRED.",
    "Calculs intermédiaires": "Tables de calcul produites par les expériences, à relancer plutôt qu'à modifier.",
    "Modèles préentraînés": "Poids et sources des modèles de prévision essayés.",
}.items():
    add(hub, "Données", "donnees", "Données", text)

# nom, chemin relatif à data/, branche, description, producteurs, pièges
DATA = [
    ("universe", "universe", "Prix", "Barres quotidiennes brutes du grand univers américain, actions vivantes et disparues, 2016-2024 : 17 418 symboles, 21,5 millions de lignes.",
     ["download_universe", "download_universe_extra", "download_universe_gaps"],
     ["Dossiers `*holdout_*` à ne pas lire pendant la recherche.",
      "API Alpaca : `asof` suit les changements de symbole et peut fusionner ou masquer des séries. Utiliser `asof=-` pour énumérer."]),
    ("universe_clean", "universe_clean", "Prix", "Dataset quotidien nettoyé : 18 745 titres, 20,9 millions de lignes, 8 119 actions dont 2 845 disparues. Base de tous les tests sur le grand univers.",
     ["clean_universe"],
     ["Filtres de prix et de liquidité sur `close` et `volume` (bruts).", "`suspect_print` se traite comme une valeur manquante.",
      "Publier les résultats sous les trois hypothèses de sortie : `exit_return_base`, `_optimistic`, `_pessimistic`.",
      "BPA à ne jamais utiliser avant `filed`.", "3 404 titres non identifiés (0,6 % du volume en dollars). Lire [[NETTOYAGE_DONNEES]] avant tout usage."]),
    ("lab_daily_adjusted", "lab_daily_adjusted.parquet", "Prix", "Barres quotidiennes ajustées de l'univers réduit du laboratoire du 06/11/2026.", ["download_lab_data"], []),
    ("lab_holdout", "lab_holdout", "Prix", "Données de la validation unique 2025-2026. Non parcouru par ce coffre.", ["prepare_validation_data"],
     ["Validation déjà consommée : voir [[RAPPORT_VALIDATION]]. Ne pas s'en servir pour régler une règle."]),
    ("tsla_1min", "tsla_1min.parquet", "Prix", "Barres à la minute de TSLA, heures étendues comprises.", ["notebook 01_collecte_donnees"],
     ["Une barre est étiquetée par son début : pour un post à 14:52:28, la référence est la clôture de la barre 14:51."]),
    ("qqq_1min", "qqq_1min.parquet", "Prix", "Barres à la minute de QQQ, utilisé comme référence de marché.", ["notebook 01_collecte_donnees"], []),
    ("daily_bars", "daily_bars.parquet", "Prix", "Barres quotidiennes de la partie Musk / Tesla.", ["notebook 01_collecte_donnees"], []),
    ("calendar", "calendar.parquet", "Prix", "Calendrier des séances de bourse.", ["notebook 01_collecte_donnees"], []),
    ("foundation_regular_bars", "foundation_regular_bars.parquet", "Prix", "Barres régulières préparées pour les modèles préentraînés.", ["src foundation_benchmark"], []),
    ("foundation_inputs", "foundation_inputs.npz", "Prix", "Entrées numériques figées des modèles préentraînés.", ["src foundation_benchmark"], []),
    ("musk_posts", "musk_posts.parquet", "Réseaux sociaux", "Publications d'Elon Musk, 2018-2024.", ["notebook 01_collecte_donnees"],
     ["Heure à recalculer depuis l'identifiant, jamais depuis la colonne date : `(id >> 22) + 1288834974657`.",
      "Lire les identifiants comme texte ou `int64`, jamais en float."]),
    ("raw", "raw", "Réseaux sociaux", "Fichiers bruts des sources de publications, avant fusion.", ["src collect"], []),
    ("finbert_musk_tesla", "finbert_musk_tesla.parquet", "Réseaux sociaux", "Cache des classifications FinBERT des posts Tesla.", ["notebook 02_finbert_vs_jev"],
     ["FinBERT classe 82 % des posts neutres."]),
    ("jev_musk_tesla", "jev_musk_tesla.parquet", "Réseaux sociaux", "Cache des classifications Jev, pour ne pas rappeler l'API payante.", ["notebook 02_finbert_vs_jev"],
     ["Fuite possible : un modèle entraîné après 2024 peut connaître la réaction du marché."]),
    ("news", "news", "News", "News complètes 2018-2024 : 1 399 118 articles uniques, tri et lecture par FinBERT, écart à l'estimation cité dans les dépêches.",
     ["download_all_news", "build_news_table", "run_news_finbert", "verify_surprise_exhibits"],
     ["Exclure les commentaires de marché avant toute étude (causalité inversée).",
      "Aucun résumé avant 2020, 30 % de résumés au total.",
      "`earnings_surprise.parquet` n'est pas un consensus vérifié ; `available_at` n'est qu'une borne prudente. Lire [[TRI_NEWS]].",
      "Ne pas se fier à `alias_symbols` pour dater un symbole."]),
    ("news_coverage", "news_coverage", "News", "Échantillon de 240 titres servant à mesurer la couverture, sans lecture de rendement.", ["measure_news_coverage"], []),
    ("tsla_news", "tsla_news.parquet", "News", "News sur TSLA.", ["notebook 01_collecte_donnees"], []),
    ("sec", "sec", "Fondamentaux et SEC", "Archives de la SEC extraites jusqu'à fin 2024 : comptes publiés, dépôts et liens symbole-société.",
     ["download_sec_bulk", "download_sec_instances", "extract_sec_dev", "extract_sec_links"],
     ["Le champ `accepted` de `dev_filings.parquet` est faux de 4 à 5 heures dans 30 % des 8-K de résultats. Ne jamais s'en servir comme heure.",
      "Couverture : 93 % des disparues du top 1 000, mais 50 % de l'ensemble des disparues."]),
    ("events", "events", "Fondamentaux et SEC", "Table des publications de résultats, études associées et heures réelles des 8-K.",
     ["build_earnings_events", "download_8k_times", "import_8k_times_pi", "download_8k_exhibits_pi"],
     ["Utiliser `accepted_new_york` de `eight_k_times/`, qui n'est qu'une borne de l'heure de diffusion."]),
    ("tsla_earnings", "tsla_earnings.parquet", "Fondamentaux et SEC", "Dates de résultats et BPA de TSLA (28 publications sur 2018-2024).", ["notebook 01_collecte_donnees"], []),
    ("french", "french", "Contexte de marché", "Facteurs de French et portefeuilles sectoriels, coupés à fin 2024.", ["download_context_data"], []),
    ("fred", "fred", "Contexte de marché", "Séries de contexte de la FRED.", ["download_context_data"], []),
    ("reference", "reference", "Calculs intermédiaires", "Buy and hold de chaque action et de chaque groupe. Voir [[REFERENCE_BUY_AND_HOLD]].", ["build_reference"],
     ["Les secteurs décrivent le marché et ne servent pas à juger une stratégie."]),
    ("per_stock", "per_stock", "Calculs intermédiaires", "Comparaisons action par action d'une règle et du buy and hold.", ["src per_stock"], []),
    ("ml", "ml", "Calculs intermédiaires", "Résultats du modèle de classement.", ["run_step5_ml_rank"], []),
    ("vendor", "vendor", "Modèles préentraînés", "Sources tierces des modèles de prévision.", ["download_forecast_models"], []),
    ("forecast_models", "forecast_models.json", "Modèles préentraînés", "Révisions épinglées des poids des modèles.", ["download_forecast_models"], []),
]
DATA_NAMES = {d[0] for d in DATA}
DATA_FILES = {d[0] for d in DATA if Path(d[1]).suffix}


def human_size(num):
    for unit in ("o", "Ko", "Mo", "Go"):
        if num < 1024 or unit == "Go":
            return f"{num:.0f} {unit}" if unit == "o" else f"{num:.1f} {unit}".replace(".", ",")
        num /= 1024


def tree_stats(path):
    """Taille et nombre de fichiers, sans jamais entrer dans un dossier holdout."""
    if path.is_file():
        return path.stat().st_size, 1
    size = count = 0
    for child in path.iterdir():
        if "holdout" in child.name:
            continue
        child_size, child_count = tree_stats(child)
        size += child_size
        count += child_count
    return size, count


def parquet_line(path):
    """Métadonnées seules : aucune valeur du fichier n'est lue."""
    meta = pq.read_metadata(path)
    columns = ", ".join(f"`{c}`" for c in meta.schema.to_arrow_schema().names[:30])
    extra = " ..." if meta.num_columns > 30 else ""
    rows = f"{meta.num_rows:_}".replace("_", " ")
    return f"| `{path.name}` | {human_size(path.stat().st_size)} | {rows} | {columns}{extra} |"


def data_content(rel):
    path = ROOT / "data" / rel
    if "holdout" in rel:
        return "Contenu volontairement non parcouru."
    if not path.exists():
        return "**Fichier absent de cette machine.**"
    size, count = tree_stats(path)
    lines = [f"**Taille** : {human_size(size)}, {count} fichier(s). **Chemin** : `data/{rel}`", ""]
    parquets = [path] if path.suffix == ".parquet" else sorted(p for p in path.glob("*.parquet")) if path.is_dir() else []
    parquets = [p for p in parquets if "holdout" not in p.name]
    if parquets:
        lines += ["| Fichier | Taille | Lignes | Colonnes |", "|---|---:|---:|---|"] + [parquet_line(p) for p in parquets] + [""]
    if path.is_dir():
        others = sorted(p for p in path.iterdir() if "holdout" not in p.name and p.suffix != ".parquet")
        folders = [p for p in others if p.is_dir()]
        files = [p for p in others if p.is_file()]
        if folders:
            lines.append("**Sous-dossiers** : " + ", ".join(f"`{p.name}/` ({tree_stats(p)[1]})" for p in folders))
        if files:
            shown = ", ".join(f"`{p.name}`" for p in files[:6])
            lines.append(f"**Autres fichiers ({len(files)})** : {shown}" + (" ..." if len(files) > 6 else ""))
    return "\n".join(lines)


# ---------------------------------------------------------------- Relevé automatique du code
CODE_SOURCES = {p.stem: p for p in sorted((ROOT / "src").glob("*.py"))}
SCRIPT_SOURCES = {p.stem: p for p in sorted((ROOT / "reports").glob("*.py")) if p.stem != "build_vault"}
NOTEBOOKS = {p.stem: p for p in sorted((ROOT / "notebooks").glob("*.ipynb"))}


def code_text(path):
    if path.suffix != ".ipynb":
        return path.read_text(encoding="utf-8")
    cells = json.loads(path.read_text(encoding="utf-8"))["cells"]
    return "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "code")


def docstring(path):
    if path.suffix == ".ipynb":
        return ""
    return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""


def data_tokens(text):
    """Noms de données cités par le code : data/x, "data" / "x", ou DATA / "x" quand DATA est data/."""
    found = set(re.findall(r'data/([\w.-]+)', text)) | set(re.findall(r'"data"\s*/\s*f?"([\w.-]+)"', text))
    if re.search(r'^\s*DATA\s*=\s*ROOT\s*/\s*"data"\s*$', text, re.M):
        found |= set(re.findall(r'\bDATA\s*/\s*"([\w.-]+)"', text))
    found |= set(re.findall(r'\bdata\s*/\s*"([\w.-]+)"', text))
    # Noms composés en f-string : seuls les fichiers ont un nom assez précis pour une recherche simple.
    found |= {name for name in DATA_FILES if re.search(rf'\b{name}\b', text)}
    return {t.split(".")[0] for t in found} & DATA_NAMES


def imported_modules(text):
    names = set(re.findall(r'^\s*(?:from|import)\s+(\w+)', text, re.M))
    return names & set(CODE_SOURCES)


def script_group(stem):
    if stem.startswith(("download", "extract", "import", "prepare", "list")):
        return "Scripts de collecte"
    if stem.startswith("run"):
        return "Scripts d'expérience"
    return "Scripts de préparation et de contrôle"


for hub, text in {
    "Modules src": "Le code réutilisable de `src/`.",
    "Scripts de collecte": "Téléchargements et extractions. Certains tournent sur le Raspberry Pi.",
    "Scripts de préparation et de contrôle": "Nettoyage, tables de synthèse, contrôles qualité et audits.",
    "Scripts d'expérience": "Lancement des tests de stratégies.",
    "Notebooks": "Exploration et première collecte.",
    "Interface web": "Page de présentation des résultats dans `web/`, préparée par [[script build_web_data]].",
}.items():
    add(hub, "Code", "code", "Code", text)

PRODUCES = defaultdict(set)  # note du code → données produites
PRODUCER_OF = {}
for name, _, _, _, producers, _ in DATA:
    PRODUCER_OF[name] = producers
    for producer in producers:
        PRODUCES[producer].add(name)


def code_note_name(stem, kind):
    return {"module": f"src {stem}", "script": f"script {stem}", "notebook": f"notebook {stem}"}[kind]


CITED_BY = defaultdict(list)
inventory = [("module", s, p) for s, p in CODE_SOURCES.items()] + [("script", s, p) for s, p in SCRIPT_SOURCES.items()] + [("notebook", s, p) for s, p in NOTEBOOKS.items()]
for kind, stem, path in inventory:
    text = code_text(path)
    name = code_note_name(stem, kind)
    key = name if kind != "script" else stem
    produced = PRODUCES.get(key, set())
    rel = path.relative_to(ROOT)
    cited = data_tokens(text) - produced
    for token in sorted(cited):
        CITED_BY[token].append(name)
    body = [docstring(path).split("\n\n")[0], "", f"**Fichier** : `{rel}`"]
    if kind == "script":
        body.append(f"**Lancement** : `venv/bin/python {rel}`")
    modules = imported_modules(text) - {stem}
    if modules:
        body += ["", "**Code utilisé**"] + [f"- [[src {m}]]" for m in sorted(modules)]
    if produced:
        body += ["", "**Données produites**"] + [f"- [[data {d}]]" for d in sorted(produced)]
    if cited:
        body += ["", "**Autres données citées dans le code** : " + ", ".join(f"`{d}`" for d in sorted(cited))]
    parent = {"module": "Modules src", "notebook": "Notebooks"}.get(kind) or script_group(stem)
    add(name, "Code/" + {"module": "src", "script": "scripts", "notebook": "notebooks"}[kind], "code", parent, "\n".join(body))

for name, rel, hub, description, producers, warnings in DATA:
    body = [description, "", data_content(rel), ""]
    labels = []
    for producer in producers:
        if producer.startswith(("notebook ", "src ")):
            labels.append(f"`{producer}`")
        else:
            labels.append(f"`reports/{producer}.py`")
    body.append("**Produit par** : " + ", ".join(labels))
    if CITED_BY[name]:
        body += ["", "**Utilisé par**"] + [f"- [[{user}]]" for user in CITED_BY[name]]
    if warnings:
        body += ["", "**Pièges à connaître**"] + [f"- {w}" for w in warnings]
    add(f"data {name}", "Données", "donnees", hub, "\n".join(body))

# ---------------------------------------------------------------- Stratégies
for hub, text in {
    "Références": "Ce qu'il faut battre pour qu'une stratégie ait un intérêt.",
    "Heuristiques": "Règles simples et fixes, écrites à l'avance. Famille *heuristics* de l'énoncé.",
    "Adaptatives": "Modèles qui apprennent des données ou lisent du texte. Famille *adaptive* de l'énoncé.",
    "Hybrides": "Combinaison de prix et de texte. Famille *hybrid* de l'énoncé.",
}.items():
    add(hub, "Stratégies", "strategie", "Stratégies", text)

add("Buy and hold", "Stratégies", "strategie", "Références", """
Acheter et ne plus toucher. C'est la référence principale du projet.

- Sur 10 000 USD en 2018-2024 : **SPY 24 531 USD**, buy and hold moyen du grand univers **16 356 USD**.
- Référence pour juger : le buy and hold moyen du même univers, avec SPY à côté comme placement achetable.

Sources : [[REFERENCE_BUY_AND_HOLD]], [[script build_reference]], [[data reference]].
""")
add("Témoin liquidité", "Stratégies", "strategie", "Références", """
Les 500 titres les plus liquides à poids égaux, sans idée de stratégie : **19 982 USD** sur 2018-2024.
Il bat les tests A et B, c'est donc une meilleure référence que le hasard pour juger la sélection.

Source : [[RESULTATS_TESTS_A_B]].
""")
add("Moyenne mobile 200", "Stratégies", "strategie", "Heuristiques", """
Rester investi dans une action tant que son cours est au-dessus de sa moyenne sur 200 séances.

- **Résultat 2018-2024** : 12 487 USD contre 16 490 pour le [[Buy and hold]] : moins de capital,
  chutes réduites, [[Alpha]] proche de 0.

Sources : [[RESULTATS_ETAPE_3]], [[script run_step3_sma200]], [[src stock_rules]].
""")
add("Bollinger et RSI 2", "Stratégies", "strategie", "Heuristiques", """
Pari sur le retour à la moyenne : acheter une action qui vient de baisser de façon inhabituelle.

- **Résultat 2018-2024** : encore en dessous de [[Moyenne mobile 200]] face au buy and hold de chaque action.

Sources : [[RESULTATS_ETAPE_4]], [[script run_step4_mean_reversion]], [[src stock_rules]].
""")
add("Momentum 12 mois", "Stratégies", "strategie", "Heuristiques", """
Chaque mois, 50 titres à poids égaux parmi ceux qui ont le plus monté sur 252 séances (test A).

- **Résultat 2018-2024** : 18 160 USD, contre 24 531 pour SPY et 19 982 pour le [[Témoin liquidité]].
- [[Sharpe]] de 0,42 et [[Drawdown]] de -59,9 %. Les [[Frais de transaction]] pèsent lourd : les doubler coûte 2 612 USD.

Sources : [[RESULTATS_TESTS_A_B]], [[script run_test_a_momentum]].
""")
add("P-E bas", "Stratégies", "strategie", "Heuristiques", """
Chaque mois, 50 titres au plus bas [[P-E]] parmi les 1 000 actions les plus liquides (test B).

- **Résultat 2018-2024** : 14 372 USD, contre 24 531 pour SPY.
- [[Sharpe]] de 0,32 et [[Drawdown]] de -61,1 %.

Sources : [[RESULTATS_TESTS_A_B]], [[script run_test_b_value]].
""")
add("Rotation top 3", "Stratégies", "strategie", "Heuristiques", """
Tenir les 3 meilleures de 7 grandes valeurs.

- **Développement 2018-2024** : 196 415 USD contre 95 603 pour le panier égal.
- **Validation 2025-2026** : 10 050 USD contre 13 274 : échec, p de Holm de 1,000. Hypothèse close.

Sources : [[RAPPORT_VALIDATION]], [[src price_lab]], [[script run_validation_once]].
""")
add("Filtre QQQ sur TSLA", "Stratégies", "strategie", "Heuristiques", """
Tenir TSLA seulement quand le marché, mesuré par QQQ, est bien orienté.

- **Développement 2018-2024** : 320 181 USD contre 203 541 pour TSLA conservée.
- **Validation 2025-2026** : 8 527 USD contre 10 070 : échec. Hypothèse close.

Sources : [[RAPPORT_VALIDATION]], [[src price_lab]], [[script run_validation_once]].
""")
add("Ciblage de volatilité", "Stratégies", "strategie", "Heuristiques", """
Réduire la position sur TSLA quand elle devient trop agitée.

- **Développement 2018-2024** : 81 105 USD contre 203 541 pour TSLA conservée.
- **Validation 2025-2026** : 10 178 USD contre 10 070 : échec au critère fixé, [[Sharpe]] inférieur et [[Alpha]] négatif.
- Propriété la plus stable : [[Drawdown]] plus faible sur les deux périodes.

Sources : [[RAPPORT_VALIDATION]], [[src price_lab]], [[script run_validation_once]].
""")
add("Classement par ML", "Stratégies", "strategie", "Adaptatives", """
Arbres de gradient boosting qui classent toutes les actions chaque mois, avec réentraînement annuel.

- **Résultat 2018-2024** : 9 670 USD. Aucun apport démontré au-delà de la faible volatilité et de la liquidité. Pas de fuite trouvée à l'audit.

Sources : [[RESULTATS_ETAPE_5]], [[AUDIT_ML_RANK]], [[script run_step5_ml_rank]], [[src ml_rank]].
""")
add("Prévision par modèles préentraînés", "Stratégies", "strategie", "Adaptatives", """
TimesFM-3, Chronos-2, Chronos-2-Synth et Kronos-small sur TSLA à 15 minutes, 2022-2024.

- **Direction correcte** : entre 48,42 % et 50,31 %, soit le niveau du hasard.
- Aucune configuration complète rentable avec 5 points de base de frais par côté.
- KiT : pilote de 36 origines seulement, avec un checkpoint qui connaît TSLA : ce n'est pas une validation.

Sources : [[Resultats_modeles_preentraines_2026-10-25]], [[script run_foundation_benchmark]], [[src foundation_benchmark]], [[data forecast_models]].
""")
add("Réaction aux posts de Musk", "Stratégies", "strategie", "Adaptatives", """
Étude d'événements : TSLA réagit-elle à +1, +5, +15 et +60 minutes après un post ?

- FinBERT et Jev ne s'accordent que sur 55 % des posts.
- Seule la question `impact` de Jev annonce la réaction, à +1 minute (Spearman 0,13), pour un effet d'environ 0,05 %.
- L'effet disparaît dès +5 minutes, et ce rendement inclut la minute du post : il n'est pas réalisable.

Sources : [[notebook 02_finbert_vs_jev]], [[src sentiment]], [[data musk_posts]], [[data finbert_musk_tesla]], [[data jev_musk_tesla]].
""")
add("Publications de résultats", "Stratégies", "strategie", "Adaptatives", """
Le cours réagit-il aux résultats trimestriels, et en reste-t-il quelque chose à gagner ensuite ?

- Le cours réagit au jour J, mais aucun effet exploitable après, en données quotidiennes.
- L'étude de la vraie surprise attend la vérification des chiffres.

Sources : [[RESULTATS_EVENEMENTS]], [[AUDIT_ETUDE_RESULTATS]], [[script build_earnings_events]], [[data events]], [[data news]].
""")
add("Prix et sentiment Musk", "Stratégies", "strategie", "Hybrides", """
Backtest à 15 minutes sur TSLA, 2022-2024, sans frais puis avec 5 points de base par côté :

| Variante | Sans frais | Avec frais |
|---|---:|---:|
| Prix seuls | -21,10 % | -82,45 % |
| Prix + Jev | -18,54 % | -81,90 % |
| Prix + FinBERT | -24,28 % | -83,44 % |
| Passif TSLA | | +5,40 % |

Pas d'avantage social robuste : ce résultat décrit ce protocole simple, sur une période déjà explorée.

Sources : [[Backtest_Musk_Tesla_2026-10-25]], [[script run_musk_backtest]], [[src backtest]], [[Frais de transaction]].
""")
add("Sortie sur news", "Stratégies", "strategie", "Hybrides", """
Tenir TSLA, et sortir quand les news sont négatives (stratégie exploratoire).

- **Développement 2018-2024** : 327 218 USD contre 203 541 pour TSLA conservée.
- **Validation 2025-2026** : 8 090 USD contre 10 070 : échec. Hypothèse close.

Sources : [[RAPPORT_VALIDATION]], [[RAPPORT]], [[src social_lab]], [[script run_validation_once]].
""")

# ---------------------------------------------------------------- Glossaire
for name, text in {
    "Backtest": "Rejouer une stratégie sur des données passées, comme si on découvrait les jours un par un. Voir [[Look-ahead]].",
    "Look-ahead": "Erreur qui consiste à utiliser une information pas encore connue au moment de la décision. Elle crée de faux gains.",
    "Sharpe": "Gain moyen au-delà du taux sans risque, rapporté aux variations du portefeuille. Plus il est haut, mieux c'est.",
    "Drawdown": "La pire chute depuis un sommet. Un drawdown de -50 % veut dire que le portefeuille a perdu la moitié de sa valeur à ce moment.",
    "Alpha": "Le gain qui reste une fois retiré ce qu'explique l'exposition au marché. Un alpha nul indique qu'il n'y a pas de talent démontré.",
    "BPA": "Bénéfice par action (EPS en anglais) : le bénéfice de la société divisé par son nombre d'actions.",
    "P-E": "Price / Earnings : le cours divisé par le [[BPA]] des 12 derniers mois. Un P/E bas signifie une action peu chère par rapport à ses bénéfices.",
    "Frais de transaction": "Le coût de chaque achat ou vente, ici exprimé en points de base : 5 pb valent 0,05 %. Très pénalisant quand on échange souvent.",
    "Holm": "Correction appliquée quand on fait plusieurs tests, car plus on teste, plus un faux positif est probable. Seuil de preuve fixé à 0,05.",
    "Volatilité": "L'ampleur des variations d'un cours. Mesurée en 2018-2024 : DIA 19 %, SPY 19 %, QQQ 24 %, TSLA 63 %.",
    "8-K": "Dépôt officiel d'une société américaine à la SEC pour annoncer un événement important, par exemple ses résultats.",
    "Survie": "Biais du survivant : n'étudier que les actions encore cotées aujourd'hui gonfle les résultats. D'où les disparues dans [[data universe_clean]].",
}.items():
    add(name, "Glossaire", "glossaire", "Glossaire", text)

# ---------------------------------------------------------------- Rapports
for hub, text in {
    "Exploration Musk Tesla": "Octobre 2026 : premiers backtests intraday et modèles préentraînés.",
    "Laboratoire quotidien": "06/11/2026 : 244 essais sur 2018-2024, puis validation unique sur 2025-2026.",
    "Grand univers": "Nettoyage du dataset, références et tests sur toutes les actions.",
    "Événements et news": "Publications de résultats, tri des news et audits.",
    "État de l'art et sources": "Recherches sur les modèles et sur les données disponibles.",
}.items():
    add(hub, "Résultats", "resultat", "Résultats", text)

REPORT_PARENTS = {
    "Backtest_Musk_Tesla_2026-10-25": "Exploration Musk Tesla",
    "Resultats_modeles_preentraines_2026-10-25": "Exploration Musk Tesla",
    "PROTOCOLE": "Laboratoire quotidien",
    "RAPPORT_VALIDATION": "Laboratoire quotidien",
    "RAPPORT": "Laboratoire quotidien",
    "AUDIT_PRIX": "Laboratoire quotidien",
    "CADRE_EXPERIENCES": "Grand univers",
    "NETTOYAGE_DONNEES": "Grand univers",
    "REFERENCE_BUY_AND_HOLD": "Grand univers",
    "RESULTATS_TESTS_A_B": "Grand univers",
    "RESULTATS_ETAPE_3": "Grand univers",
    "RESULTATS_ETAPE_4": "Grand univers",
    "RESULTATS_ETAPE_5": "Grand univers",
    "AUDIT_ML_RANK": "Grand univers",
    "RESULTATS_EVENEMENTS": "Événements et news",
    "AUDIT_ETUDE_RESULTATS": "Événements et news",
    "COUVERTURE_NEWS": "Événements et news",
    "TRI_NEWS": "Événements et news",
    "AUDIT_TRI_NEWS": "Événements et news",
    "AUDIT_TRI_NEWS_2": "Événements et news",
    "Alternatives_prediction_boursiere_2026-10-25": "État de l'art et sources",
    "Etat_projet_et_etat_art_2026-10-25": "État de l'art et sources",
    "Datasets bourse et réseaux sociaux": "État de l'art et sources",
}
report_paths = sorted((ROOT / "reports").rglob("*.md")) + sorted((ROOT / "research_notes").rglob("*.md"))
images = {}
report_names = {p.stem for p in report_paths}
stem_counts = defaultdict(int)
for _path in report_paths:
    stem_counts[_path.stem] += 1


def report_links(text, path=None):
    """Liens vers le code, les données et les autres rapports que ce rapport cite."""
    links = set()
    for stem in re.findall(r'([\w-]+)\.py\b', text):
        if stem in CODE_SOURCES:
            links.add(f"src {stem}")
        elif stem in SCRIPT_SOURCES:
            links.add(f"script {stem}")
    for token in re.findall(r'data/([\w-]+)', text):
        if token in DATA_NAMES:
            links.add(f"data {token}")
    for folder, stem in re.findall(r'(?:([\w-]+)/)?([\w-]+)\.md\b', text):
        if stem not in report_names:
            continue
        if stem_counts.get(stem, 1) == 1:
            links.add(stem)
        elif folder and any(p.stem == stem and p.parent.name == folder for p in report_paths):
            links.add(f"{folder} {stem}")
        elif path is not None and any(p.stem == stem and p.parent == path.parent for p in report_paths):
            links.add(f"{path.parent.name} {stem}")
    return links


def report_note_name(path):
    """Nom de note d'un rapport ; préfixé par son dossier quand deux rapports portent le même nom."""
    return f"{path.parent.name} {path.stem}" if stem_counts[path.stem] > 1 else path.stem


for path in report_paths:
    text = path.read_text(encoding="utf-8")

    def keep_image(match, base=path.parent):
        source = (base / match.group(2)).resolve()
        if not source.is_file():
            return match.group(0)
        target = f"{path.stem}-{source.name}"
        images[target] = source
        return f"![[{target}]]"

    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', keep_image, text)
    links = report_links(text, path) - {report_note_name(path)}
    parent = REPORT_PARENTS.get(path.stem, "État de l'art et sources")
    source_rel = path.relative_to(ROOT)
    footer = [f"\n\n---\n\n## Liens dans le projet\n\n*Copie de `{source_rel}`, à modifier dans le fichier d'origine.*"]
    footer += [f"- [[{link}]]" for link in sorted(links)]
    add(report_note_name(path), "Résultats", "resultat", parent, text + "\n".join(footer))


# ---------------------------------------------------------------- Hypothèses du registre
REGISTRY = ROOT / "reports" / "lab_2026-11" / "registre_hypotheses.csv"
STATUS_LABELS = {"proposee": "proposée", "protocole_fige": "protocole figé", "lancee": "lancée", "echec": "échec",
                 "nulle": "nulle", "reussie": "réussie", "abandonnee": "abandonnée"}


def safe_title(text):
    """Titre utilisable comme nom de fichier Obsidian (ni deux-points, ni barre oblique)."""
    text = re.sub(r"(?<=\w)/(?=\w)", "-", text)            # P/E -> P-E, comme ailleurs dans le coffre
    return re.sub(r"\s*[:/\\|?*<>\"]\s*", " - ", text).strip()


def report_link(rel):
    """Note d'un rapport cité par chemin, ou None s'il n'existe pas dans le coffre."""
    if not rel:
        return None
    path = (ROOT / rel).resolve()
    return report_note_name(path) if path in {p.resolve() for p in report_paths} else None


if REGISTRY.exists():
    import csv
    with REGISTRY.open(encoding="utf-8") as handle:
        registry_rows = list(csv.DictReader(handle))
    hypothesis_note = {r["id"]: f"{r['id']} {safe_title(r['titre'])}" for r in registry_rows}
    table = ["| Hypothèse | Famille | Statut | Résultat |", "|---|---|---|---|"]
    table += [f"| [[{hypothesis_note[r['id']]}]] | {r['famille']} | {STATUS_LABELS.get(r['statut'], r['statut'])} | {r['resultat']} |" for r in registry_rows]
    add("Hypothèses", "Hypothèses", "hypothese", ROOT_NOTE, """
Toutes les idées de stratégie, inscrites dans `reports/lab_2026-11/registre_hypotheses.csv` avant le moindre calcul
de rendement. Règles : [[REGISTRE_HYPOTHESES]]. Filtre du graphe : `tag:#hypothese`.

""" + "\n".join(table))
    for r in registry_rows:
        lines = [f"**{r['id']}**, inscrite le {r['inscrite_le']}. Statut : **{STATUS_LABELS.get(r['statut'], r['statut'])}**.", "",
                 f"> {r['hypothese']}", "",
                 f"- Famille : {r['famille']}",
                 f"- Source de l'idée : {r['source']}",
                 f"- Née de résultats déjà vus : {r['inspiree_de_resultats_vus']}",
                 f"- Données : {r['donnees']}",
                 f"- Conception : {r['conception']} ; validation : {r['validation']} ; variantes au plus : {r['variantes_max']}"]
        if r["resultat"]:
            lines.append(f"- Résultat : {r['resultat']}")
        documents = [(label, report_link(r[key])) for label, key in (("Protocole", "protocole"), ("Rapport", "rapport"))]
        lines += [f"- {label} : [[{name}]]" for label, name in documents if name]
        related = [hypothesis_note[h] for h in r["liee_a"].split() if h in hypothesis_note]
        if related:
            lines += ["", "## Hypothèses liées", ""] + [f"- [[{name}]]" for name in related]
        add(hypothesis_note[r["id"]], "Hypothèses", "hypothese", "Hypothèses", "\n".join(lines))


# ---------------------------------------------------------------- Écriture et contrôles
def check_and_link():
    children = defaultdict(list)
    for name, note in notes.items():
        if note["parent"]:
            if note["parent"] not in notes:
                sys.exit(f"Parent inconnu : {note['parent']} pour {name}")
            children[note["parent"]].append(name)
    for parent, kids in children.items():
        notes[parent]["body"] += "\n\n## Branches\n\n" + "\n".join(f"- [[{kid}]]" for kid in kids)
    edges = defaultdict(set)
    broken = []
    for name, note in notes.items():
        # Les blocs de code des rapports ne contiennent pas de liens.
        visible = re.sub(r"```.*?```|`[^`\n]*`", "", note["body"], flags=re.S)
        for target in re.findall(r'(?<!!)\[\[([^\]|#]+)', visible):
            if target in notes:
                edges[name].add(target)
            else:
                broken.append((name, target))
    if broken:
        sys.exit("Liens cassés : " + "; ".join(f"{a} -> {b}" for a, b in broken))
    seen, todo = {ROOT_NOTE}, [ROOT_NOTE]
    while todo:
        for target in edges[todo.pop()]:
            if target not in seen:
                seen.add(target)
                todo.append(target)
    missing = set(notes) - seen
    if missing:
        sys.exit("Notes non rattachées à la racine : " + ", ".join(sorted(missing)))
    return sum(len(v) for v in edges.values())


def write_vault():
    VAULT.mkdir(exist_ok=True)
    for folder in GENERATED:
        shutil.rmtree(VAULT / folder, ignore_errors=True)
    (VAULT / "Notes").mkdir(exist_ok=True)
    for name, note in notes.items():
        path = VAULT / note["folder"] / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        parent = f"Branche : [[{note['parent']}]]\n\n" if note["parent"] else ""
        path.write_text(f"---\ntags: [{note['tag']}]\n---\n{parent}{note['body']}\n", encoding="utf-8")
    (VAULT / "Annexes").mkdir(exist_ok=True)
    for target, source in images.items():
        shutil.copy2(source, VAULT / "Annexes" / target)
    config = VAULT / ".obsidian"
    config.mkdir(exist_ok=True)
    graph = config / "graph.json"
    colors = [("racine", 0xE5484D), ("sujet", 0x8E6BD8), ("donnees", 0x3B82C4), ("strategie", 0xE08A2E),
              ("resultat", 0x3FA66B), ("hypothese", 0xD6409F), ("code", 0x8A8F98), ("glossaire", 0xD4B13F)]
    defaults = [{"query": f"tag:#{tag}", "color": {"a": 1, "rgb": rgb}} for tag, rgb in colors]
    if graph.exists():
        # Réglages faits dans Obsidian conservés : on ajoute seulement les groupes de couleur manquants.
        # Obsidian ouvert réécrit ce fichier depuis sa mémoire : le fermer avant de lancer ce script.
        settings = json.loads(graph.read_text(encoding="utf-8"))
        groups = settings.setdefault("colorGroups", [])
        known = {g.get("query") for g in groups}
        missing = [g for g in defaults if g["query"] not in known]
        if missing:
            groups.extend(missing)
            graph.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    else:
        graph.write_text(json.dumps({
            "collapse-filter": False, "search": "", "showTags": False, "showAttachments": False,
            "hideUnresolved": False, "showOrphans": True, "collapse-color-groups": False,
            "colorGroups": defaults,
            "collapse-display": False, "showArrow": True, "textFadeMultiplier": 0, "nodeSizeMultiplier": 1.2,
            "lineSizeMultiplier": 1, "collapse-forces": True, "centerStrength": 0.5, "repelStrength": 12,
            "linkStrength": 1, "linkDistance": 180, "scale": 0.4, "close": False,
        }, indent=2), encoding="utf-8")
    app = config / "app.json"
    if not app.exists():
        app.write_text(json.dumps({"attachmentFolderPath": "Annexes", "newFileFolderPath": "Notes", "newFileLocation": "folder"}, indent=2), encoding="utf-8")


edge_count = check_and_link()
write_vault()
counts = defaultdict(int)
for note in notes.values():
    counts[note["tag"]] += 1
print(f"{len(notes)} notes, {edge_count} liens, {len(images)} images : {VAULT}")
print(dict(counts))
