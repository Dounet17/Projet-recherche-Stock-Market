# Protocole : réaction des cours aux dépêches de résultats, à la minute

**Figé le 07/11/2026, avant tout calcul de rendement.** Aucun rendement n'a été lu ni calculé pour ce signal. Relu et accepté par DavidTom, **sans audit indépendant** : une relecture de Dounet17 ou d'un auditeur reste souhaitable, et toute modification après ce commit doit être datée et justifiée ici. Il reprend le protocole proposé par l'audit (`news/AUDIT_TRI_NEWS_2.md`, section « Protocole acceptable ») et l'adapte aux barres à la minute.

## Vocabulaire

- **Dépêche** : titre Benzinga du type « Acme Q3 EPS $1.10 Beats $1.00 Estimate ».
- **BPA** : bénéfice par action.
- **Écart cité** : BPA publié moins estimation citée dans la même dépêche. Ce n'est **pas** un consensus vérifié : il faut l'appeler ainsi dans l'article, jamais « surprise du consensus ».
- **Rendement anormal** : rendement de l'action moins celui de SPY sur exactement la même fenêtre. Il retire le mouvement général du marché.
- **Heures étendues** : de 4 h à 9 h 30 et de 16 h à 20 h, heure de New York. Peu de transactions, écarts de prix plus larges.
- **Correction de Holm** : quand on fait plusieurs tests, la chance d'un faux succès augmente. Holm relève le seuil de chaque test pour garder 5 % de risque au total.

## Question

Après une dépêche de résultats, le cours continue-t-il dans le sens de l'écart cité une fois qu'on peut acheter ? Et un investisseur qui réagit tôt gagne-t-il de l'argent après frais ?

Hypothèse de l'équipe : une partie du mouvement viendrait de traders humains plus lents. L'hypothèse de départ du projet reste que non.

## Ce qui a déjà été vu, donc ne peut plus guider les choix sans le dire

1. L'étude quotidienne des publications (`RESULTATS_EVENEMENTS.md`) : réaction forte avant l'entrée, rien de négociable après, avec un autre signal (BPA SEC). Ce protocole est donc conçu en connaissant ce résultat.
2. Le placebo du contrôle des chiffres (`TRI_NEWS.md`), sans rendement.
3. Les mesures suivantes, faites le 07/11/2026 **sans lire aucun prix**, seulement des heures, des nombres de barres et des montants échangés passés :

| Mesure sur le groupe principal (17 659 publications) | Valeur |
|---|---|
| Dépêche après 16 h | 9 348 |
| Dépêche entre 4 h et 9 h 30 | 8 208 |
| Dépêche pendant la séance | 44 |
| Nuit, soir, week-end | 59 |
| Écart cité positif / négatif / nul | 13 404 / 4 220 / 35 |
| Montant échangé médian sur 20 séances : moins de 1 M$, 1 à 10 M$, 10 à 100 M$, plus de 100 M$ | 1 547 / 4 190 / 7 439 / 4 480 |

Sur un tirage des dépêches vérifiées : au moins une barre dans les 5 minutes qui suivent la dépêche pour **21 %** de celles d'avant l'ouverture et **39 %** de celles d'après la clôture, mais dans les 5 premières minutes de la séance régulière pour **92 %** des titres sous 1 M$ et **99 % ou plus** au-dessus. Avant l'ouverture du jour d'entrée, médiane de 26 barres pour les titres au-dessus de 100 M$, de 0 à 2 pour les autres.

**Conséquence.** Une réaction dans les minutes qui suivent la dépêche n'est testable que sur les titres très liquides. Pour les autres, la première occasion réaliste est l'ouverture de la séance régulière, là où arrive la masse des humains.

## Données figées

- Événements : `data/news/earnings_surprise_verified.parquet`, version du commit qui fige ce protocole, avec son empreinte SHA-256.
- Barres : `data/events/minute_bars/` et `data/events/minute_bars_extra/`. Jointure **par symbole et séance depuis la table corrigée** : les 1 082 couples d'anciens symboles faux ne servent jamais. Lignes `mode=current` écartées.
- Cours quotidiens : `data/universe_clean/`, avec ses règles (`suspect_print` manquant, trois hypothèses de sortie pour les disparues).
- Période : 2018-2024 uniquement. Toute fenêtre doit finir au plus tard le 31/12/2024.

