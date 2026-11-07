# Relecture indépendante du code des notes d'analystes

Date : 07/11/2026. Branche `etude-news`, commit relu `46c0aadb51262a3329cef99b4d8e155357fdf099`. Texte de référence : protocole figé au commit `6ea539e`, puis ses neuf choix d'implémentation ajoutés à `46c0aad`.

**Verdict : ne pas lancer le code tel quel.** A3 utilise des informations qui ne sont pas toutes disponibles à sa clôture de décision. Il faut corriger sa construction chronologique, sa gestion des positions disparues, la fenêtre antérieure à la note et les sorties statistiques avant l'unique lancement. Les treize tests et l'essai à blanc réussissent, mais ne détectent pas ces défauts.

## Périmètre et vérifications réalisées

Lecture des fichiers demandés : `CLAUDE.md`, protocole, `src/analyst_study.py`, lanceur, tests, `src/minute_study.py`, `src/lab.py`, `src/experiment.py`, `src/universe_data.py` et audit de l'étude précédente. Lecture complémentaire du cadre d'expériences, du nettoyage, de la référence buy and hold et des fonctions statistiques appelées dans `src/events.py`.

Aucun rendement des événements de cette étude, aucun cours de sortie de ces événements et aucun capital de cette étude n'a été calculé. Aucun lancement réel, aucun accès à `.env`, aucune lecture d'un jeu de validation 2025-2026, aucune modification d'un fichier existant et aucun commit. Les calculs sur vraies données se limitent aux titres de dépêches, identifiants, dates, effectifs, filtres d'achat et matrices de poids. Les tests autorisés utilisent des données inventées. Les deux changements déjà présents au début de la relecture, `.gitignore` et `reports/build_vault.py`, ont été laissés en place.

Commandes exécutées avec `PYTHONDONTWRITEBYTECODE=1` :

```bash
venv/bin/python tests/test_analyst_study.py
venv/bin/python reports/run_analyst_study.py --dry-run
```

Résultats : **13 tests réussis** ; **six empreintes conformes** ; arrêt de l'essai à blanc avant `daily_returns`. Les effectifs reproduisent exactement ceux annoncés :

| Étape | Relèvements | Abaissements |
|---|---:|---:|
| Notes retenues avant regroupement | 23 949 | 28 643 |
| Après regroupement des recommandations par entrée | 22 795 | 25 921 |
| Achetables, hors résultats | 18 427 | 19 194 |

L'échantillon principal compte donc 37 621 événements avant vérification des fenêtres de prix ; 15 573 sont dans la tranche d'au moins 100 M$. A3 sélectionne 18 483 relèvements. Les objectifs retenus hors résultats et achetables sont 48 112 à la hausse et 35 713 à la baisse.

Gravités : **bloquant** signifie qu'une stratégie confirmatoire utiliserait l'avenir ; **grave** signifie qu'une mesure, une règle de portefeuille ou un livrable important ne correspond pas au protocole ; **mineur** indique une convention à expliciter, une contamination limitée constatée ou un contrôle incomplet. La gravité ne préjuge jamais de l'effet sur un rendement, qui n'a pas été mesuré.

## Défauts à corriger

### D1. A3 reprend un regroupement qui peut connaître des notes futures : bloquant

**Preuve :** `reports/run_analyst_study.py:55`, `:56`, `:76` et `:159` ; `src/analyst_study.py:55` à `:61`. Le lanceur calcule deux horloges, mais `collapse` utilise uniquement `entry_idx`, l'entrée de A1/A2. A3 reçoit ensuite cette table déjà filtrée. Une séance d'entrée de A1/A2 peut contenir des notes affectées à deux clôtures de décision différentes pour A3.

Sur les vraies notes de recommandation, **523 couples titre/entrée** couvrent plusieurs décisions A3, dont **59 avec des sens contradictoires**. Pour **17 couples**, la première note est un relèvement : une note ultérieure peut donc supprimer rétrospectivement un achat envisagé.

Exemple sans prix :

| Identifiant | Titre | Disponibilité UTC | Décision A3 | Classe |
|---|---|---|---|---|
| 17741455 | AMAG#0 | 01/10/2020 16:27:21 | 01/10/2020 | relèvement |
| 17751712 | AMAG#0 | 02/10/2020 10:35:38 | 02/10/2020 | abaissement |

Les deux notes ont l'entrée A1/A2 du 02/10. Le premier titre est « Piper Sandler Upgrades AMAG Pharmaceuticals to Neutral ». Le second est « HC Wainwright & Co. Downgrades AMAG Pharmaceuticals to Neutral, Lowers Price Target to $13.75 ». Le regroupement les supprime toutes les deux, alors que la décision du 01/10 ne pouvait pas connaître la seconde.

Même sans contradiction, garder seulement la première note peut supprimer un relèvement destiné à une décision ultérieure et donc une prolongation de tenue. À titre de diagnostic de dates seulement, regrouper les recommandations par `decision_idx` donnerait 47 288 lignes, contre 48 716 par `entry_idx` ; les identifiants retenus diffèrent dans les deux sens. Ce nombre ne constitue pas une proposition d'échantillon définitif.

