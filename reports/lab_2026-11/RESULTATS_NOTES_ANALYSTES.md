# Notes d'analystes : résultats

Lancement unique du 07/11/2026, code du commit `d6ecbeb`, protocole figé `PROTOCOLE_NOTES_ANALYSTES.md` avec ses corrections datées. Code relu trois fois par Codex **avant** le lancement (`analyst_study/AUDIT_CODE_CODEX*.md`), sans aucun rendement calculé pendant ces relectures. Empreintes des données conformes. Résultats bruts : `analyst_study/summary.json` ; tables : `data/events/analyst_study/` (non versionnées).

```bash
venv/bin/python tests/test_analyst_study.py    # 30 tests
venv/bin/python reports/run_analyst_study.py   # environ 2 minutes
```

## En bref

1. **Aucun des trois tests confirmatoires ne réussit.** Après un relèvement de recommandation, le titre ne fait pas significativement mieux qu'après un abaissement sur 20 séances (+0,31 point, p de Holm 0,35).
2. **Acheter les relèvements et les garder 20 séances ne bat ni SPY ni le buy and hold.** 10 000 USD deviennent 15 013 USD, contre 24 531 pour SPY et 16 356 pour le buy and hold à poids égaux des actions achetables, avec une pire chute de 46 % contre 32 % pour SPY.
3. **Le placebo décalé de 60 séances donne déjà un écart** (+0,51 point, p = 0,014) : les notes tombent sur des titres qui bougeaient déjà différemment avant. Même un A1 significatif n'aurait pas été attribuable à la note.

L'hypothèse de départ du projet tient pour ce protocole : pas de rendement trouvé.

## Effectifs

Échantillon principal, hors notes à 2 séances d'une publication de résultats : 18 413 relèvements et 19 163 abaissements achetables ; 18 181 et 18 952 avec une fenêtre de 20 séances complète. Portefeuille A3 : 17 653 achats. 87 titres d'agences de notation refusés. 5 620 notes de sociétés sans calendrier de résultats, gardées.

## Tests confirmatoires

Moyenne des 28 trimestres, t ordinaire, p de Student à 27 degrés de liberté ; Holm sur les trois.

| Test | Mesure | Résultat | IC 95 % | p | p de Holm |
|---|---|---:|---|---:|---:|
| A1 | Rendement anormal sur 20 séances, relèvements moins abaissements | +0,31 pt | -0,08 à +0,70 | 0,117 | 0,35 |
| A2 | Relèvements, net de frais, contre SPY | -0,26 pt | -0,88 à +0,36 | 0,397 | 0,79 |
| A3 | Portefeuille de relèvements contre SPY (log-rendement annuel, p unilatérale) | -7,0 % par an | -14,9 à +0,9 | 0,96 | 0,96 |

- **Par événement**, les relèvements font -0,03 point et les abaissements -0,30 point sur 20 séances : l'écart vient surtout des abaissements, comme pour les résultats à la minute. Les petits titres (1 à 10 M$ par jour) abaissés font -1,41 point ; cette observation est descriptive, non testée, et ne serait exploitable que par la vente à découvert.
- **Sensibilités** : Newey-West (p = 0,13 pour A1, 0,40 pour A2), regroupement par date et société (t = 1,67 pour A1, -2,36 pour A2, moyennes par événement), trois hypothèses de sortie (A2 de -0,26 à -0,27 point), frais doublés (A2 à -0,54 point). Le placebo de signe donne p = 0,019 pour A1, mais il ignore la dépendance entre titres d'une même date et ne remplace pas le test prévu.
- **Par année**, l'écart A1 va de -0,78 point (2023) à +1,01 point (2021) : aucun sens stable.

## Portefeuille A3, 2018-2024

| | Capital final | Sharpe | Pire chute |
|---|---:|---:|---:|
| Achat des relèvements, 20 séances | **15 013 USD** | 0,37 | -46 % |
| Hypothèses de sortie optimiste / pessimiste | 15 032 / 14 930 USD | | |
| Frais doublés | 10 915 USD | | |
| Liquidités rémunérées (BIL) | 15 017 USD | | |
| **SPY conservé** | **24 531 USD** | 0,79 | -32 % |
| Buy and hold à poids égaux des actions achetables au 02/01/2018 | 16 356 USD | | |

