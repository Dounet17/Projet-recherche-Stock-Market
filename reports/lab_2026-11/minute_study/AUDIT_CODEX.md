# Audit indépendant de l'étude des dépêches de résultats à la minute

Audit réalisé le 07/11/2026 sur `etude-news`, HEAD `2137c2b`. Référence initiale : protocole au commit `08a366e` ; ajout des 13 précisions et du code : `3326735`.

## Verdict

**Les résultats centraux tiennent comme résultats descriptifs et statistiques de ce protocole : H1 positif, H2 non concluant et H3 perdant après les frais supposés.** Les calculs de H1, H3, de la décomposition et du portefeuille sont reproduits indépendamment. L'audit ne trouve pas de fuite d'information dans les entrées régulières et leurs filtres de liquidité.

**Le protocole initial n'a cependant pas été appliqué sans changement. Les heures étendues présentent de vrais défauts, et la preuve annoncée d'une fenêtre entre robots et humains ne tient pas.** La significativité secondaire S6 est fragile aux corrections ; les 65 % et 92 % décrivent des rapports de moyennes, sans établir la vitesse d'incorporation d'une information nouvelle ni un mécanisme humain. Aucun défaut constaté n'inverse le résultat défavorable à l'achat des écarts positifs.

Aucun défaut bloquant pour la reproduction de H1/H3 n'est établi. Les défauts graves et mineurs ci-dessous empêchent en revanche de valider le rapport sans réserves.

## Périmètre et contrôles de conservation

Lecture de `CLAUDE.md`, du protocole dans ses deux versions, de `src/minute_study.py`, du lanceur, des tests, du rapport, du JSON et des données indiquées. Lecture complémentaire de `src/events.py`, `src/universe_data.py`, `src/lab.py`, du nettoyage et des passages pertinents de `src/universe_clean.py`. Aucun fichier de données postérieur au 31/12/2024 ni dossier de validation n'a été ouvert ; `.env` et les clés n'ont pas été consultés.

Les six empreintes du gel ont été recalculées indépendamment : **toutes conformes**, dont les listes de 1 735 et 1 096 fichiers de barres. La table contient 43 007 événements vérifiés et cotés, avec identifiants uniques. Le groupe principal achetable non nul contient 15 459 événements ; aucun doublon société/séance d'entrée dans ce groupe.

Le lanceur de production n'a pas été exécuté, même en mode à blanc. Les 32 tests existants ont passé avec `venv/bin/python -B tests/test_minute_study.py`. Les scripts de vérification et leurs résultats intermédiaires sont uniquement dans `/tmp` ; ce rapport est le seul nouveau fichier du dépôt. Les modifications préexistantes de `.gitignore` et le fichier non suivi `reports/build_vault.py` sont hors audit et n'ont pas été touchés.

## 1. Fidélité au gel et nature des 13 précisions

L'ajout est bien daté avant le commit des résultats. Cela documente des choix avant le lancement déclaré ; cela ne transforme pas tous ces choix en précisions neutres. Le tableau confronte les lignes 145 à 157 du protocole actuel au texte présent dans `08a366e`.

| Nº | Nature | Motif et effet |
|---|---|---|
| 1 | Neutre | 9 h 30 à 9 h 35 inclus correspond à la première minute puis aux cinq suivantes, ligne 70. Extension cohérente aux autres entrées. |
| 2 | Neutre | Le texte initial dit qu'une dépêche arrivée **après** 9 h 25 attend ; 9 h 25 pile est compatible avec les cinq minutes de latence. |
| 3 | Mixte, écart mineur | Utiliser 13 h les jours écourtés corrige raisonnablement l'exemple de 15 h 59. En revanche, autoriser n'importe quelle dernière barre avant la clôture assouplit l'exigence d'une barre de clôture : un dernier échange ancien devient une vente supposée à ce prix. Cette hypothèse d'exécution aurait dû être explicite au gel. |
| 4 | Changement | SPY n'est plus obligatoirement sur exactement les mêmes minutes, contrairement à la définition initiale, ligne 10. Il peut commencer plus tard et terminer plus tôt. Effet constaté en heures étendues : défaut D2. |
| 5 | Neutre | Dernière séance entièrement terminée : interprétation cohérente de la séance précédant la dépêche et de sa dernière clôture. |
| 6 | Neutre avec limite | Dernière barre terminée : causalement correct et compatible avec la limite initiale sur les prix anciens. Une absence de transaction ne mesure toutefois pas un prix latent inchangé. |
| 7 | Neutre | Les facteurs par séance évitent les faux rendements lors des fractionnements ; les cours suspects étaient déjà à traiter comme manquants. |
| 8 | Changement | Le plafond devient 65 minutes après la dépêche, au lieu de 60 dans la formulation initiale, ligne 68. La veille de l'ouverture régulière est aussi substituée implicitement à la veille de l'achat réel en heures étendues. Voir D1 et D3. |
| 9 | Précision admissible, avec défaut | Compter la séance d'entrée comme séance 1 est cohérent avec H2. Le report du dernier cours pour les trous est une convention nouvelle mais usuelle, déclarée avant calcul. Les trois hypothèses de sortie sont déjà exigées. Leur application présente toutefois un défaut de borne : D4. |
| 10 | Neutre | H3 reste un rendement anormal net : frais sur le titre, SPY brut servant de référence. Le portefeuille SPY est un calcul distinct avec ses frais. |
| 11 | Mixte | Le trimestre de l'entrée est cohérent. **Newey-West à un retard change l'estimateur de variance** : le gel annonçait un t sur les 28 moyennes trimestrielles, sans cette spécification. Ce choix peut être raisonnable mais n'est pas neutre. Les conclusions H1/H3 restent les mêmes avec le t ordinaire : D6. |
| 12 | Neutre | Poids égaux déjà prévus ; 5 pb à l'achat et à la vente de SPY concordent avec les frais du protocole. |
| 13 | Changement | Restreindre la recherche de variations extrêmes à la séance régulière d'entrée réduit le contrôle initial, alors que les heures étendues et la décomposition emploient d'autres barres. Voir D7. |

