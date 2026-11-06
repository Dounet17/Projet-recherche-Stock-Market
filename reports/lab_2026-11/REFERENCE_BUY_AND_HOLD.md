# Référence du buy and hold, 2016-2024

Rapport du 06/11/2026. Aucune stratégie n'est testée ici et le journal des essais n'est pas touché. Seules les données jusqu'à fin 2024 sont lues.

```bash
venv/bin/python reports/build_reference.py   # moins de 2 minutes, 5 Go de RAM
venv/bin/python tests/test_reference.py
```

| Fichier | Contenu |
|---|---|
| `data/reference/buy_hold_by_cohort.parquet` | 967 395 lignes : titre achetable, date d'achat, horizon, multiple sous les trois hypothèses de sortie |
| `data/reference/buy_hold_all_listed.parquet` | Même chose sans filtre de prix ni de liquidité |
| `data/reference/sectors.parquet`, `sector_cohorts.parquet` | Secteur de chaque titre, statistiques par secteur et par date |
| `data/french/` | Données de Fama et French, coupées à fin 2024 |
| `reference/*.csv` | Synthèses versionnées |

## Comment la table est faite

- **107 dates d'achat** : le premier jour de bourse de chaque mois, de février 2016 à décembre 2024. Janvier 2016 manque, car il n'y a encore aucun historique de liquidité.
- **Horizons** : 1, 3 et 5 ans, et jusqu'à fin 2024.
- **Mêmes règles que le moteur** : achat à l'ouverture, frais selon la liquidité, trois hypothèses de sortie. Un titre disparu rapporte son dernier cours et sa sortie, puis reste en liquidités à 0 %.
- **Moyenne** : c'est exactement un portefeuille à poids égaux jamais rééquilibré. Multiple de 2 : 10 000 USD deviennent 20 000 USD.
- **Univers** : classés par liquidité à la veille de l'achat. « Achetables » signifie au moins 5 USD et 1 M USD par jour ; « toutes cotées » retire ces deux filtres et contient surtout de très petites valeurs.

## Résultats

### Sur 10 000 USD, achat le 02/01/2018, jusqu'à fin 2024

| Univers | Actions | Moyenne | Médiane | En perte | Perte de 90 % ou plus | Disparues | Battent SPY |
|---|---:|---:|---:|---:|---:|---:|---:|
| 500 plus liquides | 499 | 20 420 | 16 120 | 22,8 % | 1,6 % | 12,0 % | 23,4 % |
| 1 000 plus liquides | 998 | 18 740 | 14 710 | 28,1 % | 2,6 % | 17,3 % | 19,6 % |
| Toutes achetables | 3 031 | 16 360 | 12 360 | 37,6 % | 6,0 % | 27,6 % | 16,2 % |
| Toutes cotées | 4 623 | 14 770 | 10 900 | 45,6 % | 13,9 % | 32,6 % | 14,2 % |

**SPY : 24 530. QQQ : 34 700.**

### Sur 10 000 USD, achat le 01/02/2016, jusqu'à fin 2024

| Univers | Actions | Moyenne | Médiane | En perte | Disparues | Battent SPY |
|---|---:|---:|---:|---:|---:|---:|
| 500 plus liquides | 500 | 32 260 | 21 220 | 17,4 % | 17,4 % | 26,0 % |
| 1 000 plus liquides | 1 000 | 28 980 | 19 800 | 21,5 % | 24,2 % | 22,9 % |
| Toutes achetables | 2 879 | 25 240 | 16 840 | 26,5 % | 33,5 % | 19,1 % |
| Toutes cotées | 4 582 | 23 460 | 15 130 | 33,8 % | 40,1 % | 16,7 % |

**SPY : 35 350. QQQ : 53 480.**

### Sur 5 ans, moyenne des 47 dates d'achat possibles, par an

| Univers | Moyenne | Médiane | SPY | En perte | Battent SPY |
|---|---:|---:|---:|---:|---:|
| 500 plus liquides | 11,5 % | 8,4 % | 14,0 % | 22,9 % | 31,2 % |
| 1 000 plus liquides | 10,7 % | 7,5 % | 14,0 % | 25,8 % | 28,7 % |
| Toutes achetables | 9,1 % | 4,9 % | 14,0 % | 34,2 % | 24,2 % |
| Toutes cotées | 7,9 % | 2,7 % | 14,0 % | 42,2 % | 21,4 % |

