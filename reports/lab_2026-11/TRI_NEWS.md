# Tri des news et lecture par FinBERT

Rapport du 07/11/2026, 2018-2024. **Aucun rendement n'a été lu, aucune stratégie testée, le journal n'est pas touché.** Ce travail n'a pas reçu d'audit indépendant.

```bash
venv/bin/python tests/test_news_filter.py
venv/bin/python reports/build_news_table.py        # moins d'une minute
HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_news_finbert.py   # 17 minutes sur le GPU, reprise possible
venv/bin/python reports/analyze_news_finbert.py
```

Code : `src/news_filter.py`. Tables, non versionnées : `data/news/news_articles.parquet`, `news_links.parquet`, `news_scored.parquet`. Bilans : `news/filter_summary.json`, `news/finbert_check.json`, `news/filter_sample_to_review.csv`.

## Le tri

Chaque titre reçoit une catégorie par des règles fixes, sans regarder les cours. Vocabulaire : un **commentaire de marché** décrit un mouvement déjà fait, c'est donc le cours qui cause l'article ; à l'inverse, on cherche des articles qui pourraient causer le mouvement.

| Catégorie | Articles | Part | Usage |
|---|---:|---:|---|
| Commentaires de marché | 131 566 | 9 % | Écartés |
| Remplissage (« If You Invested... », aperçus) | 127 380 | 9 % | Écartés |
| Résultats publiés | 149 269 | 11 % | Gardés |
| Prévisions de la société | 57 566 | 4 % | Gardés |
| Notes d'analystes | 310 042 | 22 % | Gardés |
| Faits sur une société | 623 295 | 45 % | Gardés |

**Il reste 962 776 articles liés à au moins une action, dont environ 856 000 à une seule.** Ils contiennent 930 946 titres différents.

**Lien avec les actions.** Chaque symbole cité est rapproché du titre actif à la date de l'article, car un symbole peut changer de société. 94 % des 2,68 millions de citations sont reconnues ; 86 % des articles citent une action ordinaire ou un ADR.

### Fiabilité des règles

Les règles ont été écrites après lecture d'un premier tirage, puis contrôlées à la main sur un **second tirage figé** (graine 20261108), et plus modifiées ensuite. Jugement d'une seule personne sur de petits échantillons : ce sont des ordres de grandeur.

| Catégorie | Titres relus | Mal placés |
|---|---:|---:|
| Commentaires de marché | 30 | 0 |
| Remplissage | 30 | 2 |
| Notes d'analystes | 30 | 0 |
| Résultats publiés | 60 | 1 ou 2 |
| Prévisions | 60 | environ 9 (15 %) |
| Faits sur une société, avec une action liée | environ 46 | environ 11 (24 %) |

Les faits sur une société restent donc la catégorie la plus bruitée : sport, analyses techniques, chroniques. Des commentaires y subsistent aussi (« Why Dogecoin Is Shooting Higher Today »). Le biais attendu est plutôt d'affaiblir un signal que d'en créer un, sauf pour ces commentaires, qui peuvent créer un faux effet. Une étude sur cette catégorie devra le vérifier.

## La vraie surprise de résultats

Beaucoup de titres donnent le chiffre publié et l'estimation des analystes : « Q2 Adj. EPS $1.46 Beats $1.38 Estimate ». Le signe de la surprise vient des chiffres, le verbe sert de contrôle.

- **76 036 titres avec un BPA et son estimation, 81 394 avec des ventes et leur estimation.**
- **Taux de dépassement : 68 %** du BPA (51 736 au-dessus, 24 179 en dessous, 121 égaux). De mémoire, c'est l'ordre de grandeur habituel pour les entreprises américaines, à vérifier avant de le citer.
- **Couverture : 63 % des 80 759 publications** ont une dépêche avec BPA et estimation, et 76 % une dépêche de résultats exploitable. De 71 à 83 % selon l'année pour cette dernière.
- **Vitesse : la dépêche sort à peu près avec le dépôt SEC.** Écart médian inférieur à une minute, 10 % des cas plus de 1,3 heure avant, 10 % plus de 0,7 heure après. 52 % des dépêches précèdent le dépôt.
- **76 contradictions** entre le verbe et les chiffres, soit très peu.

