# Étape 4 : Bollinger et RSI, action par action

Rapport du 06/11/2026, chiffres mis à jour sur la version corrigée et déterministe du nettoyage, période de développement seulement : ce n'est pas une validation. Définitions reprises de `price_lab`, figées avant le premier lancement sur ce dataset, une variante journalisée par règle. Elles avaient déjà été vues sur les 10 actifs du laboratoire : ce ne sont donc pas des idées neuves, mais elles n'ont pas été choisies pour ce résultat.

```bash
venv/bin/python reports/run_step4_mean_reversion.py   # environ 2 minutes, réécrit les mêmes lignes du journal
venv/bin/python tests/test_per_stock.py
```

Règles : `src/stock_rules.py`. Détail : `per_stock/`. Méthode et vocabulaire : `RESULTATS_ETAPE_3.md`.

## Les règles

Toutes deux parient sur le **retour à la moyenne** : une action qui vient de beaucoup baisser devrait rebondir. C'est l'inverse de la moyenne mobile, qui suit la tendance.

- **Bollinger.** Achat quand le cours passe sous sa moyenne sur 20 séances moins 2 écarts-types, vente quand il repasse au-dessus de cette moyenne.
- **RSI sur 2 séances.** Le RSI mesure de 0 à 100 la force des dernières variations. Achat sous 10 si le cours est au-dessus de sa moyenne sur 200 séances. Vente au-dessus de 70, ou si le cours passe sous cette moyenne.

Mêmes actions et mêmes dates que la moyenne mobile : les trois règles se comparent directement.

## Résultats

### 10 000 USD à parts égales, achat le 02/01/2018, jusqu'à fin 2024, toutes achetables (2 908 titres)

| | Moyenne mobile 200 | Bollinger | RSI 2 | Buy and hold | SPY |
|---|---:|---:|---:|---:|---:|
| **Capital final** | **12 487** | **9 660** | **9 685** | **16 490** | **24 531** |
| Avec liquidités en BIL | 13 471 | 10 927 | 11 140 | | |
| Hypothèse pessimiste | 12 179 | 9 595 | 9 632 | 16 080 | |
| Frais doublés | 11 371 | 8 692 | 8 530 | 16 434 | |
| Volatilité | 9,5 % | 8,4 % | 2,8 % | 18,3 % | 18,4 % |
| Pire chute du portefeuille | -15,4 % | -32,8 % | -9,0 % | -36,6 % | -32,0 % |
| Part investie, en dollars | 51 % | 20 % | 9 % | 87 % | 100 % |
| Rotation par an | 6,7 fois | 7,5 fois | 9,6 fois | 0,26 fois | 0,29 fois |
| Sharpe au-delà du taux sans risque, avec BIL | 0,27 | -0,07 | -0,22 | 0,36 | |
| Alpha annuel au-delà du taux sans risque, avec BIL | -0,4 % | -2,9 % | -1,3 % | | |
| Intervalle à 95 % de cet alpha | -3,7 à +3,1 | -7,9 à +1,4 | -2,5 à -0,1 | | |
| La règle gagne sur (liquidités à 0 %) | 31,9 % | 29,2 % | 33,2 % | | |
| La règle gagne sur (liquidités en BIL) | 40,2 % | 36,8 % | 40,6 % | | |
| p corrigée contre SPY, 6 essais | 0,999 | 0,999 | 0,999 | | |

### Selon l'univers, même achat

| | Moyenne mobile 200 | Bollinger | RSI 2 | Buy and hold |
|---|---:|---:|---:|---:|
| 500 plus liquides | 14 772 | 11 508 | 10 806 | 20 376 |
| 1 000 plus liquides | 13 941 | 10 770 | 10 475 | 18 773 |
| Toutes achetables | 12 487 | 9 660 | 9 685 | 16 490 |

### Toutes les dates d'achat, en moyenne, toutes achetables

