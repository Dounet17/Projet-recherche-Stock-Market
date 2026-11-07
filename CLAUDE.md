# CLAUDE.md

## Contexte
Projet de fin d'études du master **ASI (Algorithmique et Systèmes Intelligents)**, en binôme (DavidTom et Dounet17). Échéance prévue vers février 2027 (à confirmer). Livrables attendus : une présentation orale et un article scientifique sur le travail réalisé (le professeur, anglophone, montrera comment le rédiger).

Les deux membres sont débutants en bourse : quand un concept financier apparaît (backtest, Sharpe, drawdown, P/E, etc.), l'expliquer simplement avant de l'utiliser.

État actuel : données de la partie Musk / Tesla téléchargées (`notebooks/01_collecte_donnees.ipynb`), première comparaison FinBERT / Jev faite (`notebooks/02_finbert_vs_jev.ipynb`), puis premier backtest exploratoire chronologique effectué le 25/10/2026 (`reports/Backtest_Musk_Tesla_2026-10-25.md`, code `src/backtest.py`, lancement `venv/bin/python reports/run_musk_backtest.py`).

Périmètre confirmé le 25/10/2026 : rester sur Musk / Tesla ; Trump / Dow Jones est réservé au camarade. Aucun résultat Trump n'est disponible dans ce dossier.

Laboratoire quotidien du 06/11/2026 (`reports/lab_2026-11/`, protocole `PROTOCOLE.md`, moteur `src/lab.py`, stratégies `src/price_lab.py` et `src/social_lab.py`, travail en binôme avec un worker Codex, audit `social/AUDIT_PRIX.md`) : 244 essais sur 2018-2024, journalisés. Validation unique 2025-2026 consommée, 4 stratégies figées : **aucune ne réussit** (`RAPPORT_VALIDATION.md`). Sur 10 000 USD : rotation top 3 sur 7 grandes valeurs 10 050 contre 13 274 pour le panier égal, filtre QQQ sur TSLA 8 527, ciblage de volatilité 10 178, sortie sur news 8 090, contre 10 070 pour TSLA conservée ; p de Holm de 1,000 partout. Ne pas ajuster ces règles pour les retester sur 2025-2026 : cette période est désormais connue. Grand dataset quotidien brut dans `data/universe/`, actions vivantes et disparues, dossiers `*holdout_*` à ne pas lire pendant la recherche. Téléchargements terminés : 17 418 symboles sur 2016-2024, dont 6 219 retrouvés par énumération (`reports/download_universe_extra.py`), 21,5 millions de lignes, contrôle `reports/qc_universe.py` et `reports/lab_2026-11/qc_universe.json`. Archives SEC extraites jusqu'à fin 2024 dans `data/sec/` (`reports/extract_sec_dev.py`, contact dans `.env`). **Dataset nettoyé le 06/11/2026** : `data/universe_clean/` (18 745 titres, 20,9 millions de lignes, 8 119 actions dont 2 845 disparues, rattachement rendu déterministe le 06/11/2026), règles `src/universe_clean.py`, lancement `venv/bin/python -I reports/clean_universe.py` (15 min), rapport `reports/lab_2026-11/NETTOYAGE_DONNEES.md`, à lire avant tout usage. Premiers tests faits dessus (voir « Organisation du code »). À respecter : filtres de prix et de liquidité sur `close` et `volume` (bruts) ; `suspect_print` traité comme manquant ; publier les résultats sous les trois hypothèses de sortie (`exit_return_base`, `_optimistic`, `_pessimistic`, rendement moyen -18 %, -9,4 %, -37,3 %) ; BPA à ne jamais utiliser avant `filed`. API Alpaca : le paramètre `asof` suit les changements de symbole, ce qui fusionne ou masque des séries (FRC sous FRCB, ancienne SNDK) ; utiliser `asof=-` pour énumérer. Limites : couverture SEC de 93 % pour les disparues du top 1 000 mais 50 % pour l'ensemble des disparues ; causes de disparition mal connues avant 2020 ; 3 404 titres non identifiés (0,6 % du volume en dollars) ; `reports/lab_2026-11/known_securities.csv` écrit de mémoire, à relire ; références de Shumway à vérifier avant citation ; appartenance historique aux indices non reconstituée ; 2025-2026 à nettoyer avec les mêmes règles, sans réglage. Validation par le professeur à demander pour l'élargissement, la période 2025-2026 et l'usage de l'USD. P/E et EPS encore insuffisamment traités alors que l'énoncé les demande.

