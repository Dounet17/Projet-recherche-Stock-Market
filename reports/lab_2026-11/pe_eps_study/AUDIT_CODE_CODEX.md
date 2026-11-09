# Relecture indépendante du code EPS et P/E avant lancement

08/11/2026, relecture commencée le 07/11. Branche `etude-news`, commit `173c6e9262432e77a5f1b653c0267b876255d59f`. Référence : protocole figé au commit `41db2e2`, puis ses sept choix d'implémentation ajoutés au commit relu.

**Verdict : à corriger d'abord.** Une fuite dans la construction historique des EPS modifie réellement les sélections et les témoins. Les unités de la croissance, l'emploi du facteur d'ajustement avec dividendes et plusieurs livrables doivent également être corrigés ou explicitement arbitrés avant l'unique lancement.

## Périmètre et vérifications

Tous les fichiers demandés ont été lus, y compris les trois audits `analyst_study/AUDIT_CODE_CODEX*.md`. Lectures complémentaires : cadre d'expériences, nettoyage, construction des fondamentaux, fonctions de Holm et de vérification des empreintes. Aucun rendement, capital ou backtest de ces stratégies sur les vraies données n'a été calculé, aucun lancement sans `--dry-run`, aucun accès à `.env`, aucune donnée postérieure à 2024 lue. Les calculs de portefeuille des tests autorisés utilisent exclusivement des cours inventés.

Commandes autorisées exécutées avec `PYTHONDONTWRITEBYTECODE=1` :

```bash
venv/bin/python tests/test_pe_eps_study.py
venv/bin/python reports/run_pe_eps_study.py --dry-run
```

**11 tests réussis**, cinq empreintes conformes, essai à blanc arrêté avant les rendements. Effectifs reproduits : 28 décisions en 2018-2024 ; univers éligible de 518 à 686 titres, médiane 638 ; 100 titres dans E1 et E2 à chaque décision ; médiane de 58 titres communs ; recouvrement E2/P-E bas descriptif de 33 à 76 titres, médiane 53,5.

Contrôles supplémentaires, uniquement EPS, facteurs d'unités, filtres, calendriers et poids : `/tmp/audit_pe_eps_codex_20261107.py`, `/tmp/audit_pe_eps_prefix_20261107.py`, `/tmp/audit_pe_eps_confirm_20261107.py`, plus petits exemples synthétiques. Les appels au backtest, à la comparaison financière, au résumé financier et à la journalisation sont interdits par assertions dans les scripts utilisant le marché réel. Le premier script s'arrête justement sur l'échec d'une assertion de causalité des EPS : ce n'est pas un échec de la suite des onze tests.

Seul le présent fichier est ajouté au dépôt. Les changements préexistants de `.gitignore` et `reports/build_vault.py` restent intacts. Aucun commit.

Gravités : **bloquant** pour une anticipation démontrée dans un signal ou son témoin ; **grave** pour une erreur de mesure, un choix de portefeuille matériel non arbitré ou un livrable substantiellement faux ou absent ; **mineur** pour une convention ou une précision documentaire incomplète. Aucun effet sur la performance n'a été mesuré.

## Défauts et corrections proposées

### D1. Des dépôts futurs changent les EPS passés : bloquant

**Preuve dans le code :** `src/universe_data.py:100-109` charge tous les trimestres du fichier, sans construction progressive selon `filed`. `ttm_eps_column`, lignes 84-94, calcule les écarts entre fins de période sur cette liste complète. Des versions d'un même trimestre portant des fins de période légèrement différentes restent deux lignes distinctes. Une ligne publiée ultérieurement s'intercale donc dans la liste et casse rétrospectivement une suite de quatre trimestres. Le `begin` calculé après le maximum des quatre dates `filed` empêche bien d'utiliser directement un chiffre futur, mais ne protège pas contre cette suppression d'un EPS passé par la structure future de la liste.

Exemple réel : `WAT#0`, CIK `1000697`. Les fins de période du 30/03/2019 et du 29/06/2019 ont leurs premiers dépôts respectivement les 03/05 et 31/07/2019. Des lignes presque identiques, finissant les 31/03 et 30/06/2019, sont déposées seulement le **25/02/2020**. Elles s'intercalent avant le trimestre du 28/09/2019, déposé le 30/10/2019. Les écarts de un ou deux jours font échouer le contrôle `[70, 110]`, avant même que ces dépôts de 2020 soient disponibles.

