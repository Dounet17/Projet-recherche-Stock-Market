# Audit croisé de la piste prix avant validation

Audit terminé sur le développement 2018-2024 seulement. **Huit défauts ou omissions sont reproduits par huit tests rouges** dans `tests/test_price_audit.py`; cinq autres tests de contrôle passent. Les 19 tests préexistants du moteur et de la piste sociale passent également. Les quatre fichiers audités sont restés inchangés.

La préinscription doit être précisée avant son utilisation : appel de fonction, fréquence réelle des transactions, critère de risque et règle de décision statistique. Aucune lecture de la validation n'est nécessaire pour ces corrections. L'audit n'a trouvé **aucune fuite temporelle confirmée** dans les stratégies examinées, y compris les deux modèles ML. Les défauts de fréquence de rééquilibrage sont des incompatibilités entre la définition annoncée des stratégies et l'interface de poids du moteur, plutôt qu'une erreur d'addition des gains ou des frais par `lab.backtest`.

## Périmètre et preuves

Lecture seule de `src/price_lab.py`, `reports/run_price_lab.py`, `reports/run_price_robustness.py` et `reports/lab_2026-11/preregistration_claude.json`, plus le protocole et les résultats de développement qu'ils produisent. Prix chargés uniquement par `lab.load_panel(end=lab.DEV_END)`; dernier jour du panel : 31/12/2024. Les rendements d'essais stockés sont eux aussi filtrés dans Parquet à cette date. Aucun script d'essais n'a été importé ni lancé; seules une affectation et une définition de fonction ont été extraites par analyse syntaxique pour des reproductions isolées, sans leurs écritures de fichiers.

Les empreintes des quatre fichiers, les chiffres ci-dessous et les 31 contrôles de causalité sont dans `price_audit_evidence.json`. L'empreinte de `src/price_lab.py` correspond exactement à celle de la préinscription : `0aef9b324be915f5b973c59f588cfd7d9b9e7ff10adfd27490e0c770d4946b10`.

Pour un débutant : un poids de 50 % signifie que la moitié du portefeuille est investie. Si l'action monte, ce poids augmente naturellement sans achat supplémentaire. Conserver les actions laisse ce poids varier; le ramener chaque jour à 50 % impose des ventes. C'est cette différence qui explique les deux premiers défauts.

## A1. Les portefeuilles présentés comme mensuels rééquilibrent chaque jour

**Localisation :** `src/price_lab.py:36`, `src/price_lab.py:177`, `src/price_lab.py:181`, `src/price_lab.py:215`. La sélection est mensuelle, mais `monthly_hold(...).ffill()` répète les mêmes poids chaque jour. Or `lab.backtest` interprète ces poids comme une cible à rétablir à chaque ouverture, après dérive des poids. Une cible répétée n'est pas une instruction de conserver les quantités d'actions.

**Scénario minimal :** dans un même mois, deux actifs commencent à 50 % chacun. L'un monte de 10 % par jour et l'autre reste stable. À l'ouverture suivante les poids sont environ 52,38 % et 47,62 %. Le moteur échange 4,76 % du portefeuille pour revenir à 50/50, alors qu'aucune nouvelle décision mensuelle n'a eu lieu. Trois journées intérieures du test cumulent 14,29 % de montants échangés, au lieu de zéro.

**Impact constaté à 5 pb par côté, 2018-2024 :**

| Portefeuille | Capital publié | Journées de transaction hors échéance mensuelle | Montants échangés hors échéance / capital courant, somme | Effet composé des seuls frais de ces transactions |
| --- | ---: | ---: | ---: | ---: |
| `megacap_equal` | 93 832 USD | 1 674 | 19,789 fois | 933 USD |
| `megacap_top3_mom` | 193 836 USD | 1 455 | 16,032 fois | 1 560 USD |

Les journées d'entrée initiale et de liquidation finale sont exclues de ce comptage. Une décision prise à la première clôture du mois ne s'exécute que le jour suivant, ce qui est pris en compte. Le calcul des frais ci-dessus retire seulement les coûts des transactions intermédiaires en conservant les allocations quotidiennes simulées : les capitaux correspondants seraient 94 765 et 195 396 USD. **Ce ne sont pas les capitaux d'une vraie stratégie à rééquilibrage mensuel**, dont les poids et les gains bruts seraient différents. Cet audit ne prétend pas les avoir calculés.

**Correction proposée :** soit assumer et annoncer « sélection mensuelle, pondérations rétablies quotidiennement », puis figer explicitement cette politique pour le candidat et son panier de référence; soit ajouter au moteur une instruction de maintien des quantités ou un calendrier de rééquilibrage décidé à la clôture et exécuté le lendemain. Hors échéance, le moteur doit laisser dériver les positions. Il ne faut pas simuler ce maintien en construisant des poids décidés à la clôture à partir de l'ouverture future. Si le comportement est changé, refaire les résultats de développement et le gel avant toute validation. Les règles à poids exclusivement 0 ou 1, comme la SMA mensuelle sur un seul titre, ne subissent pas cette dérive de pondération.

**Test rouge :** `ConfirmedPriceBugs.test_monthly_hold_must_not_rebalance_inside_the_month`.

## A2. La bande de tolérance ne bloque pas les petites transactions de dérive

**Localisation :** `src/price_lab.py:67`, `src/price_lab.py:119`, `src/price_lab.py:123`. `_with_band` compare la nouvelle cible à l'ancienne cible, puis répète cette dernière. Il ne compare pas la cible au poids réellement détenu. Le moteur ramène donc le portefeuille au poids mémorisé même quand `_with_band` n'a décidé aucun changement.

**Scénario minimal :** cible constante de 50 %, bande de 10 points de pourcentage, action gagnant 10 % par période. La dérive d'environ 2,38 points à chaque ouverture déclenche pourtant une transaction. Les trois journées intérieures du test cumulent 7,14 % de montants échangés. Même en laissant réellement dériver les quantités dans ce court scénario, la bande n'aurait pas encore été franchie pendant ces journées.

