# Tri des news et lecture par FinBERT

Rapport du 07/11/2026, 2018-2024. **Aucun rendement n'a été lu, aucune stratégie testée, le journal n'est pas touché.** Version corrigée après deux audits indépendants de Codex (`news/AUDIT_TRI_NEWS.md`, `news/AUDIT_TRI_NEWS_2.md`). Les deux concluent qu'il ne fallait pas lancer l'étude en l'état. Les corrections du second audit n'ont pas été recontrôlées, et les chiffres publiés restent à vérifier sur les sources : voir « Ce qui bloque encore ».

```bash
venv/bin/python tests/test_news_filter.py
venv/bin/python reports/build_news_table.py        # environ 1 minute
HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_news_finbert.py   # 17 minutes au premier passage, reprise possible
venv/bin/python reports/analyze_news_finbert.py
```

Code : `src/news_filter.py`. Tables, non versionnées : `data/news/news_articles.parquet`, `news_links.parquet`, `news_scored.parquet`, `earnings_surprise.parquet`. Bilans : `news/filter_summary.json`, `news/finbert_check.json`.

## Ce que l'audit a changé

Le verdict de l'audit : ne pas lancer l'étude en l'état. Il a été rendu sans lire aucun rendement.

| Défaut trouvé | Mesure | Correction appliquée |
|---|---|---|
| Heure de disponibilité non établie | 0,93 % des articles modifiés plus d'une heure après leur création, aucun historique des versions | `available_at` = dernière date connue du titre, corrections écartées. **Borne prudente, pas une preuve** |
| Estimation d'origine inconnue | Disponibilité antérieure prouvée pour 0 publication sur 42 | Aucune correction possible : le signal s'appelle « écart à l'estimation citée » et n'est pas présenté comme un consensus vérifié |
| Mauvaise société | 101 citations de BBT attribuées à Berkshire Hills, dont 2 publications | Un alias n'est accepté que si le titre cite la société |
| Choix entre sociétés par liquidité | Liquidité moyenne connue seulement après coup | Sociétés différentes possibles : aucun lien |
| Prévisions lues comme résultats | 6 titres, « Reaffirms » et voisins non reconnus | Verbes de prévision étendus |
| Nombres mal lus | « 4,35 » lu 435, signe inversé sur 3 titres ; suffixe « B » sur un BPA | Virgule décimale reconnue, contrôles de vraisemblance |
| Résultat annuel pris pour trimestriel | 178 titres | Trimestre exigé |
| Commentaires restés dans les articles gardés | Environ 34 000, soit 3,5 % | Motifs ajoutés. Une partie subsiste forcément |
| Faits écartés à tort, sociétés prises pour des analystes | « Here's Why » ou « Need To Know » seuls, « Quoin Initiates Pediatric Study » | Règles resserrées |
| Dépêche choisie selon sa proximité avec le dépôt SEC | Le premier titre diffère du plus proche pour 776 événements | Première dépêche admissible |
| FinBERT jugé sur un contrôle trop facile | Un simple repérage de mots fait mieux que lui | Référence ajoutée et publiée ci-dessous |
| Mélange possible de versions du modèle | Défaut de garde-fou, pas d'incident | Manifeste, refus de mélanger, pas d'écrasement |

**D'où venait BBT.** La liste d'alias du nettoyage réunit des symboles aux séries de prix identiques. Comme Alpaca donne à un symbole l'historique de son détenteur actuel, BBT y figure pour Berkshire Hills, renommée Beacon Financial après 2024, alors qu'il désignait BB&T en 2019. **Les alias ne disent donc pas à quelle date un symbole était valable.** Le contrôle par le nom coûte 94 133 citations, souvent légitimes : c'est le prix d'éviter les fausses attributions.

**Ce qui reste invérifiable.** Le titre actuel existait-il à son heure ? L'estimation citée était-elle connue avant l'annonce ? Sans archive des versions ni consensus horodaté, **l'étude ne pourra pas prétendre mesurer une réaction à la seconde de la première annonce.**

