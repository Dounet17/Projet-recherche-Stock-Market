# Protocole : suivre les robots ou parier sur le rebond après une minute brutale (H15, H16)

**Figé le 08/11/2026, avant tout calcul de rendement de stratégie.** Relu et accepté par DavidTom, sans audit indépendant du texte ; le code sera relu par Codex avant tout calcul. Toute modification après ce commit doit être datée ici et dite « changement de règle » si elle en est un. Hypothèses H15 et H16 du registre (`registre_hypotheses.csv`). Même démarche que les études précédentes : règles écrites d'avance, code relu par Codex avant tout lancement, une seule validation.

## Vocabulaire

- **Minute brutale (choc)** : une minute où le cours d'un ETF bouge beaucoup plus que d'habitude.
- **Suivre les robots (H15)** : prendre la même direction que le choc, juste après lui.
- **Rebond (H16)** : parier que le choc se retourne en partie, par exemple acheter après une chute brutale.
- **ETF** : fonds coté qui réplique un indice. SPY (S&P 500), QQQ (Nasdaq-100), DIA (Dow Jones). Ils coûtent très peu à échanger, ce qui donne à ces règles leur meilleure chance.
- **Vente à découvert** : vendre un titre emprunté pour le racheter plus bas. Sur ces ETF, c'est simple et peu coûteux, mais le cadre principal du projet s'en passe : elle n'apparaît qu'en analyse secondaire.

## Question

Après une minute brutale sur SPY, QQQ ou DIA, un investisseur qui réagit une minute plus tard gagne-t-il de l'argent, après frais, en suivant le mouvement (H15) ou en pariant sur son retournement (H16) ?

## Ce qui a déjà été vu

1. L'étude des dépêches à la minute (H10) : sur les actions, le mouvement est surtout fait en 5 minutes ; acheter après une bonne nouvelle perd. Ce résultat porte sur des actions et des dépêches de résultats, pas sur des indices sans news.
2. Les mesures suivantes, faites le 08/11/2026 sur la seule période de conception 2018-2021, **sans aucun rendement de stratégie** : 390 minutes régulières dans chaque séance pour les trois ETF ; nombre de chocs selon le seuil k (écart de la minute rapporté à l'écart habituel, défini plus bas) :

| Seuil k | Chocs par an et par ETF | Hausses / baisses (2018-2021, trois ETF) | Même minute sur 2 ou 3 ETF |
|---|---:|---:|---:|
| 8 | 124 | 658 / 832 | 459 |
| 10 | 49 | 223 / 362 | 186 |
| 12 | 21 | 92 / 165 | 80 |
| 16 | 7 | 31 / 52 | 27 |

Les plus grands chocs tombent sur des annonces : décisions de la Fed à 14 h (18/09/2019, 16/06/2021), chiffres économiques à 10 h (03/10/2019), krach de volatilité du 05/02/2018, annonce d'une procédure de destitution (24/09/2019). Les seuils 4 et 6 donnent 1 656 et 385 chocs par an et par ETF : du bruit ordinaire, écartés.

## Données à figer

- `data/events/index_bars/` : barres d'une minute de DIA, QQQ et SPY, 1 761 séances 2018-2024, prix bruts, lignes `mode=self` seulement. Une barre est datée par son début.
- `data/calendar.parquet` : heures d'ouverture et de clôture, séances écourtées comprises.

Empreintes SHA-256 au gel (code au commit `8f95eb3`), à vérifier par le code avant tout calcul. Pour le dossier, empreinte de la liste triée « empreinte  nom » de ses fichiers `bars_*.csv.gz`.

| Données | SHA-256 |
|---|---|
| `data/events/index_bars/` (1 761 fichiers) | `216157627e4de2d795c86c68e7cf7fef19903bd173c76bd3b54c4efbfc509cd8` |
| `data/calendar.parquet` | `87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03` |

## Définition d'un choc

- Séance régulière seulement. Rendement d'une minute : log(clôture de la barre / clôture de la barre précédente), seulement si les deux barres se suivent.
- **Écart habituel** σ d'un ETF pour une séance : médiane, sur les **5 séances précédentes**, de l'écart absolu médian × 1,4826 des rendements d'une minute de la 15e minute à la clôture. Il n'utilise que des séances terminées.
- **Choc** à la minute t : |rendement| ≥ k × σ, avec t au moins 15 minutes après l'ouverture (le début de séance est bruité).
- Direction du choc : signe du rendement.

## Opération

- La barre du choc couvre [t, t + 1 min) : elle est connue à t + 1. **Entrée à l'ouverture de la barre qui commence à t + 2**, soit une minute de délai pour détecter et passer l'ordre.
- **Sortie** à la clôture de la barre qui commence à entrée + h − 1, soit une tenue de h minutes.
- Une seule position à la fois par ETF : un choc pendant une tenue est ignoré. Pas d'entrée si la sortie dépasserait la dernière barre de la séance, ni si une barre d'entrée ou de sortie manque.
- **H15, confirmatoire** : achat après un choc à la hausse.
- **H16, confirmatoire** : achat après un choc à la baisse.
- Ces deux versions sont à l'achat seulement, comme le cadre principal du projet.

**Frais** par côté : 1 point de base pour SPY et QQQ, 2 pour DIA, dont l'écart entre prix d'achat et de vente est plus large. Sensibilités : 3 et 5 points de base par côté, et un **prix d'exécution défavorable** (achat au plus haut de la barre d'entrée, vente au plus bas de la barre de sortie), car l'écart entre prix d'achat et de vente s'élargit pendant un choc.

