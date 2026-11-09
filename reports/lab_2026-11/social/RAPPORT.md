# Recherche sociale, news et résultats trimestriels sur Tesla

Développement uniquement : 02/01/2018 au 31/12/2024. Validation 2025-2026 jamais ouverte. 45 essais journalisés, soit 15 règles et contrôles dans trois scénarios. 0 stratégie(s) préinscrite(s).

La variante au capital le plus élevé à 5 pb est `news_finbert_exit_5` : 327,218 USD contre 203,541 USD pour TSLA conservée, avec p corrigée 0.771. Ces observations de développement ne démontrent aucun avantage hors échantillon.

Cette règle conserve TSLA sauf lorsque la moyenne FinBERT des titres sur cinq séances est inférieure à -0.10 avec au moins trois titres classés. Elle améliore les estimations ponctuelles du CAGR (64.78 % contre 53.95 %), du Sharpe (1.108 contre 0.977) et du drawdown (-59.07 % contre -74.97 %). À 10 pb elle atteint encore 307,225 USD, avec p corrigée 0.801. Son excès annuel de log-rendement a un intervalle bootstrap à 95 % de [-5.62 %; 20.35 %], incluant zéro. Son alpha a une p brute de 0.034, sans correction multiple, et le gain de Sharpe une p brute de 0.089. Ce sont des pistes exploratoires incertaines; le résultat négatif porte sur la preuve statistique, sans démontrer l'absence de tout signal social.

## Lecture des mesures

On part de 10 000 USD. Le CAGR est le rendement composé moyen par an. Le Sharpe rapporte le rendement moyen aux variations du portefeuille : plus haut est préférable à risque comparable. Le drawdown mesure la plus forte chute depuis un sommet; il est calculé aux ouvertures, pas à l'intérieur des séances. L'alpha est le rendement annuel restant après estimation de l'exposition aux variations quotidiennes de TSLA. Une p corrigée faible serait une indication contre le hasard après prise en compte de tous les essais; elle ne garantit ni rentabilité future ni absence de biais de données. Une p de 0.10 n'est pas une preuve solide. Les liquidités ont un rendement nul dans l'analyse principale.

## Audit indépendant du moteur

Lecture de CLAUDE.md, du protocole, du moteur, de ses tests et du rapport intraday antérieur avant toute stratégie. Cinq défauts reproduits par cinq tests en échec dans tests/test_social_lab.py, transmis au coordinateur par la question msg_4b35443c23f8, puis corrigés exclusivement par lui dans src/lab.py :

- Les périodes avec un trou de prix interne disparaissaient avant le contrôle de valorisation. Le test impose désormais le refus d'une position impossible à valoriser.
- Le contrôle de causalité ignorait les colonnes absentes des panels tronqués. Le test d'une colonne ajoutée seulement sur le panel complet détecte désormais la fuite.
- Romano-Wolf donnait p = 1 à un avantage constant strictement positif. Le cas dégénéré est désormais traité selon son signe.
- La comparaison d'une stratégie intégralement en liquidités produisait un Sharpe et un intervalle NaN. La convention Sharpe nul est désormais commune aux fonctions.
- Le bootstrap de l'alpha gardait le bêta global. Chaque tirage réestime maintenant pente et intercept. Le scénario synthétique avait un intervalle incorrect [0.039875; 0.493717], contre [-0.076818; 0.620118] après réajustement, ce qui changeait l'inclusion de zéro.

Autres points contrôlés : les poids du jour sont décalés une fois par le moteur et gagnent seulement de l'ouverture suivante à celle d'après; achat initial et liquidation finale paient les frais; la dérive des poids évite de facturer un rééquilibrage fictif d'une position entièrement en TSLA ou d'un panier à deux actifs dont la cible suit exactement les poids dérivés; le drawdown inclut le capital initial; bootstrap stationnaire apparié avec blocs moyens de 21 séances; tests unilatéraux centrés sous l'hypothèse nulle; verrou refusant load_panel(end > 2024) sans autorisation. Aucun autre défaut confirmé dans le périmètre audité. Les cinq tests de régression restent dans tests/test_social_lab.py. Le test causal par troncature est un contrôle utile, pas une preuve contre toute erreur sémantique de source.

## Données et chronologie

