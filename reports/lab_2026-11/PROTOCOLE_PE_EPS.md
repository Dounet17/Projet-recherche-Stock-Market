# Protocole : stratégies fondées sur l'EPS et le P/E

**Figé le 07/11/2026, avant tout calcul de rendement.** Aucun rendement n'a été lu pour ces règles. Relu et accepté par DavidTom, sans audit indépendant du texte ; le code sera relu par Codex avant le lancement. Toute modification après ce commit doit être datée ici et dite « changement de règle » si elle en est un. Même démarche que les deux études précédentes : règles écrites d'avance, code relu par Codex **avant** le lancement, un seul lancement, tout écart daté et qualifié honnêtement.

## Pourquoi cette étude

L'énoncé classe l'EPS et le P/E parmi les heuristiques à évaluer et comparer. Le projet n'a testé qu'une seule règle sur ce terrain, le test B (`RESULTATS_TESTS_A_B.md`).

## Vocabulaire

- **EPS (BPA)** : bénéfice par action. Ici, celui des 12 derniers mois (somme de quatre trimestres), tel que publié, utilisable le lendemain de son dépôt à la SEC (`data.eps_ttm` de `load_universe`).
- **P/E** : cours divisé par l'EPS. Un P/E de 10 veut dire que l'on paie 10 dollars pour 1 dollar de bénéfice annuel. Bas : action « bon marché » ; haut : marché qui attend une forte croissance. **E/P** est son inverse, plus commode car il reste défini quand le bénéfice est proche de zéro.
- **Croissance de l'EPS** : variation de l'EPS sur 12 mois par rapport à celui connu un an plus tôt.
- **Secteur** : un des 12 grands secteurs de Fama et French, tiré du code d'activité SIC. Comparer le P/E au sein d'un secteur évite de n'acheter que des banques ou des pétrolières, structurellement moins chères.
- **Témoin** : le même univers acheté à poids égaux aux mêmes dates. Battre le témoin, c'est savoir choisir **dans** l'univers ; battre SPY, c'est battre le placement passif.

## Question

Une sélection trimestrielle d'actions selon la croissance de l'EPS, seule ou combinée à un P/E bas au sein du secteur, fait-elle mieux que l'univers dont elle est tirée, et mieux que SPY, après frais ?

## Ce qui a déjà été vu

1. **Test B** (P/E bas, 50 titres, chaque mois, 1 000 titres les plus liquides) : 14 372 USD contre 24 531 pour SPY, Sharpe de 0,32, pire chute de -61 %. Le P/E bas seul est donc consommé : **il n'est pas retesté**, ni retouché.
2. Le témoin des 500 titres les plus liquides (19 982 USD), le momentum (18 160), les règles techniques, le modèle de classement, les études d'événements de résultats et de notes d'analystes : rien ne bat SPY.
3. Les mesures suivantes, faites le 07/11/2026 **sans lire aucun rendement**, aux 28 dates de décision (premier jour de bourse de mars, juin, septembre et décembre 2018-2024), parmi les 1 000 actions ordinaires achetables les plus liquides :

| Mesure | Minimum | Médiane | Maximum |
|---|---:|---:|---:|
| EPS connu | 742 | 821 | 921 |
| EPS positif | 575 | 726 | 771 |
| EPS positif aujourd'hui et un an plus tôt (univers éligible) | 518 | 638 | 686 |
| Titres communs entre les 100 de plus forte croissance (E1) et les 100 du score combiné (E2) | | 58 | |
| Titres communs entre E2 et les 100 plus bas P/E (proche du test B) | 30 | 47 | 70 |
| Titres gardés d'un trimestre au suivant, E1 / E2 | 27 / 27 | 56 / 56 | 70 / 73 |

Secteur inconnu pour 0,2 % de l'univers. Deux pistes ont été **écartées sur ces seules mesures** : le P/E relatif au secteur seul (59 à 78 % de titres communs avec le P/E bas, donc une redite du test B) et le PEG (P/E divisé par la croissance, 68 à 84 % de titres communs avec E1).

## Données à figer

`data/universe_clean/` (cours, liquidité, coûts, sorties de cote, fondamentaux trimestriels), `data/reference/sectors.parquet`, `data/calendar.parquet`. Période 2018-2024. Empreintes SHA-256 au gel (code au commit `e33cf8d`), à vérifier par le code avant tout calcul :