Empreintes SHA-256 au gel (code au commit `15632db`). Pour un dossier, empreinte de la liste triée des empreintes de ses fichiers `bars_*.csv.gz`. Le code de l'étude doit vérifier ces valeurs avant tout calcul et s'arrêter si l'une diffère.

| Données | SHA-256 |
|---|---|
| `data/news/earnings_surprise_verified.parquet` | `ca90aee8bb65fdf34ad1eb505efe659ef4c1378ccbf49ef917daddf87f5a8a83` |
| `data/universe_clean/prices_dev.parquet` | `c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15` |
| `data/universe_clean/securities_dev.parquet` | `d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161` |
| `data/calendar.parquet` | `87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03` |
| `data/events/minute_bars/` (1 735 fichiers) | `86515248394c6ea0ec1cd2590ac456bed0097b770eb1dce4c51341c32f7b3c30` |
| `data/events/minute_bars_extra/` (1 096 fichiers) | `7046342a25b1c21996faaef5681a90ea2e421a98420a11b922ae7de972f9df43` |

## Échantillons

- **Principal** : `principal` vrai (chiffre retrouvé comme BPA du trimestre dans le communiqué, base explicite ajustée ou comptable) et `security_active` vrai.
- **Large, secondaire** : `verified` vrai, base non étiquetée comprise.
- **Achetable** : cours brut d'au moins 5 $ et montant échangé médian sur 20 séances d'au moins 1 M$, tous deux connus la veille de l'entrée.
- Groupes : signe de l'écart cité, positif ou négatif. Les écarts nuls sont décrits à part. **Aucun seuil ni aucun autre découpage n'est choisi après lecture des rendements.**

## Horloge

- Disponibilité : `available_at` (dernier horodatage de la dépêche), plus **5 minutes** de latence.
- **Entrée à l'ouverture** : prix d'ouverture de la première barre de 9 h 30 de la première séance régulière qui commence après cette heure. Une dépêche arrivée après 9 h 25 attend la séance suivante.
- **Entrée en heures étendues** (secondaire, titres au-dessus de 100 M$) : prix d'ouverture de la première barre qui commence au moins 5 minutes après `available_at`, dans les 60 minutes. Sans barre dans ce délai, pas d'entrée.
- Une barre est datée par son début : on n'utilise jamais une barre qui commence avant l'heure d'entrée.
- Sans barre dans la première minute de la séance, on prend la première barre des 5 minutes suivantes, sinon pas d'entrée. Le nombre de cas est publié.

## Tests confirmatoires, corrigés ensemble par Holm

| Test | Fenêtre | Mesure |
|---|---|---|
| **H1** | Entrée à l'ouverture, sortie à la clôture du même jour (barre de 15 h 59) | Rendement anormal moyen, positifs moins négatifs |
| **H2** | Entrée à l'ouverture, sortie à la clôture de la 5e séance (cours quotidiens) | Rendement anormal moyen, positifs moins négatifs |
| **H3** | Comme H1, achat des seuls écarts positifs, après frais | Rendement anormal net moyen, contre 0 |

H1 et H2 disent si le cours continue après l'ouverture. H3 dit si c'est gagnable : sans vente à découvert, seul l'achat est testé.

## Analyses secondaires, corrigées entre elles et annoncées comme telles

1. Fenêtres de 30 et 60 minutes après l'ouverture, 1 et 20 séances.
2. Entrée à 9 h 35 au lieu de 9 h 30, pour une réaction humaine plus réaliste.
3. **Heures étendues** : sur les titres au-dessus de 100 M$, entrée 5 minutes après la dépêche, sortie à l'ouverture régulière. C'est le test le plus direct de l'idée « avant la masse des humains ».
4. Échantillon large (`verified`).
5. Par base (ajustée, comptable), par année, par tranche de liquidité, par dépêche avant ouverture ou après clôture.

## Décomposition descriptive, sans test