La réponse à la question « sans changer une règle », ligne 143, est donc **non**. Rien dans cet audit ne démontre une sélection de variantes après lecture des rendements ; les divergences existaient dans le commit de code antérieur aux résultats. Elles restent des divergences à présenter comme telles.

## 2. Recalcul indépendant des résultats principaux

Calculs sans import du moteur de l'étude ni du lanceur. Les trimestres sont reconstruits depuis `entry_date` car cette colonne dérivée n'est pas enregistrée dans le parquet.

Pour H1 : moyenne par trimestre de la différence des deux moyennes de `h1 - h1_spy`. Pour H3 : moyenne par trimestre, parmi les positifs, de `(1+h1)*(1-cost_bps/10000)^2 - 1 - h1_spy`. Pour la variance de Newey-West à un retard : avec les 28 observations centrées d, `SE² = (sum(d²) + sum(d[t]*d[t-1])) / 28²`. P bilatérales de Student à 27 degrés de liberté, puis Holm sur les trois tests.

| Mesure | Recalcul indépendant | IC 95 % | p brute | p de Holm |
|---|---:|---|---:|---:|
| H1, 12 017 positifs / 3 322 négatifs | +0,5218375 point | +0,239289 à +0,804386 | 0,000770296 | 0,002193279 |
| H2, depuis les rendements quotidiens enregistrés | +0,3729912 point | -0,087317 à +0,833299 | 0,107957196 | 0,107957196 |
| H3, 12 017 positifs | -0,3056167 point | -0,470227 à -0,141006 | 0,000731093 | 0,002193279 |

**Reproduction des valeurs du JSON à la précision numérique affichée.** La vérification directe des barres ci-dessous porte sur H1/H3 et la décomposition ; H2 n'a pas fait l'objet d'une reconstruction complète indépendante de tous les cours quotidiens.

| Décomposition | Rapport reproduit | Même ensemble d'événements au numérateur et au dénominateur |
|---|---:|---:|
| Tous les titres, part à l'ouverture | 92,097464 % | **92,734627 %** |
| Titres liquides, part à l'ouverture | 93,969971 % | **93,612814 %** |
| Titres liquides, part à cinq minutes | 64,791887 % | **64,625923 %** |

Le passage à un ensemble commun est une sensibilité descriptive de l'audit, pas un nouveau test confirmatoire. Il explique le défaut D5 sans remettre en cause l'ordre de grandeur.

Le portefeuille est recalculé par moyenne des rendements nets des achats de chaque jour puis composition : **43,17614338 USD**, sur **1 211 jours** d'achat ; rendement moyen par jour d'achat : **-0,3824727 %**. Avec frais doublés, le JSON donne 0,856935 USD. Sans frais sur les mêmes achats, le calcul indépendant donne 2 162,58 USD : la perte du portefeuille ne vient donc pas uniquement des frais. Cela ne contredit pas une petite moyenne brute par événement, car le portefeuille pondère les jours et compose des rendements variables.

### Reconstruction depuis les fichiers de barres

Tirage de **70 événements**, cinq positifs et cinq négatifs par année, générateur `numpy.random.default_rng(937)`, sans sélection sur les rendements. Ajout de contrôles ciblés distincts : douze entrées retardées, huit grands écarts entre mesure quotidienne et mesure minute, les treize opérations suspectes en heures étendues et la séance écourtée disponible dans l'échantillon large. Après dédoublonnage : **104 événements**, **173 séances de fichiers**.