**Correction :** construire A3 depuis les notes brutes admissibles et les regrouper selon sa propre clôture de décision, en n'utilisant que les notes disponibles à cette clôture. Définir explicitement le traitement des contradictions à cette horloge et des relèvements successifs. Tester que l'ajout ou le retrait de toute note future ne modifie jamais un ordre passé. Conserver le regroupement par entrée pour A1/A2, où toutes les notes du groupe sont connues avant l'ouverture.

### D2. Le filtre de résultats d'A3 est rétrospectif et porte sur la mauvaise entrée : bloquant

**Preuve :** `reports/run_analyst_study.py:68` à `:74`, puis `:159`. Le drapeau `near_earnings` est calculé avec les dates réalisées de publications, y compris une séance après l'entrée, puis utilisé pour décider les achats A3. Le fichier ne fournit ici aucun horodatage démontrant qu'un calendrier de résultats était connu à la décision.

Sur les relèvements regroupés et achetables à la décision, **182 exclusions** sont justifiées uniquement par des dates de résultats situées après la clôture de décision. Par exemple, le relèvement IBM `11038539`, disponible le 17/01/2018 à 11:46:45 UTC, est écarté avec une décision au 17/01 et une publication dans la fenêtre future. Ce contrôle constate la date utilisée ; il ne prétend pas qu'une annonce de calendrier était impossible à connaître, seulement qu'aucune preuve de cette connaissance n'est utilisée par le code.

De plus, `near_earnings` reste centré sur l'entrée A1/A2, alors que l'achat A3 peut arriver une séance plus tard. Parmi les **18 483 achats sélectionnés**, **175** sont proches de résultats si l'on applique la même fenêtre à leur véritable entrée A3. Dans l'ensemble des 48 716 recommandations regroupées, les deux horloges changent le drapeau pour 396 événements vers une exclusion et pour 1 606 vers une inclusion.

**Correction :** distinguer l'échantillon rétrospectif de l'étude d'événements et le filtre de décision d'une stratégie achetable. Pour A3, utiliser un calendrier dont la disponibilité historique est prouvée, ou une exclusion fondée uniquement sur des publications déjà connues. Si la stratégie doit conserver l'exclusion symétrique avec des dates futures réalisées, annoncer qu'A3 est un portefeuille rétrospectivement sélectionné et changer la portée confirmatoire de son interprétation. Ce choix doit être tranché et daté avant le lancement. Toute fenêtre d'exclusion propre à A3 doit en outre être centrée sur son entrée effective.

### D3. Les « 20 séances avant la note » comprennent parfois l'après-note : grave

**Preuve :** `reports/run_analyst_study.py:141`. Avec `window(rows - 20, 20, ...)`, la fenêtre se termine à la clôture de la séance précédant l'entrée. Si une note est diffusée pendant la séance et entre le lendemain, cette clôture intervient après la note.

Cela concerne **6 512 des 37 621 événements principaux**, par simple comparaison d'horodatages, sans mesurer aucun mouvement. Exemple : DIS `10972579`, note du 02/01/2018 à 14:34 UTC, entrée le 03/01 ; la fenêtre dite antérieure finit le 02/01 à la clôture, donc après cette note. Même défaut pour RDN `10987339` et DATA `10986533`.

**Correction :** trouver la dernière séance entièrement terminée avant la disponibilité de chaque note, puis prendre ses vingt dernières séances incluses. Aligner SPY sur ces mêmes bornes. Ajouter une assertion `fin_fenetre_avant <= available_at` et distinguer explicitement cette fenêtre du placebo décalé de 60 séances.

### D4. Le plan de poids conserve des titres déjà sortis de cote : grave

**Preuve :** `src/analyst_study.py:115` à `:127` ne retire un titre de `active` qu'à sa date d'expiration prévue. `src/lab.py:181` à `:204` liquide pourtant les titres disparus et remet leur poids détenu à zéro. Lors d'un ordre suivant, `src/lab.py:223` à `:230` annule les cibles sur titres disparus, mais ne répartit pas leur quote-part entre les autres titres. Le plan et le portefeuille exécuté n'ont donc plus le même ensemble de positions.

La matrice de cibles A3 comporte **89 cellules positives après la dernière date de transaction**, pour **7 titres**, sur 89 dates. Exemples : GXP#0 reste ciblé du 05/06/2018 au-delà de sa dernière transaction du 04/06 ; NSM#0 est encore ciblé le 31/07/2018 après sa dernière transaction du 30/07. Aucun prix ni rendement de disparition n'est nécessaire à ce constat.

Le capital n'est pas investi dans ces titres par le moteur, qui les bloque correctement. En revanche, ils restent dans le dénominateur de `1 / len(active)` et peuvent réduire artificiellement l'exposition des positions existantes. La sortie réelle ne déclenche pas non plus à elle seule un recalcul de l'ensemble.

