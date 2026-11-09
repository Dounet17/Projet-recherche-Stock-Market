# Stratégies EPS et P/E : résultats

Lancement unique du 08/11/2026, code du commit `e07480b`, protocole figé `PROTOCOLE_PE_EPS.md` avec ses corrections datées. Code relu quatre fois par Codex **avant** le lancement (`pe_eps_study/AUDIT_CODE_CODEX*.md`), sans aucun rendement calculé pendant ces relectures ; ces relectures ont surtout rendu l'EPS historique causal et ses unités cohérentes. Empreintes des données conformes. Résultats bruts : `pe_eps_study/summary.json`.

```bash
venv/bin/python tests/test_pe_eps_study.py    # 26 tests
venv/bin/python reports/run_pe_eps_study.py   # environ 3 minutes
```

## En bref

1. **Ni la croissance de l'EPS (E1), ni la croissance combinée à un P/E bas dans le secteur (E2) ne choisissent mieux que l'univers dont elles sont tirées.** Elles font environ 2 points de moins par an que leur témoin (p de Holm 1,0).
2. **Aucune ne bat SPY** : 16 961 et 16 805 USD contre 24 531, avec un Sharpe d'environ 0,46 contre 0,79.
3. **Le témoin lui-même fait moins bien que SPY** (19 249 USD) : sur 2018-2024, acheter à poids égaux les 600 à 700 grandes sociétés bénéficiaires a rapporté moins que l'indice pondéré par la capitalisation, porté par les très grandes valeurs.

Avec le test B (P/E bas, 14 372 USD), les quatre heuristiques EPS et P/E du projet restent toutes sous SPY.

## Portefeuilles de 10 000 USD, 2018-2024

| | Capital final | Rendement annuel | Sharpe | Pire chute | Bêta | Alpha annuel contre SPY | Rotation par an |
|---|---:|---:|---:|---:|---:|---:|---:|
| E1, croissance de l'EPS | **16 961** | 7,9 % | 0,47 | -38,7 % | 1,04 | -5,4 % | 3,9 |
| E2, croissance et P/E sectoriel | **16 805** | 7,7 % | 0,45 | -42,7 % | 1,04 | -5,3 % | 3,7 |
| Témoin (univers éligible) | 19 249 | 9,8 % | 0,57 | -39,5 % | 0,99 | -3,1 % | 1,4 |
| **SPY conservé** | **24 531** | 13,7 % | 0,79 | -32,0 % | 1,00 | | |

Le témoin de E2 (secteur connu) donne 19 248 USD, pratiquement le même. Au-delà du taux sans risque (BIL), les Sharpe valent 0,36 (E1), 0,35 (E2), 0,46 (témoin) et 0,67 (SPY).

**Sensibilités.** Hypothèse de sortie pessimiste : 16 284 (E1), 16 395 (E2), 18 869 (témoin). Frais doublés : 16 509 (E1), 16 375 (E2). Les frais pèsent peu, environ 450 USD sur la période, grâce au rééquilibrage trimestriel. Portefeuilles tirés au hasard du laboratoire : médiane 14 477 USD ; E1 et E2 en battent 95 %, mais ces tirages piochent dans tous les titres achetables, souvent petits et chers à négocier, et ne sont qu'un repère.

## Tests confirmatoires

Écart annuel des log-rendements quotidiens, bootstrap stationnaire, p unilatérale « la stratégie n'apporte rien » ; Holm sur les deux.

| Test | Écart annuel | IC 95 % | p | p de Holm |
|---|---:|---|---:|---:|
| P1 : E1 contre son témoin | -1,8 % | -5,3 % à +1,6 % | 0,85 | 1,00 |
| P2 : E2 contre son témoin | -1,9 % | -5,8 % à +1,8 % | 0,84 | 1,00 |

L'écart de Sharpe va dans le même sens (-0,10 et -0,12). Les intervalles laissent possible un petit écart dans les deux sens, mais rien n'indique un talent de sélection.

## Analyses secondaires, contre SPY

| Test | Écart annuel | IC 95 % | p | p de Holm |
|---|---:|---|---:|---:|
| S1 : E1 | -5,3 % | -10,8 % à +0,1 % | 0,97 | 1,00 |
| S2 : E2 | -5,4 % | -12,9 % à +1,5 % | 0,93 | 1,00 |
| S3 : témoin de E1 | -3,5 % | -9,2 % à +1,7 % | 0,90 | 1,00 |

Romano-Wolf sur tout le journal du laboratoire : 1,00 et 0,9998.

## Par année

| | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|
| E1 | -10,9 % | +24,3 % | +9,4 % | +20,5 % | -18,4 % | +21,9 % | +16,8 % |
| E2 | -14,1 % | +28,6 % | -0,4 % | +25,6 % | -16,7 % | +22,9 % | +18,9 % |
| Témoin | -9,8 % | +33,1 % | +11,8 % | +28,0 % | -15,1 % | +16,2 % | +13,7 % |
| SPY | -6,9 % | +34,0 % | +18,2 % | +28,6 % | -18,0 % | +24,7 % | +26,5 % |

E1 et E2 battent leur témoin en 2023 et 2024, et perdent les autres années, nettement en 2019, 2020 (E2) et 2021. SPY devance le témoin surtout en 2020, 2023 et 2024, années des très grandes valeurs technologiques.

## Répartition sectorielle moyenne

E1 et E2 sont un peu plus chargés que le témoin en équipement d'entreprise et technologie (17,9 % et 16,5 % contre 16,3 %), en santé (10,3 % et 9,3 % contre 8,1 %) et en énergie (5,2 % et 3,8 % contre 2,6 %), et moins en finance (16,6 % et 18,4 % contre 21,0 %). Le classement de l'E/P au sein du secteur évite bien à E2 de se concentrer sur les banques. Titres plus tard disparus : 7,0 % des couples titre et décision pour E1, 6,4 % pour E2, 5,5 % pour le témoin.

## Lecture

- **L'EPS publié ne permet pas, ici, de choisir mieux que l'univers.** Une croissance passée du bénéfice est une information publique, déjà dans les cours quand on peut l'acheter, en cohérence avec les études d'événements de résultats.
- **Le témoin sous SPY rappelle que la référence compte.** Une partie de l'écart à SPY vient de la pondération égale, qui donne autant de poids à une société moyenne qu'à Apple ou Microsoft. C'est pourquoi la référence principale était le témoin.
- **L'EPS de `universe_data` n'était pas causal.** 175 à 342 des 1 000 titres les plus liquides avaient, à chaque décision, un EPS différent de plus de 1 % de celui reconstruit ici. Le test B et les autres essais qui l'utilisent en héritent ; ils ne sont pas relancés, et leurs résultats doivent être lus avec cette réserve.

## Limites

- Puissance faible : un écart annuel de quelques points avec le témoin reste dans l'intervalle de confiance.
- EPS comptable (éléments exceptionnels compris) ; opérations sur actions absentes du fichier ignorées ; fusions inversées qui mélangent deux sociétés (KDP 2018) ; codes de secteur actuels.
- Changements de règle faits avant le lancement mais après le gel (EPS causal, croissance à échelle d'actions constante, opérations documentées seulement, départ en liquidités jusqu'en mars 2018) : tous datés dans le protocole.
- 2018-2024 a servi à de nombreux essais ; E1 et E2 sont inscrits au journal (`ledger_universe.csv`).
