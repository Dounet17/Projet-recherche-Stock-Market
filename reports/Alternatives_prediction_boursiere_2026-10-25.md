# Modèles récents pour la prévision boursière — recherche du 25 octobre 2026

Mise à jour expérimentale : l’environnement ROCm 6.2.4 / PyTorch 2.6 détecte une Radeon RX 6750 XT de 12 Go. TimesFM-3, Chronos-2 et Kronos fonctionnent sur ce GPU ; KiT a également produit des prévisions valides en FP32 et FP16 avec ROCm, malgré son installation documentée orientée CUDA. Les remarques matérielles ci-dessous décrivent la documentation consultée avant ces essais, et non une incompatibilité constatée.

Les essais sont désormais terminés : [résultats, courbes et protocole](Resultats_modeles_preentraines_2026-10-25.md). La présente revue conserve les recommandations formulées avant les expériences.

**Recommandation : comparer d’abord Chronos-2-Synth, TimesFM-3 et Kronos-small.** Ces modèles apportent une autre famille de prévision que la régression logistique du premier backtest. Chronos permet aussi une comparaison avec/sans variables sociales. KiT constitue une piste de recherche particulièrement récente, avec une contrainte matérielle plus forte.

Cette recherche a vérifié les publications, dépôts des auteurs et fiches officielles de modèles. Elle n’a installé ni exécuté ces modèles et ne leur attribue donc aucun résultat sur nos données Tesla. La sélection est ciblée sur notre projet ; elle ne constitue pas une revue systématique exhaustive.

**Le modèle Google aperçu sur TikTok**