| Données | SHA-256 |
|---|---|
| `data/universe_clean/prices_dev.parquet` | `c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15` |
| `data/universe_clean/securities_dev.parquet` | `d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161` |
| `data/universe_clean/fundamentals_quarterly_dev.parquet` | `99ac5e83f4dbdf6e29f3a9691a16d0475f11fa07c1e8ff1d898a074a1c187e2d` |
| `data/reference/sectors.parquet` | `ce9cf466b59b6f12893b199a9450feb82e63673356d6e0d575cb288d5302f85e` |
| `data/calendar.parquet` | `87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03` |

## Règles

**Dates de décision** : premier jour de bourse de mars, juin, septembre et décembre, soit 28 dates. Elles suivent les échéances de dépôt des comptes trimestriels et annuels. Décision à la clôture, exécution à l'ouverture suivante, par le moteur du laboratoire (`experiment.run_experiment`).

**Univers éligible à une date** :
- action ordinaire, achetable (cours brut d'au moins 5 $, montant échangé médian sur 20 séances d'au moins 1 M$) ;
- parmi les 1 000 plus liquides de ce jour ;
- EPS positif à cette date **et** 252 séances plus tôt, chacun tel qu'il était connu à sa date ;
- secteur connu (pour E2 et son témoin).

**Stratégies confirmatoires**, poids égaux sur 100 titres :
- **E1, croissance de l'EPS** : les 100 plus fortes valeurs de (EPS − EPS d'il y a 252 séances) / EPS d'il y a 252 séances.
- **E2, croissance à prix raisonnable** : moyenne de deux rangs en centiles, celui de la croissance de l'EPS dans l'univers éligible et celui de l'E/P au sein de son secteur ; les 100 meilleures moyennes.

**Témoin** : l'univers éligible entier à poids égaux, rééquilibré aux mêmes dates, avec les mêmes frais et sorties.

## Tests confirmatoires, corrigés ensemble par Holm

| Test | Mesure |
|---|---|
| **P1** | E1 contre son témoin |
| **P2** | E2 contre son témoin |

Statistique : `lab.compare` (écart annualisé des log-rendements quotidiens, bootstrap stationnaire, p unilatérale « la stratégie n'apporte rien »), comme pour tout le laboratoire. Publier aussi, pour chaque stratégie et le témoin : capital final, Sharpe, Sharpe au-delà du taux sans risque (BIL), pire chute, rotation, bêta et alpha contre SPY.

## Analyses secondaires, corrigées entre elles par Holm

1. E1 contre SPY.
2. E2 contre SPY.
3. Le témoin contre SPY : l'univers lui-même bat-il le placement passif ?

## Sensibilités et contrôles, prévus d'avance

- Les trois hypothèses de sortie de cote et des frais doublés, pour chaque portefeuille.
- Portefeuilles tirés au hasard du laboratoire (20 tirages, mêmes dates et mêmes poids).
- Contrôle anti-fuite automatique de `run_experiment` (une stratégie tronquée à une date doit donner les mêmes poids jusqu'à cette date).
- Inscription au journal `ledger_universe.csv` et p de Romano-Wolf sur tous les essais du journal, publiée à côté.
- Descriptif sans test : rendement par année, répartition par secteur, titres communs avec le P/E bas, part des titres disparus.

## Limites connues avant calcul

- **Puissance faible** : 7 ans de rendements quotidiens d'un portefeuille. Un écart annuel de quelques points avec le témoin peut passer inaperçu.
- **EPS comptable** : il inclut les éléments exceptionnels ; une plus-value ponctuelle gonfle la croissance. Le filtre « positif un an plus tôt » écarte les retournements de pertes, où la croissance n'a pas de sens.
- **Secteurs** : code SIC actuel, pas historique ; une société qui a changé d'activité est classée selon la dernière.
- **Survie** : les sociétés disparues ont moins souvent un EPS connu (constat du test B), ce qui favorise la stratégie.
- **Liens SEC** : des erreurs de rattachement d'EPS restent possibles (AMJ, XPRO corrigés pour le test B).
- **Multiplicité** : 2018-2024 a déjà servi à de nombreux essais. Même un succès ici devrait être confirmé sur 2025-2026, après nettoyage de cette période et accord du professeur.

## Gel et exécution

1. Relu et figé par ce commit, avec les empreintes des données.
2. Code et tests sur données inventées ; essai à blanc pour les effectifs.
3. Relecture du code par Codex.
4. Un seul lancement. Toute correction ensuite est annoncée, avec les résultats avant et après.

## Décisions prises au gel

1. **100 titres** par portefeuille, plutôt que 50 comme le test B : plus diversifié et moins sensible à quelques titres.
2. **Rééquilibrage trimestriel** aux dates ci-dessus : environ 45 % des titres changent à chaque date.
3. **Témoin comme référence principale**, SPY en secondaire : on teste d'abord la capacité à choisir, puis le placement passif.