Lecture directe des CSV des deux dossiers, filtre `mode == 'self'`, sélection par symbole et séance. Facteur quotidien `adj_close / close` propre à chaque séance, masque `suspect_print`, puis sélection des ouvertures et clôtures par comparaisons explicites des horodatages. Aucun appel aux fonctions de calcul de production.

**Sur les 104 événements : erreur absolue maximale exactement 0** pour `h1`, `h1_spy`, `net_ab_h1`, `cum_open`, `cum_open_spy`, `cum_close` et `cum_close_spy`. Aucun désaccord sur les valeurs manquantes, aucune de ces sept mesures manquante dans ce tirage. Les 220 817 barres retenues sont en mode `self`, sans doublon symbole/heure entre les dossiers ni différence `requested`/`returned` dans ce sous-ensemble.

Sur les 70 événements aléatoires seulement, les moyennes anormales H1 valent +0,217436 % pour les positifs et +0,137159 % pour les négatifs ; H3 des positifs vaut -0,063456 % ; la part descriptive à l'ouverture vaut 98,070565 %. Ces valeurs sont celles du **petit tirage**, pas des estimateurs devant égaler ceux du rapport complet. Ce sont les 70 mesures individuelles et leurs agrégats calculés sur les mêmes identifiants qui reproduisent exactement les valeurs du parquet.

Exemple de séance écourtée : AZZ, id `11970779`, 03/07/2018, entrée à 13 h 31 UTC, sortie au terme de la barre de 16 h 59 UTC, soit **13 h à New York** ; rendement brut -1,422764 % environ. La sortie respecte le calendrier ; aucune entrée du groupe principal non nul ne tombe sur une séance écourtée dans les données auditées.

## 3. Défauts constatés, preuves et effets

### D1. Des opérations régulières sont classées en heures étendues, avec une liquidité future : grave

**Preuve :** `src/minute_study.py:135`, notamment lignes 137 à 145. La condition est seulement `available + 5 min < ouverture régulière retenue`. Pour une dépêche reçue après 9 h 25, cette ouverture est celle du lendemain : une barre de la séance en cours devient donc une entrée admissible en « heures étendues ». Aucun masque 4 h à 9 h 30 / après clôture n'est appliqué. `reports/run_minute_study.py:85` et lignes 87 à 90 utilisent la veille de l'entrée régulière, même si l'achat secondaire a lieu ce jour-là avant sa clôture.

**Mesure exhaustive sur les 3 757 rendements étendus bruts disponibles du groupe principal liquide : 13 achats réguliers**, tous avec une liquidité arrêtée après l'achat. Identifiants : `12128473`, `13656369`, `19263459`, `19863369`, `25409042`, `26239569`, `27008179`, `27013463`, `28973842`, `32207364`, `32211067`, `33504888`, `38580235`. Huit positifs, cinq négatifs.

Exemple : PH, id `12128473`, dépêche le 02/08/2018 à 13 h 25 min 02 UTC ; achat à **13 h 31 UTC, soit 9 h 31 à New York**, puis vente le lendemain. La liquidité employée inclut la clôture du 02/08, postérieure à l'achat. INTC, id `19263459`, est acheté le 21/01/2021 à 15 h 56 à New York, également en séance régulière.

Remplacer seulement la liquidité par celle réellement connue ne change ici aucun seuil ni coût : les treize titres dépassaient déjà 100 M$ la veille de l'achat réel. **L'effet de cette fuite particulière sur l'admissibilité est donc nul dans ces treize cas**, bien que le code soit anachronique. En revanche, éliminer les opérations régulières de l'analyse étendue change S6 de **+0,517682 point, p Holm 0,048939**, à **+0,510027 point, p Holm 0,052294**. S7 reste perdant : -0,357333 point, p Holm 0,000987. H1, H3 et le portefeuille régulier ne changent pas.

### D2. SPY n'est pas toujours sur les mêmes minutes : grave pour la définition du rendement anormal

**Preuve :** `src/minute_study.py:119` et ligne 120 autorisent un achat SPY plus tard et sa dernière clôture disponible plus tôt. Pour les heures étendues, lignes 142 et 143, même décalage possible à l'achat et à la vente. Le test `tests/test_minute_study.py:84` accepte explicitement des minutes finales différentes plutôt que de vérifier une égalité stricte.

**Mesure exhaustive à l'achat étendu :** parmi les 3 757 opérations brutes, 3 394 ont SPY à la même minute, **353 ont SPY plus tard** et 10 n'ont pas d'entrée SPY dans les six minutes. Retards : 224 d'une minute, 77 de deux, 23 de trois, 24 de quatre, 5 de cinq. Les 10 sans référence sont déjà manquantes dans `ab_extended`. Exemple : VLO, id `11115627`, achat du titre à 12 h 25 UTC le 01/02/2018, achat SPY à 12 h 29 UTC.

