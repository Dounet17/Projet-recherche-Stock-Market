# Troisième relecture ciblée du code des notes d'analystes

07/11/2026. Commit `ad861d9`, diff `4858b19..ad861d9` et section « Corrections après la seconde relecture » du protocole. Périmètre limité à D2, D4 et leurs régressions.

**Verdict : lançable tel quel pour cette étude et ses données figées.** Les deux défauts de causalité sont corrigés. Une limite de réouverture, reproduite ci-dessous, ne touche aucun des signaux du gel et ne bloque donc pas ce lancement.

## D2 : corrigé

`src/analyst_study.py:103-112` conserve chaque 8-K contenant le point 2.02 à sa propre date de dépôt, sans sélection trimestrielle ultérieure. `past_earnings`, lignes 87-99, cherche seulement dans `[d-2, d-1]`. Ajouter ou retirer un dépôt postérieur à une décision ne peut donc changer son exclusion : sa position est au moins `d`, y compris après rabattement d'un jour sans séance. Le lanceur utilise bien cette nouvelle source pour A3, lignes 90-93 ; les filtres rétrospectifs A1/A2 restent distincts.

Vérification réelle : **AMD `11115880`, décision du 01/02/2018, et DIOD `11156807`, décision du 08/02/2018, ont tous deux `tradable_a3=True` et `past_earnings=True`** : ils sont exclus des achats. Retirer tous les dépôts futurs conserve exactement les exclusions aux sept coupures 01/02/2018, 08/02/2018, 31/12/2018, 01/10/2020, 30/06/2022, 01/11/2024 et 31/12/2024, jusqu'aux 22 052 décisions A3.

## D4 : causalité corrigée

`stale_rows`, lignes 115-123, utilise une fenêtre glissante de cinq observations, séance courante comprise. `portfolio_weights`, lignes 171-179, retire le titre à la première ligne ainsi signalée pendant sa tenue. Le lanceur, lignes 211-214, ne consulte plus ni date finale ni statut de disparition pour construire ces ordres.

Les tests couvrent le retrait après cinq séances et l'invariance des ordres antérieurs à une reprise future. Sur les données réelles, les lignes d'absence et les matrices d'ordres restent identiques après troncature des cours et des signaux aux quatre coupures 31/12/2018, 01/10/2020, 30/06/2022 et 01/11/2024.

**Limite non bloquante pour ce gel :** la fusion des achats dans `holding_intervals` précède leur troncature pour absence. Sur 50 séances inventées, achat de A à 2, cours manquants de 8 à 13, reprise à 14 et nouvel achat à 15 : les ordres sont seulement achat à 2 et retrait à 12 ; le rachat à 15 est perdu, car les deux achats avaient été fusionnés jusqu'à 35. Ce cas mériterait une correction avant réutilisation sur d'autres signaux. Recherche exhaustive dans les intervalles des **17 653 achats du gel : aucun rachat admissible ainsi supprimé**. Aucun nouveau défaut bloquant ou grave pour le lancement présent n'a été identifié.

## Vérification du lancement

`PYTHONDONTWRITEBYTECODE=1 venv/bin/python tests/test_analyst_study.py` : **30 tests réussis**. Essai supplémentaire via `run.main(['--dry-run'])`, avec calculs de rendements et journalisation interdits par assertions : **huit empreintes conformes**, 2 999 exclusions A3 et 17 653 achats ; principal inchangé, 18 413 relèvements et 19 163 abaissements. Contrôles supplémentaires : `/tmp/audit_analyst_codex3_ca3888.py`.

Aucun lancement réel, rendement, cours de sortie ou capital de ces événements calculé ou consulté ; aucun accès à `.env` ou aux données après 2024. Les calculs des tests ordinaires portent sur des données inventées. Aucun fichier existant modifié ; changements préexistants de `.gitignore` et `reports/build_vault.py` laissés en place. Le lancement complet reste volontairement inexécuté.
