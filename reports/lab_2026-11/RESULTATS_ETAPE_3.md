# Étape 3 : moyenne mobile sur 200 séances, action par action

Rapport du 06/11/2026, chiffres mis à jour sur la version corrigée et déterministe du nettoyage, période de développement seulement : ce n'est pas une validation. Règle figée avant le premier lancement, une seule variante journalisée (`step3_sma200_by_stock`, journal `ledger_universe.csv`).

```bash
venv/bin/python reports/run_step3_sma200.py   # environ 1 minute, réécrit la même ligne du journal
venv/bin/python tests/test_per_stock.py
```

Code : `src/per_stock.py` (une autre règle tient en une fonction). Résultats : `per_stock/` et, pour le détail, `data/per_stock/` (non versionné).

## La question

Pour chaque action, vaut-il mieux suivre la règle que garder cette même action ? On compare donc une action à elle-même, sur les mêmes dates et avec les mêmes frais.

## La règle

Investi si la clôture dépasse la moyenne des 200 dernières séances (au moins 180 valides), sinon en liquidités. Vérifiée chaque jour, exécutée à l'ouverture suivante. Une moyenne mobile sert à suivre la tendance : l'idée est de sortir avant le gros d'une baisse.

Achats : premier jour de bourse de chaque mois, de janvier 2018 à fin 2024, jusqu'à 670 523 comparaisons action, date et horizon. Chaque action est un petit portefeuille indépendant, et l'argent n'est jamais déplacé de l'une à l'autre. Liquidités à 0 %, comme dans le protocole, puis en sensibilité au rendement de BIL (bons du Trésor).

## Résultats

### 10 000 USD à parts égales, achat le 02/01/2018, jusqu'à fin 2024

Vocabulaire : le Sharpe mesure le gain par unité de risque ; le drawdown, la pire chute depuis un sommet ; le bêta, la sensibilité au marché ; l'alpha, ce qui reste une fois cette sensibilité retirée.

| Toutes achetables (2 908 titres) | Règle | Règle, liquidités en BIL | Buy and hold des mêmes titres | SPY |
|---|---:|---:|---:|---:|
| Capital final | 12 487 | 13 471 | 16 490 | 24 531 |
| Par an | 3,2 % | | 7,4 % | 13,7 % |
| Volatilité | 9,5 % | | 18,3 % | 18,4 % |
| Sharpe, sans retirer le taux sans risque | 0,38 | | 0,48 | 0,79 |
| Sharpe au-delà du taux sans risque | | 0,27 | 0,36 | |
| Pire chute du portefeuille | -15,4 % | | -36,6 % | -32,0 % |
| Exposition moyenne, en dollars | 51 % | 51 % | 87 % | 100 % |
| Rotation par an | 6,7 fois | | 0,26 fois | 0,29 fois |

| Univers | Actions | Règle | Buy and hold | La règle gagne sur | Avec BIL |
|---|---:|---:|---:|---:|---:|
| 500 plus liquides | 493 | 14 772 | 20 376 | 25,8 % | 31,4 % |
| 1 000 plus liquides | 986 | 13 941 | 18 773 | 28,5 % | 34,5 % |
| Toutes achetables | 2 908 | 12 487 | 16 490 | 31,9 % | 40,2 % |

Sensibilités, toutes achetables, capital moyen : hypothèse optimiste 12 490 contre 16 500, pessimiste 12 180 contre 16 080, frais doublés 11 370 contre 16 430. La règle gagne alors sur 32,8 % et 26,5 % des titres.

### Toutes les dates d'achat, en moyenne, toutes achetables

| Horizon | Dates | Règle, moyenne par an | Buy and hold, moyenne par an | Règle, médiane par an | Buy and hold, médiane par an | La règle gagne sur | Pire et meilleure date | Dates où la moyenne de la règle gagne |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 an | 72 | 3,4 % | 9,3 % | -2,0 % | 4,8 % | 36,4 % | 4 % à 75 % | 29 % |
| 3 ans | 48 | 4,7 % | 8,9 % | 0,1 % | 4,9 % | 37,1 % | 20 % à 47 % | 4 % |
| 5 ans | 24 | 3,6 % | 7,5 % | -0,2 % | 3,9 % | 33,8 % | 26 % à 38 % | 0 % |

### Quand et où la règle aide

- **Selon la date.** Sur un an, elle gagne sur 75 % des actions achetées en avril 2019, qui traversent le Covid, et sur 4 % de celles achetées en avril 2020, juste après le creux : le rebond s'est fait sans elle.
- **Selon le secteur, sur 5 ans.** Seuls l'énergie (56 % des comparaisons) et les télécoms (53 %) dépassent la moitié, deux secteurs en difficulté sur la période. Les services aux collectivités sont le pire cas (20 %).