Chargements Parquet filtrés à la clôture du dernier jour du panel, jamais lecture directe des prix : 60089 posts hors retweets, 2894 avec FinBERT et 2894 avec Jev; 28432 news; 42 publications de résultats, y compris le préchauffage. Les empreintes portent uniquement sur les lignes autorisées, voir sources.json. Les compteurs de likes et de partages sont exclus car mesurés après publication.

Les heures de Musk sont vérifiées par la formule de l'identifiant Twitter, en entier 64 bits. Chaque post et news entre au premier jour dont la clôture est postérieure à sa disponibilité : nuit, week-end et séance écourtée passent à la prochaine clôture. Le calendrier local fournit les clôtures réelles; 16 h New York sert seulement avant sa couverture. La news est disponible au maximum de created_at et updated_at : un titre révisé n'est jamais exploité avant sa mise à jour. Les changements antérieurs de titre restent inconnus : les versions originales ne sont pas reconstruites et une source rétrospective peut rester incomplète.

59.0 % des news ont une mise à jour postérieure à leur création. FinBERT local sur CPU utilise seulement les titres, ProsusAI/finbert, 128 tokens maximum, sans réentraînement. Le cache est dans social/news_finbert.parquet pour respecter la liste de fichiers autorisés, plutôt que créer un nouveau fichier dans data/. Jev utilise exclusivement le cache existant : aucun appel payant, aucun accès à .env. Les scores sociaux manquants ne deviennent pas des opinions neutres : aucune abstention n'est déclenchée sans score. Les caches Musk couvrent seulement le sous-ensemble Tesla constitué antérieurement; les thèmes extérieurs proviennent d'une règle lexicale sur tous les posts disponibles hors retweets.

Une surprise de bénéfice ne peut agir qu'à la clôture du lendemain de publication au plus tôt, même lorsque l'heure de source paraît antérieure à la fermeture. L'entrée se produit donc au plus tôt à l'ouverture encore suivante. Les EPS arrondis sont comparés directement et les estimations manquantes exclues; les pourcentages de surprise aberrants sur petites bases ne sont pas utilisés. Le consensus EPS est rétrospectif et sa version exacte d'avant publication n'est pas garantie. Les dates futures réelles de publication ne sont jamais utilisées pour anticiper : aucune archive ne prouve ici quand elles étaient annoncées. Le substitut de calendrier est exclusivement la dernière publication connue plus 91 jours calendaires; il ne prétend pas connaître la prochaine date réelle.

## Recherche figée et comparaison principale

Le plan dans design.json fixe les 15 règles avant les rendements. Les paramètres ne sont pas balayés : fenêtres de 5 séances pour posts/news, seuil négatif -0.10, quantile à 90 % sur les 252 valeurs antérieures avec 126 observations minimum, part de sujets extérieurs à Tesla > 75 %, tendance moyenne de 200 clôtures. Les règles de news attendent 126 observations depuis le début effectif de couverture. Une moyenne de sentiment porte sur les seuls messages classés. Aucun modèle ML n'est entraîné si les règles simples ne justifient pas une poursuite. Toutes les fonctions passent lab.check_no_lookahead sur cinq troncatures et leurs données externes sont coupées à chaque troncature. Le dernier rendement finit à l'ouverture du 31/12/2024 : le moteur ne consomme pas l'ouverture du 02/01/2025 pour compléter la dernière séance.

Le contrôle moitié TSLA sert à voir si un risque moindre vient seulement d'une exposition moindre. Le contrôle tendance isole l'apport social des deux hybrides. Ils sont inclus dans la correction multiple. Les p corrigées ci-dessous concernent l'excès de log-rendement face au buy and hold, avec lab.romano_wolf sur les 45 essais ensemble, 4 000 tirages et blocs moyens de 21 séances. Les sensibilités de coûts et de liquidités sont donc aussi incluses. Il ne s'agit pas de p corrigées de l'alpha ou du Sharpe : leurs intervalles appariés, avec bêta réajusté pour l'alpha, sont dans metrics.csv. Aucun test d'alpha à bêta figé ne fonde la sélection.

### 5 pb par côté, liquidités à 0 %