Backtest 2022–2024 (apprentissage initial 2018–2021, réentraînement annuel, grille de 15 minutes indépendante des tweets, achat ou cash, délai d'information 60 s) : prix seuls -21,10 % sans frais / -82,45 % avec 5 points de base par côté ; prix + Jev -18,54 % / -81,90 % ; prix + FinBERT -24,28 % / -83,44 %. La stratégie passive Tesla fait +5,40 % avec le même coût par côté. Ces résultats décrivent ce protocole simple, sans établir un avantage social robuste ; période déjà explorée et contamination du préentraînement des classifieurs non exclue. Comptabilité en USD, pas de simulation EUR/USD.

Essais des modèles préentraînés terminés le 25/10/2026 : `reports/Resultats_modeles_preentraines_2026-10-25.md`. TimesFM-3, Chronos-2-Synth, Chronos-2 et Kronos-small exécutés sur GPU ROCm ; 14 variantes complètes sur les 18 000 décisions 2022–2024, direction correcte entre 48,42 % et 50,31 %. Aucune configuration complète rentable avec 5 pb par côté, même avec une marge d'abstention de 0,10 %. Les contrôles sociaux nuls montrent qu'un changement de portefeuille ne prouve pas un apport informationnel des tweets. KiT : pilote distinct de 36 origines, 24 bonnes directions (66,67 %), contre 21/36 pour toujours hausse ; checkpoint connaissant TSLA et déclarant un apprentissage jusqu'au 31/12/2025, donc pas une validation hors préentraînement. Données numériques de référence identiques mais modèles figés, sans réentraînement annuel ; contexte de 128 barres pour les modèles complets, 1200 pour KiT. Correction des unités us/ns de Pandas 3 validée avant les résultats Kronos finaux ; les lots invalides sont isolés. Treize tests automatisés et contrôles d'indépendance des lots sur CPU/ROCm et de comptabilité des frais passent.

### Répartition du travail (décidée le 12/10/2026)
- **DavidTom : Elon Musk sur Tesla (TSLA) uniquement**, pour commencer simple : un seul actif, un lien direct (Musk est le PDG). QQQ (Nasdaq-100) sert seulement d'indice de référence pour comparer, sans analyser ses autres entreprises (à confirmer avec le prof).
  - Posts de Musk mentionnant Tesla par mots-clés (dadalyndell, hors retweets, 2018-2024) : 2 818 dont 698 originaux, dont seulement 181 originaux pendant la séance. Un filtre par mots-clés rate les posts à effet indirect (rachat de Twitter en 2022, politique) : un classifieur (FinBERT ou Jev) devra juger la pertinence pour TSLA.
  - Trump ne parle presque jamais de Tesla sur 2018-2021 (3 tweets) : pas de signal Trump pour cette partie.
  - Ordre de travail : 1) event study (réaction de TSLA à +1, +5, +15, +60 min après chaque post), 2) seulement ensuite une stratégie qui achète ou vend selon le sentiment du post.
  - Premiers résultats (14/10/2026, 2 894 posts Tesla de 2018-2024, dont 546 en séance) : FinBERT et Jev ne sont d'accord que sur 55 % des posts (kappa 0,20) ; FinBERT classe 82 % des posts « neutre ». Seule la question `impact` de Jev annonce la réaction de TSLA, et seulement à +1 minute (Spearman 0,13, p = 0,003), pour un effet minuscule (environ 0,05 % de rendement anormal). L'effet disparaît dès +5 minutes. À confirmer : ce rendement inclut la minute du post (pas un gain réalisable) et 12 tests ont été faits (risque de faux positif).
- **Dounet17 : Dow Jones** (DIA et composants). Trump est la personnalité naturelle de cette partie (à confirmer).