**Correction :** synchroniser le plan avec les positions effectivement détenues et les sorties exécutées, avec une convention datée pour le prochain rééquilibrage réalisable. Ne pas transmettre à une stratégie des dates de disparition futures pour les supprimer par anticipation. Ajouter un test intégré où une disparition change l'ensemble des positions avant l'expiration prévue.

### D5. La p principale est ordinaire, mais son IC et les champs statistiques principaux sont Newey-West : grave

**Preuve :** `reports/run_analyst_study.py:149`, `:154`, `:195` et `:208` ; `src/minute_study.py:212` à `:225`. Holm reçoit bien `p_plain` pour A1/A2 : le choix du test principal n'a donc pas été remplacé silencieusement dans la correction multiple. En revanche, les champs génériques `t`, `p`, `ci_low`, `ci_high` proviennent de Newey-West, et aucun IC ordinaire n'est produit.

Le tableau confirmatoire associerait ainsi une p de Holm ordinaire à un IC d'une autre procédure. C'est précisément le genre de mélange à éviter après l'audit précédent. Le code ne force pas non plus la présence des 28 trimestres après les exclusions propres à chaque fenêtre : les fonctions éliminent les valeurs manquantes puis utilisent `n - 1` degrés de liberté.

**Correction :** publier comme résultat principal la moyenne trimestrielle, `t_plain`, `p_plain`, son IC `moyenne +/- t(0,975 ; 27) * écart_type / sqrt(28)` et sa p de Holm. Ranger les résultats Newey-West à un retard dans une sensibilité nommée. Vérifier explicitement les 28 trimestres de chaque test confirmatoire et traiter toute absence avant le lancement. Conserver des étiquettes sans ambiguïté pour les secondaires également.

### D6. La référence buy and hold du même univers manque : grave

**Preuve :** `reports/run_analyst_study.py:157` à `:173` appelle `run_variant`. Celui-ci ne fournit que SPY et des portefeuilles au hasard, `src/experiment.py:88` à `:109`. Aucun buy and hold moyen de l'univers concerné n'est construit ou joint au rapport, contrairement au protocole, ligne 84. Le portefeuille au hasard n'est pas cette référence.

**Correction :** définir avant calcul la population et les dates de référence, puis produire le buy and hold moyen correspondant avec coûts et sorties de cote cohérents, en précisant les différences de couverture éventuelles. Une référence choisie sur la liste future des sociétés recevant une note doit être présentée comme telle. Ne pas substituer silencieusement la moyenne d'un autre univers déjà calculé.

### D7. Les trois scénarios ne sont pas publiés pour A2 : grave

**Preuve :** `reports/run_analyst_study.py:131` à `:139` construit trois rendements bruts/anormaux, mais ne calcule `net_ab_20` qu'à partir de `raw_20` et `ab_20_base`. L'analyse `:217` ne publie que les moyennes A1 selon scénario. A2 n'a ni mesure nette optimiste ni mesure nette pessimiste dans le rapport. Les variantes A3 existent bien dans `run_variant` et leurs capitaux sont rendus via `extra` ; il ne faut pas les déclarer absentes.

**Correction :** calculer les mesures nettes A2 sous les trois hypothèses et les publier comme sensibilités préannoncées, avec effectifs et incertitude identifiables, en conservant une seule hypothèse principale et la famille de Holm prévue. Expliciter également quels secondaires sont publiés sous chaque scénario, puisque la règle générale de fenêtre annonce les trois.

### D8. La règle lexicale inclut des notations de crédit : mineur, changement de définition nécessaire si on les exclut

**Preuve :** `src/analyst_study.py:12` à `:37`, puis `:42` à `:47`. Les mots sont correctement reconnus au sens littéral du protocole. Leur présence ne garantit toutefois pas une recommandation d'achat ou de vente d'action.

Le contrôle ciblé trouve **59 notes sélectionnées** dont le titre commence par Moody's, Fitch ou S&P, éventuellement après `UPDATE:` ou `Hearing`. **48** de ces identifiants restent dans l'échantillon principal regroupé et achetable. Exemples certains :

- `11026548`, TEVA#0 : « Moody's Downgrades Teva To BA2, Outlook Stable » ;
- `11504862`, NFLX#0 : « Moody's Upgrades Netflix Debt Rating From B1 To Ba3; Outlook Stable » ;
- `13203173`, LLY#0 : « S&P Downgrades Eli Lilly Credit Rating From AA- To A+; Outlook Raised From Credit Watch Negative To Stable » ;
- `32669366`, CVNA#0 : « S&P Global Ratings Upgrades Securitizations Sponsored By Carvana ».

Cela contredit la définition substantielle d'un changement de recommandation sur l'action, sans contredire la règle de mots figée. Le constat porte sur les titres, pas sur l'effet financier de ces cas.

**Correction :** soit accepter explicitement ce bruit de classement et publier ces effectifs, soit dater avant lancement un **changement de règle** excluant les notations de crédit et les actifs autres que l'action citée. Une exclusion ne doit pas rejeter une vraie recommandation sur l'action Moody's ou sur Abercrombie & Fitch. Prévoir des exemples positifs et négatifs ciblés.

### D9. « Hors résultats » inclut des cas où l'exclusion est invérifiable : mineur

