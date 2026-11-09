# Dépêches de résultats à la minute : résultats

Protocole figé `PROTOCOLE_RESULTATS_MINUTE.md`. Premier lancement le 07/11/2026 (code `3326735`, `minute_study/summary_v1.json`), puis audit indépendant de Codex (`minute_study/AUDIT_CODEX.md`) et **second lancement corrigé, après lecture des premiers résultats** (`minute_study/summary.json`). Les deux versions sont publiées ; les corrections sont listées en fin de protocole. Empreintes des données conformes au gel. Table par événement : `data/events/minute_study/events.parquet` (non versionnée, première version dans `events_v1.parquet`).

```bash
venv/bin/python tests/test_minute_study.py      # 37 tests sur données inventées
venv/bin/python reports/run_minute_study.py     # environ 10 minutes
```

## En bref

1. **L'achat systématique des bonnes nouvelles testé ici perd après frais.** Acheté à l'ouverture et revendu à la clôture, il fait -0,31 point de moins que SPY en moyenne par trimestre. 10 000 USD deviennent 43 USD en sept ans, contre 24 372 USD pour SPY conservé.
2. **Entre l'ouverture et la clôture, les titres à mauvaise nouvelle font moins bien que ceux à bonne nouvelle** (+0,52 point d'écart, p de Holm 0,002). L'écart vient du côté des mauvaises nouvelles : -0,42 point en moyenne par événement, contre +0,01 point pour les bonnes, sans effet moyen positif détecté.
3. **L'essentiel de l'écart mesuré est déjà dans les prix à l'ouverture** (93 %), et pour les titres très liquides, 65 % l'est dans les prix connus 5 minutes après la dépêche. C'est une description des prix ; elle ne dit pas qui a acheté ni pourquoi.

L'hypothèse de départ du projet tient pour ce protocole : pas de rendement trouvé à l'achat.

## Effectifs

Groupe principal achetable : 15 459 publications (12 103 écarts positifs, 3 356 négatifs, 27 nuls décrits à part). 120 n'ont aucune barre dans les 6 premières minutes de la séance et n'entrent pas.

## Tests confirmatoires

Vocabulaire : le **rendement anormal** est celui du titre moins celui de SPY sur les mêmes minutes. Un **point** vaut 1 %. Les tests portent sur la **moyenne des 28 trimestres** ; chaque trimestre pèse autant. La **p de Holm** corrige le fait de faire trois tests à la fois.

| Test | Mesure | Résultat | IC 95 % | p de Holm, Newey-West | p de Holm, t ordinaire |
|---|---|---:|---|---:|---:|
| H1 | Ouverture à clôture du jour, positifs moins négatifs | **+0,52 pt** | +0,24 à +0,80 | **0,002** | **0,004** |
| H2 | Ouverture à clôture de la 5e séance, même écart | +0,37 pt | -0,09 à +0,83 | 0,108 | 0,129 |
| H3 | Achat des positifs, ouverture à clôture, net de frais, moins SPY brut | **-0,31 pt** | -0,47 à -0,14 | **0,002** | **0,003** |

Le gel prévoyait le t ordinaire ; Newey-West a été ajouté en codant. Les deux donnent la même conclusion.

- **H1** est confirmé par les écarts-types regroupés par date et société (t = 3,48) et par les signes tirés au hasard (p = 0,001). L'écart est positif chaque année, de +0,13 point en 2018 à +1,17 en 2022.
- **Pondérations.** Par événement, les positifs font +0,01 point et les négatifs -0,42 point, soit un écart de 0,42 ; par trimestre, +0,03 et -0,49, soit l'écart de 0,52 du test. Pour les positifs seuls, en sensibilité : IC 95 % de -0,13 à +0,20 point, p = 0,68.
- **H2 ne passe pas le test prévu.** Les contrôles de sensibilité sont plus favorables (t regroupé de 2,81, p de 0,046 par signes au hasard) : résultat fragile, à ne pas présenter comme un effet établi.
- **H3 est significativement perdant.** Par événement : -0,34 point de rendement anormal net, -0,36 point de rendement net du titre. Avant frais, les positifs ne battent pas SPY (-0,01 point) ; les frais coûtent en moyenne 0,35 point par aller-retour. Avec des frais doublés : -0,64 point.

