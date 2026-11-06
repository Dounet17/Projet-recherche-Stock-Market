# Tests A et B sur le grand univers (2018-2024)

Rapport du 06/11/2026. Exploration sur la période de développement : ces résultats ne sont pas une validation. Les définitions d'origine des tests A et B ayant été perdues, celles-ci ont été proposées et acceptées le 06/11/2026. Paramètres figés avant le premier calcul de performance, une seule variante par test.

```bash
venv/bin/python reports/run_test_a_momentum.py
venv/bin/python reports/run_test_b_value.py
```

## Stratégies

Chaque premier jour de bourse du mois, décision à la clôture et exécution à l'ouverture suivante, poids égaux sur 50 titres.

- **Test A, momentum 12 mois.** Les titres achetables qui ont le plus monté sur 252 séances. Actions ordinaires et sociétés étrangères (8 123 titres).
- **Test B, P/E bas.** Parmi les 1 000 actions ordinaires achetables les plus liquides, les plus bas P/E. Le P/E est le cours divisé par le bénéfice par action des 12 derniers mois. Bénéfice positif et P/E d'au moins 3 exigés.
- **Témoin.** Les 500 titres les plus liquides. Ce n'est pas une idée de stratégie.

## Résultats sur 10 000 USD

Vocabulaire : le Sharpe mesure le gain par unité de risque, le drawdown la pire chute depuis un sommet.

| | Test A | Test B | Témoin | SPY conservé |
|---|---:|---:|---:|---:|
| Capital final, hypothèse centrale | 18 553 | 14 773 | 19 979 | 24 531 |
| Hypothèse optimiste | 18 553 | 14 773 | 19 991 | |
| Hypothèse pessimiste | 16 608 | 14 434 | 19 415 | |
| Frais doublés | 15 885 | 14 015 | 19 685 | |
| Sharpe | 0,42 | 0,34 | 0,57 | 0,79 |
| Pire chute | -59,1 % | -60,0 % | -36,5 % | -32,0 % |
| Rotation par an | 8,9 fois | 6,8 fois | 3,2 fois | |
| Médiane de portefeuilles au hasard | 10 240 | 10 799 | 10 740 | |
| Part des tirages au hasard battue | 100 % | 95 % | 100 % | |
| p corrigée (3 essais du journal) | 0,88 | 0,94 | 0,94 | |

Les valeurs `romano_wolf_p` des fichiers `experiments/*.csv` ont été calculées au moment de chaque lancement, sur moins d'essais. Celles du tableau, plus sévères, couvrent les trois essais du journal.

| Rendement par année | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Test A | -16,8 % | +50,3 % | +43,7 % | -12,0 % | +2,4 % | +2,7 % | +11,5 % |
| Test B | -21,3 % | +20,6 % | -8,8 % | +38,7 % | -12,8 % | +35,3 % | +4,3 % |
| SPY | -6,9 % | +34,0 % | +18,2 % | +28,6 % | -18,0 % | +24,7 % | +26,5 % |

## Lecture

**Aucun des deux tests ne bat SPY**, ni en capital ni en Sharpe, et ils subissent une chute bien plus forte. L'écart n'est pas statistiquement net en capital : pour le test B, l'intervalle à 95 % de l'écart annuel avec SPY va de -22,6 % à +6,1 %. Sur le Sharpe du test B, l'écart est négatif de façon plus nette (de -0,87 à -0,04), sans correction pour les essais multiples.

Battre le hasard ne prouve pas un talent de sélection : le hasard pioche dans tous les titres achetables, souvent petits, chers à négocier et moins performants sur la période. Le témoin, qui ne sélectionne que sur la liquidité, le bat aussi. Il bat également les deux tests : la bonne référence pour juger la sélection est donc plutôt le témoin. Cette comparaison reste indicative, car les univers diffèrent et que 2018-2024 a été portée par les très grandes valeurs, que SPY pondère fortement.

Les frais comptent surtout pour le momentum : les doubler coûte 2 668 USD au test A, contre 758 au test B. L'hypothèse de sortie pèse aussi sur lui : 1 945 USD entre la centrale et la pessimiste.

Les hypothèses centrale et optimiste coïncident pour A et B : vérification faite, aucune position n'était tenue à une faillite. Ce n'est pas un défaut : les 46 sorties tenues du test A et les 8 du test B sont des rachats, fusions ou changements de nom. Les rééquilibrages mensuels et le filtre de liquidité ont pu écarter les titres avant leur effondrement. **La perte à la disparition n'est donc presque pas testée ici**.

## Réserves

- **Fuite dans le nettoyage, test A.** Sur 70 allers-retours masqués à cause du cours du lendemain, 4 tombent un jour de décision. Effet non mesuré, sans doute faible, potentiellement favorable.
- **Survie, test B.** Parmi les futures disparues de l'univers, 56 % à 85 % ont un bénéfice connu selon l'année, contre 72 % à 90 % pour tout l'univers. Ce biais favorise la stratégie, qui perd malgré tout.
- **Plancher de P/E.** Le seuil de 3 a été choisi en regardant la liste des plus bas P/E, sans aucune performance. Il écarte aussi de vraies sociétés.
- **Qualité des liens SEC.** AMJ, un produit de JPMorgan, est classé parmi les actions et reçoit un bénéfice. Il est apparu en contrôle. D'autres erreurs de ce type sont possibles ; à corriger dans `security_overrides.csv`.
- **Frais.** Les paliers selon la liquidité sont une hypothèse à valider.
- **Bénéfice comptable.** Il inclut les éléments exceptionnels : une plus-value ponctuelle fait paraître une société bon marché.
- **Fiscalité et EUR/USD non simulés.** Ils pénaliseraient davantage les rotations fréquentes.