Pour chaque groupe, part du mouvement entre la clôture précédant la dépêche et la clôture du jour d'entrée qui est déjà faite :
1. 5, 30 et 60 minutes après la dépêche (titres liquides) ;
2. à l'ouverture régulière ;
3. 30 minutes après l'ouverture.

Elle répond à la question « où se forme le prix », même si aucun test ne réussit.

## Frais

Coût par côté selon le montant échangé de la veille, comme `CADRE_EXPERIENCES.md` : 5 pb au-dessus de 100 M$, 15 pb au-dessus de 10 M$, 40 pb au-dessus de 1 M$. En heures étendues, coûts doublés. Sensibilité avec frais doublés partout. Ces valeurs sont des hypothèses, pas des mesures : les barres ne donnent ni l'offre ni la demande.

## Portefeuille de 10 000 USD, descriptif

Chaque jour, le capital est réparti à parts égales entre les achats de H3, de l'ouverture à la clôture, et reste en liquidités à 0 % les autres jours. Comparaison avec SPY conservé sur 2018-2024 et avec SPY acheté à l'ouverture et vendu à la clôture les mêmes jours. Comptabilité en USD, sans EUR/USD ni fiscalité.

## Statistiques

- Moyennes par trimestre civil, puis t sur les 28 trimestres : les annonces d'une même saison ne sont pas indépendantes. Sensibilité par écarts-types regroupés par date et par société.
- Publier pour chaque test : effectifs, exclusions, différence, intervalle de confiance à 95 %, p brute et p corrigée.
- Résultats nuls et négatifs publiés au même titre que les autres.

## Contrôles prévus d'avance

1. **Placebo de la veille** : même calcul de H1 sur la séance précédant la dépêche. On attend un écart nul.
2. **Placebo de signe** : signes tirés au hasard au sein de chaque trimestre, 1 000 fois.
3. **Anti-fuite dans le code** : arrêt si une entrée précède `available_at` plus 5 minutes, si une barre utilisée commence avant l'entrée, ou si une date dépasse le 31/12/2024.
4. **Contrôle des barres** : rendements extrêmes (plus de 50 % en une minute) listés et vérifiés avant interprétation, jamais retirés selon leur signe.

## Limites connues avant calcul

- `available_at` n'est qu'une borne. La dépêche peut avoir été vue plus tôt, et 48 % des dépêches vérifiées sont postérieures au dépôt SEC.
- Un chiffre faux passe encore le contrôle dans 4 à 8 % des cas.
- 38 % du groupe principal date de 2024. Les sociétés disparues passent moins souvent les filtres.
- Barres s'arrêtant à 18 h 59 en hiver et vers 18 h le vendredi. Le prix d'ouverture de la première barre peut différer du prix officiel de l'enchère d'ouverture.
- Une barre n'existe que s'il y a eu une transaction : un prix peut être ancien de plusieurs minutes pour un titre peu échangé.

## Gel et exécution

1. Relu par DavidTom et figé par ce commit. À partir de là, plus de changement de règle.
2. Code et tests sur données synthétiques, sans lancer sur les vrais cours. Une relecture du code avant lancement est souhaitable.
3. Un seul lancement complet. Toute variante ajoutée ensuite est exploratoire et inscrite au journal comme telle.
4. Une validation sur 2025-2026 demanderait les news, les barres et le nettoyage de cette période avec les mêmes règles, et l'accord du professeur.

## Décisions prises au gel

1. Groupe principal : `principal` (17 659 publications), comme le recommandait l'audit. `verified` reste une analyse secondaire.
2. Fenêtre de H1 : de l'ouverture à la clôture du même jour. Les fenêtres de 30 et 60 minutes restent secondaires.
3. Pas de vente à découvert, ni dans les tests confirmatoires ni dans les secondaires : l'analyse principale du projet s'en passe.

## Précisions d'implémentation, 07/11/2026, avant tout lancement