Autres manifestations, en conservant les mêmes cours, facteurs et métadonnées et en retirant uniquement les dépôts postérieurs à la coupure :

| Coupure | Titre | EPS à la coupure, fichier complet | EPS après retrait des dépôts futurs |
|---|---|---:|---:|
| 01/03/2018 | COHU#0 | manquant | 0,971133 |
| 02/12/2019 | ATRO#0 | manquant | 2,959686 |
| 02/12/2019 | PATK#0 | 4,379783 | 4,149957 |

La fuite atteint les décisions réelles. Au **02/12/2019**, le retrait des seuls dépôts futurs, suivi du recalcul des EPS, donne :

| Portefeuille | Titres présents seulement avec le fichier complet | Titres présents seulement après retrait des dépôts futurs |
|---|---|---|
| E1 | HUM#0 | WAT#0 |
| E2 | CY#0, MSFT#0, SNX#0 | EXEL#0, HUBB#0, WAT#0 |
| Chaque témoin | aucun | CIEN#0, EXEL#0, KSS#0, SPB#0, WAT#0 |

Les deux témoins changent aussi au 01/03/2018 avec l'ajout de WAT, et au 01/09/2021 avec l'ajout d'ITT. Le recalcul des poids n'a appelé aucun moteur financier.

**Correction proposée :** construire les EPS selon une chronologie de disponibilité. À chaque publication, résoudre les versions et doublons de périodes parmi les seuls faits déjà connus, puis rechercher quatre trimestres consécutifs et appliquer l'expiration. Une normalisation des fins de période ne doit elle-même dépendre que des faits disponibles. Il faut figer chaque valeur historique à sa propre date, y compris celle utilisée à `t - 252`. Filtrer une fois tous les faits à la date finale de simulation, ou même seulement à la décision courante pour reconstruire tout son passé, reste insuffisant.

Ajouter un test synthétique avec un doublon futur dont la fin de période diffère d'un jour, puis les régressions WAT, COHU, ATRO et PATK. Refaire les contrôles de préfixe depuis les faits sources. Les quatre fonctions de poids passent actuellement `lab.check_no_lookahead` aux coupures 01/03/2018, 02/12/2019, 01/09/2021 et 02/12/2024 : le test tronque des EPS déjà contaminés et ne voit donc pas D1. C'est la même distinction entre causalité du consommateur et causalité de sa source que dans les audits des notes d'analystes.

### D2. La croissance compare deux nombres d'actions différents lors d'un fractionnement : grave

**Preuve :** `ttm_eps_column` exprime chaque EPS dans l'échelle d'actions de sa séance, `src/universe_data.py:71-94`. En revanche, `src/pe_eps_study.py:24-27` soustrait directement l'EPS courant et celui de 252 séances auparavant, sans remettre ce dernier dans la même unité.

Exemple synthétique : société à bénéfice constant, EPS annuel 4 avant un fractionnement par deux, 2 après. Les publications suivantes sont correctement exprimées à 0,5 par trimestre au lieu de 1. Le 02/12/2019, le code mesure **-50 % de croissance**, bien qu'il n'y ait eu aucun changement du bénéfice à nombre d'actions comparable. Un regroupement d'actions produit le biais inverse.

Le problème touche des sélections réelles : au 01/06/2018, MDR est dans E1 et E2 ; EPS actuel 2,01, EPS passé 0,21, croissance affichée 857,14 %, tandis que le rapport des facteurs d'unités entre les deux dates vaut exactement **1/3**. Cela ne dit pas que toute sa croissance est fausse, mais prouve que la comparaison utilise deux échelles. Un contrôle large repère 21 couples titre/décision sélectionnés par E1 et 20 par E2 avec un rapport du facteur inférieur à 0,67 ou supérieur à 1,5 ; ces nombres regroupent différentes opérations et ne sont pas un décompte de fractionnements vérifiés.

**Correction proposée :** garder l'EPS historique connu à sa date, puis convertir son unité avec les seuls fractionnements intervenus jusqu'à la décision courante, avant de calculer la croissance. Tester fractionnement, regroupement et absence d'opération, avec bénéfice économique constant. Cette remise à l'échelle précise ou corrige la définition économique ; puisqu'elle change la formule littéralement implémentée du gel, la dater explicitement avant lancement. Ne pas remplacer l'historique par des comptes révisés connus seulement aujourd'hui.

### D3. Le facteur avec dividendes modifie aussi artificiellement les EPS et l'E/P : grave