**Impact à 5 pb :** `TSLA__vol_target_30` effectue 1 531 transactions sur des journées où sa cible appliquée est inchangée. Elles représentent 10,006 fois le capital courant en montants échangés cumulés. Les seuls frais de ces journées amputent le capital final d'environ 419 USD : 83 592 USD observés contre 84 012 USD si ces frais étaient retirés, à allocations quotidiennes identiques. Là encore, cela ne calcule pas le rendement d'une véritable bande sur les positions détenues. Le Sharpe publié de 1,026 et le drawdown d'environ -43 % décrivent la politique de cibles quotidiennes effectivement simulée.

**Correction proposée :** distinguer une décision de transaction d'un poids cible. Si le but est une vraie bande, comparer à la position détenue valorisée avec l'information connue à la clôture, puis envoyer l'ordre ou l'instruction de maintien pour l'ouverture suivante. Sinon renommer la fonction et la stratégie pour annoncer « bande sur les changements de cible, avec rééquilibrage quotidien vers la cible mémorisée ». La préinscription du ciblage de volatilité doit annoncer la politique retenue.

**Test rouge :** `ConfirmedPriceBugs.test_band_must_prevent_small_trades_caused_by_drift`.

## A3. La correction multiple sépare la recherche initiale et la robustesse

**Localisation :** `reports/run_price_lab.py:71`, `reports/run_price_robustness.py:23`, `reports/run_price_robustness.py:62`. Le premier script corrige les 175 essais initiaux; le second repart d'un dictionnaire vide et corrige seulement ses 24 essais. Le journal contient pourtant 199 essais utilisés pendant la même recherche. Cela ne satisfait pas la correction sur l'ensemble des essais demandée par le protocole.

La p corrigée mesure ici la difficulté à distinguer un avantage du hasard après avoir essayé plusieurs règles. Repartir d'une petite famille de tests après avoir sélectionné des pistes sous-estime cette recherche.

**Recalcul indépendant :** mêmes rendements enregistrés, mêmes références propres à chaque essai, même `lab.romano_wolf`, 4 000 tirages, blocs moyens de 21 jours, graine 0, mais 199 colonnes ensemble.

| Candidat de robustesse | p publiée, famille de 24 | p dans la famille de 199 |
| --- | ---: | ---: |
| `mega_top3_lb126` | 0,29700 | 0,80575 |
| `tsla_filter_QQQ_200` | 0,60275 | 0,99275 |

Les comparaisons ont des références différentes selon l'essai, ce qui est respecté : SPY pour les rotations initiales, panier équipondéré pour les expériences qui demandent si le momentum ajoute au panier. Les deux comparaisons appartiennent à la recherche et sont donc conservées. Il ne s'agit pas de modifier rétroactivement la référence d'un essai. Les valeurs ne démontraient déjà pas une supériorité significative dans la petite famille; le recalcul renforce ce constat.

**Correction proposée :** reconstruire une table commune à partir du journal et des rendements de tous les essais avant de publier les p de développement et d'écrire les preuves de la préinscription. Indiquer séparément les sensibilités de coûts et de rémunération du cash; si elles servent elles aussi à choisir une variante, les inclure explicitement dans le journal et le périmètre statistique. La correction de Holm prévue sur la future validation ne répare pas rétroactivement les p de développement.

**Test rouge :** `ConfirmedPriceBugs.test_multiple_testing_family_includes_initial_and_robustness_trials`.

## A4. L'alpha corrigé du script conserve un bêta fixe

**Localisation :** `reports/run_price_lab.py:67`, `reports/run_price_lab.py:72`. Le script calcule une fois `result.returns - row['beta'] * base`, puis soumet cette série à Romano-Wolf. Le bêta mesure l'exposition aux mouvements de la référence; il est estimé sur les données, donc son incertitude doit être prise en compte quand on teste l'alpha, le rendement restant après cette exposition.

Le `compare` du moteur a bien été corrigé pendant le premier audit : il réestime maintenant bêta et alpha à chaque tirage. Cette correction n'a pas été transportée dans le calcul conjoint de `rw_p_alpha` du script. Le test n'exécute que l'affectation syntaxique concernée, sans lancer le script.

**Scénario confirmé :** 120 rendements synthétiques, modèle `0.0003 + 0.7 * benchmark + bruit`, générateur de graine 5, bootstrap de 199 tirages, blocs de 7, graine 9. Pour une seule hypothèse, le calcul à bêta fixe donne p = 0,01005; le bootstrap de l'intercept avec réestimation du bêta donne p = 0,08543. La décision à 5 % change. Avec une seule hypothèse, la correction multiple ne peut expliquer cet écart : il vient bien du bêta figé.

**Impact réel illustratif :** pour TSLA avec ciblage de volatilité, `compare` donne alpha annuel +3,94 %, intervalle à 95 % [-6,04 %; +14,88 %], p brute 0,22275. La différence de Sharpe vaut +0,04895, p brute 0,35850. Le `rw_p_alpha` à bêta fixe publié vaut 0,99925; ce chiffre n'est pas interprété comme une correction valide de l'alpha de régression. L'audit n'a pas calculé une nouvelle famille complète d'alphas réajustés et ne lui substitue pas une p brute.

**Correction proposée :** produire conjointement, avec les mêmes blocs pour tous les essais, des tirages d'intercepts et de pentes réestimés, puis appliquer l'étape de maximum et le classement pas à pas à ces statistiques. Ou retirer l'affirmation « alpha corrigé » et conserver les alphas et intervalles correctement estimés de `compare` comme résultats exploratoires jusqu'à disposer de cette implémentation. Éviter de réutiliser simplement `romano_wolf` sur des résidus à bêta fixe en prétendant tester le même objet.

**Test rouge :** `ConfirmedPriceBugs.test_alpha_correction_refits_beta_in_each_bootstrap_sample`.

## A5. Le RSI devient manquant quand il n'existe aucune perte

**Localisation :** `src/price_lab.py:52`, particulièrement `src/price_lab.py:56`. `loss.replace(0, np.nan)` transforme le cas d'une série strictement croissante en valeur manquante. Le RSI, indicateur qui compare hausses et baisses récentes, vaut alors 100 après son préchauffage lorsque le gain est positif et la perte nulle.

**Scénario :** clôtures 1, 2, ..., 11 avec fenêtre 2 : dernière valeur obtenue `NaN`, attendue 100. Cela peut notamment supprimer un signal de sortie `RSI > 70` ou faire imputer une valeur dans un modèle.