Une sensibilité excluant seulement les 353 achats décalés donne S6 **+0,534293 point**, p Holm **0,028617** ; S7 **-0,340959 point**, p Holm **0,002290**. Le défaut ne crée donc pas nécessairement un biais favorable ; il change la mesure annoncée. Pour H1, les 104 reconstructions directes ont un alignement exact ; aucun effet sur H1 n'est constaté dans ce contrôle. Je ne revendique pas une vérification exhaustive de l'égalité des minutes de sortie de toutes les opérations régulières.

### D3. Le délai maximal est passé de 60 à 65 minutes : mineur sur les tailles d'effet, matériel pour S6

**Preuve :** protocole initial ligne 68, précision 8 ligne 152 ; `src/minute_study.py:137` et ligne 139 : le délai d'attente de 60 minutes commence après les cinq minutes de latence.

**46 achats étendus** commencent strictement plus de 60 minutes après `available_at`. Exemple CFG, id `11051453`, dépêche à 11 h 34 min 20 UTC, achat à 12 h 37 UTC, délai **62 min 40 s**. En les excluant seuls, S6 vaut **+0,507377 point**, p Holm **0,060306** ; S7 reste négatif.

Les corrections ne sont pas additives. En excluant ensemble les 13 achats réguliers, les achats après 60 minutes et les achats SPY décalés, l'union comporte **410 mesures anormales** ; S6 vaut **+0,515430 point**, p Holm **0,048939**, et S7 -0,347949 point, p Holm 0,001793. Il serait donc incorrect d'affirmer que toute correction fait disparaître S6 : sa taille est proche, sa qualification à 5 % dépend de détails de construction et de la famille Holm. Ces sensibilités d'audit ne sont pas de nouveaux succès confirmatoires.

### D4. La sortie de cote le dernier jour de la fenêtre est reportée hors fenêtre : mineur ici

**Preuve :** `src/minute_study.py:178` applique le rendement de sortie si `last_rows < end`, pas si `last_rows == end`. La règle générale du projet attache la sortie à la dernière séance, `src/lab.py:99` à 108, et `NETTOYAGE_DONNEES.md:151` à 152. La précision 9 ne prévient pas ce report.

Trois bornes H2 sont concernées : **CHFC** id `14128631`, **RRD** id `25710384`, **DEPO** id `12163128`. RRD omet un rendement de rachat de 0,092336 % environ ; CHFC et DEPO omettent à cette borne leur perte pessimiste de 30 %. Corriger uniquement cette borne fait passer H2 central de **0,3729912 à 0,3729439 point**, et H2 pessimiste à **0,3643298 point**. L'effet global est faible et ne sauve pas H2, mais les trois scénarios ne sont plus rigoureusement identiques.

Cette différence dépend de la date conventionnelle de la sortie : considérer une vente réalisable à la clôture du dernier jour avant l’opération peut défendre l’inégalité stricte économiquement, mais ce n’est pas la convention générale du projet citée ici.

Le rapport ligne 88 dit « aucune [sortie] dans les 5 séances ». Ce n'est pas établi par l'égalité des scénarios : **CPSI, HIIQ et PRMW** cessent leur série avant la fin de ces fenêtres, avec une sortie de renommage de 0 %, et trois autres titres atteignent leur dernière séance à la borne. L'égalité de scénarios n'est pas une preuve d'absence de sortie.

### D5. La part du mouvement à l'ouverture compare des populations légèrement différentes : mineur

**Preuve :** `reports/run_minute_study.py:260` à 264 calcule séparément chaque moyenne, avec exclusion implicite des valeurs manquantes colonne par colonne. Tous titres : ouverture sur **12 017 / 3 322** positifs/négatifs, clôture sur **12 102 / 3 356**. Liquides : ouverture sur **3 773 / 686**, clôture et cinq minutes sur **3 778 / 687**.

Les parts à populations communes sont données plus haut : **92,73 %** au lieu de 92,10 % tous titres, **93,61 %** au lieu de 93,97 % liquides. Ce n'est pas une décomposition strictement appariée du même ensemble d'événements. L'effet ne renverse pas le constat descriptif de mouvement majoritairement antérieur à l'ouverture.

### D6. Ajout de Newey-West présenté comme neutre et mélange de pondérations : mineur pour le verdict

**Preuve :** protocole initial ligne 109 et précision 11 ; `src/minute_study.py:199` à 210, `src/events.py:154` à 169. L'implémentation Newey-West, les p de Student et Holm sont correctement calculés selon le protocole amendé.