## Conception sur 2018-2021

Six variantes par hypothèse : k ∈ {8, 12} × h ∈ {5, 15, 30} minutes.

Mesure de chaque variante : rendement net moyen par opération, et son t calculé sur les **moyennes par séance** (les trois ETF réagissent souvent à la même minute).

**Règle de choix figée d'avance** : pour chaque hypothèse, la variante au t le plus élevé. Elle ne passe en validation que si son rendement net moyen est positif ; sinon l'hypothèse est déclarée en échec dès la conception et la période de validation n'est pas consommée.

Les résultats de conception sont publiés en entier, les six variantes de chaque hypothèse comprises.

## Validation sur 2022-2024, une seule fois

- La variante choisie de chaque hypothèse, sans aucun changement.
- **Test** : rendement net moyen par séance contre 0, t ordinaire sur les séances avec au moins une opération, p bilatérale. Holm sur les hypothèses validées (au plus deux).
- **Placebo** : mêmes ETF, même nombre d'opérations, mêmes heures de la journée et mêmes années, mais à des minutes tirées au hasard sans choc, 1 000 fois. Il mesure ce que rapporte une position quelconque de même durée.
- **Portefeuille de 10 000 USD** : un tiers par ETF, investi en totalité pendant chaque opération, en liquidités à 0 % sinon. Comparé à SPY conservé et à QQQ conservé sur 2022-2024, et à l'absence d'opération.

## Analyses secondaires

1. **Versions symétriques avec vente à découvert** : H15 vend à découvert après une baisse brutale, H16 après une hausse brutale. Hors du cadre principal, publiées à part.
2. Résultats par ETF, par année, par seuil, et pour les chocs à l'heure ronde (10 h, 14 h, 14 h 30), où tombent les annonces programmées.
3. **Descriptif** : part des chocs de la validation qui ont une dépêche Benzinga à moins de 5 minutes, pour relier ces chocs aux news et aux déclarations politiques.

## Contrôles prévus d'avance

1. Anti-fuite dans le code : arrêt si une entrée commence avant t + 2, si l'écart habituel utilise la séance du choc, ou si une date dépasse le 31/12/2024.
2. Tests sur données inventées : détection d'un choc, délai d'une minute, tenue exacte, position unique, séance écourtée, barre manquante.
3. Relecture du code par Codex **avant** le calcul de conception.

## Limites connues avant calcul

- Le prix d'ouverture d'une barre d'une minute n'est pas un prix garanti : pendant un choc, l'exécution réelle peut être nettement moins bonne. Le prix défavorable en donne une borne.
- Les frais sont des hypothèses.
- Barres limitées aux transactions consolidées ; pas de carnet d'ordres.
- 2018-2021 sert à choisir : six variantes y sont essayées, et le choix favorise la chance. Seule la validation compte.
- Une réussite sur 2022-2024 devrait encore être confirmée en temps réel sur le compte Alpaca Paper Trading, avant toute conclusion.

## Gel et exécution

1. Relu et figé par ce commit, avec les empreintes des données ; statut `protocole_fige` au registre.
2. Code et tests sur données inventées ; relecture du code par Codex.
3. Conception sur 2018-2021, publiée en entier.
4. Une seule validation sur 2022-2024 pour les variantes retenues.

## Décisions prises au gel

1. **Délai d'une minute** après le choc : entrée à l'ouverture de la barre qui commence à t + 2.
2. **Seuils 8 et 12** : environ 124 et 21 chocs par an et par ETF sur 2018-2021.
3. **Achat seulement en confirmatoire**, la vente à découvert en analyse secondaire.