**Impact mesuré :** zéro observation de développement affectée pour les 10 actifs, aux fenêtres 2 et 14. Ce défaut numérique n'explique donc pas les valeurs RSI de 2018-2024 ni le classement des candidats dans cette période. Il reste un cas limite réel de l'indicateur; le comportement d'une série totalement plate doit aussi être choisi explicitement.

**Correction proposée :** définir RSI = 100 lorsque perte = 0 et gain > 0, RSI = 0 lorsque gain = 0 et perte > 0, puis annoncer une convention pour gain = perte = 0, par exemple 50. Conserver les valeurs manquantes dues au préchauffage.

**Test rouge :** `ConfirmedPriceBugs.test_rsi_without_losses_is_one_hundred`.

## A6. L'appel préinscrit du filtre TSLA n'est pas directement reproductible

**Localisation :** `reports/lab_2026-11/preregistration_claude.json:41`, `reports/run_price_robustness.py:50`, et les empreintes de la préinscription à la ligne 5.

**Scénario :** la valeur figée `market_filter('TSLA','QQQ',200) de reports/run_price_robustness.py` n'est pas une expression Python. La fonction n'existe pas dans `price_lab`; importer le script pour l'obtenir exécuterait immédiatement les essais et leurs écritures de journal. En outre, seule l'empreinte de `src/price_lab.py` est figée, pas celle du script contenant la fonction appelée.

**Correction reproductible sans nouvelle stratégie :** remplacer l'appel par `price_lab.single_strategy('market_filter_qqq', 'TSLA')`. L'audit a extrait uniquement la définition de `market_filter` et vérifié que ses poids sont **exactement égaux**, sur tout le panel autorisé, à ceux de cette fabrique publique déjà présente dans le fichier figé. Cette substitution ne change donc aucun résultat de développement. Pour l'autre candidat, qualifier aussi la constante en `price_lab.MEGACAPS` évite de dépendre d'un import implicite. Préciser de même la fonction exacte du panier de référence.

**Test rouge :** `ConfirmedPriceBugs.test_preregistered_calls_are_standalone_python_expressions`.

## A7. La réussite du candidat de risque omet l'alpha du protocole

**Localisation :** `reports/lab_2026-11/preregistration_claude.json:64`, à comparer au critère 2 du protocole.

La préinscription demande « Sharpe supérieur et drawdown moins profond ». Le protocole définit « gagner mieux » par **Sharpe supérieur et alpha positif**. Le drawdown, la plus forte perte depuis un sommet, est utile mais ne remplace pas ce second critère. Cette omission peut changer la qualification sur une autre période, dont les rendements de référence peuvent notamment être négatifs. Elle doit donc être résolue avant de regarder la validation.

**Impact sur le développement :** le candidat a actuellement un alpha ponctuel positif de +3,94 % par an; son intervalle inclut cependant zéro. L'ajout du critère de signe ne change pas le constat ponctuel de cette période. Il interdit en revanche de déclarer ultérieurement « gagner mieux selon le protocole » avec un alpha négatif. Un gain de Sharpe sans gain de capital doit continuer à être publié comme une conclusion distincte du critère « gagner plus ».

**Correction proposée :** inscrire explicitement Sharpe supérieur et alpha positif comme conditions de « gagner mieux »; conserver le drawdown comme condition supplémentaire si elle est voulue. Préciser les coûts concernés et si ces conditions portent sur des estimations ponctuelles ou sur des tests. Si le but se limite à réduire les pertes en acceptant moins de rendement, le nommer comme objectif distinct sans lui donner l'étiquette du critère 2 du protocole.

**Test rouge :** `ConfirmedPriceBugs.test_risk_success_requires_positive_alpha_as_in_protocol`.

## A8. La règle de décision statistique n'est pas figée complètement

**Localisation :** `reports/lab_2026-11/preregistration_claude.json:36`, `reports/lab_2026-11/preregistration_claude.json:50`, `reports/lab_2026-11/preregistration_claude.json:64`, `reports/lab_2026-11/preregistration_claude.json:68`.

Holm est nommé, mais aucun seuil de rejet n'est donné. Les « comparaisons principales » ne désignent pas exactement les métriques corrigées : excès de rendement, différence de Sharpe, alpha, ou plusieurs d'entre elles. Les deux premiers candidats demandent rendement et Sharpe supérieurs à 5 et 10 pb; on ne sait pas si les deux coûts et les deux métriques sont des tests formels, des conditions de signe, ou si le coût à 10 pb est seulement descriptif. Le troisième candidat ne précise pas ses coûts dans son critère individuel.

**Scénario :** une p corrigée de 0,08 serait acceptée à 10 % mais refusée à 5 %. Une autre lecture peut déclarer la réussite dès que les estimations ponctuelles sont positives, même avec p élevée. Le texte actuel ne permet pas de départager ces décisions avant de voir les données. L'avertissement sur les 22 mois de validation est honnête, mais ne définit pas la décision.

**Correction proposée :** séparer « conditions économiques ponctuelles » et « preuve statistique », donner un seuil explicite choisi avant lecture, par exemple 0,05, indiquer les tests unilatéraux de `compare` par leur nom exact, les références, les coûts inclus et la liste complète des hypothèses soumises à Holm. Fixer également le critère global : réussite par stratégie, sans transformer après coup un succès sur une métrique secondaire en succès principal. Aucun chiffre de validation n'est nécessaire pour compléter ces champs.

**Test rouge :** `ConfirmedPriceBugs.test_preregistered_statistical_rule_has_an_explicit_significance_level` reproduit l'absence de seuil; la définition exacte de la famille demeure à contrôler éditorialement après correction.

## Points contrôlés sans défaut confirmé