**Preuve :** `share_factor` vient de `adj_close / close`, `src/universe_data.py:169-172`, puis multiplie les EPS à leur dépôt et les divise à chaque séance, lignes 87 et 94. Ce facteur contient les dividendes, pas seulement les fractionnements. La docstring reconnaît l'approximation, mais son ordre de grandeur annoncé, environ 2 % par an, n'est pas une borne contrôlée.

Contre-exemple synthétique : quatre EPS trimestriels de 1, sans aucun changement du nombre d'actions. Si seul un dividende fait passer le facteur du cours ajusté de 0,5 à 1 après les dépôts, `ttm_eps_column` ramène le bénéfice annuel de **4 à 2**. Le dividende n'a pourtant pas divisé les bénéfices comptables déjà publiés. `EPS / raw_close` utilise ensuite ce faux EPS. Un petit dividende produit le même défaut à plus petite échelle.

Le quotient des facteurs à deux dates élimine normalement leur constante de normalisation future : je n'attribue donc pas automatiquement à cette opération une lecture du niveau futur des cours. Le défaut démontré ici est une **erreur d'unité comptable**, distincte de D1 et de la comparaison entre dates de D2. Un changement de facteur à une séance suivant un dépôt effectué hors séance mérite également un test spécifique de convention d'échelle.

**Correction proposée :** suivre les opérations sur le nombre d'actions avec un facteur de fractionnement dédié, sans dividendes, connu à chaque séance. À défaut, annoncer explicitement que l'on conserve une approximation du BPA, en quantifier l'erreur sur les filtres et scores avant lancement et arbitrer sa portée. Une réparation ne doit pas conduire à relancer le test B consommé ; elle doit être consignée pour cette nouvelle étude avec les empreintes nécessaires.

### D4. L'état initial et la période des descriptifs ne sont pas explicités : grave

**Preuve :** `reports/run_pe_eps_study.py:83-86` calcule les poids sur tout le panel, qui commence le 04/01/2016. Il comporte **36** dates trimestrielles, dont 28 en 2018-2024. `lab.backtest:153-169` démarre sur la dernière cible antérieure à `DEV_START`. La décision du **01/12/2017** fournit donc dès le début de janvier 2018 des cibles de 100 titres pour E1 et E2, 608 pour chaque témoin. Le portefeuille ne reste pas en cash jusqu'à la première décision annoncée, le 01/03/2018.

Il n'y a pas ici de lecture d'une décision future : c'est une initialisation héritée du moteur. Mais elle détermine deux mois de placement et n'est ni comptée dans les 28 décisions ni explicitée parmi les sept choix. Par ailleurs, les descriptifs de secteurs et de disparitions, lignes 122-127 du lanceur, utilisent toutes les décisions de 2016-2024, alors que les rendements annuels seraient limités à 2018-2024. Ce second décalage est certain, quelle que soit l'initialisation retenue.

**Correction proposée :** fixer explicitement avant lancement si l'investissement initial reprend les cibles du 01/12/2017 ou attend la première décision de mars 2018. Conserver le comportement hérité peut être une précision du renvoi au moteur, mais il faut le publier avec sa date et ses effectifs ; imposer un démarrage en cash serait une modification à annoncer. Restreindre les descriptifs aux décisions de la période étudiée, en traitant séparément la cible initiale si elle est retenue. Ajouter un test avec historique antérieur à 2018 et contrôle des seuls poids initiaux.

### D5. La part des titres disparus inclut les titres jamais sélectionnés sous pandas 3 : grave

**Preuve :** lanceur, lignes 123-127 : `w[w > 0].stack()` conserve ici les cellules manquantes, avec **pandas 3.0.6**. Le tableau `held` contient donc également tous les titres à poids nul, avec un poids devenu `NaN`. Le calcul de la part disparue ne vérifie ensuite que `security_id`, jamais le poids.

Sur un exemple à trois titres où seul A, survivant, est acheté et où B et C disparaissent, le code annonce **2/3 de disparus au lieu de 0**. Sur les seules 28 dates de développement, le même calcul réel empile 188 104 lignes par portefeuille et annonce 36,9753 % pour E1, E2 et le témoin, alors que les seuls couples effectivement sélectionnés donnent respectivement **7,0714 %, 6,6429 % et 5,4514 %**. Ce sont des effectifs descriptifs, aucun rendement. Le code actuel ajoute en outre les dates antérieures à 2018, voir D4.

