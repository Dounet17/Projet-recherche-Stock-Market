# Seconde relecture du code des notes d'analystes

07/11/2026, branche `etude-news`, commit `4858b19d44063f3b0d9a245b03bd6c3e6a43cd1d`. Section finale du protocole et diff `46c0aad..4858b19` relus, avec vérification des fonctions sources appelées.

**Verdict : à corriger d'abord.** Les réparations locales sont largement effectives, mais deux problèmes de disponibilité historique empêchent encore de présenter A3 comme achetable.

## Vérifications

Avec `PYTHONDONTWRITEBYTECODE=1`, les **27 tests passent** et `venv/bin/python reports/run_analyst_study.py --dry-run` réussit : sept empreintes conformes, arrêt avant les rendements. Effectifs reproduits : principal **18 413 relèvements / 19 163 abaissements**, **5 620** calendriers non couverts ; A3 **22 052** relèvements regroupés, **20 652** achetables, **2 599** exclusions et **18 053** signaux d'achat.

Aucun rendement, cours de sortie ou capital de ces événements calculé ou consulté ; aucun lancement réel, accès à `.env`, lecture de données après 2024 ou modification d'un fichier existant. Les tests de rendements autorisés portent sur des données inventées. Les contrôles supplémentaires sous `/tmp` ne manipulent que dates, identifiants, filtres et poids. Les changements préexistants de `.gitignore` et `reports/build_vault.py` sont laissés en place.

## D1 à D11

Les références `lanceur` désignent `reports/run_analyst_study.py` et `an` désigne `src/analyst_study.py`.

| Défaut | État et preuve |
|---|---|
| **D1** | **Corrigé.** `portfolio_table`, lanceur 105-108, repart des notes brutes et appelle `collapse(..., key="decision_idx")`, avant le filtre d'achat. Les contradictions concernent cette décision seulement. Les préfixes réels aux 31/12/2018, 01/10/2020, 30/06/2022 et 01/11/2024 conservent exactement les mêmes identifiants A3 après retrait des décisions futures. Le test AMAG couvre l'ancien contre-exemple. |
| **D2** | **Partiellement corrigé, encore bloquant.** `past_earnings`, an 86-99, ne regarde effectivement que `[d-2, d-1]` ; le lanceur ne réutilise plus `near_earnings` pour A3. Mais les dates fournies à cette fonction sont sélectionnées rétrospectivement avec des publications futures : preuve ci-dessous. |
| **D3** | **Corrigé.** `before_idx` cherche la dernière clôture au plus tard à la note, puis `before_row - 19` ouvre les vingt séances, lanceur 69-76 et 171-174. SPY utilise les mêmes bornes. Les bornes disponibles du principal précèdent toutes la note ; une séance antérieure absente du calendrier produit une mesure manquante, sans rabattement sur une clôture future. |
| **D4** | **Partiellement corrigé.** Le retrait et le rééquilibrage fonctionnent : aucune cible positive après la dernière observation valide pour un titre disparu. Pour les sept titres concernés, la première modification du plan est strictement après cette observation, jamais avant. Toutefois, le caractère définitif de cette observation vient du futur, sans date de radiation publique : réserve grave détaillée ci-dessous. |
| **D5** | **Corrigé.** `headline`, lanceur 177-195, associe t ordinaire, sa p et son IC ; Newey-West est séparé. A1/A2 exigent 28 trimestres et Holm reçoit leurs p principales, 244-249. Test indépendant de Student à 27 degrés de liberté et test d'arrêt si trimestre absent. |
| **D6** | **Ajout effectif, portée élargie déclarée.** Lanceur 198-202 et 225 : référence figée, frais et trois sorties hérités de `reference.buy_hold_table`. Contrôle des seules dates/identités : cohorte du 02/01/2018, horizon final, **3 030 titres distincts**. Ce marché élargi n'est pas exactement l'univers des titres suivis dans A3. |
| **D7** | **Corrigé.** Mesures A2 nettes dans chaque scénario, lanceur 165-169 ; publication des trois statistiques avec effectifs et IC, 273-274. Scénario principal inchangé et coûts doublés séparés. |
| **D8** | **Corrigé selon la nouvelle règle explicite.** Préfixe d'agence exclu avant classement, an 19-32 ; tests crédit et recommandations sur Moody's, S&P Global et Abercrombie & Fitch. Les 87 titres refusés sont reproduits. |
| **D9** | **Corrigé quant à la transparence.** Drapeau distinct `calendar_covered`, maintien explicite des cas non couverts et publication par sens/année, lanceur 90 et 276. La présence d'une date ne prouve toujours pas l'exhaustivité du calendrier. |
| **D10** | **Corrigé.** `searchsorted(closes, available + LATENCY, side="left")`, an 56-59, assertion dans le lanceur et test à cinq minutes pile puis une nanoseconde après. Les 22 052 décisions A3 satisfont le délai ; les clôtures effectives du calendrier sont utilisées. |
| **D11** | **Essentiel corrigé.** A2 par liquidité, placebo de signe explicitement A1 seulement et coefficient regroupé identifié comme moyenne par événement, lanceur 264-286. Le regroupement ne se présente plus comme le même estimateur trimestriel. |

