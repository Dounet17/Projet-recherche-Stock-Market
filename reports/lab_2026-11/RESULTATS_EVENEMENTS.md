# Publications de résultats : table d'événements et réaction des cours

Rapport du 07/11/2026, 2018-2024. Aucune stratégie n'est testée et le journal des essais n'est pas touché. **Conception révisée après l'audit indépendant (`events/AUDIT_ETUDE_RESULTATS.md`), donc après avoir vu une première version des résultats.**

```bash
venv/bin/python reports/build_earnings_events.py   # moins d'une minute
venv/bin/python tests/test_events.py
```

Code : `src/events.py`. Table : `data/events/earnings_events.parquet` (non versionnée). Résultats : `events/`.

## La question

Vocabulaire. Le **BPA** est le bénéfice par action. Une **étude d'événement** mesure le rendement d'une action autour d'une date. Le **rendement anormal** est celui de l'action moins celui de SPY sur la même période. La **surprise (SUE)** est la variation du BPA par rapport au même trimestre de l'année précédente, divisée par l'écart-type de ces variations passées.

Le cours réagit-il aux résultats, et reste-t-il un mouvement à prendre une fois qu'on peut acheter ?

## La table

206 569 publications de 5 784 sociétés, dont 75,1 % avec un 8-K de résultats (item 2.02). Chaque ligne donne le titre, la fin du trimestre, la date du 8-K, la date du dépôt des comptes, le BPA et les surprises. D'autres sources (news, publications) pourront remplir le même format.

**Date.** Dernier 8-K 2.02 avant ou le jour du dépôt des comptes. Le premier serait faux : TSLA en dépose aussi un pour ses livraisons. **Seule la date sert, et on achète à l'ouverture de la séance suivante**, car l'heure SEC n'est pas fiable.

**Surprise.** Actions classées en cinq groupes, avec les seuils du trimestre précédent. Une ligne par société, le titre le plus liquide. Les trimestres déposés plus de 150 jours après leur fin sont écartés : ce sont surtout d'anciennes périodes reprises.

## Trois cas, à ne pas confondre

| Cas | Entrée | Surprise connue à ce moment dans nos données ? | Usage |
|---|---|---|---|
| Après le 8-K, rétrospectif | Lendemain du 8-K | **Non** : le BPA vient d'un dépôt ultérieur, souvent déjà dans le communiqué | Décrit le marché, ne se négocie pas tel quel |
| Après le 8-K, BPA disponible | Lendemain du 8-K | Oui, mais seulement 37 % des publications | Plus proche d'un usage réel |
| Après le dépôt des comptes | Lendemain du dépôt | Oui | Négociable avec nos données |

## Résultats

### Réaction jusqu'à l'ouverture d'entrée, non capturable

De la dernière clôture avant le jour J à la première ouverture où l'on peut acheter, sans retirer le marché :

| Groupe de surprise | 1 (mauvaise) | 2 | 3 | 4 | 5 (bonne) |
|---|---:|---:|---:|---:|---:|
| Après le 8-K, rétrospectif | -1,32 % | -0,67 % | +0,56 % | +1,24 % | +1,72 % |
| Après le dépôt des comptes | -0,84 % | -0,41 % | +0,36 % | +0,81 % | +1,09 % |

**Le cours réagit bien, dans le bon sens et par paliers.** Cet écart d'environ 3 points s'est produit avant qu'on puisse acheter. Une partie est rétrospective : le classement utilise un chiffre connu plus tard dans nos données.

### Ce qui reste après l'entrée

Écart de rendement anormal entre groupe 5 et groupe 1. Chaque trimestre pèse autant. Toutes achetables, environ 51 000 à 55 000 événements sur 27 trimestres pour le premier et le troisième cas, environ 21 000 pour le deuxième.

| Horizon | Rétrospectif : écart (t) | BPA disponible : écart (t) | Après dépôt : écart (t) |
|---|---:|---:|---:|
| 1 séance | **+0,45 pt (3,27)** | +0,18 pt (1,42) | +0,08 pt (1,16) |
| 5 séances | +0,54 pt (1,95) | +0,28 pt (0,88) | +0,15 pt (0,65) |
| 20 séances | +0,84 pt (1,19) | +0,43 pt (0,60) | +0,11 pt (0,19) |
| 60 séances | +0,88 pt (1,23) | -0,20 pt (-0,16) | -0,26 pt (-0,29) |

Sur les 1 000 plus liquides, aucun écart n'est significatif, avec un t compris entre -1,39 et 1,16.

**Sur les 24 tests, un seul résiste à la correction de Holm** : le cas rétrospectif à 1 séance sur toutes les achetables (0,025 par blocs de trimestres, 0,073 par Newey-West, donc pas robuste selon la méthode). Tous les autres valent 1,000. Le t mesure si un écart se distingue du bruit : au-delà de 2 environ, il commence à être crédible.

### Placebo en date

Mêmes groupes, dates décalées de 41, 63 et 83 séances vers l'avant : l'écart à 1 séance tombe entre -0,02 et +0,07 point, contre +0,45 point à la vraie date. **L'effet court est donc bien lié à l'événement.** À 60 séances, le placebo atteint +0,25 à +1,01 point, autant que la vraie date : cet écart ne dit rien de spécifique aux résultats. Ce contrôle est descriptif et ne sert pas de p.

