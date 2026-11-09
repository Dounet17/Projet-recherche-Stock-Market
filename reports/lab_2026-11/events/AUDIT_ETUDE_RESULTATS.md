# Audit contradictoire de l’étude des résultats — framework-backtest

Audit effectué en lecture seule le 7 novembre 2026, depuis le dossier partagé `/home/tomda/Documents/Projet-recherche-Stock-Market`.

**Verdict : la réaction rétrospective avant l’entrée existe dans ces données, mais l’avantage exploitable après le 8-K n’est pas établi.** Le résultat à une séance conserve un signal statistique avec certains contrôles correctement regroupés dans le temps ; ses dates et surtout son score ne constituent cependant pas une information disponible en temps réel. L’absence de signal convaincant après les comptes résiste aux contrôles ; elle ne prouve pas l’absence universelle de dérive après résultats.

Les six points demandés ont été traités. Les résultats ci-dessous sont descriptifs sur la période déjà explorée ; aucun essai n’a été inscrit au journal.

## Périmètre et preuves

- Lecture de `CLAUDE.md`, `NETTOYAGE_DONNEES.md`, des trois fichiers demandés, du chargeur de marché et des fonctions de nettoyage nécessaires à leur interprétation.
- Aucun fichier du dépôt écrit, aucun commit, aucune lecture de `.env`, aucun appel à `lab.record_trial`, aucun fichier contenant `holdout` ouvert. Exécution par `venv/bin/python -B` pour empêcher l’écriture des caches Python dans le dépôt.
- Données locales numériques utilisées exclusivement jusqu’au 31/12/2024. `tsla_earnings.parquet` a été lu avec filtres Parquet sur `ts` **avant** matérialisation : seulement les 28 lignes 2018–2024. Les archives SEC brutes contenant aussi des données ultérieures n’ont pas été ouvertes. Les documents SEC utilisés comme preuve portent des dépôts antérieurs à 2025.
- Calendrier chargé : 2 264 séances du 04/01/2016 au 31/12/2024 ; univers `common` : 6 718 titres. Étude : 66 430 lignes à l’annonce et 66 585 au dépôt ; groupes utilisables respectivement 55 833 et 56 009 observations, 27 trimestres.
- Les quatre sources Python ont été copiées dans ce dossier temporaire ; leurs SHA-256 ont été vérifiés inchangés en fin d’audit. Le `git diff --stat` final est vide ; les fichiers non suivis préexistants étaient les mêmes au début et à la fin.
- Tests existants : **10/10 passent**, `tests.log`. Ils ne contrôlent ni le fuseau réel de la source SEC, ni l’heure du communiqué, ni la disponibilité de tous les BPA historiques, ni la validité statistique sous dépendance de marché.

Tout ce qui suit se reproduit avec les scripts temporaires de ce dossier : `audit.py`, `source_check.py`, `random_check.py`, `numeric.py`, `leakage.py`, `causal.py`, `source_metrics.py`, `portfolio.py`, `selection_check.py`. Les CSV et les extraits SEC locaux servent de preuves. Le cache temporaire `state.pkl` ne contient que les données autorisées et facilite leur relecture.

## Défauts classés par gravité

| Gravité | Défaut concret | Localisation | Mesure / conséquence |
|---|---|---|---|
| Critique | `accepted` n’est pas uniformément UTC malgré le suffixe Z | `reports/build_earnings_events.py:62`, source `reports/extract_sec_dev.py:60` | 22/99 heures incorrectes dans un tirage aléatoire ; 5/99 dates d’entrée changent après contrôle de l’index SEC |
| Critique pour l’exploitation | BPA courant du dépôt ultérieur utilisé à l’entrée 8-K | `reports/build_earnings_events.py:78` et `:85` | 41 612/52 350 annonces avec groupe et 8-K utilisent un BPA dont `filed` n’est pas antérieur à l’entrée, soit 79,49 % |
| Élevée | L’historique de SUE contient parfois des BPA publiés après la décision, y compris au dépôt | `src/events.py:72` et `:79`, appel `reports/build_earnings_events.py:78` | Historique non causal pour 2 598 observations annonce et 1 598 observations dépôt parmi celles avec groupe |
| Élevée | Mélange individuel des groupes incompatible avec la dépendance temporelle ; p nulle possible | `src/events.py:155` et `:167`, correction `reports/build_earnings_events.py:169` | À 20 séances, t=1,18 mais p permutation=0 ; p temporelle corrigée ≈0,23–0,25 avant Holm |
| Moyenne | Dernier 8-K 2.02 choisi sans identifier le communiqué ni sa période | `src/events.py:37` | Présentation LBAI et tableau historique HY retenus ; 1/99 faux communiqué dans l’échantillon aléatoire, 1/24 dans l’échantillon stratifié |
| Moyenne | Rang de liquidité calculé sur toutes les annonces du trimestre, y compris futures | `reports/build_earnings_events.py:132` | 3 879 appartenances top1000 changent face à un classement connu avant le trimestre ; t 1 séance passe de 1,86 à 1,58 |
| Moyenne | Univers identifié et documenté très différent de l’ensemble des disparues | `reports/build_earnings_events.py:38`, `src/universe_clean.py:231`, `reports/clean_universe.py:206` | Couverture SEC 49,78 % des disparues si `unknown` inclus ; couverture en événements classés 28,82 % des `common` disparues contre 67,26 % des vivantes |
| Moyenne | Référence quotidiennement rééquilibrée, excluant certaines sorties faute d’ouverture suivante | `src/events.py:100` | Sur 2018–2024 : multiple 2,433 contre 1,565 pour le témoin gelant les actions entre trimestres ; ce changement de convention est matériel |
| Faible à moyenne | Coût aller-retour préenregistré à 20 séances pour tous les horizons | `reports/build_earnings_events.py:117` | Le calcul après frais doit prendre le coût à l’horizon effectif ; recalcul fait ici |
| Faible | Censure de fin d’échantillon asymétrique | `src/events.py:95` | À 60 séances, 7 rendements de titres disparus restent renseignés après le terme théorique 2024, contrairement aux survivants |
| Faible | Clôture fixée à 16 h même lors des demi-séances | `src/events.py:58` | Au moins NKE, 03/07/2018 : le cours de clôture précédent est décalé d’une séance |