### Par action

| Toutes achetables | Règle | Buy and hold |
|---|---:|---:|
| Sharpe médian | 0,10 | 0,30 |
| Pire chute médiane | -48,9 % | -63,1 % |
| Part des actions où la règle a un meilleur Sharpe | 22,2 % | |
| Part où sa pire chute est plus faible | 75,7 % | |
| Capital rapporté à celui du buy and hold, médiane | 0,77 | |

## Lecture

1. **La règle ne bat pas le buy and hold en capital.** Elle perd sur environ deux actions sur trois, à tous les horizons, dans tous les univers et sous toutes les hypothèses testées.
2. **C'est une assurance, pas une source de gain.** Elle divise par deux la volatilité et par plus de deux la chute du portefeuille, mais aussi le gain. Une fois retirée la baisse d'exposition, il ne reste presque rien : alpha de -0,2 % par an (intervalle à 95 % de -3,5 % à +3,2 %) avec des liquidités à 0 %, et de -0,4 % (de -3,7 % à +3,1 %) avec BIL, au-delà du taux sans risque.
3. **Le Sharpe du portefeuille n'est pas nettement différent.** Avec BIL et au-delà du taux sans risque, 0,27 contre 0,36 (écart de -0,48 à +0,28). On ne peut pas conclure qu'elle fait mieux ou moins bien par unité de risque.
4. **L'écart de capital n'est pas statistiquement net.** Écart annuel contre son buy and hold de -4,0 % (intervalle de -12,4 % à +4,9 %), p unilatérale de 0,82. Une hypothèse « elle gagne » n'est pas soutenue, ce qui ne prouve pas qu'elle perd toujours.
5. **Contre SPY, elle ne soutient aucun avantage.** p unilatérale de 0,99 ; p corrigée sur les 6 essais du journal de 0,999.
6. **Une explication possible, non mesurée ici.** Les rebonds rapides se feraient en grande partie quand la règle est sortie. Les résultats par date d'achat vont dans ce sens, sans le démontrer.

## Contrôles

- **Moteur.** Chaque ligne de cas synthétiques, de vraies lignes et le cas des liquidités en BIL sont égaux à `lab.backtest`. Le buy and hold recalculé par ce code est égal à la table de référence.
- **Anti-fuite.** `lab.check_no_lookahead` passe.
- **Audit indépendant de Codex, en lecture seule.** 123 lignes recalculées sans notre code, dont faillites et ordres bloqués, soit 336 résultats sans écart ; signal concordant sur 74 523 observations ; agrégats et décalage de BIL corrects. Défauts corrigés à sa suite : exposition et rotation moyennées par titre au lieu d'être pondérées en dollars (51 % et non 58 % ; 87 % et non 100 %), p corrigée absente, médiane du rapport non calculée. Les capitaux n'ont pas bougé.
- **Correction après l'étape 4.** Une première version donnait, avec BIL, un Sharpe de 0,50 contre 0,48 et un alpha de 0,9 %. Ces valeurs ne retiraient pas le taux sans risque et comptaient donc l'intérêt des bons comme une performance. Remplacées ci-dessus. Les autres chiffres n'ont pas changé.
- **Multiple extrême.** CVNA fait 100 fois avec la règle contre 11 fois en la gardant. Codex le reproduit, sans saut aberrant. Les extrêmes influencent la moyenne sans changer le sens du résultat.

## Limites

- **Pas exactement le même univers que la référence.** Il faut 180 valeurs de signal : 30 884 lignes de la table de référence sont exclues, surtout des titres récents. C'est pourquoi le buy and hold vaut ici 16 490 et non 16 356.
- **Signal et neutralisation.** La neutralisation réécrit les niveaux après un cours suspect, ce qui change 11 358 décisions sur 231 titres (155 comparés). Effet isolé sur le capital moyen : +1,99 USD.
- **Fuite du nettoyage.** Les 75 cours masqués à cause du lendemain subsistent. Leur effet propre n'est pas mesuré ici.
- **Fin de série.** 378 lignes (18 titres) finissent en position sur un titre sans ouverture finale ; la vente se fait au dernier cours connu, comme dans le moteur.
- **Portefeuille.** Le test statistique porte sur une seule date d'achat. Les autres chevauchent cette période et ne sont pas indépendantes.
- **Une seule règle, vérifiée chaque jour.** Le résultat ne dit rien des autres règles. Une vérification mensuelle, qui ferait moins d'allers-retours, n'est pas testée.
- **Hypothèses inchangées.** Paliers de frais à valider, BIL comme proxy des liquidités, fiscalité et EUR/USD non simulés (6,7 rotations par an seraient pénalisées), période plutôt favorable au buy and hold, sans crise longue comme 2008.