Les répartitions sectorielles pondérées ne subissent pas automatiquement le même biais numérique : `sum()` ignore les poids `NaN`. La liste des lignes prétendument détenues est néanmoins fausse.

**Correction proposée :** appeler explicitement `.stack().dropna()`, puis vérifier `weight > 0`. Définir si la part publiée compte les titres distincts, les couples titre/décision ou les poids : ces trois mesures sont différentes. Le calcul actuel semble viser les couples titre/décision. Ajouter un test pandas avec plusieurs titres non détenus et un titre sélectionné plusieurs fois.

### D6. Le deuxième témoin n'a pas tous les livrables promis : grave

**Preuve :** `describe_portfolio`, lanceur 70-74, renvoie les mesures de `lab.summarize`, le Sharpe au-delà de BIL et les rendements annuels, mais ni bêta ni alpha. Les comparaisons secondaires contre SPY, lignes 112-113, apportent bien ces mesures pour E1, E2 et **control_E1 seulement**. Les alpha/bêta de P1/P2 sont contre les témoins et ne remplacent pas ceux contre SPY. Les descriptifs de secteur et de disparitions, ligne 121, omettent aussi `control_E2`.

Les deux témoins ne sont pas identiques : ARCC, à secteur inconnu, est dans celui d'E1 et pas dans celui d'E2 aux décisions des **03/09/2024 et 02/12/2024**, avec 681 contre 680 titres, puis 680 contre 679. Les poids des autres titres changent aussi. On ne peut donc pas attribuer sans justification les statistiques du premier au second.

**Correction proposée :** publier les descriptifs, bêta et alpha contre SPY pour les quatre portefeuilles. Garder les trois tests secondaires annoncés et préciser que S3 concerne le témoin E1, ou dater une extension de la famille avant lancement si l'on veut tester aussi le témoin E2. Calculer une description supplémentaire n'oblige pas à ajouter un test à Holm.

### D7. Le descriptif « P/E bas » n'est pas le test B : mineur

**Preuve :** `counts`, lanceur 51-57, prend les 100 plus bas P/E de l'univers à EPS positif aujourd'hui et 252 séances auparavant, sans seuil minimal de P/E. Le test B, `reports/run_test_b_value.py:22-25`, prend 50 titres dans les 1 000 plus liquides, sans condition d'EPS passé, avec **P/E au moins égal à 3**. Le choix 7 déclare bien le changement d'univers, mais pas toutes ces différences. Le proxy descriptif contient jusqu'à **11 P/E inférieurs à 3** parmi ses 100 titres au 01/06/2023.

**Correction proposée :** appeler cette mesure « recouvrement avec les 100 plus bas P/E de l'univers éligible, sans plancher de 3 ». Si l'intention est de comparer au vrai test B, comparer uniquement ses identités et poids aux dates communes, avec ses 50 titres et son plancher, sans recalculer ses rendements. Conserver séparément les 47 du descriptif de conception et les 53,5 du nouveau proxy ; ne pas les présenter comme la même statistique.

### D8. Une affirmation sur le départage et plusieurs conventions héritées sont incomplètes : mineur

**Preuve :** le choix 1 affirme un départage de liquidité par ordre des colonnes « comme le test B ». Or B utilise `rank(axis=1, ascending=False)` avec rang moyen par défaut ; le nouveau code utilise `method="first"`. Deux liquidités identiques à la frontière peuvent donner une sélection différente. Le départage final des scores de B passe bien par `top_n`, qui utilise `first`.

Autres conventions non rappelées : médiane de vingt séances avec **dix observations seulement exigées**, obligation d'avoir un échange valide au jour de décision, filtre `too_short` et classifications de titres issus du nettoyage complet, expiration de l'EPS 200 jours après la fin du trimestre le plus récent. Sur les décisions éligibles du gel, **un cas**, BIIB le 01/12/2020, a moins de vingt observations valides dans la fenêtre, tout en passant le filtre hérité. Cela ne signifie pas qu'il s'agit d'une nouvelle cotation.

**Correction proposée :** corriger la comparaison documentaire au test B et expliciter le minimum de dix observations, l'expiration et les critères hérités. Modifier ces critères serait un changement de règle ; les exposer ne l'est pas. Ajouter des tests d'ex aequo à la frontière de liquidité et au centième score.

## Qualification des sept choix d'implémentation