**Preuve :** `src/analyst_study.py:70` à `:75` renvoie implicitement faux pour un CIK absent ou sans historique dans la table d'événements. Dans l'échantillon principal de recommandations, **234 événements n'ont pas de CIK** et **5 625 n'ont aucun CIK présent dans la table de dates de résultats**, les premiers étant inclus dans les seconds. Le cas n'est donc pas seulement celui des groupes statistiques évoqués au choix 9.

Ces nombres ne prouvent pas que 5 625 notes sont proches de résultats. Ils montrent qu'on ne peut pas vérifier cette exclusion pour elles avec les données utilisées. Le repli `filed` est par ailleurs conforme au texte, mais donne une date de dépôt qui peut différer de la publication économique.

**Correction :** distinguer « exclusion vérifiée négative » et « calendrier non couvert », publier les effectifs par sens et année et qualifier la couverture du principal. Garder ou écarter les cas non couverts doit être fixé avant lancement ; une exclusion nouvelle modifie l'échantillon et doit être annoncée comme changement de règle. Ne pas présenter la seule présence d'un CIK comme une preuve de calendrier exhaustif.

### D10. La clôture de décision A3 ne tient pas compte des cinq minutes : mineur

**Preuve :** `src/analyst_study.py:50` à `:52`, `reports/run_analyst_study.py:56` et `:62`. L'assertion exige seulement une clôture après `available_at`, sans les cinq minutes de disponibilité du protocole. **22 recommandations regroupées**, dont **4 achats A3 retenus**, sont décidées moins de cinq minutes après la note : SIX `14049231` le 09/07/2019 à 19:56:24 UTC ; MAS `26384025` le 30/03/2022 à 19:59:18 ; WING `34769512` le 20/09/2023 à 19:57:07 ; ACA `40232007` le 07/08/2024 à 19:56:01.

Toutes leurs ouvertures d'exécution restent bien après les cinq minutes : **ce n'est pas une entrée avant disponibilité**. Le problème est la compatibilité entre la décision à la clôture et le délai de traitement. Le choix 2 n'explicite pas cette exception.

**Correction :** appliquer le délai à la décision A3 si les cinq minutes sont un délai de disponibilité de l'information, ou qualifier explicitement l'exception A3 de changement par rapport à cette horloge. Tester les cas à clôture moins cinq minutes, une seconde avant la clôture, clôture exacte et séance écourtée.

### D11. Des sensibilités et descriptifs annoncés restent incomplets ou changent d'estimateur : mineur

**Preuve :** `reports/run_analyst_study.py:212` à `:227` : placebo de signe uniquement pour A1 ; descriptif A2 par année mais pas par tranche de liquidité ; contrôles regroupés limités au t, sans coefficient ni effectif ni p/IC. La sensibilité Newey-West est présente mais mal séparée du principal, voir D5.

`src/minute_study.py:228` à `:251` réalise une régression pondérée par événement. Son coefficient A1 est la différence des moyennes par événement, et celui A2 la moyenne par événement. Les tests principaux donnent le même poids à chacun des 28 trimestres. Changer les erreurs-types ne devrait pas changer silencieusement la quantité estimée.

**Correction :** ajouter A2 par tranche de liquidité et définir la sensibilité de signes annoncée pour A2, ou annoncer précisément que le placebo par permutation des étiquettes ne concerne qu'A1. Pour le regroupement date/société, publier explicitement le coefficient par événement et son interprétation, ou construire les contributions et pondérations correspondant à la moyenne trimestrielle. Pour A1, des poids proportionnels à `1 / effectif(trimestre, sens)` permettent de conserver l'égalité des poids trimestriels ; pour A2, utiliser `1 / effectif(trimestre)`. Ne pas qualifier le t regroupé de simple variante d'erreur-type du principal sans cette précaution.

## Qualification des neuf choix d'implémentation

