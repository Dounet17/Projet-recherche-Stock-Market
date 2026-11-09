# Validation unique 2025-2026 des stratégies quotidiennes

**Résultat : aucune des quatre stratégies figées ne réussit, ni économiquement ni statistiquement.** Les avantages observés sur 2018-2024 ne se sont pas reproduits sur la période jamais regardée.

Période : 02/01/2025 au 30/10/2026, 458 séances. Départ de 10 000 USD, frais de 5 pb par côté, décision à la clôture et exécution à l'ouverture suivante. Validation lancée une seule fois avec `reports/run_validation_once.py`, après trois passes d'audit de Codex (`social/AUDIT_PRIX.md`). Résultats bruts : `validation/validation_results.json`.

## Comment lire ces résultats
- **Sharpe** : rendement moyen rapporté aux variations du portefeuille, plus haut est meilleur.
- **Pire chute** (drawdown) : la plus forte baisse depuis un sommet.
- **p de Holm** : probabilité corrigée pour les 4 tests. Le seuil de preuve fixé à l'avance est 0,05.

## Résultats principaux

| Stratégie | Référence | Capital final | Capital référence | Sharpe | Sharpe référence | Pire chute | Chute référence | p brute | p de Holm | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Rotation top 3 sur 7 grandes valeurs | Panier égal | 10 050 | 13 274 | 0,141 | 0,693 | -29,4 % | -30,2 % | 0,935 | 1,000 | Échec |
| Filtre de marché QQQ sur TSLA | TSLA | 8 527 | 10 070 | 0,032 | 0,280 | -48,5 % | -48,3 % | 0,755 | 1,000 | Échec |
| Ciblage de volatilité sur TSLA | TSLA | 10 178 | 10 070 | 0,185 | 0,280 | -30,2 % | -48,3 % | 0,688 | 1,000 | Échec |
| Sortie si news négatives (exploratoire) | TSLA | 8 090 | 10 070 | -0,037 | 0,280 | -49,3 % | -48,3 % | 0,780 | 1,000 | Échec |

À 10 pb, les conclusions restent identiques : 9 986, 8 493, 10 142 et 7 898 USD, contre 13 252 pour le panier égal et 10 060 pour TSLA.

Références passives à 5 pb : QQQ 13 658 USD, SPY 13 159 USD. Les quatre stratégies font moins bien que QQQ et SPY sur cette période.

Le ciblage de volatilité finit légèrement au-dessus de TSLA et réduit nettement la pire chute. Il échoue au critère fixé à l'avance, car son Sharpe est inférieur et son alpha négatif (-2,4 % par an). Son écart de capital (+108 USD) est sans signification.

## Comparaison avec le développement

| Stratégie | Capital 2018-2024 | Référence 2018-2024 | Capital 2025-2026 | Référence 2025-2026 |
|---|---:|---:|---:|---:|
| Rotation top 3 | 196 415 | 95 603 | 10 050 | 13 274 |
| Filtre QQQ | 320 181 | 203 541 | 8 527 | 10 070 |
| Ciblage de volatilité | 81 105 | 203 541 | 10 178 | 10 070 |
| Sortie sur news | 327 218 | 203 541 | 8 090 | 10 070 |

Les périodes n'ont pas la même durée : 7 ans contre 22 mois. Seul le sens des écarts se compare directement.

## Résultat secondaire et descriptif
Tests d'un an, un départ par mois de janvier à octobre 2025, soit 10 tests très recoupés :

| Stratégie | Tests gagnés | Médiane | Médiane référence | Pire cas | Pire cas référence |
|---|---:|---:|---:|---:|---:|
| Rotation top 3 | 0 / 10 | 10 709 | 12 528 | 9 456 | 11 536 |
| Filtre QQQ | 5 / 10 | 11 226 | 12 236 | 8 567 | 7 926 |
| Ciblage de volatilité | 3 / 10 | 11 206 | 12 236 | 8 582 | 7 926 |
| Sortie sur news | 4 / 10 | 11 231 | 12 236 | 8 433 | 7 926 |

## Ce que l'on peut conclure
- L'hypothèse de départ du projet résiste : ces stratégies ne battent pas le placement passif hors échantillon.
- Les écarts de 2018-2024 étaient déjà compatibles avec le hasard (p corrigées de 0,858 à 1,000 sur 244 essais). La validation est cohérente avec ce constat.
- Réduire le risque par le ciblage de volatilité reste la propriété la plus stable : pire chute plus faible sur les deux périodes, avec un rendement ajusté du risque qui ne s'améliore pas en validation.

## Ce que l'on ne peut pas conclure
- 22 mois donnent peu de puissance statistique : ces résultats ne prouvent pas que ces règles n'auront jamais d'intérêt. Les intervalles à 95 % de l'écart annuel restent larges et incluent zéro, par exemple de -47 % à +17 % pour la sortie sur news.
- La période est un seul scénario de marché, et TSLA y est presque plate.
- Les sept grandes valeurs ont été choisies sur les données arrêtées à fin 2024. Le résultat ne se généralise pas à toutes les actions.
- Cours d'ouverture sans fourchette achat-vente, fiscalité et EUR/USD non simulés.
- Les news 2025-2026 ont été collectées en novembre 2026 : d'éventuelles révisions antérieures des titres ne sont pas observables.

## Conséquence pour la suite
Ces quatre hypothèses sont closes : les ajuster puis les retester sur 2025-2026 reviendrait à tricher, et cette période ne peut plus servir de preuve pour elles. Elle a aussi fait connaître la tendance générale du marché en 2025-2026 : toute nouvelle stratégie testée dessus le sera en connaissance partielle de cette période, ce qu'il faudra écrire. La preuve la plus propre pour de nouvelles idées serait une collecte prospective, avec un modèle figé avant les données.
