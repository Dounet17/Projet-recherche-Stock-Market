# Registre des hypothèses

Créé le 08/11/2026. **Toute idée de stratégie est inscrite ici avant le moindre calcul de rendement**, qu'elle vienne de l'équipe, de la littérature ou d'un agent d'IA. Le fichier canonique est `registre_hypotheses.csv` ; ce texte en donne les règles.

```bash
venv/bin/python src/registry.py              # contrôle du registre et résumé par statut
venv/bin/python tests/test_registry.py
```

## Pourquoi

Un agent d'IA produit des hypothèses beaucoup plus vite qu'on ne peut les vérifier. Tester mille idées sur le même passé garantit d'en trouver une qui « marche » par hasard. Le registre garde la trace de **tous** les essais, réussis ou non, pour que la correction statistique et l'article les comptent tous.

## Règles

1. **Inscrire avant de calculer.** Une ligne par hypothèse : énoncé testable, source de l'idée, données, périodes de conception et de validation, nombre maximal de variantes. Statut `proposee`.
2. **Dire d'où vient l'idée.** `inspiree_de_resultats_vus = oui` si elle découle de résultats déjà regardés : elle ne peut **pas** se valider sur la période qui l'a inspirée. Le contrôle du registre l'interdit pour 2018-2024.
3. **Figer un protocole** (comme `PROTOCOLE_RESULTATS_MINUTE.md`) avant le passage au statut `protocole_fige`. Un lanceur appelle `registry.require("Hxx")` et s'arrête sinon.
4. **Relecture adverse avant lancement** : un agent auditeur (Codex) cherche les fuites d'information sans calculer de rendement ; tests automatiques d'invariance au futur.
5. **Un seul lancement.** Toute correction ensuite est annoncée, avec les résultats avant et après.
6. **Inscrire le résultat**, quel qu'il soit : statuts `echec`, `nulle`, `reussie` ou `abandonnee`. Une hypothèse abandonnée avant calcul est gardée.
7. **Ne jamais réutiliser silencieusement une période.** 2018-2024 a servi à toutes les études jusqu'ici ; 2025-2026 a été consommée une fois par le laboratoire (H03).

## Périodes et validations

| Période | Usage |
|---|---|
| 2016-2017 | Préchauffage des indicateurs, apprentissage des modèles |
| 2018-2024 | Développement, très utilisé. Pour un nouveau modèle : apprentissage jusqu'en 2021, réglage en 2022, test unique sur 2023-2024 |
| 2025-2026 | Validation, déjà ouverte une fois. À nettoyer avec les mêmes règles ; usage soumis à l'accord du professeur |
| Temps réel | **Test décisif** : stratégie gelée qui tourne pendant des mois sur le compte Alpaca Paper Trading, sur des données que personne n'a pu voir |

## Statuts

| Statut | Sens |
|---|---|
| `proposee` | Inscrite, aucun protocole figé, aucun calcul de rendement autorisé |
| `protocole_fige` | Protocole commité et relu ; lancement autorisé une fois |
| `lancee` | Lancement fait, résultat en cours de lecture |
| `echec`, `nulle`, `reussie` | Résultat inscrit, avec le lien vers le rapport |
| `abandonnee` | Retirée, avec la raison |

## État au 08/11/2026

13 études terminées, toutes en `echec` : aucune stratégie ne bat le buy and hold de son univers ni SPY sur 2018-2024 (H01 à H13).

7 pistes proposées :

| Id | Piste | Idée née de résultats vus ? | Validation prévue |
|---|---|---|---|
| H14 | **Règle de protection** : vendre 5 minutes après une mauvaise nouvelle de résultats, racheter à la clôture suivante | Oui (décomposition de H10) | 2025-2026 ou temps réel |
| H15 | Suivre les robots sur QQQ, SPY, DIA après une minute brutale | Non | 2022-2024 une fois, puis temps réel |
| H16 | Parier sur le rebond après une minute brutale | Non | 2022-2024 une fois, puis temps réel |
| H17 | Petit modèle hybride sur les variables des heuristiques | Oui | 2023-2024 une fois, puis 2025-2026 |
| H18 | Grand modèle (affinage ou de zéro) | Non | 2023-2024 une fois, puis 2025-2026 |
| H19 | Modèle de motifs intraday | Non | 2022-2024 une fois, puis temps réel |
| H20 | Vente à découvert sur mauvaises nouvelles | Oui | 2025-2026 ou temps réel ; hors du cadre principal (sans vente à découvert), accord à demander |

### H14 en détail

Pour un détenteur d'une action liquide, après une dépêche de résultats sous l'estimation, l'écart moyen avec le marché était de -1,87 % 5 minutes après la dépêche et de -3,02 % à la clôture suivante (H10, 3 773 / 686 événements liquides). Vendre à 5 minutes puis racheter à cette clôture aurait donc évité environ 1,1 point en moyenne, avant frais. Réserves : ce sont des moyennes rétrospectives ; beaucoup de cas rebondissent ; l'écart entre prix d'achat et de vente en heures étendues est mal connu ; le placebo de la veille de H10 n'était pas nul. L'idée vient de résultats déjà vus : seules des données jamais regardées peuvent la confirmer.
