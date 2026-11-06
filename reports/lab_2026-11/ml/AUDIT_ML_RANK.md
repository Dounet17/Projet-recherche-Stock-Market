# Audit critique du classement mensuel, lecture seule

Branche `framework-backtest`, dossier `/home/tomda/Documents/Projet-recherche-Stock-Market`, audit du 06/11/2026. Rapport et scripts dans `/tmp/ml-rank-audit-Z55nMp/` uniquement. Aucun appel à `run_experiment`, `record_trial` ou au lanceur de l'étape 5. Aucun fichier du dépôt modifié, aucun commit, aucune ouverture de `.env`, d'un chemin `*holdout_*` ou de prix après le 31/12/2024. Le statut Git présent au démarrage comprenait déjà le journal modifié et les fichiers de l'étape 5 non suivis.

**Verdict : capital et entraînement reproductibles, pas de fuite temporelle propre au modèle trouvée, mais la corrélation brute ne démontre pas un apport au-delà de facteurs simples. Un défaut concret du diagnostic remplace rétrospectivement un titre impossible à acheter. Les 83 mois de diagnostic excluent le dernier mois négatif qui fait passer le capital net sous 10 000 USD.**

## Défauts et réserves classés par gravité

| Gravité | Fichier et ligne | Constat et taille mesurée |
|---|---|---|
| Élevée, réserve existante en amont, effet sur la performance non quantifié | `src/universe_clean.py:196`, consommation dans `src/universe_data.py:182` et `:200` | `suspect_print` utilise le rendement suivant : 75 observations de l'univers courant sont masquées exclusivement à cause du lendemain, dont 70 en 2018-2024. Quatre sont des jours de décision mensuelle, toutes déjà hors des critères de prix/liquidité (DMK 2023-08-01, GBR 2018-07-02, GMBLZ 2022-12-01, NOGN 2023-04-03). Aucun achat directement écarté parmi ces quatre, mais leur effet sur les historiques, les rangs et l'apprentissage n'est pas estimé. Il faut donc conserver cette réserve connue du cadre, sans affirmer que les données nettoyées sont entièrement connues en temps réel. |
| Moyenne, défaut de calcul du diagnostic | `src/ml_rank.py:151` puis `:158` | La disponibilité future de la cible est filtrée **avant** la sélection des 50. Le 01/04/2024, DSKE est visé à 2 %, mais n'a plus d'ouverture le 02/04 ; le moteur garde ces 2 % en cash. Le diagnostic remplace DSKE par STT, dont le mois vaut −4,81066 %. Rendement diagnostic −2,992356 %, moteur brut −2,896143 % : écart de **9,6213 pb** sur ce mois, soit 0,1159 pb sur la moyenne de 83 mois. Les 82 autres mois correspondent à 1e−12 près. |
| Moyenne, limite de présentation/comparabilité | `src/ml_rank.py:78`, `:147`, `reports/run_step5_ml_rank.py:43` | La corrélation et les déciles couvrent janvier 2018 à novembre 2024, soit 83 mois complets ; le portefeuille fait aussi décembre 2024, vendu le 31/12. Ce dernier intervalle fait **−5,06722 % brut / −5,30688 % net** : capital net avant ce mois 10 212,34 USD, après 9 670,39 USD. Exclure cette cible incomplète est correct sans prix de 2025, mais comparer directement ces diagnostics au capital sur 84 décisions nécessite de l'expliciter. |
| Moyenne, limite de preuve statistique, pas erreur arithmétique | `reports/run_step5_ml_rank.py:43`, `src/ml_rank.py:43`, `:38`, `:114` | IC modèle 0,03413, IC liquidité seule 0,03308, IC volatilité inversée 0,05931. Après résidualisation linéaire des rangs sur liquidité et volatilité, IC 0,00597 et t 0,86. Le t brut ne démontre donc pas un apport propre du ML. Ce résultat est descriptif, pas une démonstration causale exhaustive. |
| Faible, différence d'éligibilité à déclarer | `src/ml_rank.py:123` et `:128`, `reports/run_test_a_momentum.py:20` | Univers et coûts du test A sont bien identiques, mais le ML prédit aussi avec un historique incomplet : 258 434 titres-mois scorés contre 244 029 titres-mois avec momentum 252 séances connu ; **452 des 4 200 sélections** du ML ont ce momentum manquant (10,76 %). Ce choix est permis par le modèle, mais les ensembles effectivement classés ne sont pas identiques. |
| Faible, convention de mesure à préciser | `src/lab.py:196`, `:264` | 20,8899/an compte achats **plus** ventes. L'équivalent divisé par deux vaut 10,4450/an. Rien d'impossible pour un portefeuille mensuel : 43,18 nouveaux titres sur 50 en moyenne. |