| Règle | Capital USD | CAGR | Sharpe | Drawdown | Alpha/an | p corrigée |
| --- | --- | --- | --- | --- | --- | --- |
| BUY_HOLD_TSLA | 203,541 | 53.95 % | 0.977 | -74.97 % | 0.00 % | 1.000 |
| earnings_positive_20 | 26,772 | 15.14 % | 0.586 | -43.86 % | 3.39 % | 1.000 |
| earnings_negative_exit_10 | 214,457 | 55.10 % | 0.994 | -74.97 % | 2.28 % | 0.952 |
| earnings_exit_3 | 58,634 | 28.82 % | 0.715 | -75.15 % | -14.09 % | 1.000 |
| earnings_proxy_drift_10 | 7,728 | -3.62 % | -0.070 | -40.20 % | -8.00 % | 1.000 |
| earnings_proxy_exit_3 | 224,672 | 56.14 % | 1.010 | -73.24 % | 4.17 % | 0.942 |
| musk_activity_exit_5 | 87,001 | 36.31 % | 0.822 | -61.28 % | -1.50 % | 1.000 |
| musk_other_exit_5 | 203,541 | 53.95 % | 0.977 | -74.97 % | 0.00 % | 1.000 |
| musk_finbert_exit_5 | 189,450 | 52.38 % | 0.973 | -71.93 % | 1.90 % | 1.000 |
| musk_jev_exit_5 | 271,238 | 60.41 % | 1.047 | -73.88 % | 5.94 % | 0.766 |
| news_activity_exit_5 | 62,919 | 30.13 % | 0.737 | -75.72 % | -8.52 % | 1.000 |
| news_finbert_exit_5 | 327,218 | 64.78 % | 1.108 | -59.07 % | 11.96 % | 0.771 |
| hybrid_musk_trend_200 | 69,566 | 32.01 % | 0.784 | -60.34 % | 0.22 % | 1.000 |
| hybrid_news_trend_200 | 94,400 | 37.91 % | 0.879 | -58.28 % | 6.56 % | 1.000 |
| control_trend_200 | 69,566 | 32.01 % | 0.784 | -60.34 % | 0.22 % | 1.000 |
| control_half_tsla | 65,884 | 30.99 % | 0.975 | -46.31 % | -0.09 % | 1.000 |

### 10 pb par côté, liquidités à 0 %

| Règle | Capital USD | CAGR | Sharpe | Drawdown | Alpha/an | p corrigée |
| --- | --- | --- | --- | --- | --- | --- |
| BUY_HOLD_TSLA | 203,338 | 53.93 % | 0.977 | -74.97 % | 0.00 % | 1.000 |
| earnings_positive_20 | 26,320 | 14.86 % | 0.579 | -44.24 % | 3.16 % | 1.000 |
| earnings_negative_exit_10 | 212,322 | 54.88 % | 0.992 | -74.97 % | 2.15 % | 0.952 |
| earnings_exit_3 | 56,957 | 28.29 % | 0.708 | -75.25 % | -14.49 % | 1.000 |
| earnings_proxy_drift_10 | 7,515 | -4.01 % | -0.089 | -40.64 % | -8.39 % | 1.000 |
| earnings_proxy_exit_3 | 219,780 | 55.65 % | 1.005 | -73.29 % | 3.87 % | 0.952 |
| musk_activity_exit_5 | 80,227 | 34.74 % | 0.802 | -61.32 % | -2.65 % | 1.000 |
| musk_other_exit_5 | 203,338 | 53.93 % | 0.977 | -74.97 % | 0.00 % | 1.000 |
| musk_finbert_exit_5 | 180,024 | 51.27 % | 0.962 | -72.21 % | 1.17 % | 1.000 |
| musk_jev_exit_5 | 264,007 | 59.79 % | 1.041 | -74.11 % | 5.57 % | 0.801 |
| news_activity_exit_5 | 59,490 | 29.09 % | 0.724 | -76.25 % | -9.31 % | 1.000 |
| news_finbert_exit_5 | 307,225 | 63.30 % | 1.093 | -59.40 % | 11.07 % | 0.801 |
| hybrid_musk_trend_200 | 66,970 | 31.30 % | 0.774 | -60.89 % | -0.32 % | 1.000 |
| hybrid_news_trend_200 | 89,614 | 36.89 % | 0.864 | -58.95 % | 5.82 % | 1.000 |
| control_trend_200 | 66,970 | 31.30 % | 0.774 | -60.89 % | -0.32 % | 1.000 |
| control_half_tsla | 65,418 | 30.86 % | 0.971 | -46.38 % | -0.19 % | 1.000 |

