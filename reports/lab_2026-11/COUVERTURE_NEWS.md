# Couverture des news Alpaca (Benzinga) sur l'univers, 2018-2024

Rapport du 07/11/2026. **Mesure seule : aucun rendement n'a été lu, aucune stratégie testée, le journal n'est pas touché.**

```bash
venv/bin/python reports/measure_news_coverage.py   # 27 minutes pour cet échantillon
venv/bin/python -I reports/analyze_news_coverage.py
```

Détail : `news/` et `data/news_coverage/` (non versionné).

## Mise à jour : téléchargement complet

Le téléchargement complet du 07/11/2026 (`data/news/`, `reports/download_all_news.py`) **remplace les estimations ci-dessous** sur ces points. Aucun rendement n'a été lu.

| Mesure | Estimé ci-dessous | Compte complet |
|---|---:|---:|
| Articles uniques, 2018-2024 | environ 1,36 million | 1 399 118 |
| Un seul symbole cité | 52 % | 80 % |
| Avec un résumé | 43 % | 30 % |

- **Complétude.** 99,89 % des 144 627 articles de l'échantillon s'y retrouvent. Il en manque 165, sans explication établie.
- **Contrôles.** Aucun doublon, aucune ligne illisible, aucune date après 2024, tous les articles sont dans le fichier de leur mois, un seul sans titre.
- **Résumés.** Aucun en 2018-2019, puis 16 % en 2020 et de 36 à 45 % ensuite. Une étude sur toute la période doit donc se limiter aux titres.
- **Source.** Le champ est vide jusqu'à fin 2021, mais toutes les adresses pointent vers Benzinga.
- **Écart sur les symboles.** La cause n'est pas établie. Une recherche par symbole favorise peut-être les articles qui en citent plusieurs : 42 % des citations de symboles viennent d'articles à un seul symbole, ce qui s'en rapproche sans le démontrer. Le piège 2 ci-dessous pèse donc moins que prévu.

## Méthode

Échantillon figé avant téléchargement (graine 20261107) : 30 titres par strate, soit 240 titres, 4 tranches de liquidité croisées avec vivants ou disparus. On cherche le symbole et ses anciens noms, et on garde les articles parus pendant la vie du titre. Les moyennes sur l'univers sont repondérées par la taille réelle des strates. S'y ajoutent 2 semaines de tout le marché par an pour estimer le volume.

## Résultats

| Liquidité | Statut | Au moins 1 article | Au moins 12 par an | Articles par an, médiane | Semaines avec une news, médiane |
|---|---|---:|---:|---:|---:|
| 500 premiers | Vivants | 100 % | 100 % | 156 | 74 % |
| 500 premiers | Disparus | 100 % | 97 % | 138 | 63 % |
| 501 à 1 000 | Vivants | 100 % | 100 % | 84 | 50 % |
| 501 à 1 000 | Disparus | 100 % | 93 % | 68 | 48 % |
| 1 001 à 3 000 | Vivants | 97 % | 97 % | 45 | 35 % |
| 1 001 à 3 000 | Disparus | 100 % | 100 % | 43 | 36 % |
| Reste | Vivants | 100 % | 87 % | 38 | 29 % |
| Reste | Disparus | 97 % | 87 % | 28 | 24 % |

**Sur tout l'univers (estimation) :** 99 % des titres ont au moins un article, 91 % au moins 12 par an, soit 59 articles par an en moyenne. Pour les disparus, 98 % et 90 %, soit 45 articles par an. **Contrairement aux bénéfices SEC, les news couvrent bien les sociétés disparues.**

**Autour des résultats :** de 89 % à 97 % des publications ont une news dans les jours autour (2 850 publications), et de 87 % à 94 % le jour même.

**Volume :** environ **1,36 million d'articles** sur 2018-2024, soit environ 2,3 heures de téléchargement. Le rythme va de 2 300 à 5 700 articles par semaine. 96 % citent au moins un symbole et 89 % des symboles cités sont dans nos titres.

## Qualité, ce qui limite l'usage

| Mesure sur 96 061 articles uniques | Valeur |
|---|---:|
| Un seul symbole cité | 52 % |
| Trois symboles ou moins | 65 % |
| Avec un résumé (le reste : titre seul) | 43 % |
| Publiés pendant la séance | 45 % |
| Avant l'ouverture | 38 % |
| Après la clôture | 12 % |
| Modifiés plus d'une heure après leur création | 1,4 % |
| Modifiés plus d'un jour après | 0,3 % |
| Secondes égales à 0 (heure arrondie, indice faible) | 1,7 % |

Types de titres, par mots-clés approximatifs : résultats 15 %, analystes 18 %, **commentaires de marché 14 %**, autres 52 %.

## Pièges pour la suite

1. **Causalité inversée.** « 12 Stocks Moving In Tuesday's Session » décrit un mouvement déjà fait. Ces articles ne prédisent rien et peuvent créer un faux effet : à exclure avant toute étude.
2. **Articles multi-symboles.** Près de la moitié citent plusieurs titres : un même sentiment attribué à tous serait du bruit.
3. **Doublons d'information.** Une news de résultats répète ce que mesure déjà l'étude des résultats. Elle n'est pas un signal indépendant.
4. **Vitesse.** Les prix sont quotidiens sur l'univers : on ne peut tester que ce qui reste à partir de l'ouverture suivante. La fenêtre de quelques minutes ne se teste que sur les titres disposant de barres à la minute.
5. **Fuite du classifieur.** Vérifier la date d'entraînement de FinBERT et de tout autre modèle avant usage.

## Limites

- 30 titres par strate : une part de 87 % a une marge d'environ ±12 points. Ce sont des ordres de grandeur.
- Le classement par liquidité utilise toute la période : acceptable pour décrire, pas pour un signal.
- L'heure `created_at` n'a pas été confrontée à une source extérieure.
- L'API filtre sur la mise à jour : un article modifié après fin 2024 est absent. Vu le taux de modification, l'effet devrait être faible, sans être mesuré.
- Le volume repose sur 14 semaines et varie selon l'année : à ±30 % environ, estimation à la louche.
- Un symbole réutilisé peut encore attirer des articles d'une autre société pendant la vie du titre.
- Conditions d'utilisation des données Benzinga à relire avant toute diffusion.