Écrites en codant `src/minute_study.py` et `reports/run_minute_study.py`, sans aucun rendement lu. **Requalification après l'audit de Codex** (`minute_study/AUDIT_CODEX.md`) : contrairement à ce qui était écrit ici, les points 4, 8, 11 et 13 changeaient une règle du gel (SPY plus forcément sur les mêmes minutes, délai étendu porté à 65 minutes, ajout de Newey-West, contrôle des variations extrêmes réduit), et le point 3 accepte une dernière transaction ancienne comme prix de vente. Rien n'indique un choix fait après lecture des rendements, mais ce ne sont pas de simples précisions.

1. **Attente à l'ouverture** : la barre d'entrée doit commencer dans les 6 premières minutes (9 h 30 à 9 h 35 inclus). Même règle pour l'entrée à 9 h 35 (jusqu'à 9 h 40) et pour la sortie des heures étendues.
2. **Dépêche à 9 h 25 pile** : entrée le jour même ; une seconde plus tard, séance suivante.
3. **Sortie à la clôture** : clôture de la dernière barre qui commence avant l'heure de clôture du calendrier, donc avant 13 h les jours écourtés.
4. **SPY** : achat à la première barre qui commence à partir de la minute d'entrée du titre, vente à la dernière barre qui commence au plus tard à la minute de sortie du titre.
5. **Séance témoin** : dernière séance entièrement terminée au moment de la dépêche. Son dernier prix régulier sert aussi de point de départ à la décomposition.
6. **Prix connu à un instant** : clôture de la dernière barre déjà terminée, même ancienne, pour la décomposition.
7. **Séances différentes** : chaque prix est multiplié par le facteur d'ajustement de sa séance ; un facteur manquant (`suspect_print`) rend la mesure vide.
8. **Heures étendues** : barre d'entrée entre 5 et 65 minutes après la dépêche et avant l'ouverture régulière ; liquidité de la veille de l'entrée au-dessus de 100 M$.
9. **Cours quotidiens** : horizon de k séances = ouverture de l'entrée à la clôture de la séance k ; un trou de cotation garde le dernier cours ; une sortie de cote applique le rendement de sortie (hypothèse de base, optimiste et pessimiste publiées).
10. **H3** : rendement net du titre (frais aller et retour) moins le rendement brut de SPY sur les mêmes minutes.
11. **Trimestre** : celui de la séance d'entrée. Newey-West avec un retard d'un trimestre.
12. **Portefeuille** : poids égaux entre les achats d'une même séance ; SPY conservé paie 5 pb à l'achat et à la vente.
13. **Variation extrême** : listée seulement dans la séance régulière d'entrée.

**Essai à blanc** (`--dry-run`, empreintes conformes, aucune barre ni aucun rendement lus) : 43 007 événements vérifiés et cotés, dont 15 459 dans le groupe principal achetable, 12 103 positifs et 3 356 négatifs, 4 465 au-dessus de 100 M$, 7 534 dépêches avant l'ouverture.

## Corrections après l'audit, 07/11/2026, après lecture des résultats

Audit indépendant de Codex : `minute_study/AUDIT_CODEX.md`. Corrections faites **après avoir vu la première version des résultats**, donc annoncées comme telles. Les deux versions sont publiées (`minute_study/summary_v1.json` et `summary.json`) ; aucune n'est retenue pour son résultat.

1. **D1** : plus d'achat en heures étendues quand une séance régulière s'intercale entre la dépêche et l'entrée (13 achats faits en séance, avec une liquidité postérieure).
2. **D2** : SPY exactement sur les mêmes minutes que le titre, sinon pas de rendement SPY, comme le prévoyait le gel. Annule la précision 4.
3. **D3** : barre d'achat en heures étendues au plus 60 minutes après la dépêche, comme le prévoyait le gel. Annule le 65 de la précision 8.
4. **D4** : une sortie de cote le dernier jour de la fenêtre est comptée, comme dans `lab`.
5. **D5** : décomposition calculée sur les mêmes événements à chaque point.
6. **D6** : le t ordinaire sur les 28 trimestres, prévu par le gel, est publié et corrigé par Holm à côté de Newey-West.
7. **D7** : variations extrêmes cherchées dans toutes les barres utilisées, y compris à l'intérieur d'une barre. Annule la précision 13.