Le candidat le plus probable est **TimesFM**, sans pouvoir identifier avec certitude une vidéo non fournie. Google Research a présenté **TimesFM-3 le 31 août 2026**, puis Google Cloud a annoncé sa préversion dans BigQuery le **12 octobre 2026**. La version 2.5 avait été publiée en septembre 2025. [Annonce Google Research](https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/), [annonce BigQuery](https://cloud.google.com/blog/products/data-analytics/bigquery-timesfm-3-0-with-multivariate-time-series-forecasting/).

TimesFM-3 est un modèle préentraîné de 330 millions de paramètres : il peut prévoir plusieurs séries liées et prendre des variables externes historiques en entrée, avec des prévisions ponctuelles et des quantiles représentant l’incertitude. Pour nous, cela ouvre une comparaison TSLA seul, TSLA avec QQQ, puis ces prix avec des signaux sociaux numériques. Il ne lit pas directement les tweets bruts. Les classements annoncés par Google portent sur des benchmarks généraux, sans démontrer un rendement net sur Tesla à 15 minutes. [Présentation technique de Google](https://research.google/blog/timesfm-3-a-zero-shot-foundation-model-for-multivariate-forecasting/).

Le code et les poids sont disponibles. Les poids 3.0 téléchargés ont une licence réservée aux usages non commerciaux et hors production ; le code et les poids jusqu’à 2.5 sont Apache-2.0. Ces conditions distinguent une expérimentation de recherche locale d’un déploiement commercial. [Dépôt officiel et notice des licences](https://github.com/google-research/timesfm), [fiche des poids 3.0](https://huggingface.co/google/timesfm-3.0-pytorch).

**Ce que le premier backtest a réellement évalué**

Dans `src/backtest.py`, le prédicteur est une **régression logistique**. FinBERT et Jev fournissent des variables extraites des tweets ; ce ne sont pas eux qui modélisent toute la dynamique des prix. Les résultats proches de 50 % concernent cette combinaison, ce jeu de variables et un horizon de 15 minutes.

Un taux de réussite proche de 50 % n’établit pas à lui seul qu’une stratégie est identique au hasard : l’amplitude des gains et pertes, le déséquilibre entre classes, la fréquence des décisions et les frais comptent aussi. Ici, les pertes du portefeuille et l’incertitude sur la différence entre variantes ne montrent pas d’avantage social établi. Il reste pertinent de comparer d’autres représentations et d’autres modèles.

Autre limite locale : des scores sociaux sont présents dans seulement **745 des 18 000 intervalles**, soit 4,14 %. Un effet limité aux périodes proches des tweets peut être peu visible dans une précision globale. Une future comparaison doit publier les résultats globaux et ceux de ce sous-ensemble, défini à l’avance.

**Candidats réellement disponibles**

| Candidat | Apport concret | Disponibilité vérifiée | Intérêt pour Musk / Tesla |
|---|---|---|---|
| **TimesFM-3 — Google** | Prévision multivariée et variables externes | Code et poids publics ; 330 M de paramètres | Comparaison entre prix seuls et prix enrichis ; candidat probablement lié à la vidéo. [Poids](https://huggingface.co/google/timesfm-3.0-pytorch) |
| **Chronos-2 / Synth — Amazon et AutoGluon** | Prévision probabiliste avec séries et variables externes ; variante synthétique | Poids publics ; modèle principal 120 M, variante small 28 M | Premier choix pour une comparaison sociale et pour limiter la mémorisation des cours au préentraînement. [Modèle principal](https://huggingface.co/amazon/chronos-2), [Synth](https://huggingface.co/autogluon/chronos-2-synth), [Small](https://huggingface.co/autogluon/chronos-2-small) |
| **Kronos-small** | Modèle spécifiquement conçu pour les chandeliers financiers : ouverture, plus haut, plus bas, clôture, volume | Code et poids ; small 24,7 M, base 102,3 M, mini 4,1 M | Exploite directement les barres déjà collectées ; bonne référence financière pour juger les modèles généralistes. [Dépôt officiel](https://github.com/shiyu-coder/Kronos) |
| **KiT — septembre 2026** | Génère plusieurs trajectoires financières possibles avec une architecture de diffusion / flow matching | Dépôt et checkpoints publiés | Très récent et adapté aux trajectoires OHLCV ; documentation d’installation orientée CUDA. [Article](https://arxiv.org/abs/2609.34507), [code](https://github.com/Luciferbobo/KiT) |
| **FinCast — CIKM 2025** | Préentraînement spécialisé finance, experts multiples et quantiles | Code et poids publiés | Alternative financière pour un second lot d’expériences ; intégration moins documentée pour les variables sociales. [Article](https://arxiv.org/abs/2508.19609), [code](https://github.com/vincent05r/FinCast-fts), [poids](https://huggingface.co/Vincent05R/FinCast) |
| **TiRex-2 — 2026** | Prévision multivariée par architecture récurrente, avec variables externes | Code, poids et exemple CPU ; Apache-2.0 | Autre famille d’architecture pour éviter de ne comparer que des Transformers. [Dépôt des auteurs](https://github.com/NX-AI/tirex-2) |

**Pourquoi Chronos-2-Synth est particulièrement intéressant**

La fiche officielle indique un entraînement uniquement sur des séries synthétiques, univariées et multivariées. Cela réduit le risque d’avoir vu les vrais cours de TSLA de 2018–2024 au préentraînement. Cela n’élimine pas la sélection de modèles a posteriori, les erreurs d’alignement ni la contamination des scores produits par un classifieur de texte plus récent. [Fiche Chronos-2-Synth](https://huggingface.co/autogluon/chronos-2-synth).

La famille Chronos-2 accepte des variables historiques réelles ou catégorielles et fournit des quantiles. L’inférence CPU est documentée : elle offre une voie locale sans dépendre du support ROCm de la carte AMD. La vitesse réelle sur cette machine reste à mesurer. [Fiche technique Chronos-2](https://huggingface.co/amazon/chronos-2).

**Ce qui rend Kronos et KiT différents**

Kronos a été préentraîné sur des séquences de chandeliers financiers provenant de nombreux marchés. Les auteurs rapportent notamment une amélioration relative du RankIC dans leurs benchmarks. **Une amélioration de RankIC n’est pas un taux de réussite de 93 %** : il s’agit d’une mesure de classement/corrélation, obtenue dans un autre protocole que notre backtest. Son article et les modèles publics permettent une expérience reproductible, mais il faut vérifier le chevauchement du corpus de préentraînement avec TSLA. [Article Kronos](https://arxiv.org/abs/2508.02739).

KiT reformule la prévision comme génération de trajectoires OHLCV conditionnelles au passé. Son article du 28 septembre 2026 rapporte un RankIC moyen d’environ 0,057 pour les rendements et 0,66 pour la volatilité, dans son propre protocole. Ces deux valeurs correspondent à des tâches différentes, pas à des probabilités de gagner. La publication est une prépublication récente ; une réplication indépendante sur Tesla reste nécessaire. [Article KiT](https://arxiv.org/abs/2609.34507).

Le dépôt de KiT propose des poids et demande un GPU CUDA pour l’inférence, avec au moins 6 Go de VRAM recommandés. La machine décrite dans `CLAUDE.md` possède une Radeon RX 6700 XT : il ne faut pas supposer que ce chemin NVIDIA fonctionne tel quel. C’est une raison pratique de le placer après les premiers modèles, pas une conclusion sur sa qualité prédictive. [Installation et checkpoints KiT](https://github.com/Luciferbobo/KiT).

**Ce que montrent les évaluations financières récentes**

Une prépublication de juin 2026 compare TimesFM-2.5, Moirai-2.0, Chronos et Chronos-2 à plusieurs réseaux entraînés localement sur les rendements journaliers de cinq actions américaines. Les modèles préentraînés occupent souvent les premières places, mais leurs gains par rapport aux références naïves sont faibles et rarement significatifs. Ce résultat concerne les rendements journaliers, cinq actifs et des versions précises ; il ne teste ni TimesFM-3 ni notre configuration intraday. [Étude comparative de juin 2026](https://arxiv.org/abs/2606.27100).

FinVerse, prépublication d’août 2026, compare **43 modèles publics** et sépare erreur de prévision, classement des actifs et évaluation de portefeuille. Reverso Small arrive en tête de leur classement global, Chronos-2 Synth dans leur volet portefeuille, et TiRex 1.1 dans leur volet ponctuel. Ce désaccord entre classements est utile : le meilleur modèle dépend de l’objectif mesuré. Ces scores agrégés ne démontrent pas un rendement réalisable sur TSLA. [FinVerse, résultats et limites](https://arxiv.org/html/2608.03259v2).

Une prépublication de mai 2026 sur Chronos-2 rapporte des améliorations lorsque des séries financières liées sont modélisées ensemble. Le mélange de séries moins pertinentes peut au contraire dégrader les prévisions. Cela motive notre comparaison TSLA seul / TSLA avec QQQ, tout en évitant d’ajouter indistinctement toutes les variables disponibles. Les métriques de cette étude sont des erreurs de prévision, pas une validation de trading après frais. [Étude multivariée Chronos-2](https://arxiv.org/abs/2605.21504).

Pour l’aspect texte + prix, **XForecast**, présenté dans le cadre du KDD Finance Day 2026, est une référence récente : cours et textes financiers associés, 100 grandes capitalisations, apprentissage 2019–2022 et évaluation 2023, horizon de quatre semaines. C’est un benchmark de fusion multimodale, avec un horizon et des sources textuelles différents de nos tweets à la minute ; il ne fournit pas une stratégie Musk prête à l’emploi. [Article du 12 octobre 2026](https://arxiv.org/abs/2610.16131), [site des organisateurs](https://xforecast.github.io/).

**La piste innovante la plus adaptée au projet**

Ma proposition est de comparer un **modèle temporel probabiliste avec et sans contexte social**, en séparant trois éléments : qualité de la prévision, effet des publications et règle de trading.

Les scores positif/négatif actuels peuvent rester une référence, puis être complétés par des catégories d’événements : annonce produit, prix des véhicules, production/livraisons, financement, vente d’actions, réglementation, affirmation technique ou réponse sans information nouvelle. Ce sont des variables à construire et valider, pas une fonctionnalité déjà testée ici. L’objectif est de conserver l’information économique du message plutôt que de tout résumer à un sentiment moyen.

Les modèles TimesFM-3 et Chronos-2 peuvent recevoir des variables numériques historiques. Pour Kronos, KiT ou FinCast, je ne suppose pas une prise en charge native des tweets : leur intégration sociale devra passer par un mécanisme séparé, documenté et comparé à la même prévision sans texte. Les futurs tweets, les futurs scores et les futurs prix QQQ restent toujours inconnus à la décision.

Une seconde piste est de prédire **l’amplitude ou la volatilité** de la réaction, en plus de sa direction. Même si le sens est difficile à anticiper, un modèle peut éventuellement aider à ajuster l’exposition ou rester en liquidités pendant une période risquée. Les résultats de volatilité de KiT motivent ce test, sans garantir un effet sur le portefeuille. Ce serait une question de recherche distincte, avec ses propres références simples.

**Prochain benchmark proposé, sans sélection des paramètres sur les années déjà testées**

1. Conserver le premier backtest comme référence historique et publier clairement qu’il a déjà été examiné. Ajouter une référence de prix constant, de rendement nul et la stratégie passive. Comparer aussi un modèle non linéaire local simple pour mesurer l’apport du préentraînement.
2. Premier lot limité : Chronos-2-Synth, Chronos-2, TimesFM-3 et Kronos-small. Commencer sur des prévisions à 15 minutes pour garder un point commun avec le test existant ; fixer séparément une extension à 60 minutes et à un jour. Les résultats par horizon restent tous publiés.
3. Comparer les mêmes variantes d’entrée : TSLA seul ; TSLA + QQQ ; puis prix + scores sociaux pour les modèles compatibles. Ajouter des variables de type d’événement seulement dans un lot distinct, pour attribuer les gains à une modification précise.
4. Mesurer les rendements futurs et l’incertitude, pas seulement la proximité entre une courbe de prix prévue et la courbe réelle. Une prévision « le prochain prix égale le dernier » peut tracer une courbe visuellement convaincante tout en étant inutile pour gagner de l’argent.
5. Évaluer précision, amplitude des erreurs, calibration des quantiles et portefeuille net avec le même délai, les mêmes coûts et les mêmes contraintes. Une règle d’abstention doit être calibrée sur une validation chronologique, avec une marge suffisante sur les coûts ; un quantile brut n’est pas automatiquement une probabilité fiable.
6. Afficher séparément les périodes proches des publications et le reste. Garder des décisions fixes pour la comparaison principale afin que la référence « sans social » n’utilise pas indirectement les heures des tweets.
7. Auditer les données de préentraînement et figer les révisions. Les tests 2018–2024 des modèles sortis ensuite restent rétrospectifs si ces cours figuraient dans leurs corpus. Pour une validation plus forte, utiliser des observations non examinées et postérieures à une borne de préentraînement vérifiée, ou une collecte prospective avec modèle figé. La variante synthétique réduit un risque de chevauchement, sans transformer les anciennes années déjà explorées en test vierge.

Ce plan apporte des alternatives existantes et une hypothèse scientifique plus précise : déterminer si un modèle temporel préentraîné exploite mieux les prix et si le contexte social améliore sa prévision ou son contrôle du risque. À la date de ce document, aucune performance locale de ces nouveaux modèles n’a encore été mesurée.
