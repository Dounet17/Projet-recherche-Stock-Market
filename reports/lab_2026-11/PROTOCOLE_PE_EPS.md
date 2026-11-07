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

## Choix d'implémentation, 07/11/2026, avant tout lancement

Tranchés en codant `src/pe_eps_study.py` et `reports/run_pe_eps_study.py`, sans aucun rendement lu. **Précision** si le texte figé le permettait déjà, **changement** sinon.

1. Précision : classement de liquidité parmi les titres achetables du jour, ex aequo départagés par l'ordre des colonnes (comme le test B) ; même départage pour les 100 meilleurs scores.
2. Précision : rangs en centiles de E2 par `rank(pct=True)` de pandas, ex aequo à la moyenne ; E/P = EPS / cours brut, à la même échelle que le P/E du test B.
3. Précision : un jour de décision sans aucun titre éligible vendrait tout (ligne de zéros) ; cela n'arrive pas en 2018-2024.
4. Précision : le témoin de E1 garde les titres à secteur inconnu, celui de E2 les écarte, comme écrit.
5. Précision : E1 et E2 sont inscrits au journal ; les deux témoins, simples références, ne le sont pas et n'entrent donc pas dans la p de Romano-Wolf.
6. Précision : contrôle anti-fuite `lab.check_no_lookahead` lancé sur les quatre portefeuilles avant tout backtest.
7. Précision : descriptif « titres communs avec le P/E bas » calculé dans l'univers éligible (médiane de 53,5 sur 100), alors que la mesure de conception partait des 1 000 plus liquides (47). La part des titres plus tard disparus, descriptive, lit les sorties de cote futures et ne sert à aucune décision.

**Essai à blanc** (empreintes conformes, aucun rendement lu, vérifié par un test qui interdit tout calcul de portefeuille) : 28 dates de décision ; univers éligible de 518 à 686 titres ; 100 titres pour E1 et E2 à chaque date ; 58 titres communs en médiane entre E1 et E2. 11 tests passent.

## Corrections avant lancement, après la relecture du code par Codex, 08/11/2026

Relecture : `pe_eps_study/AUDIT_CODE_CODEX.md`. **Aucun rendement de ces stratégies n'avait été calculé.** `universe_data` n'est pas modifié, pour ne pas changer les résultats déjà publiés : cette étude construit son propre EPS.