## 1. Dates, fuseaux et retard du 8-K

### Recalcul indépendant de 30 cas

`sample30.csv` contient les trente cas et les dates d’entrée/recul calculées par parcours du calendrier et recherche binaire par CIK, sans appeler `match_announcements` ni `session_positions`. Il comporte cinq cas avant ouverture, cinq en séance, cinq après clôture, un cas classé week-end, cinq sans 8-K et neuf cas supplémentaires de T4/10-K. Les calculs internes reproduisent **30/30 rapprochements et 30/30 couples de séances**. Cela valide les règles programmées à partir des horodatages fournis ; cela ne valide pas ces horodatages.

Vérification externe des index SEC et des documents : 24 cas avec 8-K, six sans 8-K dont le dépôt est contrôlé. Parmi les 24 8-K, **9 heures fausses**, **3 entrées différentes**, **3 clôtures de référence différentes**. Sur les 30 dépôts vérifiés en incluant les six sans 8-K, 13 heures diffèrent du véritable UTC. Les index et les liens sont dans `source_check.json` et `source_check_metrics.csv`.

Exemples directement vérifiables :

| Cas | Horloge fournie, interprétée UTC | Index SEC, heure New York | Conséquence |
|---|---|---|---|
| HUM, 02/05/2018 | 15:31Z → 11:31 NY | 07:31 NY | Entrée 03/05 au lieu du 02/05 |
| ROK, 28/04/2021 | 15:19Z → 11:19 NY | 07:19 NY | Entrée 29/04 au lieu du 28/04 |
| HAYN, 27/01/2022 | 16:08Z → 11:08 NY | 16:08 NY | Entrée inchangée, mais clôture de référence prise un jour trop tôt |
| CFLT, 07/05/2024 | 16:06Z → 12:06 NY | 16:06 NY | Même défaut de clôture de référence |
| LBAI, 28/01/2021 | 09:30Z → 04:30 NY | 09:30:56 NY | La présentation retenue est postérieure à l’ouverture ; autre 8-K de résultats à 09:00 existe |
| PDFS, février 2018 | 17/02 05:25Z → samedi 00:25 NY | vendredi 16/02 19:25 NY | Le seul « week-end » est un artefact de fuseau ; le communiqué date en réalité du jeudi 15/02 |