## Disponibilité historique encore insuffisante

**D2, bloquant : le calendrier sélectionne les publications à l'aide du futur.** `reports/build_earnings_events.py:77` appelle `events.match_announcements` ; `src/events.py:25-42` retient le **dernier 8-K avant le dépôt trimestriel**, lequel peut être futur à la décision. Ajouter un 8-K futur remplace donc une date déjà passée et peut supprimer une exclusion antérieure, même si `past_earnings` refuse toute date future.

Deux cas réels, vérifiés uniquement sur dates et filtres :

| Signal A3 achetable et actuellement non exclu | 8-K déjà publié | 8-K finalement retenu | Dépôt trimestriel |
|---|---|---|---|
| AMD `11115880`, décision 01/02/2018 | 30/01/2018 | 27/02/2018 | 27/02/2018 |
| DIOD `11156807`, décision 08/02/2018 | 07/02/2018 | 12/02/2018 | 20/02/2018 |

En conservant le même trimestre et le même dépôt, mais en retirant uniquement les 8-K postérieurs à la décision, `match_announcements` retient respectivement le 30/01 et le 07/02 : les deux exclusions passent de **faux à vrai**. Ce n'est pas simplement un dépôt futur documentant une annonce passée : une information future change le choix du filtre passé. Il faut une liste de publications connue à chaque décision, indépendante du rattachement trimestriel ultérieur, puis un test de préfixe sur sa construction. Ce défaut de source est hérité ; la nouvelle fonction ne l'élimine pas.

**D4, grave : dernière observation et radiation publique restent confondues.** Lanceur 208-212, `last` vient de tout le panel et `gone` du statut final ; an 148-151 programme le retrait en `last + 1`. Le délai est bien postérieur à `last`, mais aucune donnée ne date la connaissance de la radiation. Une suspension temporaire et une disparition définitive peuvent présenter exactement le même historique jusque-là. Sur des poids inventés, une dernière observation à la ligne 7 déclenche un ordre à 8 ; une reprise seulement à 12 supprime cet ordre à 8, sans changer le préfixe des cotations jusqu'à 8. Il faut une radiation historiquement datée, ou une règle observable d'absence de cotation appliquée uniformément, et tester l'invariance aux reprises futures. Le test actuel fournit directement `last_rows` comme une vérité déjà connue et ne prouve pas cette disponibilité. L'affirmation « une radiation est publique quand elle a lieu » ne fournit pas la donnée manquante.

## Qualification et décision

Les étiquettes correction pour D1/D3/D5/D7 et changement pour D2/D4/D8/D10 sont honnêtes sur l'intention. La requalification des anciens choix 4 et 8 est correcte. D9 est bien une précision de couverture, avec maintien de l'échantillon.

Deux réserves de rédaction, mineures : D6 devrait nommer un **changement de portée de la référence**, puisque le gel demandait le même univers ; D11 mélange corrections de livrables, précision d'estimateur et restriction du placebo de signe à A1. Ces écarts sont désormais visibles, mais « précision » et « correction » seuls sont trop généreux. La validité achetable d'A3 reste à établir indépendamment de ces étiquettes.

**À corriger d'abord : rendre causales les dates de publications et la connaissance des disparitions avant l'unique lancement.** Aucun effet sur les rendements n'a été mesuré.