| Choix | Appréciation |
|---|---|
| 1. Liquidité parmi les achetables, départage stable | Précision raisonnable d'un classement jusque-là sous-spécifié. L'affirmation « comme le test B » est inexacte pour les ex aequo de liquidité, D8. |
| 2. Centiles pandas, moyenne des ex aequo, E/P sur cours brut | Précision correcte pour les rangs. Le cours brut est la bonne échelle visée ; cela ne démontre pas que l'EPS fourni est correctement ajusté, D2/D3. |
| 3. Zéros si univers vide | Précision conforme à la convention du moteur. Aucun cas vide aux 28 décisions réelles ; un test spécifique manque. |
| 4. Deux témoins selon la connaissance du secteur | Conforme au texte figé, qui impose déjà le secteur connu à E2 et son témoin. Ils diffèrent effectivement en fin 2024. |
| 5. Journaliser seulement E1/E2 | Précision défendable : les témoins sont des références, pas deux variantes sélectionnées pour leur performance. Romano-Wolf reste distinct de la famille confirmatoire P1/P2. |
| 6. Contrôle automatique sur quatre portefeuilles | Précision conforme et bon raccordement manuel à la place de `run_experiment`. Sa portée doit être limitée aux poids sur matrices déjà construites, D1. |
| 7. Nouveau recouvrement descriptif et disparitions futures | La lecture future des disparitions est admissible pour ce descriptif isolé des signaux. En revanche, le recouvrement change de définition par rapport à la mesure de conception : le présenter comme **changement de définition descriptive**, avec les deux populations. Ce n'est pas un changement de sélection E1/E2, mais les seules mentions « précision » et « changement d'univers » ne couvrent pas D7. Le calcul des disparitions est faux, D5. |

Choix supplémentaires à consigner : initialisation en janvier 2018 depuis décembre 2017 ; population de S3 parmi les deux témoins ; unités utilisées avant de comparer deux EPS ; facteur avec dividendes au lieu d'un facteur de fractionnement ; période et dénominateur des descriptifs. Les corrections de D1 et D5 sont des corrections de code, pas des ajustements guidés par un rendement. Les arbitrages économiques de D2/D3 et l'éventuel changement de démarrage doivent être datés honnêtement avant toute exécution.

## Points vérifiés et limites de causalité