### Sensibilité : rendement des liquidités approché par BIL

BIL est un fonds de bons du Trésor à court terme. Cette sensibilité crédite son rendement aux liquidités sans frais supplémentaires de rotation du fonds; c'est une approximation favorable aux stratégies souvent hors marché. Le benchmark reste TSLA conservée avec 5 pb par côté. Tous les essais de cette sensibilité sont journalisés.

| Règle | Capital USD | CAGR | Sharpe | Drawdown | Alpha/an | p corrigée |
| --- | --- | --- | --- | --- | --- | --- |
| earnings_positive_20 | 30,591 | 17.36 % | 0.644 | -41.52 % | 5.32 % | 1.000 |
| earnings_negative_exit_10 | 216,864 | 55.35 % | 0.997 | -74.97 % | 2.44 % | 0.949 |
| earnings_exit_3 | 58,916 | 28.91 % | 0.716 | -75.14 % | -14.02 % | 1.000 |
| earnings_proxy_drift_10 | 8,875 | -1.69 % | 0.024 | -35.62 % | -6.01 % | 1.000 |
| earnings_proxy_exit_3 | 226,038 | 56.28 % | 1.012 | -73.22 % | 4.26 % | 0.940 |
| musk_activity_exit_5 | 91,352 | 37.26 % | 0.834 | -61.28 % | -0.79 % | 1.000 |
| musk_other_exit_5 | 203,541 | 53.95 % | 0.977 | -74.97 % | 0.00 % | 1.000 |
| musk_finbert_exit_5 | 191,720 | 52.64 % | 0.976 | -71.89 % | 2.07 % | 1.000 |
| musk_jev_exit_5 | 272,329 | 60.50 % | 1.048 | -73.86 % | 6.00 % | 0.762 |
| news_activity_exit_5 | 63,572 | 30.32 % | 0.740 | -75.70 % | -8.37 % | 1.000 |
| news_finbert_exit_5 | 333,597 | 65.23 % | 1.112 | -58.96 % | 12.24 % | 0.758 |
| hybrid_musk_trend_200 | 75,539 | 33.58 % | 0.807 | -59.89 % | 1.40 % | 1.000 |
| hybrid_news_trend_200 | 103,061 | 39.66 % | 0.903 | -55.78 % | 7.82 % | 1.000 |
| control_trend_200 | 75,539 | 33.58 % | 0.807 | -59.89 % | 1.40 % | 1.000 |
| control_half_tsla | 71,131 | 32.43 % | 1.008 | -45.94 % | 1.01 % | 1.000 |

## Stabilité, échecs et limites

| Règle | Excès log 2018-2021 | Excès log 2022-2024 | Années positives /7 | Exposition |
| --- | --- | --- | --- | --- |
| news_finbert_exit_5 | 0.242 | 0.233 | 4 | 89.09 % |
| musk_jev_exit_5 | -0.111 | 0.398 | 4 | 96.70 % |
| earnings_proxy_exit_3 | -0.089 | 0.188 | 3 | 96.25 % |
| earnings_negative_exit_10 | 0.094 | -0.042 | 2 | 94.89 % |
| musk_other_exit_5 | 0.000 | 0.000 | 0 | 100.00 % |
| musk_finbert_exit_5 | 0.177 | -0.249 | 3 | 93.01 % |
| hybrid_news_trend_200 | -0.578 | -0.191 | 3 | 54.20 % |
| musk_activity_exit_5 | -1.051 | 0.201 | 1 | 77.22 % |
| control_trend_200 | -0.883 | -0.191 | 2 | 57.33 % |
| hybrid_musk_trend_200 | -0.883 | -0.191 | 2 | 57.33 % |
| control_half_tsla | -1.228 | 0.100 | 2 | 50.00 % |
| news_activity_exit_5 | -1.187 | 0.013 | 3 | 84.94 % |
| earnings_exit_3 | -0.965 | -0.280 | 0 | 95.23 % |
| earnings_positive_20 | -1.799 | -0.230 | 2 | 19.32 % |
| earnings_proxy_drift_10 | -2.753 | -0.518 | 2 | 9.03 % |