Aucune anomalie de reproduction, du filtre du 1er janvier, du décalage à l'ouverture suivante ou des rangs percentiles n'a été trouvée dans les vérifications ci-dessous. Aucun correctif ni réglage n'a été fait.

## 1. Cibles et reconstruction indépendante

`base.py` reconstruit les 13 indicateurs, les rangs via `scipy.stats.rankdata(method="average")`, le calendrier mensuel, les rendements d'ouverture à ouverture et les sorties. `models.py` entraîne directement `HistGradientBoostingRegressor` avec les paramètres figés. Aucun de ces chemins n'utilise `make_strategy`. Les fonctions publiques d'indicateurs/cibles sont ensuite utilisées comme comparateurs, pas comme source de la reconstruction.

- Les 13 indicateurs et leurs rangs correspondent exactement : écart maximal 0 et mêmes NaN.
- Toutes les cibles reconstruites correspondent : mêmes dates de décision et de fin, écart maximal 0, mêmes NaN.
- Pour **2021** : 59 dates d'entraînement, **169 904 échantillons**, dernière décision d'entraînement 02/11/2020, dernière fin de cible **02/12/2020**. La décision du 01/12/2020 a pour fin le 05/01/2021 et est exclue.
- Les 42 848 scores de 2021 sont égaux aux scores sauvegardés, écart maximal 0. La décision du 04/01/2021 est exécutée à l'ouverture du **05/01/2021** ; sa propre cible se finit le 02/02/2021 et ne peut entrer dans l'entraînement annuel 2021.
- Vérification supplémentaire sur un historique arrêté au **31/12/2020**, avec toutes les métadonnées de sorties futures retirées : **1 342** valeurs de sortie supprimées, exactement les mêmes 59 lignes, mêmes cibles et indicateurs d'entraînement, écart maximal 0. `last_dates`/`exits` ne contaminent donc pas cet entraînement par une disparition future.
- Pour chacune des années 2018 à 2024, aucune fin de cible utilisée n'est >= au 1er janvier correspondant. Nombres de mois utilisés : 23, 35, 47, 59, 71, 83, 95 ; nombres d'échantillons : 63 536, 99 816, 134 722, 169 904, 212 300, 251 177, 286 552.
- Les sorties pendant une cible sont prises à la dernière clôture multipliée par `1 + exit_return`. Un titre sorti avant l'achat reçoit une cible NaN, ce qui est cohérent avec l'ordre impossible. L'entraînement 2021 comprend 717 sorties, mais seulement **une cible à −100 %** achetable au début du mois ; en 2024, 1 196 sorties et **cinq cibles à −100 %**. Ces cinq rangs vont de 0 à 0,00016672 : les faillites sont traitées correctement mais rarement présentes après les filtres.

**Verdict 1 : aucun défaut temporel trouvé dans le modèle proprement dit ; une décision de janvier ne peut pas apprendre une cible se terminant après elle. La réserve sur le nettoyage futur reste distincte.**

## 2. Placebos, entraînement inclus

Trois historiques croissants, testés en 2018, 2021 et 2024 : respectivement 23, 59 et 95 mois d'entraînement. Les corrélations utilisent 12, 12 et 11 mois de test complets, toujours comparés aux rendements réels. Aucune performance ni étiquette de 2025 n'entre dans le calcul.

Cible mélangée indépendamment **au sein de chaque date d'entraînement**, graines 0 à 19 ; paramètres figés, seul `random_state` suit la graine. Vingt réalisations pour chacune des trois années, donc 60 ajustements :

| Année | IC du modèle initial | IC placebo moyen, 20 graines | Min / max entre graines |
|---|---:|---:|---:|
| 2018 | 0,01725 | 0,00246 | −0,01518 / 0,02325 |
| 2021 | 0,05832 | −0,00346 | −0,02312 / 0,03218 |
| 2024 | 0,07720 | −0,00152 | −0,02293 / 0,00922 |

Sur les mêmes 35 mois, moyenne initiale **0,05017** ; moyenne placebo sur les graines **−0,00082**, écart-type entre graines 0,00842, plage des moyennes par graine −0,01642 à 0,01763. Ce placebo tombe bien près de zéro ; une graine isolée peut cependant être positive.