Avec le t ordinaire sur les mêmes 28 observations, les p de Holm seraient **0,003514 pour H1**, **0,128992 pour H2**, **0,003039 pour H3**. Aucun changement de conclusion à 5 %, mais ce n'est pas la même procédure d'inférence. Le recours à Student avec une variance HAC est une approximation, pas une garantie mathématique de prudence.

Le rapport lignes 28 à 35 mélange aussi les moyennes trimestrielles des tests et les moyennes par événement des commentaires. Par événement, H1 est **+0,007403 point** chez les positifs et **-0,416852 point** chez les négatifs ; leur différence est **0,424254 point**, et non 0,521837. Par trimestre, les composantes de H1 sont **+0,033579** et **-0,488259 point**. Pour H3 : moyenne anormale nette par événement **-0,338158 point**, moyenne trimestrielle **-0,305617 point**, rendement net du titre par événement **-0,358127 point**. La formulation « -0,31 point par opération » est donc imprécise. Les pondérations devraient être indiquées à chaque fois.

### D7. Contrôle des variations extrêmes incomplet : mineur, effet non mesuré

**Preuve :** précision 13 ; `src/minute_study.py:100` à 106 et ligne 159. Seules les clôtures successives des barres de la séance régulière d'entrée sont comparées. Le contrôle ne vérifie ni le passage de l'ouverture à la clôture dans une même minute, ni les heures étendues, ni les autres séances utilisées. Deux barres éloignées faute de transactions sont également traitées comme deux minutes successives.

Contre-exemple reproductible : une série contenant une seule barre, ouverture 10, clôture 100, renvoie `nan` pour `largest_move`, malgré +900 % dans la minute. Le zéro de `extreme_minute_moves` est reproduit depuis la colonne calculée ; il ne prouve pas l'absence de toute variation extrême dans toutes les barres sources. Aucun effet chiffré sur H1/H3 n'est établi par cet audit.

### D8. Conclusions causales et générales trop fortes : grave pour l'interprétation

**Preuve :** rapport lignes 12 à 16, 53, 72 et 98.

- « Le marché a presque tout intégré avant qu'un humain puisse acheter » dépasse la mesure. La latence de cinq minutes est une hypothèse de simulation ; ni les participants ni leurs délais ne sont observés. Les prix utilisés à cinq minutes peuvent être anciens ; `available_at` est le dernier horodatage archivé, sans preuve de première diffusion ni du titre historique.
- « La fenêtre entre les robots et les humains existe » n'est démontré par aucun test du protocole. Celui-ci observe des prix et une classification de dépêches, sans identifier les acheteurs. Reformuler en constat descriptif du mouvement mesuré avant/après les horaires simulés.
- « Ce n'est pas gagnable sans vente à découvert » et « seule façon d'exploiter H1 » généralisent au-delà des règles testées. La conclusion permise est que **l'achat systématique des positifs testé ici perd avec les coûts supposés** ; aucune conclusion sur toutes les stratégies longues possibles n'est obtenue, et aucune rentabilité de vente à découvert n'a été évaluée.
- « Seulement à la baisse », « après une bonne nouvelle, rien » : le signe des moyennes va dans ce sens, mais une absence d'effet n'est pas démontrée. En sensibilité non confirmatoire, la moyenne trimestrielle positive a un IC 95 % de **-0,130860 à +0,198018 point**, p 0,679. Écrire « effet moyen positif non détecté » est plus exact.
- L'absence de significativité corrigée à 30/60 minutes ne démontre pas que la continuation est étalée sur toute la journée. La comparaison de ces fenêtres n'est pas un test de sa forme temporelle.

L'effet chiffré sur les rendements est nul : le défaut est l'inférence tirée des rendements. Il est grave car il porte sur la réponse centrale à l'hypothèse de l'équipe.

### D9. Nombre de jours SPY erroné : mineur

**Preuve :** rapport lignes 81 et 83 : 1 212 jours annoncés, contre **1 211** dans `summary.json`, clé `portfolio_usd.days_with_trades`, et dans le recalcul indépendant. Les capitaux finaux ne changent pas.

## 4. Autres vérifications demandées