- **Purge ML :** pour une frontière annuelle à la position `b`, le dernier exemple est `t = b - 7`. Sa cible utilise `open(t + 6) = open(b - 1)`, déjà connu avant la première décision de l'année. Le prétraitement de la régression logistique est ajusté seulement sur l'apprentissage. Le boosting désactive l'arrêt anticipé et n'introduit pas de découpage aléatoire de validation. Le calcul de cibles futures sur le panel complet ne fuit pas dans l'apprentissage dès lors que ces seuls indices purgés sont utilisés. Un modèle enregistreur vérifie les indices; les deux vrais modèles passent aussi les troncatures aux 02/01/2018, 31/12/2021 et 28/06/2024 avec deux threads CPU.
- **Chronologie mensuelle :** le premier jour de chaque mois est détecté par comparaison avec le mois précédent, sans consulter le dernier jour futur du mois. Le contrôle ne trouve pas de fuite par troncature. La décision se prend à cette première clôture et s'exécute à l'ouverture suivante; cela diffère d'un achat dès la première ouverture du mois, mais reste causal.
- **Momentum :** les scores utilisent les clôtures présentes et décalées vers le passé, les volatilités et moyennes roulantes du passé. Les rangs sont déterministes. Le classement précède le filtre de tendance : une place éliminée reste en liquidités et n'est pas remplacée par le quatrième actif. Ce comportement est confirmé, sans le qualifier d'erreur. Les poids restent positifs et leur somme ne dépasse pas 1.
- **Machine à états :** remplissage vers l'avant, état initial en liquidités, aucune utilisation future. En cas d'entrée et de sortie simultanées, l'entrée gagne parce qu'elle est affectée en second. Ce choix mérite d'être documenté : pour `drawdown_stop_25`, l'intersection « nouveau sommet sur 50 jours » et « baisse de plus de 25 % depuis le sommet sur 126 jours » arrive 10 jours pour TSLA, 10 pour NVDA, 4 pour AMZN et 4 pour META en développement. Cela permet une réentrée avant de retrouver 75 % du sommet long. Aucun contrat explicite de priorité ne permet d'en faire ici un neuvième bug confirmé.
- **Références :** `megacap_equal` utilise bien les sept mêmes titres que le candidat. Chaque `equal_without_*` utilise bien le sous-ensemble qui exclut ce même actif, avec un poids de 1/6 sur chaque autre titre. Tous les capitaux de référence des sept exclusions ont été recalculés et concordent à moins de 0,0000001 USD avec `robustness.csv`. Il n'y a pas de confusion de sous-ensemble ni de référence retirant un autre actif. La réserve A1 demeure sur la fréquence quotidienne effective du panier.
- **Exclusion de chaque titre :** les sept retraits conservent un capital supérieur au panier correspondant, mais sans preuve significative. Par exemple sans NVDA : 103 632 contre 72 872 USD; sans TSLA : 101 873 contre 70 575 USD. Ce contrôle ne suffit pas à supprimer le biais de choix initial de l'univers.
- **Comptabilité :** les stratégies utilisent bien `lab.backtest`, sans décaler leurs poids une seconde fois. Les entrées, les rééquilibrages effectifs et la liquidation paient les frais. Le contrôle synthétique distingue bien le coût de 4,76 % de montants échangés entre deux actions du coût de 2,38 % entre une action et des liquidités. Le moteur valorise la politique quotidienne qu'il reçoit de manière cohérente; A1 et A2 portent sur ce qui lui est demandé. Le taux de change, la fiscalité et les prix bid/ask ne sont pas couverts par cet audit.
- **Sélection :** les 175 essais initiaux et les 24 variantes de robustesse sont effectivement inscrits au journal, y compris les échecs. Le choix rétrospectif de grandes gagnantes est déjà déclaré dans le protocole et dans `price_lab.py:272`; il serait inexact de le présenter comme un biais totalement caché. Il devrait aussi apparaître dans la préinscription pour que « hors échantillon » ne soit pas compris comme une généralisation à toutes les actions. Le choix du seuil 200 jours et de QQQ après exploration, ainsi que la concentration en 2020 et 2022 et l'échec du filtre SPY, sont visibles dans le journal et le texte figé. A3 reste le défaut de traitement de cette recherche, plutôt qu'une absence de journal.

Les 15 rotations et les 14 règles simples appliquées à TSLA ont chacune passé `lab.check_no_lookahead` aux cinq troncatures par défaut. Les deux ML l'ont passé aux trois dates explicites ci-dessus. Un contrôle de troncature positif ne prouve pas à lui seul l'absence de tous les biais de source ou de sélection.

## Reproduction et décision de l'audit

```text
venv/bin/python -m unittest tests.test_price_audit -v
```

Résultat attendu sur les fichiers audités : **13 tests, 8 échecs, 5 réussites, code 1**. Ces échecs constituent ici les reproductions demandées, pas des corrections appliquées. Sortie intégrale : `price_audit_tests.txt`.

```text
venv/bin/python -m unittest tests.test_lab tests.test_social_lab
```

Résultat : **19 tests, OK, code 0**, sortie `price_audit_existing_tests.txt`. Les tests du nouvel audit ne sont pas marqués `expectedFailure`, afin qu'ils deviennent verts seulement après correction ou décision contractuelle explicite. Le test de correction multiple reconstruit les 199 séries et leurs références à partir des seuls fichiers de développement; il prend environ deux secondes sur cette machine.

L'audit est complet, mais **je ne valide pas encore le gel pour l'ouverture de la validation**. Les appels et les règles de réussite doivent devenir univoques, et la fréquence de transaction doit être assumée ou corrigée. Les p corrigées de développement doivent aussi être mises à jour sur la famille complète; l'alpha corrigé à bêta fixe doit être remplacé ou retiré. Ces points sont résolubles sans consulter un seul rendement après 2024. Ils ne démontrent pas que les candidats sont inutiles, mais empêchent de présenter leurs chiffres actuels comme une preuve robuste de supériorité.

## Contre-vérification des corrections, avant validation

**Verdict au terme de cette contre-vérification : gel non validé pour ouvrir la validation.** Les 35 tests demandés passent et la majorité des corrections est confirmée. Il reste cependant une erreur dans le poids détenu utilisé par la bande et une erreur de coût dans certaines références du correcteur familial. Deux limites supplémentaires sont reproduites : l'alpha constant positif est mal traité par `romano_wolf_alpha`, et les dates terminales des fenêtres glissantes doivent être définies explicitement. Aucun fichier de code, de test ou de préinscription n'a été modifié pendant cette contre-vérification. La présente section est ajoutée au rapport initial, dont les constats antérieurs restent l'historique de l'audit.

### État de A1 à A8