Sources primaires, par exemple : [HUM](https://www.sec.gov/Archives/edgar/data/49071/000119312518147566/0001193125-18-147566-index.html), [ROK](https://www.sec.gov/Archives/edgar/data/1024478/000102447821000011/0001024478-21-000011-index.html), [CFLT](https://www.sec.gov/Archives/edgar/data/1699838/000095017024054470/0000950170-24-054470-index.html), [PDFS](https://www.sec.gov/Archives/edgar/data/1120914/000143774918002810/0001437749-18-002810-index.html).

Un second échantillon **aléatoire de 100 événements avec groupe et 8-K**, graine 73519, donne 99 index accessibles et une erreur HTTP 503. Parmi les 99 contrôlables : **77 vrais UTC, 10 avances de 4–5 heures et 12 retards de 4–5 heures** selon la convention de comparaison cache moins vrai UTC. Plus exactement les écarts sont +4 h : 10, +5 h : 2, −4 h : 6, −5 h : 4. Donc **22/99 incorrects = 22,22 %**, intervalle de Wilson 95 % [15,16 % ; 31,36 %]. Cinq dates d’entrée changent (GSBC, EV, BCO, PTON, ONIT), six clôtures de référence changent. Les huit sociétés disparues du tirage ont toutes une heure fausse, contre 14/91 des vivantes : petit effectif mais alerte très nette sur cette sous-population. Ce taux est celui des événements classés, pas une estimation sur toutes les entrées du catalogue SEC.

Il n’existe donc **aucune correction globale « ajouter 4 heures »**. Il faut lire `Accepted` sur les index/SGML, convertir avec `America/New_York`, conserver le texte d’origine et tracer les divergences. La SEC précise que l’heure d’acceptation de l’en-tête est une heure de l’Est et qu’il n’existe pas d’horodatage attestant la première disponibilité effective sur son site : [FAQ SEC](https://www.sec.gov/about/webmaster-frequently-asked-questions).

### Le dépôt peut suivre le communiqué et la réaction

Les 99 documents 8-K du tirage aléatoire ont été lus pour identifier leur objet. **Un faux communiqué de résultats sur 99 : HY**, le 03/05/2022 à 17:01:20, fournit des tableaux historiques ; un 8-K de résultats distinct existe à 16:58:33. Ici l’erreur sémantique de 2 min 47 ne change pas la séance d’entrée. Dans le stratifié, **LBAI, 1/24**, est une présentation à 09:30:56, alors qu’un 8-K de résultats existe à 09:00:03 : ici le classement avant/après ouverture change. Les petites proportions ne doivent pas être généralisées sans intervalle et échantillon plus large.

**Autre cas prouvé, hors tirages : NKE.** Le dernier 8-K 2.02 du 03/07/2018, accepté à 14:31:40 NY, est la transcription de la conférence de résultats tenue le **28/06**, pas une nouvelle annonce ; le script retient pourtant une entrée au **05/07**, contre le **29/06** après la véritable publication. Le cours brut passe de 71,70 $ à la clôture du 28/06 à 78,76 $ à l’ouverture du 29/06, soit **+9,847 % avant le 8-K retenu**. Ce cas fournit une preuve directe de réaction antérieure, au-delà du simple diagnostic par maximum de rendement : [8-K NKE](https://www.sec.gov/Archives/edgar/data/320187/000032018718000065/0000320187-18-000065-index.html). De plus, le 03/07 est une demi-séance clôturée à 13 h : la règle fixe 16 h prend le close du 02/07 au lieu du 03/07, produisant un gap de **−2,205 %** plutôt que **+0,446 %** jusqu’à l’ouverture du 05/07. Le fichier conserve le transcript dans `NKE_halfday_8k.txt`.

Deux des 99 communiqués financiers aléatoires sont explicitement datés de la veille du dépôt : **GSBC, communiqué 23/01/2023, accepté 24/01 à 08:51**, et **MATW, communiqué 26/04/2018, accepté 27/04 à 14:13**. Cela fournit une **borne basse 2/99 = 2,02 % de retards calendaires**, sans mesurer les retards de quelques minutes/heures du même jour. Dans le stratifié, PDFS est accepté le lendemain du communiqué ; AVA présente le cas inverse, le document du soir annonçant un communiqué du lendemain. Pour une annonce un jour donné, `accepted` n’est donc ni une heure garantie du communiqué, ni même toujours une borne postérieure à celui-ci.

Les données Yahoo de TSLA corroborent **28/28 jours**, mais pas les heures : elles indiquent notamment 20 h pour juillet 2024 alors que le 8-K est accepté à 16:32. Ce contrôle existant ne permet pas de vérifier la causalité intraday.

### Contrôle par |rendement|

Autour de l’entrée stockée, moyenne de |rendement ouverture-ouverture| :

| Catégorie | n | offset −2 | offset −1 | offset 0 |
|---|---:|---:|---:|---:|
| Avant ouverture | 20 388 | 1,822 % | 4,228 % | 4,029 % |
| En séance | 9 453 | 2,903 % | 4,591 % | 3,535 % |
| Après clôture | 28 143 | 2,055 % | 5,113 % | 4,298 % |
| Sans 8-K | 8 445 | 3,654 % | 4,113 % | 3,398 % |

Le pic individuel sur onze fenêtres est plus ancien que −1 dans **27,37 % des cas classés en séance**, 16,11 % après clôture, 15,47 % avant ouverture et 37,36 % sans 8-K. Avec les heures SEC corrigées dans le tirage aléatoire, il est plus ancien que −1 pour **17/99 événements**. C’est un **diagnostic de mauvais alignement possible, pas une estimation identifiée de la part des dépôts après réaction** : le maximum d’une série volatile peut tomber plus tôt par hasard, et les fenêtres journalières se recouvrent avec les communiqués de la veille. Les seuls retards publiés prouvés dans ce tirage sont les deux cas calendaires ci-dessus ; une vraie proportion de retards intraday requiert l’heure indépendante du communiqué et des prix intraday.

## 2. Fuites et BPA réellement disponible

### Le résultat « avant entrée » est rétrospectif

La moyenne `gap_return` est −1,2467 % dans le groupe 1 et +1,4110 % dans le groupe 5 : écart **2,6578 points**, conforme aux quelque 2,7 points annoncés. Le fichier comporte aussi `gap_abnormal`, **strictement identique à `gap_return` sur toutes les lignes** alors que le script actuellement audité n’écrit plus cette colonne. Il ne faut pas présenter ce nombre comme un rendement neutralisé du marché ; c’est un écart brut, dont les groupes sont établis avec un BPA parfois futur.

Sur les 55 833 événements classés : 52 350 ont un 8-K, et **41 612 de ces 52 350** n’ont pas encore de BPA SEC causal à l’ouverture d’entrée selon la règle conservatrice `filed < entry_date`. Le délai date-annonce → `filed` a une médiane d’un jour civil et une moyenne de 4,99 jours sur ces 52 350 ; en séances jusqu’à la disponibilité conservatrice, médiane 1, moyenne 3,93. Une partie des BPA figure bien dans le communiqué, mais il faut l’extraire de celui-ci, pas supposer son égalité avec un dépôt ultérieur.

### Comparaison manuelle de 24 BPA de communiqués

`release_eps_check.csv` confronte le BPA de l’étude à celui des pièces 99.1. **20/24 égalités à un demi-cent près, 4/24 différences** :

| Société / trimestre | BPA de l’étude | BPA GAAP du communiqué | Cause étayée |
|---|---:|---:|---|
| UMPQ T4 2021 | 0,40 | 0,41 | T4 déduit de l’annuel moins neuf mois ; arithmétique de ratios arrondis et dénominateurs variables |
| GOSS T4 2021 | −0,75 | −0,74 | Même approximation T4 |
| AXTA T4 2023 | 0,34 | 0,33 | Même approximation T4 |
| BLFS T2 2024 | −0,45 | −0,50 | Communiqué du 08/08 : perte 22,775 M$ ; 10-Q du 09/08 : 20,719 M$, même nombre d’actions ; véritable différence entre versions |

Les trois erreurs de T4 représentent **3 des 9 T4 dérivés** du stratifié ; elles ne sont pas trois preuves de retraitement. BLFS est, lui, un exemple concret de fuite de version : **+0,05 $/action et +2,056 M$** provenant du dépôt du lendemain. [10-Q BLFS](https://www.sec.gov/Archives/edgar/data/834365/000162828024036470/blfs-20240630.htm). La proportion 4/24 est descriptive d’un échantillon choisi pour varier les cas et surpondérant le T4 ; elle n’est pas une estimation de fréquence universelle.

Au moins **15/24 communiqués** proposent aussi un BPA ajusté différent du GAAP utilisé par l’étude. Exemples : NDAQ 0,97 contre 1,18 ; HNI 0,80 contre 0,93 ; VTRS −0,27 contre +0,69 ; ROK 3,54 contre 2,41 ; CFLT −0,30 contre +0,05 ; NMRK −0,08 contre +0,52 ; HES 1,34 contre 1,63. Les écarts ne viennent pas automatiquement de l’avenir : ils prouvent surtout que le BPA GAAP ne représente pas toujours le chiffre auquel réagit le marché. Pour TSLA T4 2023, le tableau local donne 2,27 GAAP contre 0,71 dans la référence de résultats ajustés ; pour T3 2024, 0,62 contre 0,72. Les périodes anciennes doivent en plus être remises sur une échelle d’actions commune avant comparaison (fractionnements).

### Fuite même dans le cas dit « entièrement causal »

`standardized_surprise` ne reçoit **aucune date de disponibilité**. Une période ancienne peut apparaître pour la première fois dans un document comparatif ultérieur ; la trier par fin de trimestre ne la rend pas disponible historiquement.

En reconstruisant les dates de tous les termes utilisés, **2 598 historiques annonce** et **1 598 historiques dépôt** contiennent au moins un chiffre non encore publié à l’entrée, parmi les observations avec groupe. Le cas dépôt n’est donc pas « entièrement causal » tel qu’il est codé. L’étude comprend aussi 5 840 périodes dont `filed − period_end > 150 jours`, dont 1 141 avec groupe ; 4 702 dépassent un an, dont 586 avec groupe. La majorité du sous-ensemble sans 8-K est ainsi composée de vieilles périodes rapportées dans des documents ultérieurs, pas seulement de résultats courants dont manquerait le communiqué.

J’ai recalculé la SUE en n’admettant, à chaque décision, que le BPA courant, sa référence annuelle et les variations historiques dont **tous les dépôts précèdent l’entrée**. Les seuils sont recalculés sur le trimestre précédent.

| Cas | Observations avec groupe | Écart 1 séance | t NW | Écart 5 séances | t NW | Écart 20 séances | t NW | Écart 60 séances | t NW |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Annonce, étude originale | 55 833 | 0,5448 pt | 3,51 | 0,6294 pt | 2,27 | 0,8147 pt | 1,18 | 0,9708 pt | 1,21 |
| Annonce, seulement BPA effectivement disponible | 14 163 | 0,4714 pt | 2,19 | 0,5516 pt | 1,45 | 0,8882 pt | 1,24 | 0,8622 pt | 0,87 |
| Idem, périodes récentes ≤150 j | 13 061 | 0,4422 pt | 1,96 | 0,3851 pt | 0,91 | 0,9120 pt | 1,18 | 0,7897 pt | 0,75 |
| Dépôt, historique réellement disponible | 55 863 | 0,0729 pt | 1,26 | 0,1512 pt | 0,70 | 0,1202 pt | 0,21 | −0,1391 pt | −0,19 |

Le tableau original inclut **3 483 événements classés sans 8-K** : sa formule « après 8-K » est donc déjà approximative. En exigeant `has_8k`, le spread original à une séance est **0,5667 point, t=3,54**, sur 52 350 observations ; avec score disponible et historique causal, **0,5330 point, t=2,18**, sur 10 696 ; en exigeant aussi des périodes récentes et en reconstruisant les seuils, **0,4663 point, t=1,97** sur ces mêmes 10 696. Détail à tous les horizons : `strict_8k_causal.csv`.

La réduction de l’échantillon change sa composition : ce n’est pas une estimation isolée de « combien vaut la fuite ». Le p nominal à une séance du sous-ensemble annonce causal est environ **0,0376**, donc insuffisant pour une famille de 16 tests ; avec seulement les périodes récentes, t≈1,96. Les résultats après dépôt restent sans avantage démontré.

### Autres contrôles de causalité

- **Seuils du trimestre précédent** : leur logique temporelle est correcte pour un score disponible. Mais 524 scores du trimestre précédent ne sont pas encore déposés au début du suivant dans l’étude annonce ; les retirer change 242 groupes. Écart 1 séance quasiment inchangé : 0,54475 pt, t=3,57. Au dépôt : zéro score exclu, zéro groupe changé pour cette raison.
- **`factor.ffill().bfill()`** : le backward fill sert 75 085 dates de BPA sur 206 569 lignes candidates, essentiellement de l’historique antérieur au début de cotation/panel. **Zéro BPA courant des 66 430 événements retenus** utilise un facteur antérieur au premier facteur observé. Aucun avantage futur à l’entrée démontré pour ce `bfill` isolément ; les historiques pré-cotation et les échelles de fractionnement restent à vérifier. L’absence de fuite du facteur ne répare pas les dates de publication des BPA.
- **Titre le plus liquide** : le choix utilise la médiane des 20 séances au cours de référence pré-événement ; pas de score de liquidité future trouvé à ce stade. La réduction finale laisse zéro doublon `(cik, period_end)`. En revanche le **rang top1000 du trimestre** compare l’événement courant à tous les événements futurs du même trimestre. Reclasser les titres avec la liquidité connue à la clôture du trimestre précédent change 3 879 appartenances ; t top1000 à 1 séance 1,86 → 1,58.
- **`eligible`** : prix brut, liquidité passée et existence d’une exécution à l’ouverture ; pas de filtre direct sur le rendement futur. Les cours suspects sont toutefois construits dans le nettoyage avec la séance suivante (`src/universe_clean.py:196`). J’ai trouvé 55 drapeaux de retournement qui nécessitent le futur parmi les 560 drapeaux `common`, mais **zéro date de référence pré-événement candidate** touchée dans les deux études. Cette fuite de nettoyage existe dans le code, sans effet de sélection mesuré ici.

## 3. Statistiques : les 16 lignes refaites

Le mélange individuel par trimestre détruit la dépendance entre actions, dates et secteurs et traite comme échangeables des entreprises dont les risques sont différents. Ce n’est pas le même nul que « moyenne temporelle du spread nulle ». Le problème est visible sans ambiguïté à 20 séances : p permutation=0 avec t NW=1,18. De plus, une permutation finie ne devrait pas retourner zéro : employer `(1 + dépassements)/(B + 1)`, soit un minimum **1/501≈0,002** pour 500 tirages, et calculer l’écart à zéro du nul correctement défini.

Contrôles calculés sur les **16 lignes**, `statistics16.csv` :

1. p bilatérale de Student à 26 degrés de liberté appliquée au t de Newey-West existant (un lag trimestriel). C’est une approximation prudente d’effectif, pas une distribution exacte du HAC.
2. Bootstrap circulaire par blocs de **deux trimestres**, 20 000 tirages, série trimestrielle centrée, correction +1. Il conserve mieux la dépendance temporelle et les co-mouvements déjà intégrés dans chaque spread.
3. Variante Fama-MacBeth simple : chaque mois, régression saturée par groupes, dont le coefficient G5−G1 égale la différence de moyennes mensuelles ; moyenne des coefficients mensuels avec NW à trois lags. Ce sont 79–81 mois selon l’horizon, pas des dizaines de milliers d’unités indépendantes. Pas de contrôles de caractéristiques supplémentaires dans cette variante.
4. Holm appliqué séparément aux 16 p de chaque procédure, sans choisir a posteriori celle qui donne le meilleur résultat.

| Entrée | Univers | h | Spread (points) | t NW | p NW | Holm NW | p blocs2 | Holm blocs2 | Holm mensuel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| announcement | top1000 | 1 | 0.2412 | 1.86 | 0.0736 | 1.0000 | 0.0581 | 0.8134 | 1.0000 |
| announcement | top1000 | 5 | 0.2618 | 0.88 | 0.3845 | 1.0000 | 0.3752 | 1.0000 | 1.0000 |
| announcement | top1000 | 20 | 0.5786 | 0.74 | 0.4634 | 1.0000 | 0.4616 | 1.0000 | 1.0000 |
| announcement | top1000 | 60 | 1.0320 | 0.86 | 0.3995 | 1.0000 | 0.3638 | 1.0000 | 1.0000 |
| announcement | all | 1 | 0.5448 | 3.51 | 0.0017 | 0.0267 | 0.0007 | 0.0112 | 0.0722 |
| announcement | all | 5 | 0.6294 | 2.27 | 0.0317 | 0.4749 | 0.0225 | 0.3375 | 0.2185 |
| announcement | all | 20 | 0.8147 | 1.18 | 0.2484 | 1.0000 | 0.2310 | 1.0000 | 1.0000 |
| announcement | all | 60 | 0.9708 | 1.21 | 0.2387 | 1.0000 | 0.2195 | 1.0000 | 1.0000 |
| filing | top1000 | 1 | -0.0722 | -0.76 | 0.4533 | 1.0000 | 0.4363 | 1.0000 | 1.0000 |
| filing | top1000 | 5 | -0.0192 | -0.06 | 0.9489 | 1.0000 | 0.9482 | 1.0000 | 1.0000 |
| filing | top1000 | 20 | -0.0057 | -0.01 | 0.9933 | 1.0000 | 0.9933 | 1.0000 | 1.0000 |
| filing | top1000 | 60 | -0.3352 | -0.40 | 0.6923 | 1.0000 | 0.6910 | 1.0000 | 1.0000 |
| filing | all | 1 | 0.0821 | 1.37 | 0.1815 | 1.0000 | 0.1630 | 1.0000 | 1.0000 |
| filing | all | 5 | 0.1642 | 0.74 | 0.4633 | 1.0000 | 0.4608 | 1.0000 | 1.0000 |
| filing | all | 20 | 0.1383 | 0.24 | 0.8128 | 1.0000 | 0.8169 | 1.0000 | 1.0000 |
| filing | all | 60 | -0.0951 | -0.13 | 0.8996 | 1.0000 | 0.8994 | 1.0000 | 1.0000 |

À 20 séances, annonce/all : p bloc2 **0,2310**, p NW **0,2484**, Holm=1, contre 0 dans le tableau initial. À une séance : p NW **0,001666**, Holm **0,02665** ; p bloc2 **0,000700**, Holm **0,01120** ; Fama-MacBeth mensuel p **0,004512**, Holm **0,07219**. Il reste donc une association rétrospective courte, sensible à l’unité de pondération et à la disponibilité du score. À cinq séances, p NW 0,0317 devient **0,4749** après Holm. Aucun test après dépôt ne devient convaincant.

**Holm ne doit pas reposer sur la permutation actuelle.** Holm contrôle la multiplicité uniquement si les p d’entrée sont valides. Son implémentation arithmétique passe les tests ; c’est le test de base qui ne correspond pas à la dépendance observée.

### Placebos de dates

`date_placebo.csv` contient les 16 lignes, avec les mêmes titres et groupes et des déplacements de **−83, −63, −41, +41, +63, +83 séances**, uniquement dans la fenêtre de données autorisée. Référence SPY et support temporel commun pour chaque horizon ; une ouverture du titre doit exister à la date décalée. L’étiquette trimestrielle originale est conservée afin de garder les mêmes unités de pondération. Les effectifs varient légèrement lorsqu’un titre n’est pas encore ou plus coté à une date décalée : ils figurent dans le CSV.

Pour annonce/all, écart à 1 séance : **0,575 pt à la date originale**, puis +41 : 0,006 pt ; +63 : 0,065 pt ; +83 : 0,030 pt. À 20 séances : 0,919 pt original ; +41 : 0,142 pt ; +63 : 0,064 pt ; +83 : 0,083 pt. En revanche −63 donne 0,342 pt à 1 séance et 2,132 pt à 20 séances ; −83 donne 3,205 pt à 20 séances. Les décalages négatifs montrent qu’une future bonne SUE classe aussi des trajectoires passées : ce sont des contrôles de spécificité, **pas un nul échangeable pour une p empirique**. En particulier −63 se rapproche des résultats du trimestre précédent. Les six dates ne suffisent pas à une p précise ; je n’utilise pas ce placebo pour Holm.

## 4. Mesure, référence et chevauchements

`forward_multiple` mesure bien une ouverture à l’ouverture située `h` séances plus tard. Le test manuel d’une sortie avec perte totale passe. L’ajout d’une perte de disparition s’effectue après le dernier cours si l’horizon le dépasse ; il n’y a pas de gain fictif évident sur ce chemin testé.

Deux défauts restent quantifiés : à 60 séances, **7 sorties finies hors support commun 2024** ; et des prix d’ouverture de sortie reportés par `ffill`. À 1/5/20/60 séances, parmi les événements à horizon dans l’échantillon, il manque respectivement 12/47/206/591 ouvertures exactes ; presque toutes correspondent à une disparition traitée. Seulement **1/1/2/1 cas sans disparition** restent valorisés par un cours reporté. Ce dernier effet est négligeable ici.

Le choix `base` seul ne respecte pas la sensibilité aux trois hypothèses demandée par la documentation. Je l’ai refaite : à 60 séances, spread brut base **1,1326 pt**, optimiste **1,1311 pt**, pessimiste **1,1466 pt** ; 597 événements affectés sur tout l’échantillon. L’écart de conclusion est petit dans cette étude, mais cette vérification manquait.

### Pourquoi tous les groupes sont négatifs à 60 séances

Ce sont les **rendements anormaux**, pas les rendements bruts. À l’annonce, les moyennes brutes des groupes 1→5 à 60 séances sont **+0,962 %, +1,671 %, +2,106 %, +3,198 %, +2,547 %**. La référence moyenne des fenêtres vaut environ +3,001 % sur l’ensemble ; sa composition par dates diffère selon les groupes. Après dépôt, moyennes brutes également positives, de +1,351 % à +3,087 % selon le groupe. Il n’y a donc pas cinq groupes perdant nécessairement de l’argent.

L’indice quotidien rachète les perdants et revend les gagnants chaque jour, gratuitement, avec entrées/sorties variables ; ce n’est pas un buy and hold. Sur 2018–2024, son multiple est **2,4335**, contre **1,5653** pour un témoin distinct gardant les actions achetables au début de chaque trimestre puis rééquilibrant trimestriellement, sorties centrales et liquidités après disparition. SPY donne **2,4556**. Le premier calcul trimestriel a échoué numériquement car le début 2016 n’a pas dix observations de liquidité ; la version correcte ci-dessus commence en 2018 avec un historique disponible. L’écart quotidien/trimestriel mêle fréquence de rééquilibrage, renouvellement de l’univers et calendrier des filtres : il ne permet pas d’attribuer toute la différence à un biais de rééquilibrage pur.

L’indice quotidien exclut aussi 1 364 couples titre-séance dont l’ouverture suivante est manquante, soit **0,0230 %** des 5 936 498 couples éligibles ; ce filtre dépend du lendemain et n’intègre pas systématiquement le produit de disparition. À corriger pour une référence investissable.

### Recalcul avec SPY

Les 16 résultats existent avec référence originale, SPY et rendement brut dans `benchmarks.csv`. Pour annonce/all :

| Horizon | Écart original | t original | Écart contre SPY | t SPY |
|---|---:|---:|---:|---:|
| 1 | 0,5448 pt | 3,51 | 0,5403 pt | 3,43 |
| 5 | 0,6294 pt | 2,27 | 0,6406 pt | 2,21 |
| 20 | 0,8147 pt | 1,18 | 0,9151 pt | 1,32 |
| 60 | 0,9708 pt | 1,21 | 1,0653 pt | 1,35 |

Le signal à une séance ne vient donc pas principalement de l’indice maison. Avec SPY, tous les groupes restent sous la référence à 60 séances, dont G1 −2,123 % et G5 −0,899 %. Cette observation confirme une sous-performance relative de cet échantillon, sans expliquer à elle seule sa cause.

### Pondération et fenêtres qui se recouvrent

`quarterly_spread` donne autant de poids à chaque trimestre ; la différence entre les colonnes `group_5` et `group_1` du CSV donne autant de poids à chaque événement. Ces deux chiffres ne sont pas identiques : à 1 séance annonce/all, écart des moyennes événementielles ≈**0,400 pt**, contre **0,545 pt** pour la moyenne des spreads trimestriels. Ce n’est pas une erreur arithmétique ; la définition doit être annoncée.

Le prochain événement de la même société intervient avant la fin de la fenêtre dans **2 922 / 5 168 / 5 859 / 18 960 cas** à 1/5/20/60 séances à l’annonce, et **5 966 / 5 972 / 6 002 / 21 079** au dépôt. Jusqu’à **343 annonces** et **445 dépôts** sont traités le même jour. Une partie des chevauchements courts vient des anciennes périodes rapportées dans un même dépôt. Dédupliquer par `(cik, entry_date)` laisse 63 508 événements annonce et 60 619 dépôt ; à l’annonce, le spread à une séance reste 0,5442 pt, t=3,58 ; au dépôt, 0,0758 pt, t=1,24. Le défaut n’explique donc pas à lui seul le résultat court, mais interdit les tests assimilant les événements à des observations indépendantes.

## 5. Achat du seul groupe 5 après le 8-K, après frais

Sélection limitée aux **vrais événements avec `has_8k` dans le fichier**, sans prétendre que les heures et SUE sont réparées. Prix brut ≥5 $ conservé dans tous les cas. « Sans filtre de liquidité » retire seulement le plancher de volume en dollars, puis reconstruit les seuils des groupes sur l’univers élargi ; les autres filtres utilisent les groupes originaux, puis les seuils de liquidité indiqués. Les comparaisons ne sont donc pas un traitement causal isolé de la liquidité.

Coût à chaque ouverture pris dans `cost_bps`, dont le calcul est bien décalé d’une séance. Pour chaque trade :

`net = (1 + rendement_brut) × (1 − coût_sortie) / (1 + coût_entrée) − 1`.

La sortie est à l’horizon effectif 1/5/20, ou à la disparition si elle survient avant. Pas de frais de vente à découvert puisque le portefeuille achète seulement G5. Pas d’annualisation d’un rendement événementiel chevauchant.

| Sélection | h | n | Brut | Coût AR (pb) | Net | Net − SPY |
| --- | --- | --- | --- | --- | --- | --- |
| no_liquidity_min | 1 | 12427 | 0.333 % | 61.1 | -0.277 % | -0.343 pt |
| no_liquidity_min | 5 | 12427 | 0.794 % | 60.6 | 0.185 % | -0.228 pt |
| no_liquidity_min | 20 | 12393 | 1.967 % | 59.5 | 1.362 % | -0.019 pt |
| min1m_existing | 1 | 10679 | 0.289 % | 38.8 | -0.099 % | -0.167 pt |
| min1m_existing | 5 | 10679 | 0.601 % | 38.5 | 0.215 % | -0.177 pt |
| min1m_existing | 20 | 10653 | 1.583 % | 38.1 | 1.199 % | -0.116 pt |
| min10m_existing | 1 | 7682 | 0.212 % | 22.9 | -0.017 % | -0.083 pt |
| min10m_existing | 5 | 7682 | 0.559 % | 22.7 | 0.331 % | -0.059 pt |
| min10m_existing | 20 | 7662 | 1.626 % | 22.8 | 1.394 % | 0.144 pt |
| min100m_existing | 1 | 2726 | 0.184 % | 10.0 | 0.084 % | 0.055 pt |
| min100m_existing | 5 | 2726 | 0.686 % | 10.1 | 0.585 % | 0.197 pt |
| min100m_existing | 20 | 2713 | 2.266 % | 10.4 | 2.161 % | 0.723 pt |
| causal_filing_min1m | 1 | 10673 | 0.058 % | 38.3 | -0.324 % | -0.385 pt |
| causal_filing_min1m | 5 | 10673 | 0.254 % | 38.0 | -0.126 % | -0.393 pt |
| causal_filing_min1m | 20 | 10640 | 0.836 % | 38.3 | 0.453 % | -0.867 pt |

Le groupe 5 avec le filtre existant ≥1 M$/jour fait **−0,099 % net à une séance**, +0,215 % à cinq et +1,199 % à vingt, mais **−0,167 / −0,177 / −0,116 point** relativement à SPY sur les mêmes fenêtres. Sans filtre de liquidité : **−0,277 %, +0,185 %, +1,362 %**. Le coût moyen aller-retour à une séance est respectivement **38,8 pb** et **61,1 pb**, ce qui absorbe le petit rendement brut.

Au-delà de 100 M$/jour, l’estimation événementielle est plus favorable : +0,084 %, +0,585 %, +2,161 % nets, surplus SPY +0,055 / +0,197 / +0,723 point. C’est un sous-échantillon descriptif de 2 726 événements, sans confirmation statistique ni score causal ; ce filtre a été regardé pendant l’audit et n’est pas une règle validée.

Le cas dépôt plus causal, avec les groupes originaux et ≥1 M$, produit **−0,324 %, −0,126 %, +0,453 % nets** à 1/5/20 séances, et reste sous SPY de **0,385 / 0,393 / 0,867 point**.

### Portefeuille de budget fini, pour ne pas additionner des trades chevauchants

J’ai aussi simulé **10 000 $**, cash non rémunéré, `h` poches indépendantes initialement égales pour un horizon `h`, chacune renouvelée tous les `h` jours ; la poche investit à poids égaux dans les G5 du jour, sinon reste en cash. Les gains des poches sont conservés, pas de levier ; marques d’ouverture, disparitions centrales, achat et vente au coût du titre ; liquidation finale au dernier cours disponible. SPY est acheté dans les mêmes poches aux mêmes dates et avec 5 pb par côté. Cette construction est un choix descriptif explicite et conserve les défauts de score/date de l’étude.

| Liquidité | h | Capital net ($) | SPY même calendrier ($) | Exposition moyenne | Baisse maximale |
| --- | --- | --- | --- | --- | --- |
| no_liquidity_min | 1 | 134 | 4,636 | 72.2 % | -99.5 % |
| no_liquidity_min | 5 | 9,894 | 13,428 | 72.3 % | -45.1 % |
| no_liquidity_min | 20 | 15,254 | 18,002 | 72.2 % | -40.2 % |
| min1m | 1 | 1,459 | 4,643 | 69.2 % | -96.0 % |
| min1m | 5 | 13,454 | 13,468 | 69.5 % | -40.5 % |
| min1m | 20 | 14,443 | 17,918 | 68.8 % | -38.6 % |
| min10m | 1 | 976 | 5,093 | 63.3 % | -94.2 % |
| min10m | 5 | 12,492 | 14,708 | 63.2 % | -41.3 % |
| min10m | 20 | 17,230 | 17,058 | 62.6 % | -35.0 % |
| min100m | 1 | 4,957 | 5,856 | 46.7 % | -72.9 % |
| min100m | 5 | 13,889 | 12,871 | 47.2 % | -27.3 % |
| min100m | 20 | 17,427 | 14,518 | 46.1 % | -23.5 % |

Les chiffres du portefeuille diffèrent des moyennes événementielles : chaque jour reçoit ici un budget limité, au lieu de laisser les journées comprenant beaucoup d’événements peser davantage. Une vérification indépendante par produit des rendements moyens journaliers, à horizon 1 et filtre ≥1 M$, retrouve **1 459,30733999006 $**, écart de seulement 7×10⁻¹² $ avec le simulateur. Le coût du renouvellement quotidien de tout le budget investi peut être énorme : le rendement brut composé correspondant est positif, mais il ne résiste pas à cette rotation et aux coûts. Les lignes 10/100 M$ favorables à certains horizons ne constituent pas de nouveaux essais validés.

## 6. Univers, disparitions et plusieurs classes

La forte couverture apparente des `common` ne doit pas masquer que le type du titre dépend lui-même de la présence de comptes SEC.

| Univers, titres d’au moins 20 séances | État fin 2024 | Titres | Avec CIK | Avec BPA |
|---|---|---:|---:|---:|
| common | disparus | 2 484 | 2 432 (97,91 %) | 2 123 (85,47 %) |
| common | vivants | 4 234 | 4 204 (99,29 %) | 4 040 (95,42 %) |
| common + adr + unknown | disparus | 5 538 | 2 757 (49,78 %) | 2 200 (39,73 %) |
| common + adr + unknown | vivants | 5 985 | 5 243 (87,60 %) | 4 208 (70,31 %) |

Les effectifs actualisés diffèrent légèrement de l’ancien rapport de nettoyage, comme sa note le prévoyait. Parmi les seuls `common`, l’étude annonce retient au moins un événement pour **846/2 484 disparus**, contre **3 070/4 234 vivants** ; au moins un événement avec groupe pour **716 (28,82 %) contre 2 848 (67,26 %)**. Les disparus ne fournissent que **6 007 des 55 833 observations classées**, 10,76 %, alors qu’ils représentent 36,98 % des titres `common`. Les différences de durée de cotation expliquent une partie de cette dernière comparaison, mais pas l’écart de couverture SEC de l’univers élargi. Il subsiste donc un **biais de couverture favorable aux survivants**, sans que les disparus soient complètement absents de l’étude.

Parmi les CIK renseignés des `common`, **338 CIK ont deux titres, 32 trois et deux quatre**. L’étude candidate comporte 10 217 couples CIK/période multi-titres, soit 11 075 lignes supplémentaires avant déduplication. Après sélection, **zéro doublon CIK/période** : les classes multiples ne gonflent pas directement l’effectif final. 152 CIK présentent néanmoins 177 paires de titres dont les cotations se chevauchent ; cela mélange de vraies classes (BIO/BIO.B, HEI/HEI.A, etc.) et de faux rattachements.

Exemples de rattachement/classification erronés repérés : **OND#0**, ETF ProShares coté depuis octobre 2021, est déclaré `common`, CIK **80424 de Procter & Gamble** ; le prospectus SEC de 2023 identifie au contraire ProShares Trust, CIK **1174610** : [prospectus OND 2023](https://www.sec.gov/Archives/edgar/data/1174610/000168386323006688/f36297d1.htm). **TWC#0** est rattaché au CIK **30697 de Wendy’s**, alors que Time Warner Cable utilisait **1377013**, confirmé par [son dépôt de mai 2016](https://www.sec.gov/Archives/edgar/data/1377013/000122520816033750/0001225208-16-033750-index.htm). Des titres Qwest CTQ/CTZ et CSI/SUNE demandent aussi une revue d’identité avant assimilation à des classes ordinaires. **Aucune ligne d’étude retenue pour OND, TWC, CTQ, CTZ ou CSI** dans les contrôles : les exemples confirment un défaut de métadonnées, sans effet direct mesuré sur le spread retenu. L’indice peut rester exposé à d’autres faux rattachements non contrôlés.

## Limites restantes et actions concrètes

1. Refaire l’horloge de tous les 8-K via en-têtes/index, puis identifier le **premier vrai communiqué portant sur la période étudiée** et son heure de diffusion indépendante ; le taux de 22/99 ne remplace pas cette réparation exhaustive. Les données journalières ne suffisent pas à attribuer le mouvement intraday entre communiqué et dépôt.
2. Extraire les BPA GAAP et ajustés **dans les pièces du communiqué**, versionner les chiffres et les dates, et reconstruire tous les termes de SUE à partir des seules publications disponibles. Le cas dépôt doit aussi filtrer l’historique, pas seulement dater le BPA courant.
3. Fixer avant une nouvelle analyse l’univers causal, le témoin investissable, l’unité temporelle, la procédure d’inférence et une seule règle de coût/portefeuille ; aucun réglage nouveau sur les périodes de validation déjà connues.
4. Publier « association rétrospective courte avec score imparfait » pour l’annonce et « aucun avantage établi avec ces données après dépôt ». Éviter « rien d’exploitable » au sens d’une preuve générale d’absence d’effet.

Deux incidents de scripts sont consignés sans les confondre avec un échec de l’audit : une première requête de 10-Q sans en-tête explicite a terminé avec `AttributeError` car sa page ne contenait pas le tableau attendu, puis la requête avec User-Agent a réussi et confirmé BLFS ; `extra.py` a terminé avec **code 1** sur un `NameError: re` après avoir écrit tous les tableaux de couverture et d’indice. L’extraction de dates restantes a été exécutée séparément dans `manual_checks.py`, et les deux retards GSBC/MATW vérifiés à la lecture des documents. Le premier indice trimestriel vide au début 2016 a produit NaN et un avertissement, puis a été recalculé sur 2018–2024 avec historique ; ces incidents ne sont pas utilisés comme preuves contre le code de l’étude. Un index SEC sur 100 est resté HTTP 503 : il est conservé comme manquant, pas inventé.

Les dix tests existants passent ; les recalculs de rapprochement et de calendrier reproduisent 30/30 règles internes ; les calculs statistiques, causalité, référence SPY, coûts et déduplication ont tous abouti. Les chiffres bruts, paramètres, résultats et sources nécessaires à l’examen sont dans ce dossier temporaire, sans modification du dépôt.