| Point | Conclusion et preuve |
|---|---|
| Entrée régulière après disponibilité | Reconstitution indépendante de toutes les séances : aucun désaccord sur `entry_idx` ni `placebo_idx`. Chaque ouverture retenue suit `available_at + 5 min` ; les retards éventuels restent positifs. `reports/run_minute_study.py:57` à 68. |
| Barres avant entrée / après sortie | H1 prend un open à partir de l'ouverture puis un close de barre terminée au plus tard à la clôture ; fenêtres 30/60 minutes analogues. Les 104 reconstructions respectent ces bornes. La décomposition utilise intentionnellement des barres antérieures, ce qui est sa définition, pas une fuite. Réserve SPY : D2. |
| Liquidité, prix et coûts réguliers | Reconstruction indépendante sur tous les 43 007 événements depuis les cours et volumes bruts : **erreur maximale de liquidité 0**, **0 désaccord d'admissibilité**, **0 désaccord de coût**. La médiane glissante est arrêtée à la veille ; `cost_bps[r]` est déjà décalé d'une séance, donc le lire en r est correct. `src/universe_data.py:190` à 205. |
| Médiane sur 20 séances | Le code exige au moins 10 observations, pas 20 observations pleines, dans la fenêtre de 20. Convention supplémentaire mineure à documenter ; aucune preuve ici d'effet matériel sur le verdict. |
| Facteurs et nettoyage | Les facteurs par séance sont explicitement en échelle cohérente ; aucune erreur dans les 104 reconstructions interséances. Un facteur futur commun aux deux prix d'une même séance se simplifie et n'entre pas dans le filtre de prix brut. Attention conceptuelle : `suspect_print` est un nettoyage rétrospectif, avec regard à la séance suivante dans `src/universe_clean.py:196`. Aucun des 43 007 événements n'a ce drapeau sur sa veille d'entrée, ni aucun événement principal achetable sur sa séance d'entrée : pas d'effet de cette sélection anticipée constaté sur H1/H3. |
| ns contre us, pandas 3 | Conversions explicites correctes dans `src/minute_study.py:59`, `reports/run_minute_study.py:57`, lignes 119, 163 et 133. La date d'entrée enregistrée est en us, sans être confondue avec les compteurs ns. Aucun décalage de facteur 1 000 détecté. |
| Symbole et séance | Identité `symbol == securities[event_security].symbol` sur toute la table. Le lecteur cherche les fichiers de chaque séance et groupe par `requested`, sans reprendre les anciens couples événement/symbole faux. Les 104 vérifications brutes confirment la jointure. Cela valide l'usage de la table corrigée, pas toute la reconstitution historique des identités en amont. |
| `mode=current` | Exclusion explicite à `reports/run_minute_study.py:118`, test synthétique correspondant passé. Pas de réintroduction constatée. |
| Sorties de cote | Trois scénarios transmis correctement ; report des derniers cours pour les trous. Réserve de borne D4, et hypothèses de perte déjà reconnues comme incertaines dans le nettoyage. |
| Trimestres | 28 trimestres civils d'entrée, tous avec les deux signes pour H1/H2 ; pas de trimestre silencieusement supprimé dans les tests principaux. Pas de mélange avec le trimestre du BPA. |
| Newey-West et Holm | Formules reproduites indépendamment, correction conjointe des trois confirmatoires et séparée des neuf secondaires correcte. Réserve sur le changement de méthode : D6. |
| Placebo de signe | Reproduction exacte des 1 000 permutations : **0,000999001 pour H1**, **0,045954046 pour H2**. Permuter de nouveau le vecteur déjà permuté n'est pas un bogue : les permutations demeurent uniformes avec conservation des effectifs par trimestre. Ce contrôle ne conserve cependant pas les dépendances par société/date et ne démontre pas une causalité. |
| Regroupement en deux dimensions | Recalcul OLS et matrice par sommes de scores date + société moins intersection : t **3,483283**, **2,811207**, **-5,401625** pour H1/H2/H3. Correct comme sensibilité asymptotique sans correction de petit échantillon. Attention : coefficient pondéré par événement, **0,424254 point pour H1**, donc pas exactement l'estimateur pondéré par trimestre. CIK non manquants dans la table. |
| Portefeuille | Poids égaux entre achats de la séance, composition journalière, cash à 0 % hors achat ; pas de doublons société/séance surpondérant le même titre. Capital de 43,18 USD reproduit. Les références SPY emploient les cours quotidiens et leurs propres coûts ; les prix minute peuvent différer légèrement des cours quotidiens. |
| Décomposition | Ratios de différences des moyennes des groupes, pas moyenne de parts événement par événement. Ajustements, heures des barres terminées et prix d'ouverture reproduits ; réserve de population D5 et d'interprétation D8. |

## 5. Ce que signifie le placebo de la veille

Le contrôle prévu comme devant être nul est **non nul** : **+0,1237254 point**, IC 95 % **+0,024914 à +0,222537**, p **0,0160369**. Cela constate une association entre le signe futur de l'écart cité et le rendement antérieur, dans cet échantillon et avec cette mesure. Ce n'est ni une preuve automatique de fuite du code, ni une preuve automatique de transactions informées avant l'annonce.