La meilleure et la pire date d'achat encadrent les toutes achetables de 3,8 % à 15,5 % par an : la date compte beaucoup, même en moyenne sur des milliers de titres.

### Par secteur, sur 5 ans, moyenne des 47 dates d'achat, toutes achetables

| Secteur | Titres | Moyenne par an | Médiane par an | En perte |
|---|---:|---:|---:|---:|
| Semi-conducteurs (`Chips`) | 123 | 17,6 % | 11,4 % | 20,2 % |
| Équipement et technologie (`BusEq`) | 418 | 14,6 % | 8,6 % | 25,6 % |
| Armes et espace (`Guns`) | 9 | 14,2 % | 7,0 % | 24,8 % |
| Logiciels (`Softw`) | 176 | 13,7 % | 7,6 % | 26,5 % |
| Défense, liste manuelle | 14 | 11,3 % | 10,9 % | 13,3 % |
| Industrie (`Manuf`) | 242 | 10,4 % | 7,3 % | 30,2 % |
| Santé (`Hlth`) | 348 | 7,0 % | -0,3 % | 49,3 % |
| Finance (`Money`) | 633 | 6,9 % | 4,5 % | 30,6 % |
| Énergie (`Enrgy`) | 118 | 2,0 % | -0,1 % | 50,9 % |
| Télécoms (`Telcm`) | 81 | 1,7 % | -1,6 % | 58,0 % |

Tous les secteurs sont dans `reference/summary_by_sector.csv`. **Ces chiffres décrivent le passé et ne sont pas une cible.** Choisir la technologie en 2018 en sachant qu'elle gagnerait, c'est lire l'avenir. Le long terme le montre : `Softw` fait 0,8 % par an sur 2000-2015 puis 19,3 % sur 2016-2024, et `Chips` -1,3 % puis 29,8 % (pondérés par la taille).

`Guns` ne représente pas l'armement : il contient LMT et KTOS, mais aussi Axon, Ruger, Smith & Wesson et Rocket Lab, et pas Northrop, General Dynamics ni RTX. La liste manuelle `defense_securities.csv` corrige cela, mais **elle a été écrite de mémoire en 2026, ne contient que des sociétés encore vivantes** et est donc biaisée à la hausse. À relire.

### Long terme : 2016-2024 était une bonne période

Marché américain pondéré par la taille depuis 1926 (French, sans frais), fenêtres glissantes :

| Fenêtre | Rendement par an | Rang parmi toutes les fenêtres de cette durée | Pire | Médiane | Meilleure | Fenêtres négatives |
|---|---:|---:|---:|---:|---:|---:|
| 2016-2024 (9 ans) | 14,4 % | 74e centile | -7,9 % | 10,7 % | 21,6 % | 4,1 % |
| 2018-2024 (7 ans) | 13,6 % | 65e centile | -7,5 % | 11,6 % | 24,2 % | 6,4 % |

## Lecture

1. **La moyenne sous-estime la difficulté, et SPY la dépasse.** Une action prise au hasard parmi les achetables fait en général bien moins que la moyenne, car quelques très grands gagnants la tirent vers le haut (NVDA multiplie par 28,5 depuis 2018). Environ 84 % des actions achetables font moins que SPY sur ce parcours.
2. **SPY bat la moyenne à poids égaux, ce qui change la question.** Il pèse les grandes sociétés, qui ont dominé la période. Ne pas battre SPY peut donc simplement vouloir dire ne pas avoir assez de très grandes valeurs.
3. **L'hypothèse de sortie compte peu ici en moyenne** (16 360 contre 15 950 en pessimiste pour les achetables depuis 2018), parce que beaucoup de disparitions sont des rachats.

### Les tests A et B relus avec cette référence