Le portefeuille est investi en permanence (99,9 %), sur environ 400 titres à la fois, et tourne 32 fois son capital par an. Il a un bêta de 1,13 et un alpha annuel de -7,9 % (IC -15,3 à -0,5 %). Au-delà du taux sans risque, son Sharpe vaut 0,27 contre 0,67 pour SPY. Les frais coûtent environ 4 100 USD sur la période (comparaison avec les frais doublés). La référence à poids égaux porte sur un univers plus large que les sociétés suivies par des analystes.

## Analyses secondaires

Corrigées entre elles par Holm : aucune ne réussit.

| | Mesure | Résultat | p | p de Holm |
|---|---|---:|---:|---:|
| S1 | A1 à 5 séances | +0,15 pt | 0,082 | 0,49 |
| S2 | A1 à 60 séances | +0,68 pt | 0,101 | 0,51 |
| S3 | A1 le jour de l'entrée (ouverture à clôture) | +0,15 pt | 0,015 | 0,11 |
| S4 | Objectif de cours relevé moins abaissé, 20 séances | -0,37 pt | 0,214 | 0,64 |
| S5 | A1 sur les notes proches des résultats | +0,52 pt | 0,139 | 0,56 |
| S6 | A1 sur les titres au-dessus de 100 M$ | +0,14 pt | 0,557 | 1,00 |
| S7 | A2 sur les titres au-dessus de 100 M$ | -0,05 pt | 0,823 | 1,00 |

Sur les titres les plus liquides, il ne reste rien (S6, S7).

## Contrôles

- **Placebo à 60 séances : non nul**, +0,51 point (p = 0,014), plus que A1 lui-même. Les deux groupes de titres ne se comportent pas pareil bien avant la note : l'effet propre à la note n'est pas identifié.
- **20 séances avant la note** : les titres abaissés avaient fait +2,07 points de plus que SPY, les titres relevés +0,21. Les abaissements suivent souvent une hausse. Descriptif, sans test.
- **Valeurs extrêmes** : 54 rendements sur 20 séances au-delà de +200 % ou en deçà de -90 %, dont 2 dans l'échantillon principal, de vrais mouvements (Immunomedics en avril 2020, AMC en mai 2021). Gardés ; sans eux, A1 vaut +0,335 point au lieu de +0,311.
- 25 % des fenêtres de 20 séances contiennent une publication de résultats. 443 événements principaux n'ont pas de fenêtre de 20 séances complète (fin 2024 ou ouverture manquante).

## Lecture

- **Le résultat est nul, pas « négatif » au sens d'une preuve d'absence.** L'IC de A1 va de -0,08 à +0,70 point : un petit effet reste possible, mais il serait trop faible pour couvrir les frais d'un portefeuille qui tourne 32 fois par an (A2, A3).
- **Ce qui est établi** : sur 2018-2024, avec les dépêches Benzinga et un achat à l'ouverture qui suit, acheter les relèvements de recommandation et les garder 20 séances a fait nettement moins bien que SPY, avec plus de risque.
- **Ce qui n'est pas testé** : la note elle-même, que les clients des banques reçoivent souvent avant la dépêche ; la vente à découvert sur les abaissements ; d'autres durées ou règles d'achat. Toute nouvelle variante sur 2018-2024 serait exploratoire.

## Limites

- Changements de règle faits avant le lancement mais après le gel (exclusion des agences de notation, horloge et filtres propres à A3, retrait des titres sans cotation) : tous datés dans le protocole.
- Les frais sont des hypothèses par tranche de liquidité.
- `available_at` n'est qu'une borne de diffusion ; la couverture Benzinga augmente au fil des années.
- La référence de buy and hold porte sur un univers plus large que les titres suivis par des analystes.
- 2018-2024 a servi à de nombreux essais : ce résultat s'ajoute au journal (`ledger_universe.csv`, essai `analyst_upgrades_hold20`).
- La littérature décrit une dérive après les changements de recommandation ; références à vérifier avant de les citer, et à comparer avec ce résultat nul sur une période récente.
