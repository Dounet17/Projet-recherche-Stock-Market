# Protocole : notes d'analystes et dérive des cours

**Figé le 07/11/2026, avant tout calcul de rendement.** Aucun rendement n'a été lu pour ce signal. Relu et accepté par DavidTom, sans audit indépendant du texte ; le code sera relu par Codex avant le lancement. Toute modification après ce commit doit être datée ici et dite « changement de règle » si elle en est un. Même démarche que `PROTOCOLE_RESULTATS_MINUTE.md`, en tenant compte de son audit (`minute_study/AUDIT_CODEX.md`) : chaque règle est écrite ici, et tout ce qui sera tranché en codant devra être daté et qualifié honnêtement.

## Vocabulaire

- **Note d'analyste** : avis publié par une banque ou un bureau d'études sur une action, relayé par une dépêche Benzinga.
- **Relèvement** (« upgrade ») : l'analyste améliore sa recommandation, par exemple de « Neutre » à « Achat ». **Abaissement** (« downgrade ») : l'inverse.
- **Objectif de cours** (« price target ») : prix que l'analyste attend dans environ un an. Il peut être relevé ou abaissé sans changer la recommandation.
- **Dérive** : le cours continue dans le même sens pendant plusieurs semaines après l'annonce. Elle est décrite dans la littérature pour les changements de recommandation (références à vérifier avant de les citer).
- **Rendement anormal** : celui du titre moins celui de SPY sur la même fenêtre.

## Question

Après un relèvement ou un abaissement de recommandation, le cours dérive-t-il dans le même sens pendant les semaines suivantes, une fois qu'on peut acheter ? Un portefeuille qui achète les relèvements bat-il SPY après frais ?

Pourquoi cet axe : l'étude à la minute a montré que les frais tuent les stratégies qui échangent chaque jour. Une tenue de 20 séances échange vingt fois moins.

## Ce qui a déjà été vu

1. Les études des publications de résultats (quotidienne et à la minute) et le laboratoire de stratégies : aucun gain à l'achat après frais.
2. Le contrôle de FinBERT (`TRI_NEWS.md`), qui montre que le repérage de mots classe bien ces titres, sans rendement.
3. Les mesures suivantes, faites le 07/11/2026 **sans lire aucun prix** :

| Étape | Relèvements | Abaissements | Objectif relevé | Objectif abaissé |
|---|---:|---:|---:|---:|
| Titres d'analystes reconnus par la règle | 26 538 | 31 890 | 100 174 | 76 526 |
| Une seule action citée, ni correction ni relais tardif | 24 883 | 29 934 | 96 252 | 73 297 |
| Lien direct vers une action ordinaire ou un ADR | 23 949 | 28 643 | 93 928 | 71 123 |
| Part à moins de 2 séances d'une publication de résultats | 14 % | 18 % | 39 % | 36 % |
| Hors publication de résultats | **20 549** | **23 521** | | |

Changements de recommandation : 2 382 à 3 859 par an et par sens. 82 % entrent à l'ouverture du jour même (note publiée avant 9 h 25). 272 couples titre et séance ont des notes de sens contraire. 48 titres tirés au hasard (12 par type) sont tous correctement classés.

## Données à figer

- `data/news/news_articles.parquet` et `data/news/news_links.parquet` (tri du 07/11/2026, après correction du rattachement).
- `data/universe_clean/` : cours quotidiens, filtres, coûts et sorties de cote, avec ses règles (`suspect_print` manquant, trois hypothèses de sortie).
- `data/events/earnings_events.parquet` : dates des publications de résultats, pour l'exclusion.
- `data/calendar.parquet`. Période 2018-2024 : toute fenêtre doit finir au plus tard le 31/12/2024.

Empreintes SHA-256 au gel (code au commit `1694801`), à vérifier par le code avant tout calcul :

| Données | SHA-256 |
|---|---|
| `data/news/news_articles.parquet` | `39a98efe473c46e2b3a0d701d4533a42f0e3ccb070111a14488786c8a12d6038` |
| `data/news/news_links.parquet` | `4d7fe4152650453164a641ee2ebb0f190319857578a0b5ca78e600fd3c80f161` |
| `data/universe_clean/prices_dev.parquet` | `c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15` |
| `data/universe_clean/securities_dev.parquet` | `d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161` |
| `data/events/earnings_events.parquet` | `f2da57a43b9bdda8ab455121480968259d385b4d516450cbb5808aae6c2cca12` |
| `data/calendar.parquet` | `87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03` |

## Événements

