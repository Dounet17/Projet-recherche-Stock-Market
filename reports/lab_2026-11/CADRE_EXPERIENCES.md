# Cadre d'expérience sur le grand univers

Ajouté le 06/11/2026, pour tester des stratégies quotidiennes sur `data/universe_clean/`, actions disparues comprises. Lire d'abord `NETTOYAGE_DONNEES.md` et `PROTOCOLE.md`. L'intraday reste dans `src/backtest.py`.

## Écrire et lancer une stratégie

```python
from experiment import run_experiment, top_n
from universe_data import load_universe

def momentum(data, lookback=252, top=50):
    score = data.close.pct_change(lookback, fill_method=None)
    return top_n(score, n=top, tradable=data.tradable)

market = load_universe()
table = run_experiment(momentum, market, name="momentum", family="heuristic", lookback=[126, 252])
```

Une stratégie reçoit les données connues à la clôture et renvoie des poids par date. Une ligne vide signifie « aucun ordre ». Le moteur exécute à l'ouverture suivante : ne jamais décaler les poids soi-même.

`run_experiment` enchaîne, pour chaque combinaison de paramètres :
1. le contrôle anti-fuite ;
2. le backtest sous les trois hypothèses de sortie, et avec des frais doublés ;
3. la comparaison à SPY et à des portefeuilles tirés au hasard ;
4. l'inscription au journal `ledger_universe.csv`, et une p corrigée (Romano-Wolf) sur tous les essais de ce journal.

Le tableau est gardé dans `experiments/<name>.csv`. Relancer un essai du même nom remplace sa ligne : ne pas s'en servir pour effacer un essai raté.

## Ce que contient `data`

| Champ | Contenu |
|---|---|
| `open`, `high`, `low`, `close` | Cours ajustés. **Seuls les rapports entre deux dates ont du sens.** |
| `raw_close`, `volume` | Bruts. Les seuls valables pour un filtre de prix ou de liquidité. |
| `dollar_volume` | Médiane sur 20 séances du montant échangé, connue à la clôture. |
| `traded`, `tradable` | Échangé ; achetable (au moins 5 $ et 1 M$ par jour par défaut). |
| `cost_bps` | Coût par côté à l'ouverture de la date, fixé par la liquidité de la veille. |

Les sorties, les métadonnées et les références sont dans `market`, hors de portée d'une stratégie.

## Règles de simulation ajoutées

- **Disparition.** À la dernière séance L, la période rapporte `close(L) / ouverture * (1 + rendement de sortie) - 1`, sans frais. L'argent reste ensuite en liquidités, à 0 %, jusqu'au prochain ordre.
- **Ordre impossible.** Sans ouverture valide à la date d'exécution, ni achat ni vente, et l'ordre n'est pas reporté. Si la position bloquée fait dépasser 100 %, les autres cibles sont réduites à proportion.
- **Trou de cotation.** La position garde sa dernière ouverture connue ; le rendement est constaté à la reprise.
- **Fin de fenêtre.** Tout est vendu à la dernière ouverture avant ou à `end`, sans lire de prix ultérieur.
- **Cours suspects et ouvertures aberrantes.** Une séance `suspect_print` est manquante. Une ouverture hors de [1/3, 3] fois la clôture n'est pas un prix d'exécution (189 séances). **Un gain à travers un cours suspect est annulé, une perte est gardée** (389 hausses annulées, 346 titres) : c'est ce qui retire le faux +7 660 % de BCEI, et aussi quelques vraies hausses, donc une prudence assumée.

## Hypothèses à valider

Ces valeurs ont été choisies sans mesure et ne sont pas tirées de la littérature. Le résultat avec frais doublés en donne la sensibilité.

| Liquidité (montant médian par jour) | Coût par côté |
|---|---|
| Au moins 100 M$ | 5 pb |
| Au moins 10 M$ | 15 pb |
| Au moins 1 M$ | 40 pb |
| Moins, ou inconnue | 100 pb |

## Fuites connues que le contrôle automatique ne voit pas

Le contrôle tronque des données déjà nettoyées : il ne détecte que les fuites de la stratégie, pas celles du nettoyage.

1. **Niveau des cours ajustés.** `adj_close` est replacé sur le dernier cours du titre et intègre les dividendes futurs (AAPL : facteur de 1,023 selon qu'on s'arrête fin 2020 ou fin 2024). Une stratégie qui lit un niveau, et non un rapport, lit donc l'avenir.
2. **Allers-retours de `suspect_print`.** 75 séances sur 755 sont masquées parce que le cours s'est retourné **le lendemain**, dont 25 passent les filtres de prix et de liquidité (EXPR le 27/01/2021, par exemple). Une stratégie qui achète les fortes hausses évite donc ces chutes. Effet probablement faible, mais favorable : à contrôler pour toute stratégie de ce type.
3. **Sélection des titres.** `too_short` (moins de 20 séances) et `security_type` sont calculés sur toute la période ou avec des métadonnées de 2026.

## Limites

- Appartenance historique aux indices non reconstituée.
- Fondamentaux non branchés : `fundamentals_quarterly_dev.parquet` n'est pas dans `data`. À ajouter en respectant `filed`.
- Le portefeuille au hasard pioche parmi tous les titres achetables : il paie plus de frais qu'une stratégie sur grandes valeurs, et sert donc de repère, pas de preuve.
- Le verrou de 2025-2026 reste actif ; ce dataset n'existe pas encore pour cette période.

## Vérifications

```bash
venv/bin/python tests/test_lab.py
venv/bin/python tests/test_lab_lifecycle.py    # calculs à la main, écrits sans voir le moteur
venv/bin/python tests/test_universe_data.py
venv/bin/python tests/test_experiment.py       # dont 27 résultats publiés reproduits à l'identique
venv/bin/python reports/run_universe_control.py   # témoin de bout en bout, 36 s, 5,2 Go de RAM
```

Témoin, 2018-2024, 10 000 USD : poids égaux sur les 500 titres les plus liquides, chaque mois.

| | Capital final |
|---|---|
| Hypothèse centrale | 19 979 |
| Hypothèse optimiste | 19 991 |
| Hypothèse pessimiste | 19 415 |
| Frais doublés | 19 685 |
| SPY conservé | 24 531 |
| Hasard, médiane de 10 tirages | 10 740 |

Ce témoin ne démontre rien sur une stratégie : il vérifie la chaîne et donne un repère.