| Défaut | Correction | Nature |
|---|---|---|
| D1, bloquant | EPS construit **à chaque dépôt avec les seuls dépôts déjà connus** (`pe.causal_eps_matrix`) : versions d'un même trimestre (fins à moins de 20 jours) regroupées en gardant la plus récente connue, quatre trimestres consécutifs (écarts de 70 à 110 jours), valeur dès la séance qui suit le dépôt, expiration 200 jours après la fin du dernier trimestre. Un dépôt futur ne change plus aucune valeur passée (WAT, COHU, ATRO, PATK testés sur les vraies données) | Correction d'une fuite de la source |
| D2, grave | Croissance calculée avec l'EPS d'il y a un an **remis à l'échelle d'actions d'aujourd'hui** | **Changement** de la formule littérale du gel, dans le sens de sa définition économique |
| D3, grave | Échelle d'actions suivie par un multiplicateur de **fractionnements seuls** : sauts du facteur d'ajustement hors de [1/1,2 ; 1,2] ; les dividendes ne touchent plus l'EPS. Le jour d'un fractionnement, un éventuel dividende du même jour reste dans le saut (écart de l'ordre de 0,01 %) | **Changement** de construction |
| D4, grave | Aucun ordre avant le 01/03/2018 : le portefeuille part en liquidités jusqu'à la première des 28 décisions ; descriptifs limités à ces 28 dates | Précision (fidélité aux 28 dates) |
| D5, grave | Titres détenus = couples titre et décision à poids strictement positif, vides retirés (pandas 3) | Correction |
| D6, grave | Bêta, alpha contre SPY, secteurs et disparitions publiés pour les quatre portefeuilles ; S3 porte sur le témoin de E1, nommé `S3_control_E1_vs_SPY` | Correction |
| D7, mineur | Deux mesures distinctes : « 100 plus bas P/E de l'univers éligible, sans plancher » (médiane 51,5) et **titres communs avec les vraies sélections du test B** aux mêmes dates (médiane 27,5 sur 100), calculées sans aucun rendement. La mesure de conception (47) en est une troisième | Changement de définition descriptive |
| D8, mineur | Le choix 1 était faux : le test B départage la liquidité par rang moyen, cette étude par ordre des colonnes | Précision corrigée |

**Conventions héritées, désormais écrites.** Médiane de liquidité avec 10 observations sur 20 ; échange valide exigé le jour de décision ; filtres `too_short` et types issus du nettoyage complet ; expiration de l'EPS à 200 jours après la fin du dernier trimestre, pas après le dépôt ; SIC actuel, non historique.

**Constat sans rendement.** Parmi les 1 000 titres les plus liquides, 175 à 342 EPS par date (médiane 282) diffèrent de plus de 1 % entre cette construction et celle de `universe_data`, surtout à cause des dividendes et des versions de trimestres. Le test B et les autres essais qui utilisent `data.eps_ttm` en héritent ; ils ne sont pas relancés ici.

**Essai à blanc corrigé** (aucun rendement lu) : 28 décisions ; univers éligible de 520 à 686 titres, médiane 645 ; 100 titres pour E1 et E2 ; 57 titres communs en médiane entre E1 et E2. 22 tests passent, dont la causalité des EPS sur les vraies données et un lancement complet sur un marché inventé. Construction de l'EPS en 24 secondes.

## Corrections après la seconde relecture, 08/11/2026, toujours avant tout rendement

Relecture : `pe_eps_study/AUDIT_CODE_CODEX_2.md`. D1 et D4 à D8 y sont jugés corrigés ; le seuil de la correction D3 confondait les opérations.

1. **D3, changement** : le nombre d'actions suit d'abord les **opérations réelles** de `data/universe/corporate_actions_dev.parquet` (empreinte `e5a2238b…bd672a35`, ajoutée au contrôle du code) : fractionnements et regroupements (`new_rate / old_rate`) et dividendes en actions (`rate`), à leur date d'effet, rattachés au titre qui portait ce symbole et cotait à cette date. **Repli** : un saut du facteur d'ajustement hors de [1/1,2 ; 1,2], sans opération connue à 5 séances près, ne compte que si son ratio est un fractionnement simple à 1 % près (entier de 2 à 100, son inverse, 3/2, 4/3, 5/4 et leurs inverses). Les dividendes en espèces, même exceptionnels, et les scissions ne changent plus l'EPS. Vérifié : KDP sans faux fractionnement en juillet 2018, NTRB 7 pour 6, TR 3 % en actions, AAPL 4 pour 1.
2. **Correction** : dans chaque trimestre, la version gardée est celle **au dépôt le plus récent**, même si sa fin de période est plus tôt d'un jour (contre-exemple de la relecture testé).
3. **Limite constatée, sans nouvelle règle** : une fusion inversée mélange deux sociétés dans l'EPS sur 12 mois. KDP au 01/03/2019 additionne deux trimestres de DPS et deux de KDP (2,48) ; ni cette valeur, ni le 1,74 de l'ancien faux fractionnement n'ont de sens économique. Ces cas restent dans l'étude et sont signalés comme limite.
4. **Mesure de couverture, sans rendement** : sur 1 588 grands sauts du facteur des actions ordinaires depuis mi-2016, 1 174 ont une opération du fichier à 5 jours près ; les autres sont surtout des scissions, des dividendes exceptionnels et des regroupements de petites valeurs absents du fichier.

**Essai à blanc** : 28 décisions ; univers éligible de 520 à 685 titres, médiane 645 ; 100 titres pour E1 et E2 ; 57 titres communs entre E1 et E2 ; 27,5 titres communs avec le vrai test B. 27 tests passent.

## Correction après la troisième relecture, 08/11/2026, toujours avant tout rendement

Relecture : `pe_eps_study/AUDIT_CODE_CODEX_3.md`. Le choix de version y est jugé corrigé, ainsi que KDP, NTRB, TR (2024) et HEI ; mais le **repli** sur les sauts du facteur d'ajustement, décrit à la section précédente, prenait encore des scissions pour des fractionnements (EHC, Enhabit, 2022 : saut proche de 5/4, qui changeait E2 au 01/03/2024 ; MMM et GE en 2024 ; le dividende exceptionnel d'ACI en 2022).

1. **Changement** : le repli est **supprimé**. Le nombre d'actions ne suit plus que les opérations documentées du fichier (fractionnements, regroupements, dividendes en actions). Vérifié sur les cours bruts pour RTX : le saut de 0,5 du 03/04/2020 venait de la distribution de Carrier et d'Otis lors de la fusion avec Raytheon, pas d'un regroupement. Effet de la suppression sur les sélections, mesuré sans rendement : 2 décisions changées pour E1, 3 pour E2 (dont EHC remplacé par LBRT au 01/03/2024), 2 pour chaque témoin (RTX).
2. **Correction** : une même opération publiée deux fois ne compte qu'une fois (SNEX 3 pour 2 en 2023, FBYD en 2024).
3. La réserve de causalité de la fenêtre centrée disparaît avec le repli.
4. **Limite** : une opération absente du fichier reste ignorée (par exemple la distribution de 3 % en actions de TR en mars 2020, sans effet sur les sélections selon la relecture). L'affirmation de la section précédente selon laquelle les scissions et dividendes exceptionnels ne changeaient plus l'EPS était fausse avec le repli ; elle est vraie sans lui.

**Essai à blanc** : 28 décisions ; univers éligible de 520 à 685 titres ; 100 titres pour E1 et E2 ; 27,5 titres communs avec le vrai test B. 26 tests passent, dont les régressions KDP, EHC, RTX, NTRB, TR et AAPL sur les vraies données.

## Quatrième relecture, 08/11/2026 : lançable

`pe_eps_study/AUDIT_CODE_CODEX_4.md` : faux fractionnements supprimés, construction causale, aucun faux négatif qui change les sélections aux 28 décisions (OVV, FLG, BALL et TR 2020, absents du fichier, testés sans effet). **Rectification** : FBYD n'est pas dédoublonné (une ligne `forward_splits` et une `stock_dividends` pour la même distribution, 1,44 au lieu de 1,2) ; l'opération tombe le 10/12/2024, après la dernière décision, sans effet sur cette étude. Code lancé tel quel.
