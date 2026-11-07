# Seconde relecture du code EPS et P/E

08/11/2026, branche `etude-news`, commit `9137bf5e474ed43cbfd1c90cc11daba62f568c4a`, diff depuis `173c6e9`. Section des corrections du protocole et trois fichiers demandés relus.

**Verdict : à corriger d'abord.** D1 est réparé, mais D3 reste grave : un dividende exceptionnel devient un faux fractionnement et change réellement les deux sélections. Aucun rendement, capital ni backtest, même synthétique, n'a été calculé pendant cette relecture.

## Réponses et preuves

**1. D1 : causalité réparée vis-à-vis des dépôts futurs.** `src/pe_eps_study.py:64-90` travaille par préfixes de dépôts, puis écrit seulement les séances strictement postérieures. L'EPS de `t - 252` reste celui construit à cette ancienne date. Avec les vrais facteurs, WAT, COHU, ATRO et PATK donnent des préfixes identiques après retrait des dépôts et séances futurs aux quatre coupures 01/03/2018, 02/12/2019, 01/09/2021 et 02/12/2024. Au 02/12/2019, contrôle supplémentaire sur les **6 718 titres** : tous les EPS historiques, dont ceux à 252 séances, et les quatre vecteurs de poids sont identiques avec et sans futur. E1 et E2 comptent 100 titres, chaque témoin 644. EPS retrouvés : COHU au 01/03/2018 = 0,98 ; WAT, ATRO et PATK au 02/12/2019 = 8,12, 2,96 et 4,15. Les cas initiaux sont réglés. Réserve distincte sur le choix des versions ci-dessous.

**2. D2 : sens et formule corrects, sous réserve d'un multiplicateur correct.** Un fractionnement en deux multiplie `M` par deux ; l'EPS est divisé par deux. `growth`, lignes 121-125, convertit correctement le passé par `M(t - 252) / M(t)`. Le cumul des seuls rapports passés est causal sur les facteurs fournis ; une renormalisation uniforme future s'élimine. Contrôle numérique de cette invariance réussi. Cela ne résout pas les erreurs de classification de D3.

**D3 : correction insuffisante, grave.** Le seuil des lignes 38-52 ne distingue pas la nature des opérations.

| Cas réel | Rapport du facteur ajusté/brut | Résultat |
|---|---:|---|
| HEI, 18/01/2018 et 28/06/2018, fractionnements 5 pour 4 | 1,249872 et 1,250056 | Correctement détectés |
| BF.B, 01/03/2018 ; CENTA, 09/02/2024, 5 pour 4 | 1,249933 ; 1,249928 | Correctement détectés |
| NTRB, 12/08/2022, fractionnement 7 pour 6 | 1,166667 | Faux négatif, `M` reste à 1 |
| TR, 05/03/2024, dividende en actions de 3 % | 1,034611 | Changement du nombre d'actions ignoré |
| KDP, dividende exceptionnel de juillet 2018 | 6,212189 au 11/07 | Faux positif, faux multiplicateur de fractionnement |

Opérations vérifiées dans `data/universe/corporate_actions_dev.parquet`, cours dans `prices_dev.parquet`, exclusivement avant 2025. Pour KDP, la séance du 10/07 est marquée suspecte : le report du facteur décale le saut au 11/07. Le [document SEC de 2018](https://www.sec.gov/Archives/edgar/data/1418135/000141813518000025/dps-10qx063018.htm) confirme le dividende exceptionnel de **103,75 dollars par action**, associé à la fusion. Ce n'est pas un fractionnement en 6,21.

Preuve d'incidence, en neutralisant uniquement ce faux multiplicateur KDP, sans changer ses faits EPS : au **01/03/2019**, EPS 1,741657 au lieu de 2,48 ; croissance **+171,17 % au lieu de -37,84 %**. Le code actuel sélectionne KDP dans E1 et E2 ; sans ce faux fractionnement, **CHE remplace KDP dans E1 et ETFC dans E2**. Les témoins restent identiques. Il ne s'agit donc pas seulement d'une limite théorique ou d'un écart de 0,01 %. Les petits dividendes en espèces sont bien écartés, mais l'affirmation « fractionnements seuls » est fausse.

**3. D4 à D8 : corrections conformes.** Départ sans cible avant mars 2018 ; descriptifs limités aux 28 décisions ; couples à poids positif seulement ; alpha, bêta, secteurs et disparitions pour les quatre portefeuilles ; S3 explicitement limité au témoin E1 ; proxy P/E et véritables identités du test B distingués ; conventions de liquidité et départages documentés. Branche financière inspectée sans exécution. Les tests explicites d'ex aequo aux frontières proposés dans D8 restent absents.

**4. Nouveau défaut : version la plus récente pas toujours retenue.** Lignes 70-74, le tri privilégie `period_end`, puis conserve la dernière ligne du groupe : il retient la fin de période maximale, même si son dépôt est plus ancien. Contre-exemple : quatre EPS de 1, puis révision du premier de 1 à 2, déposée le 01/03/2020 avec une fin ramenée du 31/03/2019 au 30/03/2019 ; le 02/03/2020, le code retourne **4 au lieu de 5**. Cela ne recrée pas une anticipation ; incidence matérielle sur les vraies sélections non établie. Choisir le dernier `filed` dans chaque groupe et tester les décalages dans les deux sens. Aucun nouveau défaut bloquant démontré ; D3 demeure grave et suffit à empêcher le lancement.

## Vérification et suite

**20 tests sans branche financière réussis**, dont l'essai à blanc avec appels financiers interdits : cinq empreintes conformes, 28 décisions, éligibles 520 à 686, médiane 645, 100 titres pour E1/E2. Les deux tests calculant des portefeuilles synthétiques ont volontairement été exclus.

Commandes : `PYTHONDONTWRITEBYTECODE=1 venv/bin/python tests/test_pe_eps_study.py Rules CausalEps LauncherRules.test_no_order_before_2018 LauncherRules.test_holdings_drop_empty_and_zero_weights DryRun`, puis même commande avec `Days`. Contrôles complémentaires dans `/tmp/audit_pe_eps_2_{scan,actions,dividends,real,versions}.py` ; le script `real` interdit par assertions le backtest, les comparaisons financières, résumés et écritures au journal.

Avant lancement : remplacer le seuil seul par un suivi validé des opérations sur les actions, incluant petites distributions en actions et excluant dividendes en espèces et autres ajustements ; figer les sources supplémentaires et dater la correction. Ajouter les régressions KDP/NTRB/TR et corriger le choix des versions. Ne pas relancer le test B. Seul ce rapport est ajouté ; fichiers existants et changements préexistants laissés intacts, aucun commit, aucun accès à `.env` ni aux données de validation après 2024.