**Règle de classement**, sur les titres de catégorie `analyst`, sans tenir compte de la casse :
- relèvement : contient `upgrade` ou `upgrades` comme mot, sans `downgrade` ;
- abaissement : contient `downgrade` ou `downgrades`, sans `upgrade` ;
- objectif relevé : commence par « *bureau* Maintains » ou « *bureau* Reiterates » (2 à 40 caractères avant le verbe) et contient `raises`, `boosts`, `increases` ou `lifts` avant `price target` ;
- objectif abaissé : même début, avec `lowers`, `cuts`, `reduces` ou `trims` avant `price target`.

**Filtres** : une seule action citée (`n_stocks = 1`), lien direct sans conflit vers une action ordinaire ou un ADR, ni correction ni relais tardif. **Plusieurs notes sur un même titre et une même séance d'entrée** : un seul événement si elles vont dans le même sens, aucun sinon.

**Exclusion des résultats** (échantillon principal) : la note est écartée si une publication de résultats de la même société (`announced`, sinon `filed`, dans `earnings_events`) tombe entre 2 séances avant et 1 séance après la séance d'entrée. Ces notes réagissent souvent aux résultats ; elles forment une analyse secondaire.

**Achetable** : cours brut d'au moins 5 $ et montant échangé médian sur 20 séances d'au moins 1 M$, connus la veille de l'entrée.

## Horloge

- Disponibilité : `available_at` plus 5 minutes.
- Entrée : ouverture quotidienne de la première séance qui ouvre au moins 5 minutes après la disponibilité. Une note arrivée à 9 h 25 pile entre le jour même.
- Horizon de k séances : de l'ouverture d'entrée à la clôture de la k-ième séance, entrée comprise.
- Trou de cotation : dernier cours connu. Sortie de cote **jusqu'au dernier jour de la fenêtre compris** : dernier cours puis rendement de sortie, sous les trois hypothèses, comme dans `lab`.
- Rendement anormal : contre SPY, de son ouverture à sa clôture aux mêmes séances.

## Tests confirmatoires, corrigés ensemble par Holm

| Test | Mesure |
|---|---|
| **A1** | Rendement anormal sur 20 séances, relèvements moins abaissements, moyenne des 28 trimestres |
| **A2** | Relèvements seuls, rendement anormal sur 20 séances net des frais aller et retour, moyenne des 28 trimestres, contre 0 |
| **A3** | Portefeuille de 10 000 USD achetant les relèvements (règles plus bas), rendement quotidien moins celui de SPY, contre 0 |

- A1 et A2 : **t ordinaire sur les 28 moyennes trimestrielles** (trimestre de la séance d'entrée), p de Student à 27 degrés de liberté. Sensibilités annoncées dès maintenant : Newey-West à un retard, écarts-types regroupés par date et par société, signes tirés au hasard au sein de chaque trimestre (1 000 fois).
- A3 : `lab.compare` contre SPY (bootstrap par blocs), avec capital final, Sharpe au-delà du taux sans risque et pire chute, à côté du buy and hold moyen du même univers (`REFERENCE_BUY_AND_HOLD.md`).
- Publier pour chaque test : effectifs, exclusions, moyenne, IC à 95 %, p brute et p de Holm, **en précisant si une moyenne est par trimestre ou par événement**.

## Portefeuille de A3

- Moteur quotidien existant (`lab.backtest` avec sorties de cote, frais par titre selon la liquidité de la veille). Il décide à la clôture et exécute à l'ouverture suivante : une note arrivée avant la clôture de la séance t est achetée à l'ouverture de t + 1, une note arrivée après la clôture à l'ouverture de t + 2. **C'est une séance plus tard que A1 et A2 pour les notes du matin**, à dire tel quel.
- Chaque relèvement achetable ouvre une position tenue 20 séances. Un nouveau relèvement sur un titre déjà tenu prolonge la tenue à 20 séances à partir de lui.
- Poids égaux entre les positions ouvertes, recalculés seulement les jours où l'ensemble change ; au plus 10 % par titre ; le reste en liquidités à 0 %. Sensibilité : liquidités rémunérées (BIL).
- Frais doublés publiés en sensibilité.

## Analyses secondaires, corrigées entre elles par Holm

1. A1 à 5 et à 60 séances.
2. A1 sur la seule séance d'entrée (ouverture à clôture).
3. Objectif relevé moins objectif abaissé (sans changement de recommandation), 20 séances, hors résultats.
4. A1 sur les notes proches d'une publication de résultats.
5. A1 sur les titres au-dessus de 100 M$ par jour.
6. A2 sur les titres au-dessus de 100 M$ par jour.

## Descriptif, sans test

- Rendement anormal des 20 séances **avant** la note, par sens : les analystes suivent-ils le cours ? On s'attend à un écart non nul ; il ne sert pas de placebo.
- A1 et A2 par année et par tranche de liquidité.
- Part des fenêtres de 20 séances qui contiennent une publication de résultats.

## Contrôles prévus d'avance

1. **Placebo en date** : A1 avec les mêmes titres et la même saison, entrée décalée de 60 séances plus tôt. On attend un écart nul ; s'il ne l'est pas, l'effet propre à la note n'est pas identifié.
2. **Placebo de signe** (voir plus haut).
3. **Anti-fuite dans le code** : arrêt si une entrée précède `available_at` plus 5 minutes, si un filtre ou un coût utilise une donnée de la séance d'entrée ou après, ou si une date dépasse le 31/12/2024.
4. **Valeurs extrêmes** : rendements sur 20 séances au-delà de +200 % ou en deçà de -90 % listés et vérifiés avant interprétation, jamais retirés selon leur signe.
5. Tests sur données inventées, puis relecture du code par Codex **avant** le lancement.

## Limites connues avant calcul

- `available_at` n'est qu'une borne : beaucoup de notes circulent chez les clients des banques avant la dépêche. L'étude mesure ce qui reste à un lecteur de Benzinga, pas la valeur de la note.
- La couverture Benzinga des notes n'est pas exhaustive et augmente au fil des années (20 616 titres d'analystes en 2018, 69 752 en 2024).
- Les frais sont des hypothèses par tranche de liquidité, non mesurées.
- Pas de vente à découvert : un abaissement ne peut servir qu'à ne pas acheter.
- 2018-2024 a déjà servi à beaucoup d'essais : même un succès ici devrait être confirmé sur 2025-2026, après nettoyage de cette période et accord du professeur.