Volatilité annuelle mesurée sur 2018-2024 (Alpaca, cours journaliers ajustés) : DIA 19 %, SPY 19 %, QQQ 24 %, TSLA 63 %. Une forte volatilité augmente autant les gains possibles que les pertes : elle ne garantit pas un meilleur rendement.

## Question de recherche
Un modèle d'IA peut-il obtenir de bons résultats en prédisant le marché, mieux qu'un simple placement passif (type ETF S&P 500 ou Nasdaq) ? L'hypothèse de départ est que non : les résultats seront probablement proches du hasard. Le but est de tout mettre en place pour maximiser le rendement ou minimiser les pertes, puis d'analyser honnêtement pourquoi chaque approche réussit ou échoue.

Cas d'étude : **Dow Jones Industrial Average (2018-2024)** avec un portefeuille virtuel de **10 000 €**.

### Sujet officiel (énoncé du professeur, en anglais)
- Les modèles doivent être testés sur un indice : « the EURO STOXX 50, DOW JONES or similar should be utilized in order to try and test the underlying models ». Le choix de l'indice est libre parmi ceux-là ou un équivalent (S&P 500, Nasdaq-100, CAC 40, etc.).
- L'énoncé cite explicitement les publications du président américain : « postings of the US president might shake or move the markets unforeseeable ».
- Classement des stratégies imposé par l'énoncé : **heuristics** (moving averages, Bollinger bands, EPS, P/E), **adaptive** (machine learning, sentiment analysis, AI-based), **hybrid**. Toutes doivent être évaluées et comparées systématiquement, avec leurs avantages et inconvénients.
- Objectifs officiels : 1) créer une collection de données financières temporelles, 2) implémenter les stratégies (heuristiques, adaptatives, hybrides), 3) les évaluer sur un budget virtuel de 10 000 €, 4) analyser et expliquer les résultats.

**Exigence du professeur : relier le projet aux réseaux sociaux.** L'idée est d'analyser les publications de personnalités influentes (Donald Trump, Elon Musk, etc.) et leur impact sur le marché. C'est, selon l'équipe, la piste la plus prometteuse pour trouver du rendement. Tesla n'est pas dans le Dow Jones : pour Musk, soit traiter TSLA comme étude complémentaire, soit choisir un indice qui la contient (Nasdaq-100 sur toute la période, S&P 500 depuis décembre 2020).

Hypothèse de l'équipe : le but n'est pas d'être le tout premier à réagir à une annonce (les algorithmes des grands fonds le sont), mais de réagir **avant la masse des humains**. Une bonne partie du mouvement de prix qui suit une annonce viendrait de traders humains, plus lents : il y aurait donc une fenêtre exploitable entre les robots les plus rapides et les humains. La stratégie doit rester rentable après frais.

Conséquences pour la méthode :
- Il faut des **prix intraday** (à la minute) et l'horodatage exact de chaque publication. Des prix journaliers ne permettent pas de voir cette fenêtre.
- Le backtest doit simuler un délai d'exécution réaliste : temps pour détecter la publication, temps d'inférence du modèle, passage de l'ordre.
- Une publication faite marché fermé (soir, week-end) ne peut être exploitée qu'à l'ouverture suivante, où tout le monde l'a déjà vue.

## Objectifs
1. **Données** : construire un dataset temporel qui fusionne les prix (quantitatif) et le sentiment des news (qualitatif).
2. **Implémentation** : développer des stratégies de trading, des heuristiques simples jusqu'aux modèles d'IA adaptatifs.
3. **Backtest** : simuler chaque stratégie sur les données passées dans un portefeuille virtuel réaliste de 10 000 €.
4. **Analyse** : expliquer les résultats, les avantages, les inconvénients et le comportement de chaque approche.

## Stratégies à comparer
Organisées selon les trois familles de l'énoncé.