### Peut-on l'exploiter ? Achat du seul groupe 5

Rendement moyen par événement après frais selon la liquidité, et écart à SPY sur les mêmes fenêtres. Toutes achetables.

| Horizon | Rétrospectif, net (contre SPY) | BPA disponible, net (contre SPY) | Après dépôt, net (contre SPY) |
|---|---:|---:|---:|
| 1 séance | -0,21 % (-0,18 pt) | -0,35 % (-0,33 pt) | -0,33 % (-0,29 pt) |
| 5 séances | +0,12 % (-0,17 pt) | +0,02 % (-0,30 pt) | -0,15 % (-0,31 pt) |
| 20 séances | +1,10 % (-0,15 pt) | +0,92 % (-0,57 pt) | +0,38 % (-0,83 pt) |
| 60 séances | +2,20 % (-1,25 pt) | +2,58 % (-0,97 pt) | +2,06 % (-1,38 pt) |

**Aucun cas négociable ne dépasse SPY à aucun horizon**, y compris sur les 1 000 plus liquides. Seule exception sur les 24 lignes : le cas rétrospectif sur les 1 000 plus liquides à 20 séances (+0,31 pt), non négociable et isolé. Ces moyennes additionnent des achats qui se chevauchent : ce n'est pas un portefeuille à budget fini.

## Lecture

1. **Les résultats font bouger les cours.** Le signal existe, et on le mesure proprement au jour J.
2. **En données quotidiennes, on arrive après.** Il ne reste rien d'exploitable après le dépôt des comptes ni quand le BPA est réellement disponible. C'est cohérent avec un marché qui intègre vite cette information.
3. **Le seul effet résiduel est très court, fragile et non négociable tel quel.** Il dépend d'un BPA pris après coup, vient surtout de la baisse des mauvaises surprises et ne résiste pas aux frais à l'achat. Sa taille varie aussi selon les années (de -0,12 à +1,09 point).
4. **Ce n'est pas une preuve générale d'absence d'effet.** Sans prévisions d'analystes ni prix intraday, on ne teste qu'une version approximative, à l'échelle de la journée. De mémoire, la littérature décrit une dérive après les résultats avec de vraies surprises : à vérifier avant de la citer. Cette étude ne la confirme pas sur cette période, avec cette mesure.

## Ce que l'audit a changé

Codex a recalculé 30 événements et vérifié les horodatages sur les index SEC. Corrections appliquées :

| Défaut trouvé | Mesure | Correction |
|---|---|---|
| `accepted` n'est pas toujours en UTC | 22 heures fausses sur 99 (intervalle de 15 à 31 %), 5 entrées changées, 8 sur 8 pour les disparues du tirage | Seule `filing_date` sert, entrée le lendemain |
| BPA pas encore disponible à l'entrée après 8-K | 79 % des cas | Cas séparé, nommé rétrospectif |
| Historique de surprise non causal, même après dépôt | 1 598 cas | Seuls les chiffres déjà déposés entrent |
| Placebo par permutation invalide | p = 0 pour un t de 1,18 | Tests par trimestres (Newey-West, blocs) |
| Classement de liquidité utilisant le reste du trimestre | 3 879 appartenances changées | Rang connu la veille de l'entrée |
| Indice de référence rééquilibré chaque jour | Multiple de 2,43 contre 1,57 pour un témoin gelé par trimestre | SPY |
| Rendements de disparus au-delà de la fin des données | 7 cas à 60 séances | Horizon exigé pour tous |

Cette révision a réduit l'effet principal de +0,54 pt (t = 3,5) à +0,45 pt (t = 3,27).

## Limites

- **Dates imparfaites.** Le 8-K peut suivre le communiqué : au moins 2 % de retards d'un jour dans le tirage de l'audit, qui n'a pas mesuré les retards de quelques heures. La règle du dernier 8-K se trompe parfois vers le tard (NKE, juillet 2018, retient une transcription cinq jours après). L'entrée est alors trop tardive, ce qui réduit l'effet mesuré. Acheter le lendemain perd aussi l'ouverture du jour J pour les publications du matin.
- **Le BPA comptable n'est pas forcément le chiffre qui compte.** Au moins 15 communiqués sur 24 de l'audit mettent en avant un BPA ajusté différent. Sur 24, 4 BPA diffèrent du communiqué, dont une vraie différence de version (BLFS) et trois quatrièmes trimestres reconstitués.
- **Biais du survivant.** 28 % des actions disparues sont couvertes, contre 67 % des vivantes, et elles fournissent 10 % des événements. L'hypothèse de sortie change très peu le résultat (moins de 0,02 pt à 60 séances).
- **Faux rattachements signalés, non corrigés.** OND (lié à Procter & Gamble) et TWC (lié à Wendy's), sans ligne retenue dans cette étude. À traiter au prochain nettoyage.
- **Effectif réel.** 27 trimestres, soit bien moins d'observations indépendantes que d'événements. 24 tests sur la même question, déjà regardés une fois avant révision.
- **Pas de news, pas d'intraday.** Le marché réagit en minutes : tester cette fenêtre demanderait des barres à la minute, disponibles seulement pour quelques titres.
