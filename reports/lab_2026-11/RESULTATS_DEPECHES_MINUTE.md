# Dépêches de résultats à la minute : résultats

Lancement unique du 07/11/2026, code du commit `3326735`, protocole figé `PROTOCOLE_RESULTATS_MINUTE.md`. Empreintes des données conformes au gel. Code relu par l'auteur seul avant le lancement, **sans audit indépendant**. Résultats bruts : `minute_study/summary.json` ; table par événement : `data/events/minute_study/events.parquet` (non versionnée).

```bash
venv/bin/python tests/test_minute_study.py      # 32 tests sur données inventées
venv/bin/python reports/run_minute_study.py     # environ 10 minutes
```

## En bref

1. **Le marché a presque tout intégré avant qu'un humain puisse acheter.** Sur les titres très liquides, 65 % de l'écart entre bonnes et mauvaises nouvelles est déjà fait 5 minutes après la dépêche, 94 % à l'ouverture.
2. **Il reste une continuation dans la journée, mais seulement à la baisse.** Après une mauvaise nouvelle, le titre perd encore 0,42 point de plus que SPY entre l'ouverture et la clôture. Après une bonne nouvelle, rien (+0,01 point).
3. **Ce n'est pas gagnable sans vente à découvert.** Acheter les bonnes nouvelles à l'ouverture perd 0,31 point par opération après frais, et 10 000 USD deviennent 43 USD en sept ans, contre 24 372 USD pour SPY conservé.

L'hypothèse de départ du projet tient : pas de rendement exploitable avec ce protocole.

## Effectifs

Groupe principal achetable : 15 459 publications (12 103 écarts positifs, 3 356 négatifs, 27 nuls décrits à part). 120 n'ont aucune barre dans les 6 premières minutes de la séance et n'entrent pas. Aucune variation de plus de 50 % d'une minute à l'autre.

## Tests confirmatoires

Vocabulaire : le **rendement anormal** est celui du titre moins celui de SPY sur les mêmes minutes. Un **point** vaut 1 %. La **p de Holm** corrige le fait de faire trois tests à la fois.

| Test | Mesure | Résultat | IC 95 % | p | p de Holm |
|---|---|---:|---|---:|---:|
| H1 | Ouverture à clôture du jour, positifs moins négatifs | **+0,52 pt** | +0,24 à +0,80 | 0,0008 | **0,002** |
| H2 | Ouverture à clôture de la 5e séance, même écart | +0,37 pt | -0,09 à +0,83 | 0,108 | 0,108 |
| H3 | Achat des positifs, ouverture à clôture, net de frais, contre SPY | **-0,31 pt** | -0,47 à -0,14 | 0,0007 | **0,002** |

- **H1 réussit**, avec la même conclusion par écarts-types regroupés par date et société (t = 3,48) et par signes tirés au hasard (p = 0,001). L'écart est positif chaque année, de +0,13 point en 2018 à +1,17 en 2022.
- **H1 vient des mauvaises nouvelles** : -0,42 point en moyenne pour les négatifs, +0,01 pour les positifs.
- **H2 ne passe pas le test prévu.** Les deux contrôles de sensibilité sont plus favorables (t regroupé de 2,81, p de 0,046 par signes au hasard) : résultat fragile, à ne pas présenter comme un effet établi.
- **H3 est significativement perdant.** Le brut est nul (-0,01 point avant frais), les frais coûtent en moyenne 0,35 point par aller-retour. Avec des frais doublés : -0,64 point.

## Analyses secondaires

Corrigées entre elles par Holm, annoncées comme secondaires.

| | Mesure | Résultat | p de Holm |
|---|---|---:|---:|
| S1 | 30 minutes après l'ouverture | +0,18 pt | 0,44 |
| S2 | 60 minutes après l'ouverture | +0,27 pt | 0,13 |
| S3 | Ouverture à clôture, cours quotidiens | +0,52 pt | 0,006 |
| S4 | 20 séances | +0,33 pt | 0,75 |
| S5 | Entrée à 9 h 35 | +0,46 pt | 0,012 |
| S6 | Heures étendues, titres au-dessus de 100 M$, positifs moins négatifs | +0,52 pt | 0,049 |
| S7 | Heures étendues, achat des positifs, net | **-0,36 pt** | 0,001 |
| S8 | H1 sur toutes les dépêches vérifiées | +0,36 pt | 0,049 |
| S9 | H2 sur toutes les dépêches vérifiées | +0,19 pt | 0,75 |