Plusieurs explications restent compatibles avec les données : anticipation, autre information déjà diffusée, titre mis à jour plus tard que sa première diffusion, différences persistantes entre sociétés et risques, composition des groupes ou hasard. Le code place correctement la séance témoin entièrement avant `available_at`, mais cette borne n'est pas la preuve que le marché ignorait le résultat pendant toute la séance témoin.

Dire que H1 est quatre fois plus grand ne neutralise pas ce contrôle défaillant. Sur les événements disposant des deux mesures, la sensibilité exploratoire **H1 moins placebo** donne **+0,3928030 point**, IC 95 % **+0,077799 à +0,707807**, p brute **0,0164334**, sans correction de multiplicité supplémentaire. Elle montre qu'il reste un écart plus grand le jour testé ; elle ne mesure pas à elle seule un effet causal de la dépêche. Le placebo est aussi non nul dans le sous-groupe reçu avant l'ouverture du jour d'entrée : +0,121992 point, p 0,0252. Il ne suffit donc pas d'invoquer quelques dépêches tardives en séance pour l'écarter.

Le rapport signale honnêtement le placebo non nul, mais sa phrase « une partie de la dérive mesurée n'est donc pas propre à la dépêche » doit rester prudente : **la spécificité causale à la dépêche n'est pas identifiée**, et la part attribuable à chaque explication n'est pas estimée.

## 6. Reproduction pratique

Scripts d'audit conservés uniquement dans `/tmp` :

```bash
venv/bin/python -B /tmp/audit_minute_codex.py
venv/bin/python -B /tmp/audit_minute_codex_bars.py
venv/bin/python -B /tmp/audit_minute_codex_extended.py
venv/bin/python -B /tmp/audit_minute_codex_daily.py
venv/bin/python -B /tmp/audit_minute_codex_sens.py
```

Ils n'appellent pas `reports/run_minute_study.py` et n'écrivent que dans `/tmp`. Le script de sensibilité affiche aussi des effectifs et IC initiaux conservés du JSON ; pour les sensibilités, retenir ses champs recalculés `mean`, `lo`, `hi`, `p` et `new_holm`, pas les anciennes clés `events_positive`, `ci_low` et `p_holm_secondary`.

Les deux recettes autonomes ci-dessous ont été extraites de ce rapport et exécutées avec succès. La première reproduit les tests centraux et l'effet de l'exclusion des 13 opérations régulières, sans dépendre de ces fichiers temporaires :

```python
import numpy as np
import pandas as pd
from scipy.stats import t

E = pd.read_parquet('data/events/minute_study/events.parquet')
assert E.available_at.max() < pd.Timestamp('2025-01-01', tz='UTC')
E['q'] = E.entry_date.dt.to_period('Q')
M = E[E.principal & E.tradable & ~E.zero].copy()
M['ab'] = M.h1 - M.h1_spy
M['net'] = (1 + M.h1) * (1 - M.cost_bps / 10000)**2 - 1 - M.h1_spy

def spread(d, col):
    a = d.groupby(['q', 'positive'])[col].mean().unstack()
    return (a[True] - a[False]).dropna()

def estimate(x):
    x = np.asarray(x.dropna(), dtype=float)
    n = len(x)
    d = x - x.mean()
    se = np.sqrt((d @ d + d[1:] @ d[:-1]) / n**2)
    return x.mean(), 2 * t.sf(abs(x.mean() / se), n-1)

def holm(p):
    p = np.asarray(p)
    order = p.argsort()
    out = np.empty(len(p))
    out[order] = np.minimum(1, np.maximum.accumulate(
        p[order] * (len(p) - np.arange(len(p)))))
    return out

series = [spread(M, 'ab'), spread(M, 'ab_d5_base'),
          M[M.positive].groupby('q').net.mean()]
r = [estimate(x) for x in series]
print('H1/H2/H3 :', r)
print('Holm :', holm([p for mean, p in r]))

bad = [12128473, 13656369, 19263459, 19863369, 25409042,
       26239569, 27008179, 27013463, 28973842, 32207364,
       32211067, 33504888, 38580235]
L = M[M.liquid & ~M.id.isin(bad)]
print('S6 sans achats réguliers :', estimate(spread(L, 'ab_extended')))
```

Pour reconstruire le tirage depuis les sources, la recette ci-dessous est autonome. Elle vérifie H1, H3 et la part à l'ouverture sur les 70 événements aléatoires ; le script temporaire ajoute les contrôles ciblés décrits plus haut.