Ce champ pourrait lever le blocage de l'étude des résultats : notre BPA n'était jamais connu pour un achat le jour même, alors que celui-ci est horodaté à la seconde.

**À traiter avant usage.** Des chiffres de ventes ont des unités fausses (« Sales $10.730 Miss $10.317B Estimate », « $57.000M Beat $58.000K Estimate ») : il faudra écarter les rapports invraisemblables. Le BPA peut être ajusté ou comptable selon les titres, et il arrive qu'un titre annuel soit pris pour un résultat. L'estimation est celle que cite Benzinga, dont la source et la date ne sont pas connues.

## FinBERT

**Fuite d'information.** La fiche du modèle indique un affinage sur Financial PhraseBank (Malo et al., 2014) et un préentraînement sur une partie du corpus Reuters TRC2. La date de ce corpus n'y figure pas : de mémoire 2008-2010, à vérifier. L'article date d'août 2019. **Rien n'indique donc que le modèle ait vu les réactions du marché de 2018-2024.**

Le dépôt a reçu de nouveaux poids en octobre 2026. Nous avons figé la version du 23/05/2023 (`4556d130`) et vérifié que les deux jeux de poids sont strictement identiques.

**Choix.** Titres seuls, car il n'y a aucun résumé en 2018-2019. Longueur limitée à 64 jetons. 930 946 titres en 1 029 secondes sur la RX 6750 XT.

### Lit-il correctement ?

Contrôle sur les titres dont le verdict est écrit, sans aucun cours. L'AUC vaut 0,5 pour un classement au hasard et 1 pour un classement parfait.

| Verdict écrit | Titres | AUC | Bonne nouvelle lue positive | Mauvaise nouvelle lue négative | Mauvaise nouvelle lue positive |
|---|---:|---:|---:|---:|---:|
| Prévision relevée ou abaissée | 5 823 / 2 041 | **0,98** | 84 % | 90 % | 5 % |
| Analyste qui relève ou abaisse | 25 353 / 30 403 | **0,94** | 71 % | 61 % | 14 % |
| BPA au-dessus ou en dessous de l'estimation | 50 976 / 23 592 | **0,72** | 64 % | 52 % | **35 %** |

**FinBERT lit bien les mots (« raises », « cuts », « downgrades »), mais mal les titres chiffrés.** Il juge encore positif un BPA manqué sur trois. Pour les résultats, il vaut donc mieux utiliser la surprise chiffrée que le sentiment.

Ce contrôle mesure s'il comprend le titre. **Il ne dit rien de sa capacité à annoncer un rendement.**

**Répartition.** Sur l'ensemble, environ 43 % de positifs, 41 % de neutres et 16 % de négatifs, avec une part de négatifs de 12 à 21 % selon l'année. Ce déséquilibre ne prouve rien en soi, mais toute étude devra classer les scores au sein de chaque période.

## Limites

- **L'heure de l'article n'est pas forcément l'heure de la première diffusion du fait.** Une dépêche peut reprendre une information déjà sortie ailleurs.
- **Doublons d'information.** Plusieurs articles peuvent porter sur le même fait, et une news de résultats répète ce que mesure l'étude des résultats. Elle n'est pas un signal indépendant.
- **Modifications.** Le texte est celui d'aujourd'hui. Environ 1,4 % des articles de l'échantillon ont été modifiés plus d'une heure après leur création : le titre lu n'est pas forcément celui de l'époque.
- **Biais du survivant.** Les articles sont liés avec la liste de titres nettoyée, disparus compris, mais 6 % des citations restent sans titre.
- **Règles écrites après lecture.** Le premier tirage a servi à les écrire, sans aucun cours. Elles restent à relire par une autre personne.

## Suite proposée

1. **Étude de la vraie surprise.** Mêmes règles que l'étude des résultats, avec entrée après la dépêche, classement figé d'avance et correction sur tous les tests. C'est le test le plus direct de l'hypothèse « réagir vite ».
2. **Étude du sentiment** sur les faits et les prévisions, à l'ouverture suivant l'article.
3. **Audit indépendant** de ce tri et de la surprise avant toute conclusion.