## Analyses secondaires

Corrigées entre elles par Holm, annoncées comme secondaires.

| | Mesure | Résultat | p de Holm |
|---|---|---:|---:|
| S1 | 30 minutes après l'ouverture | +0,18 pt | 0,44 |
| S2 | 60 minutes après l'ouverture | +0,27 pt | 0,13 |
| S3 | Ouverture à clôture, cours quotidiens | +0,52 pt | 0,006 |
| S4 | 20 séances | +0,33 pt | 0,75 |
| S5 | Entrée à 9 h 35 | +0,46 pt | 0,012 |
| S6 | Heures étendues, titres au-dessus de 100 M$, positifs moins négatifs (2 806 / 531) | +0,52 pt | 0,049 |
| S7 | Heures étendues, achat des positifs, net | **-0,35 pt** | 0,002 |
| S8 | H1 sur toutes les dépêches vérifiées | +0,36 pt | 0,049 |
| S9 | H2 sur toutes les dépêches vérifiées | +0,19 pt | 0,75 |

- S3 reproduit H1 avec les cours quotidiens (corrélation de 0,9985 entre les deux mesures), et S5 montre qu'une entrée 5 minutes plus tard donne un écart proche.
- Les fenêtres de 30 et 60 minutes ne sont pas significatives après correction. Cela ne prouve pas que l'écart se forme sur toute la journée : la forme dans le temps n'a pas été testée.
- **S6 est fragile** : selon des détails de construction relevés par l'audit, sa p de Holm oscille entre 0,029 et 0,060. Il ne faut pas le présenter comme établi.
- Acheter en heures étendues 5 minutes après une bonne nouvelle perd aussi après frais (S7).

## Écart déjà présent dans les prix

Rendement anormal cumulé depuis la dernière clôture avant la dépêche, sur les mêmes événements à chaque ligne, et part de l'écart de clôture déjà présente. Prix « connu » à un instant : clôture de la dernière barre terminée, qui peut être ancienne pour un titre peu échangé.

| Moment | Positifs | Négatifs | Part de l'écart de clôture |
|---|---:|---:|---:|
| **Titres au-dessus de 100 M$** (3 773 / 686) | | | |
| 5 minutes après la dépêche | +0,55 % | -1,87 % | **65 %** |
| 30 minutes après | +0,55 % | -2,40 % | 79 % |
| 60 minutes après | +0,61 % | -2,63 % | 86 % |
| Ouverture régulière | +0,60 % | -2,91 % | 94 % |
| 30 minutes après l'ouverture | +0,69 % | -2,76 % | 92 % |
| Clôture du jour d'entrée | +0,73 % | -3,02 % | 100 % |
| **Tous les titres** (12 017 / 3 322) | | | |
| Ouverture régulière | +1,35 % | -3,88 % | **93 %** |
| 30 minutes après l'ouverture | +1,33 % | -4,01 % | 95 % |
| Clôture du jour d'entrée | +1,36 % | -4,28 % | 100 % |

**Lecture prudente.** Ces parts sont des rapports de moyennes. Elles décrivent où se trouve déjà l'écart dans les prix observés, avec un délai de 5 minutes simulé. Elles ne mesurent pas la vitesse à laquelle une information nouvelle est intégrée, car `available_at` n'est qu'une borne de l'heure de diffusion, et elles n'identifient pas les acheteurs. L'hypothèse de l'équipe, une fenêtre entre robots et humains, reste donc **non testée** : ce qu'on peut dire, c'est qu'après nos 5 minutes il reste peu d'écart à prendre, et que ce qui reste ne couvre pas les frais à l'achat.

## Portefeuille de 10 000 USD, 2018-2024

