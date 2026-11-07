# Troisième relecture ciblée EPS et P/E

08/11/2026, branche `etude-news`, commit `05c20293e4354412d31c82da320b8bed044bf7a5`. Périmètre : les deux points restants de la seconde relecture et leur correction documentée.

**Verdict : à corriger d'abord.** Le choix de version est réparé, mais D3 reste grave : une scission devient encore un faux fractionnement et change réellement E2. Aucun rendement, capital ni backtest, même synthétique, n'a été calculé.

**1. Opérations : les quatre cas demandés sont corrigés, la classification générale ne l'est pas.** `pe.action_ratios`, lignes 51-70, utilise le symbole et les dates de cotation ; aucune ligne source rattachée à plusieurs titres dans le contrôle des actions ordinaires retenues. Ratios constatés du multiplicateur : KDP en juillet 2018 = **1** ; NTRB en août 2022 = **7/6** ; TR en mars 2024 = **1,03** ; HEI aux 18/01 et 28/06/2018 = **1,25** exactement, sans double comptage des facteurs.

Le repli des lignes 89-94 conserve pourtant des opérations étrangères au nombre d'actions, dès que leur facteur ressemble à un ratio simple :

| Opération réelle | Saut retenu à tort | Incidence en neutralisant uniquement ce repli, sur les 28 décisions |
|---|---:|---|
| EHC, scission d'Enhabit, 01/07/2022 | 1,256043, proche de 5/4 | **Au 01/03/2024, E2 perd EHC et gagne LBRT** ; E1 et les deux témoins restent identiques |
| ACI, dividende exceptionnel, 21/10/2022 | 1,331837, proche de 4/3 | Aucun poids changé |
| MMM, scission de Solventum, 01/04/2024 | 1,246838, proche de 5/4 | Aucun poids changé |
| GE, scission de Vernova, 02/04/2024 | 1,253867, proche de 5/4 | Aucun poids changé |

Nature des opérations confirmée par les communications historiques des émetteurs : [EHC, juillet 2022](https://healthsouth.mediaroom.com/2022-07-01-Encompass-Health-Corporation-Completes-Spin-Off-of-Enhabit-Home-Health-Hospice), [ACI, octobre 2022](https://albertsons2021rd.q4web.com/newsroom/press-releases/news-details/2022/Albertsons-Companies-Announces-Special-Dividend-in-Connection-with-Signing-of-Merger-Agreement/default.aspx), [MMM, avril 2024](https://news.3m.com/2024-04-01-3M-Completes-Spin-off-of-Solventum), [GE, avril 2024](https://www.gevernova.com/news/articles/ge-vernova-completes-spin).

Preuve numérique EHC au 01/03/2024 : EPS courant **3,46** dans les deux constructions ; EPS à 252 séances **2,522651 au lieu de 2,70** ; croissance **37,16 % au lieu de 28,15 %**. Seul le multiplicateur change, aucun fait EPS. L'affirmation du protocole selon laquelle les scissions et dividendes exceptionnels ne changent plus l'EPS reste donc fausse.

Autres réserves mesurées : TR manque encore sa distribution de 3 % de mars 2020, absente du fichier et sous le seuil du repli ([dépôt SEC de 2020](https://www.sec.gov/Archives/edgar/data/98677/000155837020005994/R4.htm)) ; son ajout ne change aucun des quatre vecteurs de poids aux 28 décisions. Deux doublons d'événements sont multipliés ligne 70 : SNEX au 27/11/2023 donne **2,25 au lieu de 1,5**, FBYD au 10/12/2024 **1,44 au lieu de 1,2** ; leur dédoublement ne change aucun poids aux 28 décisions. Le [communiqué StoneX de novembre 2023](https://ir.stonex.com/news-releases/news-release-details/stonex-announces-three-two-stock-split) confirme un seul fractionnement 3 pour 2. Aucun faux négatif changeant réellement ces sélections n'est démontré ici.

**Causalité : réserve structurelle, sans incidence constatée sur ce gel.** La fenêtre `center=True`, ligne 89, consulte cinq séances futures. Contre-exemple sans rendement : facteur passant de 0,5 à 1 à la séance 10, opération de ratio 2 à la séance 12 ; multiplicateur en séance 10 = **1** avec la série complète, **2** avec le préfixe arrêté en séance 10. Sur les vrais facteurs et opérations des 6 718 titres, aucun saut admissible au repli n'est supprimé par une opération uniquement future dans cette fenêtre : ce mécanisme ne change donc pas les poids aux 28 décisions du gel. Il ne constitue pas une garantie générale de causalité.

**2. Version la plus récente : correction correcte.** Lignes 106-117 : préfixe des dépôts connus, groupes de fins de période, puis tri par `filed` à l'intérieur de chaque groupe. La dernière ligne garde bien le dépôt le plus récent, même avec une fin ramenée d'un jour. Régressions dans les deux sens réussies ; le contre-exemple de la seconde relecture donne désormais **5**, puis **7** après une seconde révision d'un autre trimestre. Pas de nouvelle anticipation des dépôts constatée.

**3. KDP : limite acceptable sans nouvelle règle.** EPS au 01/03/2019 = **2,48**, sans sélection dans E1/E2, présent dans leurs témoins. Le mélange de périmètres comptables de la fusion inversée est explicitement annoncé avant tout rendement. Le conserver comme limite générale, sans exclusion opportuniste ni règle supplémentaire, est acceptable ; cela ne justifie pas les faux fractionnements d'autres opérations.

**4 et 5. Gravité et lancement.** Aucun nouveau défaut bloquant distinct établi ; **D3 demeure grave et suffit à empêcher le lancement**. Avant calcul, valider la nature des replis susceptibles d'affecter les signaux, exclure notamment le faux fractionnement EHC et ajouter sa régression de sélection ; traiter aussi les doublons et expliciter la réserve de causalité. Une simple proximité numérique ne valide pas une opération sur actions.

**Vérification.** Six empreintes conformes ; 25 tests sans branche financière réussis, dont l'essai à blanc protégé : 28 décisions, 520 à 685 éligibles, médiane 645, 100 titres pour E1/E2. Commande : `PYTHONDONTWRITEBYTECODE=1 venv/bin/python tests/test_pe_eps_study.py Days Rules CausalEps ShareActions LauncherRules.test_no_order_before_2018 LauncherRules.test_holdings_drop_empty_and_zero_weights DryRun`. Contrôles dans `/tmp/audit_pe_eps_3.py` et `/tmp/audit_pe_eps_3b.py` : 320 replis repérés ; calcul indépendant des seuls poids validé contre les quatre fonctions de production, puis comparaisons aux 28 décisions avec appels financiers interdits. Aucun lancement sans `--dry-run`, aucun accès à `.env` ni aux fichiers de validation après 2024 ; seul ce nouveau rapport est ajouté, changements préexistants laissés intacts, aucun commit.