| 10 000 USD depuis 2018 | Stratégie | Buy and hold moyen, univers proche | SPY |
|---|---:|---:|---:|
| Test A, momentum | 18 553 | 16 360 (toutes achetables) | 24 530 |
| Test B, P/E bas | 14 773 | 18 740 (1 000 plus liquides) | 24 530 |
| Témoin, 500 plus liquides | 19 979 | 20 420 (500 plus liquides) | 24 530 |

Le momentum dépasse ainsi la moyenne de son univers, mais avec une chute de 59 %. Ce n'est **pas une preuve** : une seule histoire, sans test statistique, avec une liste figée en 2018 alors que la stratégie achète aussi les nouvelles cotations. Le P/E bas reste en dessous de sa référence. Sa référence inclut les sociétés étrangères, pas lui.

## Contrôles

- **Moteur.** Chaque ligne de cas synthétiques et un échantillon de vraies lignes (AAPL, SIVB, TWTR, BCEI, WLL, GME) sont égales à `lab.backtest`.
- **Audit indépendant de Codex, en lecture seule.** 226 lignes recalculées sans notre code concordent à 4e-14 près (678 résultats, dont faillites, trous et horizons). Secteurs vérifiés sur 14 sociétés. Corrigés à sa suite : un plancher sur les médianes nulles, et des fenêtres longues faussées par les 1 158 samedis de cotation d'autrefois.
- **SPY contre le marché CRSP de French.** Corrélation quotidienne de 0,99 ; 15,1 % par an contre 15,3 %.
- **Nos secteurs contre ceux de French** (moyenne à poids égaux rééquilibrée chaque jour, actions ordinaires). Corrélation moyenne de 0,98 sur 12 secteurs, 0,91 sur 49 ; les petits secteurs concordent moins (`Agric` 0,62, `Guns` 0,80). Nous sommes en moyenne 1,7 point par an sous French, surtout à cause de la neutralisation des gains à travers un cours suspect : sans elle, l'écart tombe à 0,5 point ou moins dans 5 des 12 secteurs, mais l'énergie s'envole de 14 points à cause de sorties de faillite comme BCEI. Il reste environ 2 points en finance, commerce et santé, et 1 à 1,6 point en chimie et télécoms, non expliqués ; la présence des REIT dans nos données, que French exclut peut-être, est une piste non vérifiée.
- **Effet de la neutralisation sur le buy and hold.** Négligeable : 1,635 contre 1,637 de multiple moyen pour janvier 2018 (35 titres sur 3 032).

## Limites

- **Fenêtre.** 2016-2024 seulement, sans crise longue comme 2008, et période plutôt favorable.
- **Corrélation entre titres.** Des milliers d'actions vivent le même marché : ce ne sont pas des milliers de preuves indépendantes. Les dates d'achat se chevauchent aussi.
- **Exclusions.** CETXP (action préférentielle) et quatre doublons de cotation (`reference_exclusions.csv`) sont retirés de cette table seulement. **Le nettoyage reste à corriger** ; les tests A et B ne sont pas refaits. D'autres cas existent peut-être, car le contrôle n'a examiné que les paires de même CIK.
- **Fuite du nettoyage.** 75 cours masqués à cause du lendemain empêchent quelques achats dans « toutes cotées » (5 cas). Effet très faible.
- **Filtre rétrospectif.** Les titres de moins de 20 séances et les 3 404 titres non identifiés sont absents, y compris de « toutes cotées ». Ils sont surtout disparus : la moyenne est donc plutôt flattée.
- **Secteurs.** Codes SIC d'aujourd'hui, inconnus pour 2,3 % des titres (3,7 % des disparus), hors de tout usage comme signal. Fichiers de définition de French datés de 2020.
- **Classes d'actions.** GOOG et GOOGL comptent pour deux titres : la distribution est par titre, pas par société.
- **French.** Portefeuilles recomposés chaque année, sans frais, donc pas exactement un buy and hold. La documentation consultée ne confirme pas que la perte de disparition est comptée. Fichiers gardés en local, à citer dans l'article.
- **Cas individuels.** FSR#0 sort à 0 % avec le motif « renamed » alors que le cours est déjà presque nul : le motif est peut-être inexact.