## Ce que le second audit a changé

| Défaut trouvé | Mesure | Correction appliquée |
|---|---|---|
| Dépêche d'un autre trimestre | 2 titres recyclés prouvés (A.O. Smith, Accuray) | Titre déjà paru 45 jours plus tôt, ou numéro de trimestre contraire au calendrier de la société : écarté |
| Base du BPA lue au mauvais endroit | 121 étiquettes fausses : GATX, PepsiCo, Core & Main | Base lue dans la clause du couple retenu, hors nom de société |
| Faux lien malgré le nom | Wyndham Hotels sur Travel + Leisure, « bear » dans « Bearish » | Mot entier, mots faibles retirés. **Le périmètre de la surprise n'utilise plus aucun alias** |
| Symbole direct contredit par un alias d'une autre société | 2 591 citations | Écartées de la surprise |
| Nom de société pris pour un verbe | 16 titres d'Affirm perdus | Le premier mot du titre ne compte plus comme verbe |
| Commentaires restants | Environ 1,1 % des articles gardés | Motifs ajoutés, « gain on » comptable protégé |
| Relais tardifs admis | 469 lignes | Écartés |
| Dates non verrouillées partout | Défaut de garde-fou | Noms de fichiers et toutes les dates bornées avant lecture |

## Ce qui bloque encore

1. **Le chiffre publié n'est pas vérifié.** Sur 28 publications contrôlées, 26 sont exactes, une reconstituable et une fausse : Waterstone annonce 0,23, le BPA du même trimestre un an plus tôt. Ce cas **reste dans la table** : aucun filtre ne le voit. Soit environ 4 % d'erreur, sur un très petit tirage.
2. **La base est inconnue pour 28 989 lignes sur 49 310.** L'audit trouve beaucoup de chiffres ajustés dans ces titres sans étiquette.
3. **L'estimation n'est pas vérifiée**, et la première diffusion n'est pas prouvée. Ces deux limites ne se corrigeront pas : elles imposent le nom du signal et interdisent de parler de réaction à la seconde.

Le protocole proposé par l'audit, à figer avant tout calcul, se trouve dans `news/AUDIT_TRI_NEWS_2.md`.

## Le tri

Chaque titre reçoit une catégorie par des règles fixes, sans regarder les cours. Vocabulaire : un **commentaire de marché** décrit un mouvement déjà fait, c'est donc le cours qui cause l'article.

| Catégorie | Articles | Part | Usage | Précision au second audit, avant ses corrections (IC 95 %) |
|---|---:|---:|---|---:|
| Commentaires de marché | 139 660 | 10 % | Écartés | 96,7 % (92,4 à 98,6) |
| Remplissage | 126 159 | 9 % | Écartés | 90,7 % (84,9 à 94,4) |
| Résultats publiés | 147 838 | 11 % | Gardés | 94,7 % (89,8 à 97,3) |
| Prévisions de la société | 57 393 | 4 % | Gardés | 82,0 % (75,1 à 87,3) |
| Notes d'analystes | 307 899 | 22 % | Gardés | 100 % (97,5 à 100) |
| Faits sur une société | 620 169 | 44 % | Gardés | 72,7 % (65,0 à 79,2) |

Sur 150 titres neufs par catégorie, un seul relecteur. Ces intervalles recouvrent ceux du premier audit : aucune amélioration n'est démontrée catégorie par catégorie. **Les faits sur une société restent très bruités.** Mes premières estimations étaient trop optimistes.

**Il reste 949 850 articles liés à au moins une action, dont 847 089 à une seule.** Sur 2,68 millions de citations de symboles : 2 354 686 reliées directement, 58 058 par alias avec le nom, 95 209 alias refusés, 158 026 symboles inconnus, 13 548 hors dates de cotation. Le second audit retrouve au moins 8 % de citations plausiblement justes parmi les refusés, le reste étant surtout indécidable sur le seul titre.

## L'écart à l'estimation citée

Le signe vient des chiffres : « Q2 Adj. EPS $1.46 Beats $1.38 Estimate ». Seuls les liens directs sans conflit comptent.

