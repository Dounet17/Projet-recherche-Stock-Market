# Étape 5 : premier modèle de classement des actions

Rapport du 06/11/2026, période de développement seulement : ce n'est pas une validation. Modèle figé avant le premier lancement sur les vraies données, sans réglage, une seule variante journalisée (`step5_ml_rank__top=50`, 7e essai de `ledger_universe.csv`).

```bash
venv/bin/python reports/run_step5_ml_rank.py   # environ 1 minute 30, réécrit la même ligne du journal
venv/bin/python tests/test_ml_rank.py
```

Code : `src/ml_rank.py`. Audit complet : `ml/AUDIT_ML_RANK.md`. Scores : `data/ml/` (non versionné).

## Le modèle

**Principe.** Il ne prédit ni un cours ni la direction du marché, mais le rang d'une action parmi les autres sur le mois suivant. Les 50 mieux classées sont achetées à poids égaux, avec le même moteur et les mêmes frais que le test A.

**Architecture.** `HistGradientBoostingRegressor` de scikit-learn : 200 petits arbres de 15 feuilles, chacun corrigeant les erreurs des précédents (taux d'apprentissage de 0,05, au moins 200 observations par feuille, régularisation L2 de 1).

**Données.** Environ 3 000 actions achetables chaque mois, résumées par 13 indicateurs de prix et de liquidité, classés de 0 à 1 parmi les actions du mois : rendements sur 1, 3, 6 et 12 mois, 12 mois sans le dernier, volatilité sur 20 et 60 séances, écart aux moyennes 50 et 200 séances, chute depuis le plus haut sur un an, RSI 14, liquidité et son évolution. La cible inclut les faillites. Le modèle n'utilise ni fondamentaux, ni news, ni réseaux sociaux.

**Apprentissage.** Réentraînement chaque 1er janvier, sur les mois déjà terminés : 2017 seul pour tester 2018, soit très peu de données au début ; 169 904 observations sur 59 mois pour 2021.

## Résultats sur 10 000 USD, 2018-2024

Vocabulaire : le Sharpe mesure le gain par unité de risque, le drawdown la pire chute depuis un sommet, et l'alpha ce qui reste une fois retirée l'exposition au marché.

| | Modèle | Test A, momentum | Témoin, 500 plus liquides | Buy and hold moyen, toutes achetables | SPY |
|---|---:|---:|---:|---:|---:|
| **Capital final** | **9 670** | 18 160 | 19 982 | 16 356 | 24 531 |
| Hypothèse pessimiste | 9 281 | 16 257 | 19 418 | 15 949 | |
| Frais doublés | 7 717 | 15 548 | 19 688 | | |
| Sans frais | 12 110 | | | | |
| Sharpe | 0,09 | 0,42 | 0,57 | | 0,79 |
| Pire chute | -50,8 % | -59,9 % | -36,5 % | | -32,0 % |
| Rotation (achats et ventes) par an | 20,9 fois | 8,9 fois | 3,2 fois | | 0,29 fois |

| Par année | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Modèle | -19,7 % | +28,9 % | +18,5 % | -15,4 % | -25,1 % | +6,3 % | +17,0 % |
| SPY | -6,9 % | +34,0 % | +18,2 % | +28,6 % | -18,0 % | +24,7 % | +26,5 % |

- **Contre SPY.** Écart annuel de -13,3 %, alpha de -12,7 %, p unilatérale de 0,996, p corrigée sur 7 essais de 1,000.
- **Contre le hasard.** Il bat seulement 30 % de 20 portefeuilles tirés au hasard (médiane de 10 278), pourtant plus exposés aux petites valeurs.

## Ce que le modèle a appris

| Indicateur | Rang moyen des 50 choisis (0,5 = comme l'univers) |
|---|---:|
| Liquidité | 0,71 |
| Rendement sur 12 mois sans le dernier | 0,63 |
| Volatilité sur 60 séances | 0,43 |
| RSI 14 | 0,37 |
| Rendement sur 1 mois | 0,38 |

Il préfère les grandes valeurs liquides, peu volatiles, en hausse sur un an et en légère baisse récente. Titres les plus souvent choisis : MSFT (49 mois sur 84), AAPL (44), GOOGL (38), AMZN (35). Ces préférences ressemblent à des effets connus, ce qui rend le modèle plausible.

## Mesure de l'information, avant frais

| Mesure | Valeur |
|---|---:|
| Corrélation de rang entre score et rendement du mois, moyenne sur 83 mois | 0,034 (t = 3,01 ; 2,75 en tenant compte de l'autocorrélation) |
| Part de mois positifs | 60 % |
| Décile le mieux classé moins le moins bien classé, par mois | +0,44 % (t = 0,84) |
| 50 premiers moins moyenne de l'univers, par mois | -0,26 % (t = -0,92) |

| Décile de score | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Rendement mensuel moyen | 0,21 % | 0,63 % | 0,83 % | 0,77 % | 0,99 % | 0,98 % | 0,91 % | 1,00 % | 0,87 % | 0,65 % |

## Lecture

1. **Échec net sur l'objectif.** Même sans frais, le modèle (12 110) reste sous le buy and hold moyen (16 356) et loin de SPY.
2. **Un t de 3 qui ne prouve pas un apport.** Il repère un peu mieux les mauvaises actions (décile 1), pas les meilleures : le décile 10 est moins bon que les déciles du milieu. Comme le portefeuille n'achète que le haut du classement, il ne profite pas de cette information.
3. **Le modèle ne fait pas mieux que deux facteurs simples.** Selon l'audit, la faible volatilité seule atteint une corrélation de 0,059, et la liquidité seule 0,033, contre 0,034 pour le modèle. Une fois ces deux effets retirés, il reste 0,006 (t = 0,86). **Il n'y a donc pas d'apport démontré du machine learning.**
4. **Pas de signal réactif.** Décaler les indicateurs de 3 mois laisse la corrélation presque intacte (0,056 contre 0,050 sur les mêmes mois) : le modèle capte des caractéristiques lentes, pas une information récente.
5. **Les frais pèsent lourd.** Il remplace 86 % du portefeuille chaque mois (43 titres sur 50) et perd ainsi 2 440 USD. C'est un défaut de la construction : rien ne l'incite à garder ses positions.
6. **Résultat fragile, dans un sens comme dans l'autre.** Décembre 2024 seul fait passer le capital de 10 212 à 9 670 USD. Le meilleur titre apporte à lui seul plus que le gain moyen total des 50 (158 %). La hiérarchie change donc facilement, mais pas la conclusion.

## Contrôles

**Audit indépendant de Codex, en lecture seule, sans fuite trouvée dans le modèle :**

- Indicateurs, cibles et tous les scores reconstruits sans notre code, écart maximal de 0. En 2021, la dernière cible apprise finit le 02/12/2020, et retirer les 1 342 sorties futures ne change rien à l'entraînement.
- **Placebo.** Avec la cible mélangée à l'intérieur de chaque date, sur 2018, 2021 et 2024 et 20 graines, la corrélation tombe à -0,0008 contre 0,050 sur les mêmes mois.
- Capital et scores identiques à travers les répétitions, les processus, les graines et le nombre de threads.
- Défaut corrigé : le diagnostic remplaçait un titre choisi sans rendement mesurable, ce qui n'affectait qu'un mois et pas le backtest.

`lab.check_no_lookahead` passe. Sept tests vérifient notamment qu'un signal planté est retrouvé et que le bruit n'en fabrique pas.

## Limites

- **Une seule architecture et aucun réglage.** Ce résultat ne dit rien d'autres modèles, d'un réseau de neurones ou de la prédiction d'autres horizons.
- **Période et portefeuille.** Période très favorable aux très grandes valeurs. Un portefeuille de 50 titres à poids égaux ne peut pas exploiter la capacité à éviter les mauvaises actions.
- **Fuite du nettoyage.** Les 70 cours de développement masqués à cause du lendemain subsistent. Aucun ne tombe sur une décision utile ici, mais leur effet indirect n'est pas mesuré.
- **Données manquantes.** 452 sélections sur 4 200 n'ont pas de momentum sur 252 séances (titres récents).
- **Hypothèses inchangées.** Paliers de frais à valider, première position le 03/01/2018, fiscalité non simulée (20,9 rotations par an seraient pénalisées).

## Une piste, non testée

Le modèle semble mieux éviter les mauvaises actions que trouver les meilleures. Retirer son décile 1 d'un portefeuille large, avec une faible rotation, serait une hypothèse testable. C'est **une idée née en regardant ce résultat** : elle compterait comme un nouvel essai et devrait être présentée comme telle.