| Choix | Appréciation |
|---|---|
| 1. p unilatérale A3, bilatérales A1/A2 | Déclaration de changement prudente et explicite, acceptable avant lancement. Le renvoi initial à `lab.compare` impliquait déjà son comportement usuel, mais l'explicitation évite une ambiguïté de direction. Holm peut combiner ces p : elles n'ont pas à être toutes unilatérales ou toutes bilatérales, pourvu que leurs hypothèses soient fixées et leurs p valides. |
| 2. Première clôture après la note, filtres à cette clôture | Précision fidèle pour l'horloge A3 et l'information de la veille de son exécution. Qualification incomplète pour les notes des cinq dernières minutes : D10. Ne règle pas D1/D2. |
| 3. `announced`, sinon `filed`, report à la séance suivante ou courante | Précision conforme, correctement codée par `fillna` puis `searchsorted`. Il s'agit de dates, pas du champ SEC `accepted` erroné. |
| 4. Première note, regroupement par famille | Garder la première et départager par identifiant sont des précisions raisonnables. La séparation des familles introduit une exception au libellé global de la ligne 61, « plusieurs notes [...] aucun sinon » : la qualifier intégralement de précision est insuffisant. On compte 1 945 couples titre/entrée ayant les deux familles et des sens opposés, alors que les 272 contradictions annoncées au gel se reproduisent pour les seules recommandations. Cela suggère une intention par famille, mais l'exception doit être explicitement assumée et datée, comme changement si le libellé global du gel est la règle retenue. Son réemploi pour A3 est en tout cas incorrect : D1. |
| 5. Recommandation prioritaire sur objectif dans le même titre | Précision défendable de la séparation des signaux. Les tests incluent bien un relèvement avec objectif abaissé. Ne résout pas la qualification des notations de crédit. |
| 6. Journal du laboratoire, sans Romano-Wolf dans le protocole | Précision conforme. `record_trial` journalise A3, tandis que Holm propre à l'étude est calculé séparément. |
| 7. Sharpe au-delà de BIL, ouverture à ouverture | Précision conforme à la demande de Sharpe au-delà du taux sans risque et à l'horloge du moteur. Les Sharpe ordinaires de `lab.summarize` existent aussi : le rapport doit identifier lequel il commente. |
| 8. Placebo et avant-note en scénario de base, principal seulement | Le choix de l'échantillon principal est une précision raisonnable. La restriction au seul scénario de base déroge à la règle générale des trois hypothèses de la ligne 72 : cette restriction mérite l'étiquette changement, même si son impact réel peut être nul. Surtout, « avant-note » est mal construit, D3. |
| 9. Tous les CIK manquants dans un groupe | Précision statistique explicite, sans fuite temporelle propre. Ce regroupement de sociétés distinctes n'a pas de garantie générale de conservatisme. Il ne couvre pas le défaut de calendrier de D9. |

La direction des p de Holm est correctement raccordée dans `analyze`. Le bootstrap A3 est celui du laboratoire : 4 000 tirages stationnaires, longueur moyenne 21 séances, comparaison des **log-rendements** quotidiens et écart annualisé. Ce choix hérité doit être nommé, car « rendement quotidien moins SPY » peut être compris comme un écart arithmétique. Il n'existe pas de calcul de Romano-Wolf caché dans les trois confirmatoires.

Autres conventions absentes de la liste des neuf :

- **Médiane de vingt séances avec seulement dix observations exigées**, `src/universe_data.py:200`. Parmi les recommandations regroupées achetables, 30 passent avec moins de vingt observations de volume valide dans la fenêtre. Documenter le minimum de dix ; exiger vingt modifierait le filtre hérité.
- **Titre effectivement échangé la veille exigé**, via `valid` dans `tradable`, `src/universe_data.py:180` et `:201`. C'est plus strict que les seuls seuils de prix et de médiane. `too_short` est aussi un filtre supplémentaire, calculé sur la vie complète du titre, `:130`.
- **Coût aller et retour A2 fixé à partir de la liquidité précédant l'entrée**, identique aux deux côtés, `reports/run_analyst_study.py:136` à `:139`. C'est connu avant l'entrée et défendable comme hypothèse de coût ; ce n'est pas une lecture de la liquidité future de sortie.
- **Tenue A3 mesurée par vingt périodes ouverture à ouverture**, et liquidation imposée à la dernière ouverture de 2024 par le moteur. A1/A2 restent ouverture à clôture de la vingtième séance. Il y a 257 signaux A3 dans la zone finale ne permettant pas une tenue complète jusqu'à l'ouverture prévue. Documenter cette différence et ces tenues tronquées.
- **Plafond de 10 % appliqué aux cibles des rééquilibrages**, pas garanti continuellement entre eux : `portfolio_weights` laisse les poids dériver, conformément à l'absence d'ordres lorsque l'ensemble ne change pas. Un plafond permanent exigerait une autre règle de rééquilibrage.
- **Ordre impossible non reporté automatiquement**, et **ouvertures aberrantes supprimées avec un contrôle utilisant la clôture du même jour**, hérités du lecteur/moteur. Le second est un nettoyage rétrospectif, pas une information disponible à l'ouverture, `src/universe_data.py:183` à `:186`. Il faut distinguer absence d'exécution et exclusion d'un événement. On compte quatre événements principaux sans ouverture valide et un signal d'achat A3 sans ouverture valide à son exécution prévue, sans calculer leurs rendements.
- **Couverture des calendriers manquante traitée comme absence de résultats**, et filtres A3 rétrospectifs : D2/D9. Ce sont des choix d'échantillon et de faisabilité, pas de simples détails techniques.

## Points vérifiés sans défaut nouveau établi