Les excès par sous-période sont des sommes de log-rendements, pas des pourcentages simples. 2022-2024 était déjà explorée dans le projet : ce découpage décrit la stabilité chronologique mais ne constitue pas une validation finale vierge. Les années sont découpées dans le portefeuille continu; elles ne simulent pas un nouvel achat indépendant au 1er janvier.

Les fenêtres avant une date approximative peuvent rater la publication réelle. Les règles après résultat manquent volontairement la réaction immédiate et peuvent sortir après la baisse. Les filtres d'activité confondent sujet et régime de marché : un pic ne dit pas si le titre montera ou baissera. Les scores financiers sont peu adaptés à l'ironie et à la politique; la règle lexicale de sujets reste grossière. Le sentiment des news peut résumer une variation déjà réalisée. Les stratégies en liquidités évitent certaines baisses mais ratent aussi les fortes hausses de TSLA, qui sont concentrées dans quelques périodes. Les frais sont hypothétiques : 5 pb = 0.05 % par montant acheté ou vendu, 10 pb double ce taux. Les sorties et entrées restent largement moins fréquentes que les essais intraday abandonnés.

Le seuil fixé de 75 % de posts explicitement liés à Twitter ou à la politique hors Tesla ne s'active jamais dans le développement. L'essai musk_other_exit_5 reproduit donc le buy and hold, et hybrid_musk_trend_200 reproduit le contrôle de tendance. Ces doublons sont conservés dans le journal et la correction. Ce résultat montre l'inadéquation de ce détecteur lexical à ce seuil, sans réfuter un éventuel effet des sujets extérieurs à Tesla. Aucun seuil n'est ensuite assoupli pour chercher un gain.

Les deux critères du protocole restent distincts. À 5 pb, 4 règle(s) ont un capital supérieur à TSLA; 4 ont simultanément un Sharpe supérieur et un alpha positif au niveau des estimations ponctuelles : news_finbert_exit_5, musk_jev_exit_5, earnings_proxy_exit_3, earnings_negative_exit_10. La baisse maximale est aussi publiée pour chaque règle. Réduire la perte maximale en gagnant moins ne satisfait pas le premier critère. Les intervalles de Sharpe et d'alpha dans metrics.csv indiquent leur incertitude; aucune p corrigée sur ces deux mesures ne fonde ici une revendication de supériorité ajustée au risque. La sélection volontairement stricte exige une preuve de développement sur le capital avant de consommer la validation.

Les données rétrospectives peuvent être corrigées après les faits. La date d'apprentissage des classifieurs n'est pas auditée : une contamination temporelle reste possible. Aucun rendement futur des likes, du consensus révisé ou de nouvelles versions de titres ne doit être interprété comme une information historique certaine. Les résultats de TSLA, gagnante connue choisie pour le projet, ne se généralisent pas à un univers d'actions. Les drawdowns aux ouvertures sous-estiment potentiellement les pertes intrajournalières. Fiscalité, change EUR/USD, prix bid/ask et impact de marché ne sont pas simulés. La comptabilité est en USD, pas un placement réel de 10 000 EUR.

## Préinscription et reproduction

La préinscription est vide : aucune règle n'a franchi les critères fixés. Il est préférable de conserver ce résultat négatif de développement que d'ouvrir la validation pour chercher un gagnant.

Les données nécessaires après 2024 sont décrites dans holdout_data_needed : posts complets avec identifiants exacts, titres Benzinga et historique de versions, résultats avec consensus daté, prix et calendrier. Aucune collecte de cette période n'est faite ici. La couverture sociale déjà annoncée jusqu'à mai 2025 serait trop courte pour une conclusion forte, même si elle était ouverte.

Reproduction : `venv/bin/python reports/run_social_lab.py`. Sans cache, cette commande effectue FinBERT sur CPU à partir des poids déjà présents localement; elle n'utilise pas le réseau. Les relances remplacent les mêmes noms d'essai, sans doubler leur compte. Vérification obligatoire : `venv/bin/python -m unittest tests.test_lab tests.test_social_lab`. Les preuves sont dans tests_output.txt, completion.json, corrected_pvalues.csv, metrics.csv et le journal ../ledger_codex.csv.