```python
from pathlib import Path
import numpy as np
import pandas as pd

R = Path('.')
E = pd.read_parquet(R / 'data/events/minute_study/events.parquet')
M = E[E.principal & E.tradable & ~E.zero]
rng = np.random.default_rng(937)
ix = []
for _, g in M.groupby([M.entry_date.dt.year, 'positive']):
    ix.extend(rng.choice(g.index, 5, replace=False))
Q = M.loc[ix].sort_values('entry_date')
C = pd.read_parquet(R / 'data/calendar.parquet', filters=[
    ('date', '<=', pd.Timestamp('2024-12-31'))]).sort_values('date').reset_index(drop=True)
for col in ['open', 'close']:
    C[col] = C[col].dt.tz_localize('America/New_York').dt.tz_convert('UTC')
P = pd.read_parquet(R / 'data/universe_clean/prices_dev.parquet',
    columns=['security_id', 'ts_utc', 'adj_close', 'close', 'suspect_print'],
    filters=[('security_id', 'in', list(set(Q.event_security) | {'SPY#0'})),
             ('ts_utc', '<', pd.Timestamp('2025-01-01', tz='UTC'))])
P['day'] = P.ts_utc.dt.tz_convert('America/New_York').dt.tz_localize(None).dt.normalize()
P['f'] = (P.adj_close / P.close).where(~P.suspect_print)
factors = P.set_index(['security_id', 'day']).f.to_dict()
cache = {}
one = pd.Timedelta(minutes=1)

def get_bars(row, symbol, security):
    parts = []
    for j in range(row.placebo_idx, row.entry_idx + 1):
        day = C.date.iloc[j]
        if day not in cache:
            fs = []
            for folder in ['minute_bars', 'minute_bars_extra']:
                path = R / 'data/events' / folder / f'bars_{day:%Y-%m-%d}.csv.gz'
                if path.exists():
                    f = pd.read_csv(path, usecols=['requested', 'mode', 't', 'o', 'c'])
                    fs.append(f[f['mode'] == 'self'])
            data = pd.concat(fs) if fs else pd.DataFrame(columns=['requested','t','o','c'])
            data['t'] = pd.to_datetime(data.t, utc=True, format='ISO8601')
            cache[day] = data
        part = cache[day][cache[day].requested == symbol].copy()
        part[['o', 'c']] *= factors.get((security, day), np.nan)
        parts.append(part)
    return pd.concat(parts).sort_values('t', kind='stable')

def first(b, start, stop):
    return b[(b.t >= start) & (b.t < stop)].iloc[0]

def last(b, start, stop):
    return b[(b.t >= start) & (b.t < stop)].iloc[-1]

rows = []
for _, a in Q.iterrows():
    b, s = get_bars(a, a.symbol, a.event_security), get_bars(a, 'SPY', 'SPY#0')
    op, cl = C.loc[a.entry_idx, ['open', 'close']]
    po, pc = C.loc[a.placebo_idx, ['open', 'close']]
    buy = first(b, op, op + 6*one)
    sell = last(b, buy.t, cl)
    sbuy = first(s, buy.t, buy.t + 6*one)
    ssell = last(s, sbuy.t, sell.t + pd.Timedelta(nanoseconds=1))
    h1, spy = sell.c / buy.o - 1, ssell.c / sbuy.o - 1
    net = (1+h1)*(1-a.cost_bps/10000)**2 - 1 - spy
    base, sbase = last(b, po, pc).c, last(s, po, pc).c
    cumop = buy.o / base - 1
    scumop = first(s, buy.t, buy.t + 6*one).o / sbase - 1
    cumcl, scumcl = last(b, op, cl).c / base - 1, last(s, op, cl).c / sbase - 1
    got = [h1, spy, net, cumop, scumop, cumcl, scumcl]
    ref = a[['h1', 'h1_spy', 'net_ab_h1', 'cum_open', 'cum_open_spy',
             'cum_close', 'cum_close_spy']].to_numpy(dtype=float)
    np.testing.assert_allclose(got, ref, rtol=0, atol=1e-12, equal_nan=True)
    rows.append([a.positive, h1-spy, net, cumop-scumop, cumcl-scumcl])
    if len(cache) > 6:
        cache = {k: cache[k] for k in sorted(cache)[-3:]}
A = pd.DataFrame(rows, columns=['positive','h1','h3','open','close'])
g = A.groupby('positive').mean()
print(g)
print('Part à ouverture :',
      (g.loc[True,'open']-g.loc[False,'open']) /
      (g.loc[True,'close']-g.loc[False,'close']))
```

## Conclusion de l'audit

**Oui pour les résultats centraux du protocole amendé : écart H1, absence de confirmation H2 et perte de l'achat H3. Non pour une application intégralement fidèle au gel initial, une validation sans réserve des heures étendues, ou une démonstration de la fenêtre entre robots et humains.** Le rapport devrait conserver les résultats négatifs, expliciter ses changements de règles et de pondérations, corriger les défauts secondaires et présenter le placebo non nul comme une limite d'identification, sans chercher une nouvelle règle gagnante sur 2018-2024.