Indicateurs décalés de **3 ou 6 observations mensuelles vers le passé**, à l'entraînement comme au test, masque d'achat de la date courante conservé ; graines 0, 1, 2 et hyperparamètres inchangés :

| Décalage | 2018, IC | 2021, IC | 2024, IC, plage des trois graines | IC pondéré sur 35 mois, plage |
|---|---:|---:|---:|---:|
| 3 mois | 0,02087 | 0,08280 | 0,06641 à 0,06851 | 0,05641 à 0,05707 |
| 6 mois | 0,00002 | 0,05874 | 0,04070 à 0,04324 | 0,03294 à 0,03374 |

**Verdict 2 : le mélange des cibles passe le contrôle nul ; le décalage d'indicateurs ne tombe pas vers zéro. Ce deuxième contrôle n'est pas un vrai signal nul lorsque la liquidité, la volatilité et les rendements longs persistent. Sa survie, associée aux contrôles de facteurs ci-dessous, limite l'interprétation d'un signal mensuel spécifique, sans établir une fuite.**

## 3. t statistique, autocorrélation, égalités et facteurs

La formule du lanceur est bien le t de Student d'une moyenne de 83 observations : `mean / (std(ddof=1) / sqrt(83))`. Moyenne **0,034128715**, écart-type **0,103167073**, t **3,013823929**. Ce n'est pas la formule de significativité d'une corrélation calculée sur tous les titres-mois, ni une preuve de rentabilité.

Autocorrélations des IC mensuels aux retards 1/5/6/8/12 : **0,00457 / 0,20839 / 0,17360 / −0,22108 / −0,23359**. Ljung–Box : p = 0,967 au retard 1 ; 0,325 sur 6 retards ; 0,082 sur 12. Pas de forte autocorrélation immédiatement adjacente détectée. t corrigés HAC, noyau Bartlett avec correction n/(n−1), retards 1/3/6/12 : **3,0071 / 3,1507 / 2,9459 / 2,7546**. Un bootstrap circulaire en blocs de 12 mois donne un intervalle à 95 % de la moyenne **[0,01004 ; 0,05843]** ; cette vérification porte sur l'IC brut.

`method="first"` ne sert **pas** au calcul de `spearmanr`, qui utilise les rangs moyens des égalités. Si l'on force les rangs `first` pour les deux variables, moyenne 0,034128494 et t 3,013804 : effet négligeable. Repasser les déciles de `first` à `average` change 21 affectations titres-mois, mais seulement **0,0312 pb** de rendement moyen du décile 10. Inverser l'ordre des colonnes ne change aucun des 50 titres choisis sur les 84 décisions ; aucune égalité ne traverse la frontière du 50e titre.

| Score simple / contrôle | IC mensuel moyen | t naïf |
|---|---:|---:|
| Modèle | 0,03413 | 3,014 |
| `log_dollar_volume` seul | 0,03308 | 3,655 |
| `volatility_60` seule | −0,05931 | −2,841 |
| Modèle, rangs résidualisés sur liquidité et volatilité | 0,00597 | 0,860 |

Pour la volatilité, le modèle sur le même sous-ensemble de valeurs connues donne IC 0,03317 ; le score **faible** volatilité donne donc IC positif 0,05931, supérieur. La corrélation entre score ML et liquidité vaut en moyenne +0,3532 ; celle avec volatilité −0,4279. La corrélation partielle est calculée séparément chaque mois, en projetant les rangs du score et des rendements sur une constante et les deux rangs de facteurs, puis en corrélant les deux résidus. Elle contrôle une relation linéaire dans les rangs, sans prétendre couvrir tous les effets non linéaires.

À titre descriptif, aux mêmes dates, sur le même univers et avec les mêmes frais, les 50 titres les plus liquides donnent **20 039,74 USD** et les 50 moins volatils **13 091,48 USD**, contre 9 670,39 USD pour le ML. Aucun de ces contrôles n'a été journalisé ni proposé comme stratégie retenue.

**Verdict 3 : formule correcte, autocorrélation modérée qui ne fait pas disparaître le t brut, égalités sans effet matériel ; l'apport propre du modèle au-delà de liquidité/volatilité n'est pas établi.**

## 4. Déciles, extrêmes, portefeuille et rotation