- **Baselines** : Buy and Hold (référence principale) et stratégie aléatoire (pour tester l'hypothèse "proche du hasard").
- **Heuristics** :
  - analyse technique : moyennes mobiles, bandes de Bollinger ;
  - fondamentaux : EPS (Earnings per share) et ratio P/E.
- **Adaptive** :
  - machine learning : prédiction à partir de l'historique des prix ;
  - sentiment NLP : impact des news financières via des modèles transformers (FinBERT) ;
  - réseaux sociaux : impact des publications de personnalités influentes (Trump, Musk, etc.) : sentiment, thèmes (droits de douane, Chine, Fed, etc.), fréquence de publication.
- **Hybrid** : indicateurs techniques combinés aux scores de sentiment (news et réseaux sociaux).

L'idée est de tester un maximum de possibilités.

### Classifieurs de sentiment envisagés
- **FinBERT** (`ProsusAI/finbert` sur Hugging Face) : modèle BERT entraîné sur des textes financiers, qui classe un texte en positif / négatif / neutre. Gratuit, tourne en local, rapide.
- **Jev** (TypeSafe, déjà utilisé par DavidTom dans `firefox-jev-mcp`) : modèle hébergé qui renvoie une probabilité par option (`choice` du SDK `@typesafe-ai/sdk`). Il peut servir de classifieur avec des options choisies librement (par exemple : hausse / baisse / sans effet, ou thème de la publication). API payante mais très peu chère : 0,25 s par appel et 0,06 $ pour les 2 894 posts (mesuré). FinBERT : 0,02 s par post sur CPU.
- Comparer les deux est une piste d'analyse pour l'article.
- Fuite d'information : un modèle généraliste entraîné après 2024 peut déjà « savoir » comment le marché a réagi aux événements testés, ce qui fausserait le backtest. Vérifier la date des données d'entraînement de chaque modèle et le signaler dans l'article.

## Données
Comparatif détaillé de toutes les sources : `reports/Datasets bourse et réseaux sociaux.md` (notes brutes dans `research_notes/`). Sources retenues :

- **Prix à la minute** : API de données Alpaca, plan Basic gratuit (compte Paper Trading de DavidTom). Testé le 12/10/2026 : barres 1 minute consolidées (`feed=sip`) disponibles en 2018 pour SPY, DIA et TSLA, heures étendues comprises (4 h - 20 h, heure de New York). L'indice `^DJI` n'existe pas chez Alpaca : utiliser DIA (ou le future YM, payant ailleurs). Barres horodatées en UTC par leur début, prix bruts par défaut.
- **News horodatées** : API News d'Alpaca (Benzinga, depuis 2015, horodatage à la seconde). Testée le 12/10/2026 sur TSLA en 2018 : fonctionne. FNSPID (Hugging Face) seulement pour un sentiment journalier : dates sans heure, fin en janvier 2024, 23 Go à lire en flux.
- **Tweets de Trump (2018 à janvier 2021)** : CSV `tweets_01-08-2021.csv` de la Trump Twitter Archive (11,6 Mo).
- **Truth Social de Trump (2022-2024)** : archive CNN/Stiles `https://ix.cnn.io/data/truth-social/truth_archive.parquet` (CC0). Trump ne publie quasiment rien avant le 28/04/2022.
- **Tweets de Musk (2018-2024)** : Kaggle `dadalyndell/elon-musk-tweets-2010-to-2025-march` fusionné avec Hugging Face `fdaudens/musk-tweets` sur l'identifiant du tweet (le premier seul manque 42 % de 2024). Musk se teste sur TSLA, pas sur le Dow Jones.
- **Fondamentaux** : `yfinance` (`get_earnings_dates`) donne les dates de résultats et l'EPS de TSLA (28 publications sur 2018-2024, dans `data/tsla_earnings.parquet`). Utile aussi pour exclure ces dates des fenêtres d'événement. Pas encore de source pour le P/E historique.
- **Scraping** : inutile pour 2018-2024 (archives suffisantes). En dernier recours pour X : `twscrape` avec un compte jetable (contraire aux conditions d'utilisation de X). Pour Truth Social : `truthbrush` (fork maintenu `w2rc/truthbrush`, compte requis).
- Le Dow Jones a changé 6 fois de composition entre 2018 et 2024 : suivre environ 40 tickers avec leurs dates d'appartenance.

### Accès et secrets
- Les clés sont dans `.env`, exclu de Git par `.gitignore` : `ALPACA_API_KEY` et `ALPACA_SECRET_KEY` (Alpaca), `TYPESAFE_API_KEY` (Jev, copiée de `firefox-jev-mcp/.env`). Ne jamais afficher, commiter ni copier ces clés ailleurs. Dounet17 doit créer son propre `.env`.
- Les données téléchargées vont dans `data/` (non versionné), de préférence en Parquet.
- Essais des modèles préentraînés : environnement isolé `.venv-forecast/`, poids épinglés dans `data/forecast_models.json`, sources tierces dans `data/vendor/` (non versionné). Lancement ROCm : `HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_foundation_benchmark.py --family timesfm3 --batch-size 32`. Ce venv utilise un PyTorch ROCm local et réutilise les bibliothèques générales du venv initial par un fichier `.pth`.

## Points de vigilance (backtest et ML)
- Pas de look-ahead bias : une décision prise au jour t n'utilise que des informations disponibles au jour t.
- Séries temporelles : jamais de mélange aléatoire train/test, découper chronologiquement.
- **Heure des posts : toujours la recalculer depuis l'identifiant**, jamais depuis la colonne date des datasets (erreurs mesurées de 12 h, 4 h, troncature à la minute). Tweet : `ms_utc = (id >> 22) + 1288834974657`. Truth Social : `ms_utc = id >> 16`. Lire les identifiants comme texte ou `int64`, jamais en float. Une heure trop tôt crée un faux gain dans le backtest.
- Une barre à la minute est étiquetée par son début : pour un post à 14:52:28, le prix de référence est la clôture de la barre 14:51 et la première barre de réaction propre est 14:53 (plus le délai d'exécution simulé).
- Aligner les news et les publications sur les jours de bourse (week-ends, jours fériés, publications après la clôture) en gardant l'horodatage précis (avec fuseau horaire).
- Le marché réagit à une publication en quelques secondes ou minutes : il faut des prix intraday, que `yfinance` ne fournit que sur un historique récent : utiliser Alpaca (voir « Données »).
- Prendre en compte les frais de transaction.

## Organisation du code
- Phase actuelle : **Jupyter Notebooks** (exploration, construction du dataset, premières stratégies).
- `notebooks/` : un notebook par étape, numérotés (`01_collecte_donnees`, `02_finbert_vs_jev`, ...). Ils importent le code de `src/`.
- `src/collect.py` : téléchargements (posts de Musk, barres et news Alpaca, calendrier de bourse). `src/timeutils.py` : heure depuis l'identifiant, séances de bourse. `src/sentiment.py` : FinBERT et Jev. `src/universe_clean.py` : règles de nettoyage du grand dataset quotidien.
- `data/` (non versionné) : fichiers Parquet produits par `01_collecte_donnees`, plus les caches de classification (`finbert_musk_tesla.parquet`, `jev_musk_tesla.parquet`) qui évitent de rappeler l'API de Jev.
- Cadre d'expérience sur le grand univers (`reports/lab_2026-11/CADRE_EXPERIENCES.md`, à lire avant un test) : `src/universe_data.py` (`load_universe`), `lab.backtest(..., exits=...)` (disparitions, frais par titre), `src/experiment.py` (`run_experiment`, `top_n`). Hors intraday, qui reste dans `src/backtest.py`. Premiers tests : momentum et P/E bas, tous deux sous SPY (`reports/lab_2026-11/RESULTATS_TESTS_A_B.md`).
- Référence du buy and hold, à lire avant de juger une stratégie : `reports/lab_2026-11/REFERENCE_BUY_AND_HOLD.md`. Lancement `venv/bin/python reports/build_reference.py` (moins de 2 min), code `src/reference.py`, détail dans `data/reference/` et French coupé à fin 2024 dans `data/french/`. Référence principale : le buy and hold moyen du même univers que la stratégie ; SPY à côté comme placement achetable ; les secteurs décrivent le marché et ne servent pas à juger une stratégie.
- Comparaison d'une règle au buy and hold de chaque action : `src/per_stock.py`. Moyenne mobile 200 séances : sous le buy and hold en capital (12 487 contre 16 490 USD), chutes réduites, alpha proche de 0 (`reports/lab_2026-11/RESULTATS_ETAPE_3.md`). Bollinger et RSI 2 : encore en dessous (`RESULTATS_ETAPE_4.md`). Règles dans `src/stock_rules.py`, nouvelle règle via `per_stock.evaluate_rule`. Avec des liquidités rémunérées, toujours mesurer Sharpe et alpha au-delà du taux sans risque.
- Premier modèle de classement (`src/ml_rank.py`, arbres de gradient boosting sur prix et liquidité, réentraînement annuel) : 9 670 USD, sans apport démontré au-delà de la faible volatilité et de la liquidité, sans fuite trouvée à l'audit (`reports/lab_2026-11/RESULTATS_ETAPE_5.md`). - Événements datés : `src/events.py`, lancement `venv/bin/python reports/build_earnings_events.py` (moins d'une minute), rapport `reports/lab_2026-11/RESULTATS_EVENEMENTS.md`. Publications de résultats : le cours réagit au jour J, mais aucun effet exploitable après, en données quotidiennes, même avec les vraies heures SEC et un achat le jour même. Dans ce dernier cas, notre BPA n'est jamais encore connu : il faudrait le lire dans le communiqué ou le 8-K. **Le champ `accepted` de `data/sec/dev_filings.parquet` est faux de 4 à 5 heures, dans les deux sens, dans 30 % des 81 304 8-K de résultats (mesure complète du 07/11/2026, 39 % en 2018, 22 % en 2024) malgré son suffixe Z : ne jamais s'en servir comme heure. Utiliser `accepted_new_york` de `data/events/eight_k_times/` (heure de New York), en sachant que ce n'est qu'une borne de l'heure de diffusion, ou `filing_date` en entrant à la séance suivante.** Une SUE ne doit utiliser que des chiffres dont `filed` précède la décision, historique compris.
- Couverture des news Alpaca mesurée sur un échantillon de 240 titres (`reports/lab_2026-11/COUVERTURE_NEWS.md`, sans lecture de rendement) : 99 % des titres couverts, disparus compris, environ 1,36 million d'articles sur 2018-2024. Exclure les commentaires de marché avant toute étude (causalité inversée). Contexte : facteurs de French et séries FRED dans `data/french/` et `data/fred/` (`reports/download_context_data.py`). Heures réelles des 8-K dans `data/events/eight_k_times/` (`reports/download_8k_times.py`, version Pi `download_8k_times_pi.py`, import `import_8k_times_pi.py`), 81 304 sur 81 304. **News complètes dans `data/news/`** (`news_AAAA-MM.jsonl.gz`, `reports/download_all_news.py`) : 1 399 118 articles uniques, 80 % à un seul symbole (compte complet, l'échantillon de `COUVERTURE_NEWS.md` donnait 52 %), aucun résumé avant 2020, 30 % de résumés au total, `source` vide jusqu'à fin 2021 alors que toutes les URL sont Benzinga. Triées et classées par FinBERT (`reports/lab_2026-11/TRI_NEWS.md`, `src/news_filter.py`, `data/news/news_scored.parquet`), sans aucun rendement lu, corrigées après deux audits (`news/AUDIT_TRI_NEWS.md`, `news/AUDIT_TRI_NEWS_2.md`). **`data/news/earnings_surprise.parquet` donne l'écart à l'estimation citée dans la dépêche pour 61 % des publications, dont 20 319 avec une base explicite ; chiffres contrôlés le 07/11/2026 dans les communiqués (`data/events/exhibits/`, résultat `data/news/earnings_surprise_verified.parquet`) : `verified` pour 87 %, `principal` pour 17 659 lignes dont 38 % en 2024, et un chiffre faux passe encore le contrôle dans 4 à 8 % des cas (Waterstone passe), voir `TRI_NEWS.md`. Barres à la minute 2018-2024 autour des publications : `data/events/minute_bars/` et `minute_bars_extra/`, 99,97 % des couples titre-séance couverts. **Étude lancée le 07/11/2026, puis corrigée après l'audit de Codex** (`reports/lab_2026-11/RESULTATS_DEPECHES_MINUTE.md`, `minute_study/AUDIT_CODEX.md`, protocole `PROTOCOLE_RESULTATS_MINUTE.md` avec ses écarts datés, code `src/minute_study.py`) : acheter les bonnes nouvelles à l'ouverture perd après frais (-0,31 pt, 10 000 USD deviennent 43 USD) ; écart ouverture-clôture de +0,52 pt (Holm 0,002) porté par les mauvaises nouvelles, mais placebo de la veille déjà +0,12 pt, donc effet propre à la dépêche non identifié ; 93 % de l'écart déjà dans les prix à l'ouverture, description et non preuve d'une fenêtre robots / humains. Ne pas ajuster ces règles pour les retester sur 2018-2024. **Notes d'analystes, lancées une fois le 07/11/2026** (`reports/lab_2026-11/RESULTATS_NOTES_ANALYSTES.md`, protocole `PROTOCOLE_NOTES_ANALYSTES.md`, code `src/analyst_study.py` relu trois fois par Codex avant lancement) : aucun test confirmatoire ne réussit (relèvements moins abaissements sur 20 séances +0,31 pt, Holm 0,35 ; placebo à 60 séances déjà +0,51 pt) ; acheter les relèvements 20 séances : 15 013 USD contre 24 531 pour SPY et 16 356 pour le buy and hold des achetables. Ce n'est pas un consensus vérifié, et ni la version historique du titre ni l'heure de première diffusion ne sont prouvées : `available_at` n'est qu'une borne prudente.** **`event_security` corrigé le 07/11/2026 : c'est l'action citée par la dépêche (1 310 lignes changées). Les barres à la minute du Pi demandées avant cette date contiennent d'anciens symboles faux : les joindre par symbole et séance depuis la table corrigée, complément dans `minutes/todo_extra.tsv` (voir `TRI_NEWS.md`).** **Ne pas se fier à `alias_symbols` pour dater un symbole : il peut venir d'un renommage postérieur (BBT sur Berkshire Hills).** Un repérage de mots fait mieux que FinBERT sur les titres à verdict écrit : pour les résultats, utiliser les chiffres. FinBERT figé à la révision `4556d130`.
- Exécuter un notebook en ligne de commande : `venv/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 notebooks/<nom>.ipynb`.
- L'API Alpaca est lente (environ 20 min pour 7 ans de barres à la minute d'un symbole) : `collect.py` télécharge par année en parallèle et réessaie en cas d'erreur réseau.
- Plus tard, si les résultats le justifient : interface web affichant la courbe du portefeuille, les points d'achat et de vente et la raison de chaque décision.