## Gel et exécution

1. Relu et figé par ce commit, avec les empreintes des données.
2. Code et tests sur données inventées, sans vrais cours ; essai à blanc pour les effectifs.
3. Relecture du code par Codex.
4. Un seul lancement. Toute correction ensuite est annoncée, avec les résultats avant et après.

## Décisions prises au gel

1. Horizon principal de **20 séances** ; 5 et 60 séances restent secondaires.
2. Notes proches d'une publication de résultats **exclues** de l'échantillon principal, étudiées à part (secondaire 4).
3. Portefeuille de A3 : **au plus 10 % par titre**.

## Choix d'implémentation, 07/11/2026, avant tout lancement

Tranchés en codant `src/analyst_study.py` et `reports/run_analyst_study.py`, sans aucun rendement lu. Classés selon la leçon de l'audit précédent : **précision** si le texte figé le permettait déjà, **changement** sinon.

1. **Changement** : la p de A3 est la p **unilatérale** de `lab.compare` (« la stratégie n'apporte rien », bootstrap stationnaire, comme dans tout le laboratoire), alors que A1 et A2 sont bilatérales. Holm les combine telles quelles. Une p bilatérale serait au plus le double.
2. Précision : séance de décision de A3 = première séance dont la clôture suit strictement `available_at` ; achetable et liquidité lus à cette clôture.
3. Précision : date d'une publication de résultats = `announced`, sinon `filed`, ramenée à la première séance à partir de cette date.
4. Précision : notes d'une même famille sur un titre et une séance d'entrée : la plus ancienne est gardée (heure, puis identifiant) ; les changements de recommandation et les objectifs de cours sont regroupés séparément.
5. Précision : un titre qui contient à la fois un changement de recommandation et un objectif de cours compte comme changement de recommandation.
6. Précision : A3 est aussi inscrit au journal `ledger_universe.csv` sous le nom `analyst_upgrades_hold20`, sans que la p de Romano-Wolf du journal entre dans les tests de ce protocole.
7. Précision : Sharpe au-delà du taux sans risque calculé sur les rendements quotidiens moins ceux de BIL (ouverture à ouverture).
8. Précision : placebo et rendement des 20 séances avant la note calculés sous l'hypothèse de sortie de base, sur les événements de l'échantillon principal.
9. Précision : regroupement à deux dimensions : les rares notes sans CIK forment un seul groupe.

**Essai à blanc** (empreintes conformes, aucun rendement lu) : 22 795 relèvements et 25 921 abaissements après regroupement par séance ; échantillon principal achetable hors résultats de **18 427 relèvements et 19 194 abaissements**, dont 15 573 au-dessus de 100 M$ ; 18 483 relèvements achetables pour le portefeuille A3 ; 48 112 objectifs relevés et 35 713 abaissés hors résultats.