La continuation est étalée sur la journée : elle n'est pas significative à 30 ou 60 minutes. Elle ne dépend pas des cours à la minute (S3, cours quotidiens, donne la même chose), ni d'une entrée immédiate (S5). Acheter en heures étendues 5 minutes après une bonne nouvelle perd aussi après frais (S7) : les positifs y perdent même 0,10 point avant frais.

## Où se forme le prix

Rendement anormal cumulé depuis la dernière clôture avant la dépêche, et part de l'écart final déjà faite.

| Moment | Positifs | Négatifs | Part de l'écart de clôture |
|---|---:|---:|---:|
| **Titres au-dessus de 100 M$** (3 778 / 687) | | | |
| 5 minutes après la dépêche | +0,55 % | -1,87 % | **65 %** |
| 30 minutes après | +0,55 % | -2,40 % | 79 % |
| 60 minutes après | +0,61 % | -2,62 % | 87 % |
| Ouverture régulière | +0,60 % | -2,91 % | 94 % |
| Clôture du jour d'entrée | +0,73 % | -3,01 % | 100 % |
| **Tous les titres** | | | |
| Ouverture régulière | +1,35 % | -3,88 % | **92 %** |
| 30 minutes après l'ouverture | +1,35 % | -4,03 % | 95 % |
| Clôture du jour d'entrée | +1,39 % | -4,30 % | 100 % |

C'est la réponse à l'hypothèse de l'équipe. **La fenêtre entre les robots et les humains existe, mais elle se compte en minutes, en heures étendues, sur les titres liquides** : les deux tiers du mouvement sont faits avant notre délai de 5 minutes. Ce qui reste ensuite ne couvre pas les frais à l'achat.

## Portefeuille de 10 000 USD, 2018-2024

| | Capital final |
|---|---:|
| Achat des écarts positifs, ouverture à clôture | **43 USD** |
| Même chose, frais doublés | 0,86 USD |
| SPY conservé | 24 372 USD |
| SPY acheté à l'ouverture et vendu à la clôture les mêmes 1 212 jours | 3 338 USD |

La stratégie perd 0,38 % en moyenne par jour d'achat. Le dernier repère paie aussi 10 pb par jour : ces frais suffisent à ramener 10 000 USD vers 3 000 USD en 1 212 jours. Négocier chaque jour coûte cher, même sur le titre le moins cher à échanger.

## Contrôles

- **Placebo de la veille : non nul.** Sur la séance précédant la dépêche, l'écart vaut déjà +0,12 point (p = 0,016) : les titres qui vont annoncer une bonne nouvelle montent un peu avant, et inversement. H1 est quatre fois plus grand, mais une partie de la dérive mesurée n'est donc pas propre à la dépêche.
- **Sorties de cote** : aucune dans les 5 séances du groupe principal, les trois hypothèses donnent le même H2. À 20 séances, écart de moins de 0,02 point.
- Les mesures à la minute et quotidiennes concordent (corrélation de 0,9985 sur H1).

## Limites

- **Pas d'audit indépendant** du protocole ni du code avant le lancement. Les 13 précisions d'implémentation sont de l'auteur seul.
- **Les frais sont des hypothèses** : les barres ne donnent pas l'écart entre prix d'achat et de vente. En heures étendues, il est probablement plus large que nos coûts doublés, ce qui rendrait S7 encore plus négatif.
- `available_at` n'est qu'une borne : une dépêche vue plus tôt par le marché ferait paraître la réaction plus rapide encore.
- 38 % du groupe principal date de 2024 ; les sociétés disparues passent moins souvent les filtres ; un chiffre faux sur 13 à 25 environ peut passer le contrôle.
- **Puissance limitée pour les négatifs** (environ 120 par trimestre) : un effet plus faible que 0,3 point peut passer inaperçu.
- La vente à découvert, seule façon d'exploiter H1, n'est pas testée : elle a ses propres coûts (emprunt des titres, interdictions ponctuelles) que nos données ne contiennent pas. Toute étude dans ce sens serait exploratoire et devrait être validée sur 2025-2026.
- Le résultat sur les mauvaises nouvelles rappelle une dérive après annonce décrite dans la littérature ; références à vérifier avant de les citer.