Les rendements moyens mensuels des déciles 1 à 10 sont, en pourcentage : **0,2097 ; 0,6332 ; 0,8251 ; 0,7731 ; 0,9877 ; 0,9756 ; 0,9109 ; 1,0018 ; 0,8682 ; 0,6469**. L'écart 10–1 vaut +0,4372 point de pourcentage, t 0,838. Les 50 premiers rapportent +0,5192 % par mois contre +0,7833 % pour l'univers : **−0,2642 point**, t **−0,919** avant frais. L'écart DSKE/STT décrit plus haut ne change pas la conclusion.

Part des extrêmes, calculée en donnant le même poids à chaque mois puis aux titres du groupe :

| Groupe | Moyenne mensuelle | Moyenne des médianes mensuelles | Contribution des meilleurs ceil(1 % × n) titres | Moyenne après retrait symétrique de ceil(1 % × n) à chaque extrémité |
|---|---:|---:|---:|---:|
| Univers | +0,7833 % | +0,4336 % | +0,6079 point, **77,6 % de la moyenne** | +0,6196 % |
| Décile 1 | +0,2097 % | −1,1514 % | +1,0418 point | −0,1787 % |
| Décile 10 | +0,6469 % | +0,3900 % | +0,4997 point | +0,5191 % |
| Top 50 | +0,5192 % | −0,0314 % | +0,8182 point, **157,6 % de la moyenne** | +0,2945 % |

Pour les 50 premiers, `ceil(1 % × 50)` vaut un titre, donc cette dernière contribution représente le **meilleur titre sur 50**, soit 2 % du portefeuille. Les seuls gains de plus de 100 % contribuent +0,6849 point à la moyenne du décile 1, mais seulement +0,0836 point à celle du décile 10. Les extrêmes expliquent donc pourquoi un classement qui évite une partie des mauvais rangs peut garder une moyenne en dollars non monotone. Apprendre le rang attendu (`src/ml_rank.py:114`) n'optimise pas le rendement moyen en dollars des 50 premiers ; cela correspond aussi à l'exposition aux faibles volatilités.

Capital reproduit : **12 110,24 USD sans frais**, **9 670,39 USD avec frais**, soit 2 439,86 USD d'écart final. La comptabilité des coûts suffit à faire passer la performance globale de positive à négative ; le défaut du diagnostic ne change pas ce capital.

Rotation : somme de tous les achats et ventes = **145,89778** sur **1 760** périodes journalières, soit 6,98413 années de 252 séances ; division donne **20,88991/an**. Montant échangé moyen par rééquilibrage, entrée comprise : **1,72497** fois le capital, maximum 2 ; **43,18** nouveaux titres sur 50 en moyenne d'un mois au suivant. Le total inclut l'entrée et la liquidation finale (1 chacune) ; aucune rotation inexpliquée hors des dates de rééquilibrage et de la liquidation. La rotation « une face », moitié du volume achats+ventes, vaut **10,44495/an**. La même convention est utilisée pour le test A (8,87262/an).

**Verdict 4 : capital et rotation cohérents ; le diagnostic est presque aligné mais comporte le remplacement rétrospectif DSKE/STT et une fenêtre plus courte ; les queues de distribution et l'objectif en rang expliquent une part importante des déciles non monotones.**

## 5. Comparabilité et valeurs manquantes

- `top_n` avec tous les scores NaN sélectionne zéro titre, puis renvoie une ligne de **zéros** les jours de décision et une ligne vide les autres jours : aucune sélection arbitraire avant 2018. Il y a 24 ordres mensuels nuls sur 2016-2017. Ces ordres ne créent aucune position dans le préchauffage.
- Le backtest démarre sans position le 02/01/2018, puis prend 50 poids de 2 % à l'ouverture du **03/01/2018**, total 100 %. Le décalage est effectué une seule fois, par `lab.backtest`.
- ML et test A appellent le même `load_universe()` : **8 119** titres actuels, types common/adr, mêmes seuils bruts 5 USD et 1 MUSD, mêmes frais de 5/15/40/100 pb par côté et mêmes sorties. Reconstruction du test A : **18 160,285413705216 USD**, exactement son résultat actuel publié. Le chiffre de 8 123 titres encore dans le texte du test A est ancien.
- Aucune des 13 colonnes d'indicateurs n'est entièrement NaN sur les échantillons d'entraînement d'une des sept années ; `usable` est vrai partout. Les valeurs manquantes partielles sont réelles et acceptées par HGB : sur les 83 mois diagnostiqués, 14 320 valeurs de `return_252` manquent sur 255 379 candidats (5,61 %), contre zéro pour `log_dollar_volume`.
- Rang percentile : NaN et valeurs masquées restent NaN, égalités au rang moyen ; contrôle indépendant exact. Tests ciblés des égalités, masque, vecteur tout NaN et singleton. Biais maximal de la moyenne des rangs dû au float32 : **5,96e−8** autour de 0,5. Le cas singleton renvoie NaN, conforme au contrat actuel et sans occurrence problématique dans l'univers de l'audit.
- Différence effective d'éligibilité ML/A documentée dans le tableau des réserves : il faut distinguer un univers de données identique et un ensemble de scores connus identique.