| Point initial | Contre-vérification |
| --- | --- |
| A1, rééquilibrages mensuels | Corrigé : `_finish` émet des lignes entièrement NaN hors échéance et le moteur conserve les positions. Zéro transaction hors échéance pour les deux portefeuilles mégacapitalisations. |
| A2, bande de tolérance | Partiellement corrigé : NaN évite bien le rééquilibrage quotidien vers une cible mémorisée, mais le poids détenu estimé inclut à tort un mouvement de prix antérieur à l'exécution de l'ordre. Détail ci-dessous. |
| A3, famille statistique | Les 199 essais prix sont bien réunis et les 244 noms des deux journaux sont présents dans `family_pvalues.csv`. Réserve : les références des 15 variantes sociales à 10 pb sont recalculées à 5 pb. |
| A4, bêta réestimé | Corrigé dans le cas non dégénéré : les mêmes blocs sont partagés et `_fit_alpha` réestime pente et intercept à chaque tirage. Nouveau cas limite incorrect lorsque l'alpha bootstrap a une variance nulle. |
| A5, RSI sans perte | Corrigé : hausse seule donne 100, baisse seule donne 0, cours plat donne 50 après préchauffage. |
| A6, appel reproductible | Corrigé : le filtre TSLA utilise la fabrique publique et la constante MEGACAPS est qualifiée. L'appel de référence équipondérée est aussi explicite. |
| A7, réussite ajustée au risque | Corrigé dans le texte : Sharpe supérieur, alpha positif et drawdown moins profond aux deux coûts. L'alpha reste une condition de signe, pas un test principal supplémentaire. |
| A8, règle statistique | Les quatre hypothèses de Holm sont identiques dans les deux préinscriptions, le seuil vaut 0,05, le coût statistique principal est 5 pb et les conditions économiques concernent 5 et 10 pb. Les verdicts économiques et statistiques restent distincts. |

Avec la nouvelle politique mensuelle, le capital de `megacap_equal` vaut 95 603,10 USD et celui de `megacap_top3_mom` 196 415,15 USD, contre respectivement 93 832,26 et 193 836,34 USD auparavant. Les journées d'entrée et de liquidation exclues, le nombre de transactions hors échéance est maintenant exactement zéro pour les deux. Il s'agit cette fois d'un changement effectif de politique de portefeuille, et pas seulement d'un retrait de frais à allocations constantes.

### Les deux tests réécrits n'ont pas été affaiblis sur leur objet initial

Dans `tests/test_price_audit.py:85`, le test d'alpha ne teste plus une affectation obsolète du script : il vérifie son retrait puis appelle `romano_wolf_alpha`. Il conserve le scénario qui distinguait p = 0,01005 à bêta fixe de p = 0,08543 avec réestimation. Une vérification par mutation temporaire en mémoire, sans modifier de fichier, remplace la nouvelle fonction par l'ancien calcul à bêta fixe : **le test réécrit échoue bien**, avec un échec et aucune erreur d'exécution. Le test indépendant de `tests/test_social_lab.py` calcule toujours directement les intercepts réajustés pour contrôler `compare`, ce qui complète cette vérification.

Dans `tests/test_price_audit.py:187`, le `ffill` sert seulement à relire les dernières cibles afin de vérifier l'exclusion du bon actif, les six poids à 1/6 et la somme égale à 1. Cela adapte ce test au format NaN des jours sans ordre. Il ne transforme pas une simulation de positions en rééquilibrage quotidien. Le test séparé A1, inchangé, continue de vérifier l'absence de transactions intermédiaires. Cette réécriture ne retire donc pas la vérification de fréquence ni celle du sous-ensemble.

Ces tests ne couvrent toutefois ni les sauts nocturnes dans la bande, ni les références à 10 pb du correcteur familial, ni l'alpha constant positif. Leur réussite ne suffit pas à valider ces cas nouveaux.

### R1. La bande utilise encore un poids détenu incorrect après un saut à l'ouverture

**Localisation :** `src/price_lab.py:83` à `src/price_lab.py:89`, et appel du candidat à `src/price_lab.py:132`.

Au jour d'une décision, `_with_band` affecte immédiatement `held = target`, comme si l'achat avait été exécuté à cette clôture. À la clôture suivante, il applique toute la variation entre les deux clôtures. Or l'achat réel a lieu à l'ouverture intermédiaire. Le mouvement entre la première clôture et cette ouverture ne doit donc pas modifier le poids détenu après cet achat. La valeur estimée peut ainsi diverger de la position réellement détenue, sans que le contrôle de causalité détecte de fuite : tous les prix utilisés sont passés, mais la comptabilité de l'estimateur est incorrecte.

**Reproduction minimale :** clôture initiale 100; ordre de poids 0,50; ouverture suivante à 200 et clôture suivante à 200. L'achat s'est fait à 200 : le poids réel à cette clôture vaut toujours 0,50. La fonction le fait pourtant passer à environ 0,6667. Si la nouvelle cible vaut 0,65, l'écart réel vaut 15 points, mais aucun ordre n'est émis car l'écart calculé n'est que de 1,67 point. Le mouvement nocturne antérieur à l'achat explique entièrement cette erreur.

```python
dates = pd.bdate_range("2020-01-02", periods=6)
close = pd.Series([100, 200, 200, 200, 200, 200], index=dates, dtype=float)
target = pd.Series([0.50, 0.65, 0.65, 0.65, 0.65, 0.65], index=dates)
orders = price_lab._with_band(target, band=0.10, close=close)
# orders.iloc[1] est NaN, malgré 0.65 - 0.50 = 0.15 de distance réelle.
```

Le panel synthétique a ici des ouvertures égales aux clôtures indiquées; `lab.backtest` confirme le poids réellement acheté de 0,50. Sur TSLA, en simulant depuis le début du panel pour éviter une remise à zéro au 01/01/2018, puis en ne comptant que 2018-2024, le candidat envoie 160 ordres. La comparaison avec ses positions réellement détenues, valorisées de l'ouverture à la clôture du jour, trouve **11 jours où la bande réelle impose un ordre qui manque et 8 ordres émis à l'intérieur de la bande réelle**. Le plus grand écart sans ordre atteint 10,3558 points. Ce diagnostic porte sur les positions de la politique actuelle; il ne chiffre pas le résultat d'une politique corrigée dont les décisions suivantes seraient différentes.