| Étape, sur 80 759 publications | Publications restantes |
|---|---:|
| Au moins une dépêche de résultats dans la fenêtre (72 h avant, 24 h après l'acceptation SEC) | 70 477 |
| Avec BPA et estimation | 50 100 |
| Chiffres vraisemblables | 50 071 |
| Marqueur trimestriel | 49 985 |
| Hors corrections | 49 954 |
| Hors relais tardifs | 49 504 |
| Verbe en accord avec le BPA | 49 496 |
| Titre non recyclé | 49 492 |
| Une seule action citée | 49 427 |
| Trimestre cohérent avec le calendrier de la société | **49 310 (61 %)** |
| Base explicite, ajustée ou comptable | **20 319** |

- **Répartition.** De 57 à 67 % selon l'année, **63 % pour les sociétés encore cotées contre 51 % pour les disparues**. Cette sélection ne se corrige pas en filtrant les disparues.
- **La base explicite est très inégale** : 7 667 des 20 319 lignes datent de 2024, à cause d'un changement de format des titres. Une étude sur ce seul groupe pèserait surtout sur 2024.
- **Signe.** 35 117 au-dessus de l'estimation, 14 123 en dessous, 70 égaux.
- **Délai.** Écart médian avec le dépôt SEC de 30 secondes avant, de 1,3 heure avant à 0,7 heure après pour 8 cas sur 10. 52 % des dépêches précèdent le dépôt, ce que le premier audit juge plausible.
- **Contrôle croisé local.** Quand le titre annonce un BPA comptable, 94 % des chiffres concordent à 0,02 près avec les comptes SEC.

## FinBERT

**Fuite d'information.** La fiche du modèle indique un affinage sur Financial PhraseBank (Malo et al., 2014). L'article, d'août 2019, décrit Reuters TRC2 comme couvrant 2008-2010. **Rien n'indique que le modèle ait vu les réactions de 2018-2024.** Un modèle de 2019 n'était pas disponible début 2018 : c'est un outil de mesure rétrospectif.

**Version figée** : `4556d130` du 23/05/2023, poids identiques à ceux d'octobre 2026. L'audit a recalculé 500 titres : aucun changement d'étiquette.

**Choix.** Titres seuls, car il n'y a aucun résumé en 2018-2019. 64 jetons au plus, ce qui tronque 0,7 % des titres.

### Lit-il correctement ?

L'AUC vaut 0,5 pour un classement au hasard et 1 pour un classement parfait. La dernière colonne repère seulement les mots « beat », « upgrade », « raises » et « boosts », sans modèle.

| Verdict écrit | Titres | AUC de FinBERT | Mauvaise nouvelle lue positive | AUC du repérage de mots |
|---|---:|---:|---:|---:|
| Prévision relevée ou abaissée | 5 791 / 2 023 | 0,98 | 5 % | **0,996** |
| Analyste qui relève ou abaisse | 25 149 / 30 239 | 0,94 | 14 % | **0,96** |
| BPA au-dessus ou en dessous de l'estimation | 50 498 / 23 361 | 0,72 | 35 % | **0,81** |

**Un simple repérage de mots fait mieux que FinBERT dans les trois cas.** Ces contrôles sont faciles, puisque les verdicts sont justement définis par ces mots. Ils montrent que FinBERT n'apporte rien de plus sur ces formats, sans rien dire de sa valeur sur les autres titres. Pour les résultats, on utilisera les chiffres. Aucun de ces contrôles ne dit si le score annonce un rendement.

## Limites

- **Pas de consensus vérifié, pas de première diffusion prouvée** : voir plus haut.
- **Doublons d'information.** Plusieurs articles peuvent porter sur un même fait, et les annonces groupées mêlent plusieurs nouvelles.
- **Règles relues sur des exemples.** Les tirages des deux audits ont servi à corriger les règles : mesurer leur précision demande un tirage neuf.
- **Biais du survivant et sélection.** Voir la couverture des sociétés disparues.