| Point demandé | Constat |
|---|---|
| Disponibilité après `filed` | Pour une liste de quatre trimestres fixée, `searchsorted(..., side="right")` commence à la première séance strictement postérieure au dépôt le plus tardif. Le dépôt courant est exclu même avant la clôture, comme prévu. D1 concerne la sélection des quatre lignes, pas ce décalage. |
| Expiration | `period_end + 200 jours`, borne incluse, puis EPS manquant. Exemple synthétique : fin 31/12/2019, valeur présente le 18/07/2020 et absente le 19/07. Ce n'est pas 200 jours après `filed`. |
| EPS à 252 séances | `shift(252)` prend la valeur stockée à cette ancienne séance, sans remplacer explicitement son chiffre par celui d'aujourd'hui. Mais la source doit d'abord être causale à cette ancienne date, D1, et les unités doivent être comparables, D2. |
| Liquidité et achetable | Prix brut au moins 5, médiane de montant brut au moins 1 M$, connus à la clôture ; classement des 1 000 avant le filtre EPS. Aucun poids positif sur un titre non achetable aux 28 décisions, pour les quatre portefeuilles. Coût à l'ouverture fondé sur la liquidité de la veille. |
| Dates | Le panel reproduit exactement les 1 761 séances du calendrier 2018-2024. La première séance de mars, juin, septembre et décembre est correctement choisie, jours fériés compris. Le calendrier est vérifié par empreinte mais le lanceur ne l'utilise pas pour construire ses dates. |
| E2 | Croissance classée dans tout l'univers éligible à secteur connu, E/P classé dans chaque secteur, rangs croissants divisés par l'effectif, moyenne des ex aequo, moyenne des deux rangs, puis 100 scores les plus élevés. Un secteur d'un seul titre obtient 1 : conséquence de la convention déclarée, pas erreur de code. |
| Poids et lignes vides | Somme des cibles égale à 1 à l'arrondi flottant près. Hors décision, lignes entièrement `NaN`, donc maintien et dérive des positions ; jour vide, zéros donc liquidation. Une seule translation vers l'ouverture suivante dans `backtest`, aucune double translation. |
| Témoins | Même éligibilité et mêmes dates que chaque stratégie, tous les candidats à poids égaux, mêmes coûts et scénarios. Ils ne sélectionnent pas rétrospectivement les titres effectivement retenus par la stratégie. D1 les affecte aussi. |
| SIC actuel | Limite explicitement annoncée au gel, `PROTOCOLE_PE_EPS.md:93`. E2 et son témoin utilisent cette information rétrospective ; le contrôle de préfixe ne peut pas la certifier historique. Ce n'est pas une nouvelle découverte silencieuse ni une raison d'affirmer une parfaite reconstitution historique. |
| P1/P2 et Holm | `lab.compare` reçoit E1 moins son témoin et E2 moins le sien, dans le bon sens. Les deux p unilatérales de l'écart annualisé des log-rendements sont seules corrigées ensemble. Bootstrap stationnaire hérité : 4 000 tirages, blocs moyens de 21 séances. Pas de substitution d'une p d'alpha ou de Sharpe. |
| Secondaires | E1/SPY, E2/SPY et témoin E1/SPY sont corrigés dans une famille séparée de trois. La direction et l'association des p à leurs noms sont correctes. Le choix du témoin E1 doit être explicite, D6. |
| Scénarios | `run_variant:84-109` calcule les trois hypothèses de sortie et les coûts doublés pour chacun des quatre portefeuilles ; les capitaux de sensibilité sont bien rendus dans `extra`. Le scénario de base figure dans le résumé principal. Pas de sensibilité manquante prétendue ici. |
| Aléatoires | Vingt tirages, calendrier et poids de chaque portefeuille conservés, graine 0. Comme le laboratoire, ils piochent dans tous les titres achetables, sans appariement EPS, secteur ou top 1 000 : repères larges, pas tests isolant le signal fondamental. |
| Journal et Romano-Wolf | E1/E2 sont enregistrés avant l'appel à `adjusted_p_values`. Celui-ci lit toutes les séries du dossier `trials/universe`, applique Romano-Wolf contre SPY puis ne restitue que les deux nouvelles p. Ces p ne corrigent pas P1/P2 contre les témoins. Aucun calcul de cette procédure n'a été exécuté pendant l'audit. |
| Autres héritages | Métadonnées complètes pour `too_short` et les types, `suspect_print` parfois fondé sur un retour du lendemain, nettoyage d'ouverture utilisant la clôture du même jour, sorties à la dernière cotation et hypothèses de radiation : limites documentées du cadre. Elles ne sont pas certifiées causales par le test sur les poids. La stratégie ne lit pas directement les scénarios de sortie pour choisir ses titres. |

## Tests manquants avant lancement

1. **Sources des EPS :** invariance après ajout/retrait de tout dépôt futur, notamment doublons de trimestre décalés d'un jour ; invariance de l'EPS historique à sa propre date, puis des poids E1/E2 et des témoins. Régressions WAT au 02/12/2019 et autres cas de D1.
2. **Unités :** EPS et E/P à échelle cohérente avec `raw_close` après fractionnement et regroupement ; croissance économique inchangée à bénéfice constant ; dividende seul sans modification d'EPS ; dépôt hors séance juste avant une opération.
3. **Bornes de disponibilité :** dépôt le jour de décision, vendredi, week-end, quatre dates de dépôt non monotones ; présence à 200 jours et absence à 201 ; trou de trimestre et publication d'un trimestre ancien après un plus récent.
4. **Classements et poids :** ex aequo de liquidité au rang 1 000, score au rang 100, centiles ex aequo, secteur singleton, moins de 100 candidats, aucun candidat ; différence entre ordre de liquidation et absence d'ordre.
5. **Lanceur sur marché entièrement inventé :** vérifier la famille P1/P2 et son appariement, les trois secondaires, le passage des quatre portefeuilles, les trois sorties et coûts doublés, la journalisation de deux essais puis l'appel global de Romano-Wolf. Les onze tests actuels ne traversent jamais cette branche complète : le test de raccordement appelle seulement `run_one`, et l'autre branche testée est l'essai à blanc.
6. **Livrables :** présence du bêta et de l'alpha SPY de chaque témoin, descriptifs des quatre portefeuilles, rejet des poids `NaN` dans les effectifs de disparitions, période correcte et règle d'initialisation explicite.

**À corriger d'abord : réparer la construction causale des EPS, trancher leurs unités et l'initialisation, corriger les descriptifs et compléter les livrables, puis renouveler les tests et l'essai à blanc avant l'unique lancement.**