| Horizon | Dates | Moyenne mobile : par an, gagne sur | Bollinger : par an, gagne sur | RSI 2 : par an, gagne sur | Buy and hold, par an |
|---|---:|---:|---:|---:|---:|
| 1 an | 72 | 3,4 %, 36,4 % | -1,0 %, 44,5 % | -0,3 %, 44,1 % | 9,3 % |
| 3 ans | 48 | 4,7 %, 37,1 % | -0,9 %, 34,3 % | 0,4 %, 37,8 % | 8,9 % |
| 5 ans | 24 | 3,6 %, 33,8 % | -1,5 %, 28,5 % | 0,1 %, 34,9 % | 7,5 % |

La part d'actions gagnantes sur 1 an varie énormément selon la date : de 11 % à 77 % pour Bollinger, de 5 % à 78 % pour le RSI. Le meilleur moment se situe avant une baisse du marché (milieu 2021, avril 2019), le pire juste après le creux du Covid (avril 2020).

Sur 5 ans, seuls les télécoms et, pour le RSI, la santé dépassent la moitié (Bollinger : télécoms 51 %, santé 50 % ; RSI : télécoms 55 %, santé 52 %).

## Lecture

1. **Aucune des trois règles ne bat le buy and hold.** Elles perdent sur environ deux actions sur trois sur 5 ans, dans tous les univers et sous toutes les hypothèses testées.
2. **Le retour à la moyenne fait moins bien que le suivi de tendance ici**, et perd même de l'argent sur tout l'univers, malgré un marché haussier.
3. **Ces règles sont peu investies et changent souvent de position.** Leur gain vient donc surtout des très rares jours en position, et les frais pèsent lourd : les doubler enlève environ 1 000 USD à chacune. En extrapolant, le RSI sans frais finirait vers 11 000 USD, encore loin du buy and hold, mais cette estimation n'a pas été simulée.
4. **Un faux résultat évité.** La première version affichait pour le RSI, sur les 500 plus liquides avec BIL, un alpha de +1,8 % (p = 0,004) et un Sharpe de 0,97. Ce n'était que l'intérêt des bons du Trésor, où la règle reste environ 90 % du temps. Au-delà du taux sans risque, l'alpha tombe à -0,1 % (de -1,5 % à +1,2 %) et le Sharpe à 0,29, contre 0,52 pour le buy and hold. Le même défaut touchait l'étape 3, corrigée.
5. **Le seul avantage réel est la réduction des chutes**, et il vient surtout du fait d'être rarement investi. Le RSI réduit fortement la pire chute de presque toutes les actions (98 %), mais il ne fait que 9 % d'exposition et il ne gagne presque rien.
6. **Prudence sur la significativité.** L'alpha négatif du RSI sur tout l'univers (-2,5 % à -0,1 %) n'est pas corrigé pour les essais multiples. Il ne prouve pas une règle nuisible, seulement l'absence d'avantage.

## Contrôles

- `lab.check_no_lookahead` passe pour les deux règles.
- Le calcul action par action est égal à `lab.backtest` sur les cas de `tests/test_per_stock.py`, déjà audités à l'étape 3 par Codex.
- Bollinger est identique à la définition de `price_lab` sur une série simulée de 700 séances ; le RSI concorde à plus de 98 %, l'écart venant de l'exigence de 180 clôtures au lieu de 200.
- La refonte du code n'a pas changé les résultats de l'étape 3 (résumé identique).
- **Pas d'audit Codex indépendant à cette étape** : seules les deux règles et la mesure au-delà du taux sans risque sont nouvelles.

## Limites

- Mêmes limites qu'à l'étape 3 : paliers de frais à valider, une seule date pour le test statistique, période haussière sans crise longue, fiscalité non simulée.
- BIL sert de taux sans risque, et l'argent après une disparition y est aussi placé.
- Ces règles restent souvent en liquidités : leur comparaison en capital à une position toujours investie est dure dans un marché haussier. Une période baissière longue pourrait changer le classement, mais ces données n'existent pas dans ce dataset.
- Une variante de seuils ou de fréquence n'est pas testée, volontairement, pour éviter de chercher jusqu'à trouver un résultat.