| Point demandé | Vérification |
|---|---|
| Entrées A1/A2 | `entry_sessions`, `src/minute_study.py:63` à `:65`, retient bien la première ouverture supérieure ou égale à `available_at + 5 min`. L'égalité 9 h 25 est admise. Conversion explicite en nanosecondes correcte. |
| Horloge A3 usuelle | Une note avant la clôture est décidée ce jour puis exécutée le lendemain ; après clôture, décision à la prochaine clôture puis exécution encore une séance après. Cela respecte le décalage annoncé, sous la réserve D10. |
| Prix et liquidité d'A1/A2 | `attach_daily` lit `tradable` et la médiane à `row - 1`. Les prix et volumes des filtres sont bruts, pas des niveaux ajustés. |
| Coûts | `cost_bps[row]` est déjà décalé d'une séance dans `load_universe`. Le lire à l'entrée n'est pas lire sa liquidité du jour. Pour A3, `backtest` applique le coût connu avant chaque ouverture, liquidation finale comprise. |
| Identité et symbole | Sur les 18 745 titres du fichier de métadonnées, **zéro différence** entre `security_id.split('#')[0]` et `symbol`. Le filtre de symboles de `load_universe` ne perd donc pas un titre à cause de cette extraction dans les données gelées. Cela valide cet invariant actuel, pas une généralisation à de futures identités. |
| Jointures aux colonnes | Aucun doublon d'identifiant après sélection des liens directs vers common/ADR ; **les 48 716 recommandations regroupées sont présentes** dans le panel quotidien. Jointure par `security_id`, pas par position ou alias. Le calendrier du panel en 2018-2024 contient exactement les 1 761 séances régulières attendues. |
| Regroupement A1/A2 | La contradiction au sein des recommandations supprime bien tout le groupe ; les notes de même sens gardent la première. Les 272 groupes contradictoires du gel sont reproduits. Réserves : exception entre familles et réemploi pour A3. |
| Dates de résultats | `announced.fillna(filed)`, première séance à partir de la date et bornes inclusives `entrée - 2` à `entrée + 1` sont conformes pour l'étude d'événements. Ce n'est pas une fuite de signal pour une analyse conditionnelle explicitement rétrospective. L'usage en stratégie A3 est différent, D2. |
| Fenêtres quotidiennes | `daily_window`, `src/minute_study.py:177` à `:193`, prend ouverture d'entrée, clôture de `entrée + k - 1`, report des clôtures pour les trous et sortie avec `last_rows <= end`. La correction de borne de l'audit précédent est présente. Pas de cours de sortie réel consulté pour les vérifier ici. |
| Fin 2024 | Une fenêtre dépassant le panel devient manquante, y compris pour un titre disparu. Sur les 37 621 événements principaux, les seules bornes temporelles rendent incomplets 3 événements à cinq séances, 439 à vingt et 1 174 à soixante. Ce sont des effectifs de fenêtres, pas des effectifs de rendements valides. Aucun trimestre d'entrée nominal ne manque parmi les 28. |
| Placebo de date | `rows - 60` puis vingt séances respecte le décalage annoncé. Les prix quotidiens commencent en 2016, donc l'historique des premières notes est disponible au niveau du calendrier. Les trous et nouvelles cotations peuvent encore modifier la population effectivement mesurable : publier ses effectifs et ne pas conclure sur l'effet propre avant son résultat. |
| Intervalles et prolongation | Les intervalles `[d, d + 20)` prolongent correctement la tenue ; un signal à l'expiration peut prolonger sans vendre/racheter. Le plan n'anticipe pas la prolongation avant qu'elle puisse affecter une expiration passée. La fuite constatée est celle de la sélection des notes, D1. |
| Lignes vides et plafond | `lab.backtest:132` à `:154`, puis `:188` à `:192`, conserve bien la distinction NaN = aucun ordre, zéros = liquidation. Les cibles A3 comportent 1 758 dates d'ordre et ne dépassent jamais 0,10 par titre. `run_variant` ne remplit pas préalablement les lignes NaN de la stratégie. |
| Sorties A3 et coûts doublés | `run_variant` exécute les trois hypothèses et les coûts doublés. La sensibilité cash BIL est effectivement appelée dans `portfolio`. Ces variantes restent à vérifier dans les résultats du lancement ultérieur, sans les exécuter pendant cette relecture. |
| Placebo de signe | La permutation des étiquettes au sein du trimestre conserve les effectifs des groupes ; répéter une permutation du vecteur déjà permuté n'est pas un bogue. Ce contrôle A1 ne conserve pas les dépendances par société/date et ne suffit pas à établir une causalité. |
| Valeurs extrêmes | Les deux seuils figés sont utilisés et une liste est écrite, sans suppression selon le signe, `reports/run_analyst_study.py:256`. L'écriture seule ne constitue pas encore leur vérification humaine avant interprétation. |

Les nettoyages rétrospectifs de `suspect_print`, la neutralisation asymétrique des gains traversant un cours suspect et les métadonnées d'identification sont hérités du cadre déjà documenté. Le filtre sur cours/volumes bruts n'efface pas ces limites. Je n'ai pas calculé leur effet sur les rendements de notes et ne conclus donc pas à un effet nul.

`run_variant` ne lance pas le test de préfixe `lab.check_no_lookahead`, contrairement à `run_experiment`. Les assertions actuelles ne contrôlent que les bornes d'horloge, pas l'invariance des ordres sous retrait de notes ou de résultats futurs. Sa statistique `untradable_share` est un diagnostic, pas une barrière ; elle vaut ici environ 0,4934 % sur les cibles. Elle mélange anciennes positions et nouvelles cibles et ne prouve pas à elle seule un achat illégal.