| | Capital final |
|---|---:|
| Achat des écarts positifs, ouverture à clôture | **43 USD** |
| Même chose, frais doublés | 0,86 USD |
| Même chose, sans frais | environ 2 163 USD (calcul de l'audit) |
| SPY conservé | 24 372 USD |
| SPY acheté à l'ouverture et vendu à la clôture les mêmes 1 211 jours | 3 338 USD |

La stratégie perd 0,38 % en moyenne par jour d'achat. Elle perd même sans frais : le portefeuille pondère les jours et compose des rendements variables. Le dernier repère paie aussi 10 pb par jour : ces frais suffisent à ramener 10 000 USD vers 3 000 USD en 1 211 jours.

## Contrôles

- **Placebo de la veille : non nul.** Sur la séance précédant la dépêche, l'écart vaut déjà +0,12 point (IC 95 % de +0,02 à +0,22, p = 0,016), y compris pour les dépêches arrivées avant l'ouverture. H1 moins ce placebo reste positif (+0,39 point, p = 0,016, calcul exploratoire de l'audit). **Ce que la dépêche cause elle-même n'est donc pas identifié** : anticipation, autre information déjà diffusée, dépêche vue plus tôt que son horodatage, différences durables entre sociétés ou hasard restent possibles.
- **Sorties de cote** : dans les 5 séances, CPSI, HIIQ et PRMW cessent de coter (renommages, sortie de 0 %), et trois titres atteignent leur dernière séance à la borne. H2 vaut +0,373 point en hypothèse de base et +0,364 en hypothèse pessimiste.
- **Variations extrêmes** (plus de 50 % dans une minute ou d'une minute à la suivante, toutes barres utilisées) : 10 événements, dont un seul dans le groupe principal achetable, FBM le 12/05/2020, avec une transaction isolée de 100 actions à 18,50 $ à 17 h contre 12,24 $ juste avant. Gardé ; sans lui, H1 passe de +0,5218 à +0,5227 point. ITI (rachat d'Iteris) et TTS (sortie de cote annoncée) sont de vrais mouvements.

## Ce que l'audit a changé

| | Première version | Version corrigée |
|---|---:|---:|
| H1, H2, H3, portefeuille, placebo | voir plus haut | identiques (H2 : 0,37299 contre 0,37294) |
| S6 : écart, effectifs, p de Holm | +0,518 pt, 3 140 / 607, 0,049 | +0,515 pt, 2 806 / 531, 0,049 |
| S7 | -0,36 pt, p de Holm 0,001 | -0,35 pt, 0,002 |
| Part à l'ouverture, tous / liquides | 92 % / 94 % | 93 % / 94 % |
| Variations extrêmes listées | 0 (séance d'entrée seule) | 10 (toutes barres) |

Le texte a aussi été corrigé : la première version affirmait que la fenêtre entre robots et humains existait, que H1 n'était exploitable que par la vente à découvert et qu'aucune sortie de cote n'avait lieu dans les 5 séances. Ces affirmations n'étaient pas établies.

## Limites

- **Écarts au gel** : quatre précisions d'implémentation changeaient une règle, et des corrections ont été faites après lecture des résultats. Toutes sont datées dans le protocole.
- **Les frais sont des hypothèses** : les barres ne donnent pas l'écart entre prix d'achat et de vente. En heures étendues, il est probablement plus large que nos coûts doublés.
- **Prix anciens** : une vente « à la clôture » utilise la dernière transaction de la séance, qui peut dater de plusieurs minutes pour un titre peu échangé.
- `available_at` n'est qu'une borne de la diffusion ; un chiffre faux sur 13 à 25 environ peut passer le contrôle ; 38 % du groupe principal date de 2024 ; les sociétés disparues passent moins souvent les filtres.
- **Puissance limitée pour les négatifs** (environ 120 par trimestre) : un effet plus faible que 0,3 point peut passer inaperçu.
- **Non testé** : la vente à découvert (emprunt des titres, interdictions ponctuelles, absentes de nos données) et toute autre stratégie à l'achat. Une étude dans ce sens serait exploratoire et devrait être validée sur 2025-2026, avec l'accord du professeur.
- Le résultat sur les mauvaises nouvelles rappelle une dérive après annonce décrite dans la littérature ; références à vérifier avant de les citer.