**Correction à faire avant gel :** estimer les quantités et le cash à partir des ordres effectivement exécutés aux ouvertures déjà connues, puis les valoriser à la clôture de décision. Cela reste causal : à la clôture de t, l'ouverture de t est connue et l'ordre décidé en t ne sera exécuté qu'en t+1. Ne pas appliquer à une position nouvellement achetée un rendement commençant avant son achat. Si l'estimateur entre clôtures est volontairement conservé, il faut le déclarer comme un portefeuille fictif servant de signal, et retirer l'affirmation « vraie bande autour du poids détenu ». Recalculer le développement et les empreintes après le choix.

### R2. Les références des essais sociaux à 10 pb sont reconstruites à 5 pb

**Localisation :** `reports/run_family_correction.py:23` à `reports/run_family_correction.py:42`.

`base_returns` reçoit uniquement le nom de référence, met son résultat en cache sous ce nom et appelle `backtest` au coût par défaut. `load_family` ne lit pas `cost_bps` dans les paramètres du journal. Les 15 variantes à 10 pb de Codex sont donc comparées à TSLA à 5 pb, tandis que leur journal initial utilisait correctement TSLA à 10 pb. Les 199 essais prix, tous à 5 pb dans le journal, ne rencontrent pas cette erreur.

**Chiffrage :** la référence TSLA vaut 203 541,50 USD à 5 pb et 203 337,91 USD à 10 pb. Pour `news_finbert_exit_5__10bps__zero`, la référence du nouveau correcteur diffère de la bonne référence sur les deux journées d'entrée et de liquidation, avec un écart quotidien maximal de 0,0005144231. L'excès annuel de log-rendement y vaut 0,05894932 avec la mauvaise référence, au lieu de 0,05909261 avec la bonne. L'écart est faible mais réel. La famille complète utilisée pour les p publiées doit respecter chaque comparaison.

**Correction proposée :** lire les paramètres de chaque ligne du journal et construire les références avec le même coût, en mettant le cache sous `(nom_reference, cost_bps)`. Recalculer ensuite les 244 comparaisons et mettre à jour les preuves de développement. Le contrôle de trésorerie BIL conserve TSLA comme référence à son coût propre; on n'ajoute pas artificiellement BIL au buy and hold entièrement investi.

Le champ d'affichage `focus` à la ligne 81 contient en outre `codex:news_finbert_exit_5`, alors que le nom réel comprend `__5bps__zero`. Cette ligne d'affichage renvoie donc une valeur manquante. Le bon essai est présent dans le CSV, avec p d'excès 0,99325 et p d'alpha 0,90850 dans la famille calculée actuellement. Ce défaut de libellé ne signifie pas que l'essai a été omis de la famille.

### R3. L'alpha constant positif est classé comme non significatif

**Localisation :** `src/lab.py:278` à `src/lab.py:285`.

Quand l'écart-type des intercepts rééchantillonnés est inférieur ou égal à `1e-12`, la nouvelle fonction laisse la statistique observée et tous les tirages nuls à zéro, quel que soit le signe de l'alpha. Elle donne alors p = 1 même pour un alpha strictement positif sans incertitude.

**Reproduction, données synthétiques uniquement :**

```python
rng = np.random.default_rng(1)
b = pd.Series(rng.normal(0.001, 0.02, 300))
s = 0.5 * b + 0.001
lab.compare(s, b, n_boot=199)["alpha_p_one_sided"]  # 0.0
lab.romano_wolf_alpha(s.to_frame("s"), b.to_frame("s"), n_boot=199).iloc[0]  # 1.0
```

La régression retrouve exactement le même alpha et le même bêta dans chaque tirage. Il faut appliquer une convention de signe au cas dégénéré, comme celle déjà présente dans `romano_wolf` pour un excès constant : statistique positive infinie pour un alpha positif, négative infinie pour un alpha négatif, nulle si l'alpha est nul. Ce défaut est conservateur pour le cas positif; il **n'explique pas** le p = 0 du contrôle TSLA/BIL étudié ci-dessous.

### NaN, causalité et nouveaux départs glissants