**Verdict 5 : pas de défaut de démarrage, de rang ou de frais ; comparabilité du moteur confirmée, mais historique manquant et dernière période à expliciter.**

## 6. Reproductibilité et contrôles exécutés

Sept réentraînements annuels par reconstruction, sur les sept années : deux répétitions avec 1 thread, puis 2 et 8 threads. Ensuite deux **nouveaux processus** avec `OMP_NUM_THREADS=1`, `PYTHONHASHSEED=1` et `OMP_NUM_THREADS=8`, `PYTHONHASHSEED=2`. Les nombres effectifs de threads OpenMP sont vérifiés à 1 et 8.

Pour toutes les répétitions : **258 434 scores finis**, même masque NaN, **écart maximal 0** par rapport au Parquet sauvegardé ; capital **9 670,386748294111 USD**, rotation **20,88990920685018**. SHA-256 des matrices de scores des deux processus distincts : `7946471d652883b587983c2b1eb0d5e17d23211711e3ddd7ec50f58ea7212f1e` dans les deux cas. Cela vérifie cette installation CPU/scikit-learn 1.9.1 ; aucune extrapolation à une autre version logicielle ou architecture n'est nécessaire.

`PYTHONDONTWRITEBYTECODE=1`, `venv/bin/python -B tests/test_ml_rank.py` : **7 tests passent**, en 1,403 s. Les scripts de l'audit sont également lancés avec `venv/bin/python -B`, sans produire de cache Python dans le dépôt.

Incidents d'audit consignés, sans conséquence sur le dépôt : premier lancement de `base.py` en code 1 car `statsmodels` n'est pas installé ; HAC ensuite calculé directement avec la formule Bartlett, sans installation. Premier lancement de `models.py` en code 1 car les identifiants object des tableaux temporaires nécessitent `allow_pickle=True` pour relire nos propres tableaux. Un calcul exploratoire en ligne en code 1 essayait le minimum d'un ensemble vide de cibles à −100 % en 2018 ; le garde-fou a confirmé qu'il y en a zéro cette année-là. Tous les scripts d'audit finaux et les tests ont abouti ; aucun de ces codes 1 n'est présenté comme une erreur du projet.

Empreintes SHA-256 avant/après : `src/ml_rank.py`, `reports/run_step5_ml_rank.py`, `tests/test_ml_rank.py`, `src/experiment.py`, `reports/lab_2026-11/ledger_universe.csv`, `reports/lab_2026-11/experiments/step5_ml_rank.csv` **inchangés**. Détails dans `hashes_before.json` et `hashes_after.json`.

**Verdict 6 : reproduction exacte dans les répétitions, les processus distincts et les nombres de threads testés.**

## Pièces disponibles

- Reconstruction : `base.py`, `base_results.json`, `arrays.npz`, `monthly_independent.csv`.
- Réentraînements et placebos : `models.py`, `repro_results.json`, `repro_capitals.json`, `placebo_results.json`, `more_null.py`, `more_null_results.json`, `null_summary.json`.
- Processus distincts : `fresh.py`, `fresh_1.json`, `fresh_8.json`.
- Alignement et comparabilité : `extra.py`, `extra_results.json`, `diagnostic_alignment.csv`, `top50_differences.csv`, `nan_features.csv`, `extremes.csv`, `bankrupt_training.json`.
- Réserve du nettoyage : `upstream.py`, `upstream_results.json`.

Ce qui reste : corriger le diagnostic sans substituer un titre ex post, expliciter les fenêtres et les facteurs de risque dans le compte rendu, et quantifier séparément le nettoyage fondé sur le lendemain si l'on veut lever cette réserve de données ; aucun de ces changements n'était autorisé dans cet audit en lecture seule.