## Classement sur de vrais titres

Échantillon de **48 titres**, douze par classe, tirés avec `random_state=937` dans `data/news/news_articles.parquet`, colonne `headline`, catégorie `analyst`, disponibilité strictement antérieure au 01/01/2025 : les 48 exemples ordinaires ont le sens attendu. Exemples :

| ID | Titre | Classe correcte |
|---|---|---|
| 15580678 | Keefe, Bruyette & Woods Upgrades Fiserv to Outperform | relèvement |
| 32619295 | BMO Capital Upgrades Alliant Energy to Outperform, Lowers Price Target to $56 | relèvement, malgré l'objectif abaissé |
| 41545516 | (Updated Price Target): Deutsche Bank Downgrades Teck Resources to Hold, Lowers Price Target to $50 | abaissement |
| 21315753 | Morgan Stanley Maintains Overweight on American Intl Gr, Raises Price Target to $60 | objectif relevé |
| 26272738 | Piper Sandler Maintains Overweight on Ollie's Bargain Outlet, Lowers Price Target to $62 | objectif abaissé |

Cette réussite de l'échantillon aléatoire ne permet pas de déclarer la classification parfaite : la recherche ciblée révèle D8.

La regex de préfixe ajoute aussi `UPDATE:` et restreint les caractères du nom de bureau, au-delà du texte littéral « 2 à 40 caractères ». Une comparaison à `^.{2,40}\s(?:maintains|reiterates)\b` montre 87 différences avant filtres, presque toutes des corrections ensuite écartées ; une seule subsiste après filtres d'article, ID `13074249`, elle-même absente des liens directs sélectionnés. **Aucune différence d'événement sélectionné n'est établie pour cette variation de préfixe.** Documenter la regex exacte est préférable à inventer une règle plus large après observation des résultats.

## Tests à ajouter avant lancement

Les tests présents couvrent les classes ordinaires, quelques filtres, les contradictions simples, la recherche de clôture, les bornes d'exclusion de résultats, l'inclusion dans une fenêtre tenue, la prolongation et les cibles égales. Le test de tenue passe directement par `lab.backtest`, **sans cycle de vie**, sur un seul titre, avec plafond 100 %. Le test global remplace entièrement `portfolio` par une fonction factice, `tests/test_analyst_study.py:126`. Aucun des deux ne valide le chemin A3 réel via `run_variant`.

Tests prioritaires, uniquement sur données inventées, avec résultats attendus calculés indépendamment :

1. **Préfixe chronologique des notes** : relèvement à t, abaissement à t + 1 avant la même entrée A1 ; la future note ne doit pas changer la décision A3 à t. Même test avec deux relèvements, dont le second prolonge une tenue.
2. **Préfixe des résultats** : ajouter une publication future ou modifier sa date ne doit pas modifier un ordre antérieur sans calendrier annoncé et horodaté. Vérifier le recentrage de l'exclusion sur la vraie entrée A3.
3. **Disponibilité et horloge intégrée** : 9 h 25 pile, une seconde après, cinq minutes avant clôture, quelques secondes avant, clôture exacte, après clôture, vendredi, férié et demi-séance ; contrôle explicite des unités us/ns.
4. **Avant-note et placebo** : note le matin, en séance et après clôture ; toutes les clôtures de la fenêtre avant-note doivent précéder la note ; placebo exactement à moins soixante séances ; historique insuffisant et nouvelle cotation.
5. **A3 complet via `run_variant`** : données synthétiques avec liquidités, coûts par date/titre, plusieurs positions, NaN sans ordre, zéros de liquidation, ventes simultanées aux achats, prolongation à l'expiration et plafond 10 %. Intercepter `record_trial` pour ne rien écrire au vrai journal.
6. **Sortie réelle contre intervalle prévu** : disparition avant vingt séances, sortie le dernier jour d'une fenêtre, sortie sans autre signal ce jour ; retrait effectif du dénominateur, convention de cash puis rééquilibrage et absence de réachat de titre disparu.
7. **Exécution impossible** : ouverture absente à l'achat ou à la vente, reprise ultérieure ; expliciter ce qui reste en cash et ce qui peut être acheté au prochain rééquilibrage. Tester aussi une dernière séance suspecte et une colonne entièrement sans cours.
8. **Mesures quotidiennes du lanceur** : horizons 1, 5, 20, 60 avec clôture finale, SPY sur les mêmes bornes, trou interne, trois hypothèses de sortie, coût net simple/doublé, fenêtre hors 2024. Les tests réutilisés de `minute_study` couvrent déjà plusieurs briques, mais pas leur raccordement au nouveau lanceur.
9. **Filtres et jointures** : `announced` prioritaire et `filed` de repli, report week-end, CIK manquant/sans calendrier, identifiants de segments réutilisés, colonne absente et seuils inclusifs 5 $, 1 M$, 100 M$. Changer les prix/volumes à partir de l'entrée ne doit pas modifier le filtre ou le coût d'entrée. Tester dix contre vingt observations pour figer ce choix.
10. **Statistiques** : vingt-huit moyennes trimestrielles très inégalement peuplées, t ordinaire et IC calculés à la main, p de Student à 27 degrés de liberté ; sensibilité Newey-West séparée ; même estimateur avec regroupement ; absence d'un trimestre ; Holm mélangeant p unilatérale et bilatérales avec valeurs attendues. Vérifier aussi que les familles secondaire et principale restent séparées.
11. **Contrat du rapport et du dry-run** : présence du buy and hold moyen, des trois mesures nettes A2, des tranches A2 et des exclusions par cause ; dans le dry-run, remplacer par des fonctions qui lèvent `daily_returns`, `portfolio`, `lab.backtest` et `record_trial`, et vérifier qu'aucune n'est appelée ni aucun fichier de résultats écrit.
12. **Corpus de titres ciblés** : crédit contre recommandation d'action, recommandation sur Moody's et Abercrombie & Fitch, deux mots contradictoires, verbe dans une citation, mélange recommandation/objectif et familles contradictoires. Figer les attentes sémantiques et les éventuels changements de règle avant tout résultat.