Le nouveau contrôle de causalité distingue bien une ligne entièrement NaN, qui signifie aucun ordre, d'une ligne explicitement nulle, qui signifie vente de toutes les positions. Un exemple dont ces deux décisions diffèrent seulement entre panel complet et panel tronqué est refusé avec `Jours d'ordre différents`. Les colonnes sont ensuite réunies avant comparaison. Le correctif ne réintroduit donc pas l'ancien contournement consistant à cacher une décision dans une colonne ou à remplacer une liquidation par une absence d'ordre.

L'entrée au milieu d'un cycle reprend causalement le dernier ordre connu, puis paie son achat initial. Cela correspond à un **nouvel investissement**, pas à une tranche du portefeuille historique déjà dérivé : dans un exemple 50/50 dont A a doublé avant le nouveau départ, l'ancien portefeuille est à 2/3 et 1/3, tandis que le nouveau portefeuille entre à 1/2 et 1/2. Le comportement est maintenant annoncé et cohérent pour une règle mensuelle et sa référence. Pour la bande, en revanche, les poids du script glissant sont calculés une fois depuis 2016 : son estimateur de position continue de suivre cette histoire, alors que le moteur redémarre avec le dernier ordre. Une bande réellement liée au portefeuille financé doit aussi traiter explicitement cette remise à zéro pour les nouveaux départs.

**Borne terminale de `run_rolling_starts.py:35` :** le script conserve le panel complet jusqu'à 2024 et appelle `backtest(..., end=end)` sans le tronquer. Le moteur interprète `end` comme une dernière date de début de période; sa valorisation peut alors employer l'ouverture de la séance suivante, après la date de fin affichée. Il faut soit afficher cette date réelle de sortie, soit tronquer le panel à la fin nominale si une sortie au plus tard à cette borne est voulue. C'est un problème de définition et d'étiquetage de la fenêtre, pas une preuve de fuite dans les décisions.

Un exemple dont le prix reste à 100 jusqu'à `end`, puis double seulement à l'ouverture suivante, donne 20 000 USD avec le panel complet et 10 000 USD avec le panel tronqué à `end`. Dans les 13 fenêtres de développement d'un an et de pas six mois, la convention de sortie change le capital de TSLA sur 12 fenêtres, avec un écart absolu maximal de 3 319,15 USD. Les écarts maximaux sont 1 241,03 USD pour le ciblage de volatilité et 981,59 USD pour le momentum mégacapitalisations. La dernière fenêtre finit en 2024 et reste plafonnée par l'absence de prix 2025 : aucune donnée de validation n'a été utilisée pour ce constat. Les comparaisons entre stratégies partagent les mêmes bornes, mais leurs rendements de la dernière nuit diffèrent; cela ne dispense pas de déclarer précisément les dates.

### Le p d'alpha nul de moitié TSLA/BIL est bien d'origine mécanique

Annonce confirmée au sens économique : le résultat mesure essentiellement la rémunération des liquidités, pas une capacité à prévoir TSLA. L'alpha est ici celui d'une régression sur les rendements bruts de TSLA, avec liquidités implicitement à zéro dans la référence. Le contrôle, lui, reçoit BIL sur environ la moitié du capital.

Pour `control_half_tsla__5bps__BIL_proxy`, sur les seules observations de développement :

| Mesure | Valeur |
| --- | ---: |
| Bêta estimé | 0,499890 |
| Alpha annuel | +1,00852 % |
| Intervalle à 95 % de l'alpha | [+0,71629 %; +1,30335 %] |
| p brute de l'alpha | 0,0000 sur 4 000 tirages |
| p d'alpha de la famille publiée | 0,0000 |
| Moyenne annualisée de la moitié du rendement de BIL | +1,09593 % |
| Corrélation du résidu avec la moitié de BIL | 0,997081 |
| Écart-type quotidien du résidu | 0,00007420 |
| Écart-type quotidien du benchmark TSLA | 0,04208758 |

La différence entre le résidu et la moitié de BIL vaut environ -0,08741 % par an, liée notamment aux frais et au léger écart du bêta à 0,5. Sans rémunération BIL, le contrôle a un alpha de -0,09411 % par an. En retirant BIL des **deux** séries avant la régression, son alpha devient -0,09414 % par an et sa p unilatérale vaut 1. Le bruit résiduel est donc très faible comparé aux fluctuations de TSLA, mais il n'est pas nul; le cas dégénéré R3 n'est pas déclenché ici.

Le p empirique 0 signifie qu'aucun des 4 000 tirages n'a atteint la statistique observée sous le recentrage utilisé; cela ne signifie pas une probabilité mathématique exactement nulle. Il n'y a pas ici de défaut confirmé du bootstrap qui fabriquerait un rendement inexistant. C'est l'interprétation comme avantage informationnel ou talent de sélection qui serait incorrecte, parce que le facteur de rémunération du cash n'est pas retiré de la régression brute.

### Préinscriptions : cohérence confirmée et réserve de protocole

Les quatre hypothèses de `holm_family` sont strictement identiques, sans doublon, dans les deux fichiers : excès pour le momentum contre le panier, excès pour le filtre TSLA, différence de Sharpe pour le ciblage de volatilité, excès pour les news. Le seuil, les deux verdicts séparés, le coût statistique à 5 pb, les coûts économiques à 5 et 10 pb et le caractère descriptif des analyses secondaires concordent. L'ajout news annonce honnêtement qu'il ne passe pas le filtre strict de Codex et reste un choix exploratoire du coordinateur. Il ne faut donc pas le présenter comme une sélection validée par la règle initiale de Codex.

Les empreintes des trois modules concordent exactement dans les deux préinscriptions et avec les fichiers présents :

```text
src/lab.py        4812cb8907a90aa887152ee7d17caa80d959d5cc88e9a4c5790ce025bc4c02be
src/price_lab.py  468ada000e3df6d6ef3f616f63d2840c145c3d8aab87fbad491bed4b6e5a3acd
src/social_lab.py 03d84abd159d43fab6d478d3717c5fdf57255b94e028a595c4fdb12867a6c2e3
```

La limite initiale du protocole est toutefois « chaque binôme déclare au plus 3 stratégies ». Le coordinateur en déclare trois dans le fichier prix et une quatrième dans l'addendum. La famille de Holm couvre bien les quatre, mais cela ne modifie pas à lui seul la limite textuelle. Avant ouverture, préciser explicitement la dérogation au protocole ou l'attribution des déclarations; conserver la préinscription vide de Codex comme trace de sa décision initiale. De même, remplacer « choisies avant 2025 » par « choisies uniquement sur les données arrêtées à 2024 » évite de confondre la date des données avec la date réelle du gel, en novembre 2026.

### Preuve de tests et conclusion de la contre-vérification

Commande exécutée sans changement des fichiers de tests :

```text
venv/bin/python -m unittest tests.test_lab tests.test_social_lab tests.test_price_audit
...................................
----------------------------------------------------------------------
Ran 35 tests in 2.452s