## Langue
- Identifiants du code (variables, fonctions, fichiers) en anglais.
- Commentaires, cellules markdown des notebooks et documentation en **français** pour l'instant. Traduction en anglais en fin de projet.

## Stack
- Python : `yfinance`, `pandas`, `numpy`, `scikit-learn`, `transformers`, `torch`, `matplotlib` (voir `requirements.txt`).
- Machine de DavidTom : Linux natif, Ryzen 7 5800X3D (8 cœurs / 16 threads), 32 Go de RAM. Vérification matérielle le 25/10/2026 : **AMD Radeon RX 6750 XT**, 12 Go, `gfx1031` (les notes précédentes indiquaient RX 6700 XT). ROCm 6.2.4 est installé (`rocminfo`, `rocm-smi`).
  - Pour le GPU, il faut le build ROCm de PyTorch (le `torch` par défaut de pip vise CUDA). Avec ROCm, PyTorch expose quand même le GPU via `torch.cuda` / `device="cuda"`.
  - La RX 6700 XT (gfx1031) n'est pas officiellement supportée par ROCm : il faut en général `HSA_OVERRIDE_GFX_VERSION=10.3.0`.
  - Test réel du 25/10/2026 : `torch==2.6.0+rocm6.2.4` et `HSA_OVERRIDE_GFX_VERSION=10.3.0` permettent le calcul sur la RX 6750 XT ; les modèles chargés utilisent bien le GPU. Le venv initial conserve son PyTorch CPU.
  - Sinon, FinBERT reste utilisable sur CPU en traitant les textes par batch et en mettant les scores de sentiment en cache.

## Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # PyTorch CPU, plus léger
pip install -r requirements.txt
```
Le venv de DavidTom a été créé avec `uv` (Python 3.12, pandas 3, transformers 5).