## Reproduction des contrôles sans rendement

Scripts utilisés, écrits exclusivement dans `/tmp` :

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/audit_analyst_codex_structure.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/audit_analyst_codex_details.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/audit_analyst_codex_final_checks.py
```

Leurs sorties sont respectivement dans les fichiers `.txt` de mêmes noms sous `/tmp`. Ces scripts ne font appel ni à `daily_returns`, ni à `portfolio`, ni à `run_variant`, ni à `lab.backtest`. Ils utilisent le chargement de panel autorisé par l'essai à blanc, uniquement pour les indices, filtres, disponibilité des observations et cibles de poids. Les valeurs de prix d'entrée ou de sortie ne sont pas affichées.

Recette autonome réduite pour retrouver la fuite de regroupement et le classement, sans même charger de cours :

```python
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, 'src')
import analyst_study as an
import minute_study as ms

A = pd.read_parquet('data/news/news_articles.parquet', columns=[
    'id', 'available_at', 'headline', 'category', 'n_stocks',
    'correction', 'late_relay'], filters=[
    ('available_at', '<', pd.Timestamp('2025-01-01', tz='UTC'))])
L = pd.read_parquet('data/news/news_links.parquet',
                    columns=['id', 'security_id', 'link', 'conflict'])
S = pd.read_parquet('data/universe_clean/securities_dev.parquet',
                    columns=['security_id', 'security_type']).set_index('security_id')
C = pd.read_parquet('data/calendar.parquet', filters=[
    ('date', '<=', pd.Timestamp('2024-12-31'))])
T = ms.session_table(C)
N = an.select_notes(A, L, S.security_type)
N['available_ns'] = N.available_at.dt.as_unit('ns').astype('int64')
N['entry_idx'] = ms.entry_sessions(N.available_ns, T.open_ns)
N['decision_idx'] = an.decision_sessions(N.available_ns, T.close_ns)
N = N[N.entry_idx < len(T)]
R = N[N.kind.isin(['upgrade', 'downgrade'])]
G = R.groupby(['security_id', 'entry_idx'])
multi = G.decision_idx.nunique().gt(1)
conflict = G.kind.nunique().gt(1)
print('Plusieurs décisions :', int(multi.sum()))          # 523
print('Dont contradictoires :', int((multi & conflict).sum()))  # 59
print(R[R.id.isin([17741455, 17751712])][[
    'id', 'security_id', 'available_at', 'entry_idx', 'decision_idx', 'kind']])
credit = R.headline.str.contains(
    r"(?i)^(?:(?:UPDATE:|Hearing)\s*)?(?:Moody'?s|Fitch|S&P)\b")
print('Préfixes agences de crédit :', int(credit.sum()))  # 59
for kind in an.KINDS:
    print(N[N.kind == kind].sample(12, random_state=937)[['id', 'headline']])
```

L'échantillon aléatoire de 48 titres décrit plus haut a été tiré avant la sélection des liens, dans les articles de catégorie analyst classés par la règle. La dernière boucle de cette recette tire un autre échantillon, cette fois après sélection ; elle sert à faciliter une reproduction du contrôle visuel sans prétendre reproduire les mêmes 48 identifiants.

## Conditions préalables au lancement unique

**Le code ne peut pas être lancé tel quel comme application fidèle et achetable du protocole.** Il faut au minimum supprimer les anticipations D1/D2, corriger la fenêtre D3, rendre l'ensemble des positions A3 cohérent avec les sorties D4, publier une inférence principale homogène D5 et compléter les livrables D6/D7. Les décisions sur le délai A3, les notations de crédit, les familles, les calendriers non couverts et les scénarios des contrôles doivent être consignées avec une qualification honnête avant lecture de rendement, puis les tests de risque doivent passer et l'essai à blanc être renouvelé.

Ce travail est encore possible **avant** l'unique lancement : aucun résultat de cette étude n'a été consommé par cette relecture. Le verdict porte sur le code et sa fidélité au protocole, pas sur le succès ou l'échec financier du signal.