OK
Code de sortie : 0
```

Les reproductions supplémentaires ont été exécutées en mémoire avec des données synthétiques ou le panel plafonné à 2024; elles n'ont pas été ajoutées aux fichiers de tests, interdits de modification dans cette mission. Les 35 réussites confirment les régressions couvertes, sans couvrir les nouveaux cas R1 à R3.

**Gel non validé en l'état.** Corriger ou redéfinir explicitement la bande, respecter les coûts de chaque référence dans la famille, traiter l'alpha dégénéré, préciser les bornes et la remise à zéro des fenêtres et formaliser l'ajout de la quatrième stratégie. Les changements de code exigent de nouvelles empreintes, le recalcul des preuves de développement concernées et une dernière vérification avant ouverture. Aucune simulation de validation, collecte ni lecture de rendements postérieurs au 31/12/2024 n'a été effectuée dans cette mission.

## Dernière vérification ciblée et verdict de gel

**Verdict : gel validé pour ouvrir la validation unique des quatre stratégies déclarées, avec les règles et les empreintes ci-dessous.** Les réserves bloquantes de la contre-vérification précédente sont levées pour cette nouvelle version. Ce verdict porte sur la cohérence technique et le protocole figé; il ne constitue pas une preuve de supériorité des stratégies. La validation n'a pas été lancée dans cette mission et aucune donnée postérieure au 31/12/2024 n'a été consultée.

### R1 : diagnostic TSLA revenu exactement à zéro

`_with_band` conserve maintenant des quantités d'actions et des liquidités. Un ordre décidé à la clôture de t n'est exécuté dans son portefeuille fictif qu'à l'ouverture de t+1, puis les positions sont valorisées à la clôture. Le mouvement entre la décision et cette ouverture n'est donc plus attribué à des actions non encore achetées. Le cas synthétique « décision à 100, achat à 200, nouvelle cible 0,65 » émet désormais correctement l'ordre 0,65 à la clôture suivante.

Le diagnostic indépendant reprend le panel depuis 2016, simule sans frais et ne compte que 2018-2024, afin d'écarter la différence de démarrage entre portefeuille fictif et nouvel investissement. Pour chaque clôture, le poids détenu est recalculé à partir du poids d'ouverture de `lab.backtest` et du rapport clôture/ouverture. Il est ensuite comparé à la cible de volatilité avec la même bande de 10 points.

| Mesure, 2018-2024 | Résultat |
| --- | ---: |
| Clôtures contrôlées | 1 760 |
| Ordres émis | 154 |
| Ordres manquants par rapport aux positions détenues | **0** |
| Ordres injustifiés à l'intérieur de la bande | **0** |
| Plus grand écart sans ordre | 9,98769 points, inférieur à 10 |

Les fonctions `vol_target_30` et `trend_vol_target_30` passent aussi `lab.check_no_lookahead`. Le capital de développement du candidat TSLA, réexécuté à 5 pb, vaut 81 105,46 USD, conformément aux résultats recalculés. Ses rendements stockés sont identiques aux rendements recalculés jour par jour, avec un écart maximal nul.

Le portefeuille fictif sans frais servant de signal, lancé au début de l'historique, et la reprise du dernier ordre lors d'un nouveau départ sont maintenant explicitement annoncés dans le code, le protocole et la préinscription. Une différence éventuelle avec les poids d'un portefeuille nouvellement financé n'est donc plus présentée comme une « vraie bande » sur ce dernier : la règle figée utilise bien le signal du portefeuille fictif. Cette politique est causale et reproductible.

### R2 : coûts des références et résultats enregistrés cohérents

Le correcteur familial lit maintenant le coût dans les paramètres du journal et met les références en cache sous `(nom, coût)`. Les seules définitions de fonctions ont été extraites pour le vérifier, sans exécuter le script et ses écritures. **Les 45 références sociales ont été comparées à des backtests indépendants au coût propre de chaque essai : écart maximal nul**, y compris les 15 variantes à 10 pb.

Les p d'excès ont ensuite été recalculées indépendamment sur les **244 essais** des deux journaux : mêmes noms, mêmes blocs moyens de 21 jours, 4 000 tirages, graine 0. L'écart maximal avec `family_pvalues.csv` est exactement nul. Les valeurs utiles au gel sont :

| Essai | p d'excès, famille complète | p d'alpha, famille complète publiée |
| --- | ---: | ---: |
| Momentum contre le panier, `robust_mega_top3_lb126` | 0,85800 | 0,78475 |
| Filtre TSLA/QQQ 200 jours | 0,99825 | 0,96650 |
| TSLA ciblage de volatilité | 1,00000 | 1,00000 |
| News FinBERT, 5 pb et liquidités nulles | 0,99050 | 0,90800 |

Le libellé news du tableau d'affichage a également été corrigé. Les rendements enregistrés des quatre candidats, recalculés avec les fonctions actuelles et les seuls prix de développement, concordent jour par jour avec un écart maximal nul. Les chiffres de développement ne franchissent toujours pas les critères statistiques de preuve; l'ouverture prévue sert précisément à tester les hypothèses figées sur la période jusque-là verrouillée.

### R3, bornes et dérogation corrigés

Le cas d'alpha dégénéré applique désormais la convention de signe. Dans une vérification conjointe avec bêta 0,5 et intercept constant, les p ajustées sont **0 pour l'alpha positif, 1 pour l'alpha nul et 1 pour l'alpha négatif**. Le scénario qui donnait auparavant p = 1 à un avantage certain est corrigé.

`window_final_capital` tronque le panel à la borne terminale avant d'appeler le moteur. Le script glissant utilise cette fonction. Dans le scénario synthétique du doublement après la fin, le capital reste à 10 000 USD; remplacer tous les prix postérieurs par un million laisse ce capital exactement inchangé. La vente se fait au plus tard à la dernière ouverture disponible dans la fenêtre, conformément au protocole. Les fenêtres ne sont plus étiquetées comme terminées avant l'ouverture réellement utilisée pour leur valorisation.

La dérogation aux trois stratégies est maintenant écrite dans le protocole et référencée dans les deux préinscriptions. Elle annonce les trois candidats prix et le quatrième candidat news choisi à titre exploratoire par le coordinateur, sans attribuer ce choix à la sélection stricte de Codex. Les quatre hypothèses de Holm sont identiques et sans doublon dans les deux fichiers; le seuil de 0,05, les tests statistiques à 5 pb et les conditions économiques aux deux coûts concordent. Les résultats secondaires restent descriptifs.

### Versions contrôlées et preuve de tests

Les nouvelles empreintes des deux préinscriptions concordent avec les modules présents :

```text
src/lab.py        542f24f8a527fd1395082f1ce79172b1bd9662fcc24e6fb521edf7aa754e860d
src/price_lab.py  011eddd9cc3ab872c63e0030fd58b9ac0114f12d2bb73e131fd8150dc00f4b00
src/social_lab.py 03d84abd159d43fab6d478d3717c5fdf57255b94e028a595c4fdb12867a6c2e3
```

Les tests de `SecondAuditRegressions` couvrent désormais le saut antérieur à l'achat, les positions du moteur, l'alpha positif constant, la borne finale et le coût des références. Les vérifications numériques indépendantes ci-dessus complètent notamment le test de coût qui inspecte le texte du script.

```text
venv/bin/python -m unittest tests.test_lab tests.test_social_lab tests.test_price_audit
........................................
----------------------------------------------------------------------
Ran 40 tests in 2.432s

OK
Code de sortie : 0
```

Aucun des fichiers audités n'a été modifié par cette vérification; seule cette conclusion a été ajoutée. **Aucun point bloquant susceptible de modifier un résultat ou une décision de validation n'est confirmé dans le périmètre ciblé. Le gel est validé pour ces versions et ces règles de décision.** Les limites déjà annoncées, dont la faible puissance d'environ 22 mois, le choix de l'univers et l'alpha mécanique lié à BIL, restent des limites d'interprétation à publier avec les résultats futurs, sans constituer de nouveaux motifs pour ajuster les règles après ouverture.
