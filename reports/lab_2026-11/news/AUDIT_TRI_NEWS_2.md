# Verdict : NON, les tables actuelles ne suffisent pas encore

Deuxième audit indépendant, 7 novembre 2026, arbre de travail non commité de la branche `interface-web`, base `b6ea6f1`. Le signal reste nommé **« écart à l’estimation citée »**.

Les corrections ont nettement amélioré les garanties mécaniques : horloge conservée, retrait des arbitrages par liquidité future, sélection stable de la première dépêche admissible, contrôles numériques et suppression des anciens BBT erronés. Je reproduis les **51 636 publications** sans différence de sélection. Mais deux dépêches de trimestres antérieurs restent affectées à des publications nouvelles, un réalisé de l’année précédente est présenté comme celui de l’année courante, **121 étiquettes de base comptable sont certainement fausses**, et le contrôle de nom ne distingue toujours pas certaines sociétés différentes. Une nouvelle règle supprime aussi les résultats d’Affirm à cause du nom de l’entreprise.

**L’étude rétrospective limitée pourra être lancée après les corrections obligatoires de la dernière section, sans exiger un consensus historique introuvable. Elle ne doit pas être lancée sur ces tables en l’état.** L’absence d’archive de versions reste une hypothèse à déclarer et interdit les affirmations sur la première diffusion ou une stratégie historiquement déployable. Aucun rendement n’a été ouvert ni calculé pendant cet audit.

## Périmètre et nouveaux tirages

Toutes les écritures sont dans `/tmp/news-audit2/`. Aucun fichier du dépôt n’a été modifié par l’audit. Les projections d’événements contiennent seulement les huit colonnes autorisées. Aucun cours, rendement, SUE, dossier de holdout, secret, `.env` ou observation postérieure au 31 décembre 2024 n’a été lu. Un exercice fiscal nommé 2025 dans une dépêche publiée en 2024 n’est pas une observation de 2025. Les métadonnées de noms actuels expressément autorisées servent à contester les alias; elles ne prouvent pas leur validité historique.

Les sources externes retenues sont des pièces SEC historiques précises, retrouvées dans les index quotidiens historiques. Le client HTTP utilise `MasterResearchNewsAudit/2.0 public academic research`, avec au moins 0,45 seconde entre requêtes séquentielles, moins de 8 requêtes par seconde. Les extraits affichés sont limités aux résultats et identités. Aucun contact par e-mail.

Graine principale **846217** : 150 titres distincts par catégorie, `n_stocks >= 1`, soit **900 jugements à l’aveugle** du champ catégorie. Grille : commentaire/flux de marché, aperçu/opinion, résultat réalisé, prévision de la direction, note externe d’analyste, fait sur une société, autre, indécidable. Les 1 198 identifiants et titres du premier audit sont exclus avant le tirage. Les jugements sont fixés dans `manual_categories.py`; le fichier aveugle et la clé sont séparés. Il s’agit d’une relecture par la même personne après connaissance des anciens défauts, pas d’un double aveugle avec deux annotateurs.

Les graines **846219**, **846220**, **846221** donnent respectivement 200 lignes de surprise, 100 liens directs et 100 liens par alias. Ces 1 300 articles sont tous distincts entre eux et des anciens articles, y compris par texte de titre. Un tirage supplémentaire de **200 citations refusées**, graine **846222**, exclut encore tous ces articles : il comporte 199 articles et 183 textes distincts, les citations étant son unité. Les 28 publications publiques viennent des 200 nouvelles lignes : quatre par année de 2018 à 2024, dont **huit sociétés disparues à fin 2024**, sans reprise des 42 publications du premier audit. Les témoins ciblés supplémentaires ne servent pas à estimer une fréquence.

Les IC de précision sont des Wilson bilatéraux à 95 %, conditionnels aux jugements du relecteur. Les indécidables ne sont pas transformés en erreurs certaines. Les titres distincts ont été échantillonnés uniformément : pour extrapoler à des articles répétés, j’utilise leurs fréquences réelles et les probabilités de tirage, pas une simple multiplication par la taille des catégories.

## Défauts classés par gravité

### 1. Bloquant : le bon émetteur et la bonne fenêtre n’assurent pas le bon trimestre ni le bon réalisé

**Mesures vérifiées.** Les clés de `earnings_surprise.parquet` sont propres : aucun identifiant réutilisé, aucun doublon `(cik, accepted_utc)` ni `(cik, period_end)`, aucune ligne hors fenêtre, aucun désaccord avec `available_at = max(created_at, updated_at)`. Ma sélection indépendante par recherches dans des tableaux de temps construit **52 236 couples admissibles**, puis retrouve exactement **51 636 lignes**, sur **80 759 publications**, soit **63,94 %**. Aucune dépêche admissible n’est candidate pour deux publications dans ces données. La règle « une dépêche à la publication la plus proche » n’a donc pas d’effet ici; elle ne doit pas remplacer un contrôle de période si un conflit apparaît plus tard.

Les **200 paires relues** concordent avec le titre pour les deux montants, le signe arithmétique, la société explicitement citée et la base effectivement indiquée. Le taux d’erreur arithmétique du signe observé est **0/200**, IC Wilson **[0 % ; 1,88 %]**; cet IC ne couvre pas la véracité économique du titre. Leur contrôle externe révèle néanmoins une erreur du titre lui-même. Sur les **28 publications contrôlées**, **26 montants sont confirmés exactement**, un est seulement reconstructible et un est faux. Les dates et périodes des documents ont été vérifiées; le montant faux se rapporte à une période antérieure. Aucun de ces comptes n’utilise le champ EPS des événements comme vérité automatique.

**Exemple aléatoire : Waterstone, article du tirage 144.** La dépêche du 30 janvier 2018 donne un BPA Q4 de **0,23** contre **0,21**, retenu pour le trimestre clos le 31 décembre 2017. Le [communiqué SEC](https://www.sec.gov/Archives/edgar/data/1569994/000156999418000002/exhibit991.htm) donne **0,11 GAAP**, **0,21 hors effet fiscal**, et **0,23 pour Q4 2016**. Le parseur copie correctement un chiffre du mauvais exercice. L’écart positif de 0,02 du titre n’est soutenu par aucune des deux bases courantes indiquées : avec la même estimation 0,21, le réalisé courant donnerait zéro ou un écart négatif selon la base. La base historique de l’estimation n’est pas vérifiée.

**Recherche systématique de vieux titres recyclés.** Cinq lignes finales ont exactement le même titre qu’un article publié au moins 45 jours plus tôt. Les cinq ont été vérifiées publiquement : trois sont des coïncidences numériques valides, deux sont des erreurs. Ce contrôle ciblé n’est pas un taux d’erreur global.

| Article final | Publication assignée | Constat primaire |
|---|---|---|
| `20859283`, A.O. Smith | Q1 clos le 31 mars 2021, dépôt du 29 avril | Titre identique à `19364375` du 28 janvier : « Q4 EPS 0.74 ... Sales 834.50M ». Le [communiqué de janvier](https://www.sec.gov/Archives/edgar/data/91142/000009114221000003/a1282021exhibit991.htm) confirme Q4 2020 à 0,74; le [communiqué d’avril](https://www.sec.gov/Archives/edgar/data/91142/000009114221000079/a3312021exhibit991.htm) donne Q1 2021 à 0,60 et ventes 769,0 M. |
| `33681999`, Accuray | Q4 fiscal clos le 30 juin 2023, 9 août | Reprise exacte du titre Q3 du 26 avril, BPA +0,01 et ventes 118,06 M. Le [communiqué Q4](https://www.sec.gov/Archives/edgar/data/1138723/000095017023040538/aray-ex99_1.htm) donne une perte par action de **-0,03**; le chiffre +0,01 du titre n’y figure pas. |
| `29714742`, TRACON | Q3 2022 | -0,30 confirmé, malgré le titre identique de 2018. |
| `14159422`, Capitol Federal | Q3 fiscal 2019 | 0,17 confirmé, malgré le titre identique de 2018. |
| `33430473`, Vicarious Surgical | Q2 2023 | -0,16 ajusté confirmé, malgré le titre identique de 2022. |

Un autre détecteur, indépendant de la proximité SEC, cherche une incohérence entre numéro de trimestre et mois fiscal habituel de l’émetteur. Il signale **172 lignes**, pas 172 erreurs. Les changements de calendrier fiscal produisent des alertes légitimes. Cinq témoins ont été contrôlés : A.O. Smith ci-dessus est faux; pour **AZZ `11711685`**, **Magellan Health `11264909`**, **Bank of Hawaii `39879221`** et **Agilysys `18083175`**, le montant appartient bien à la publication courante, mais le numéro de trimestre du titre est faux. Par exemple Bank of Hawaii annonce Q3 dans le titre de juillet 2024 alors que la [pièce SEC](https://www.sec.gov/Archives/edgar/data/46195/000095017024085173/boh-ex99_1.htm) décrit le deuxième trimestre. Ne pas « réparer » ces titres en forçant une correspondance de calendrier sans source.

**Effet sur l’étude.** Un ancien résultat peut devenir un nouveau signal à une date arbitraire; le signe économique peut même s’inverser. Un parseur numériquement exact ne protège pas contre cette erreur de mesure ni contre un mauvais événement.

**Correction obligatoire.** Extraire et conserver le numéro et l’année fiscale associés au couple de BPA effectivement choisi; vérifier leur accord avec la période du communiqué ou une référence fiscale historique. Mettre en quarantaine les divergences et titres recyclés jusqu’à vérification, sans correction silencieuse. Pour le sous-échantillon principal, exiger la confirmation du réalisé courant et de sa base dans une source primaire, automatiquement lorsque la correspondance est non ambiguë et manuellement sinon. On peut lancer une étude plus petite sur ce sous-échantillon vérifié; on ne doit pas considérer les 51 636 lignes comme déjà validées. Conserver les valeurs rejetées et les raisons avant toute ouverture des rendements.

### 2. Grave : la base du BPA est lue avant un autre EPS, ou dans le nom de la société

**Mesure indépendante.** Mon analyseur de montants, distinct de `parse_surprise`, retrouve les mêmes valeurs et estimations sur les **51 636 lignes**, sans valeur manquante ni désaccord numérique. Après correction de ses propres faux positifs de qualification, la relecture de toutes les divergences de base donne **122 alertes**, dont **121 erreurs certaines de l’étiquette du couple analysé**, soit **0,234 %** de la table, et un cas ambigu `Adj. FFO EPS` à exclure du BPA principal. Ces erreurs peuvent changer le groupe d’analyse; ce ne sont pas 121 erreurs du signe numérique.

La cause est concrète : `text.lower().find("eps")` pointe vers la première sous-chaîne EPS, alors que `_pair` peut sélectionner un EPS ultérieur. La fenêtre tronquée de 25 caractères permet aussi à `core` d’un nom propre d’être pris pour un ajustement.

- **69** des 71 titres où le couple porte sur un EPS ultérieur ont une base différente de celle stockée. `11045972` : « GATX ... GAAP EPS 8.83, Adj. EPS 0.68 vs 0.73 Est. » stocke le couple 0,68/0,73 comme `gaap`.
- **22** erreurs concernent une sous-chaîne EPS dans un nom, notamment **PepsiCo**, **StepStone** et **UEPS** : « PepsiCo Q2 Adj. EPS 2.28 ... » devient `unlabeled`.
- **23** titres commençant par Core-Mark, Core & Main, Core Scientific ou Core Laboratories sont mal étiquetés. `40704358` dit explicitement « Core & Main Q2 2024 GAAP EPS 0.61 ... », stocké `adjusted`.
- D’autres cas reprennent la qualification d’un **FFO précédent**, par exemple Essex `16906660`, ou un fragment de nom comme Encore ou Heartcore. Les ensembles précédents ne doivent pas être additionnés aveuglément.

Le tirage de 200 ne contient aucune de ces 121 erreurs : c’est précisément pourquoi une recherche systématique complète utile le contrôle aléatoire. **117/200 BPA du tirage et 30 618/51 636 de la table sont sans base explicite.** Parmi les 28 sources, les titres non qualifiés de Hologic, Sterling, TransUnion, Invacare, Paycom et MillerKnoll reprennent des chiffres ajustés. `unlabeled` n’est pas synonyme de GAAP. Pour M/I Homes, 2,93 ajusté est seulement reconstituable à partir de 2,71 et d’une charge de 0,22; ce n’est pas un montant explicitement attesté dans la pièce.

**Effet sur l’étude.** Les groupes comptable/ajusté sont mélangés; une estimation d’une autre base n’est pas une surprise comparable. L’erreur est liée au format et au nom, donc potentiellement aux émetteurs et aux années.

**Correction obligatoire.** Retourner les bornes du couple retenu depuis `_pair`; qualifier uniquement ce couple et sa clause. Délimiter les mots et exclure le préfixe d’identité de l’émetteur. Conserver des champs distincts pour base du réalisé, base de l’estimation, devise, unité par action ordinaire/ADR et caractère préliminaire. Ne jamais inférer la base de l’estimation par le seul voisinage du réalisé. Exclure du principal les bases non établies ou non comparables; les 30 618 non qualifiés peuvent faire une analyse exploratoire séparée clairement étiquetée. Vérifier de nouveau les regroupements après régénération.

### 3. Grave : le contrôle de nom reste une heuristique, avec une fausse société certaine

**Reproduction.** Ma reconstruction des citations donne exactement **2 679 535 citations**, **2 354 686 liens directs**, **59 123 alias acceptés**, **94 133 alias refusés**, **158 026 inconnues**, **13 548 hors dates**, **19 ambiguïtés rejetées** et **2 413 531 liens uniques**. Aucune différence avec la table. Les **101 BBT** anciennement faux sont désormais tous refusés. Aucun arbitrage par liquidité n’est utilisé.

| Contrôle neuf | Cohérents nominalement | Faux certains | Indécidables | Taux de faux certains et IC Wilson |
|---|---:|---:|---:|---|
| 100 liens directs, articles distincts | 97 | 0 | 3 | 0 % [0 % ; 3,70 %] |
| 100 liens par alias, articles distincts | 97 | 1 | 2 | 1 % [0,18 % ; 5,45 %] |

Les intervalles portent sur la détection d’erreurs certaines dans ces tirages, pas sur une précision totale validée. En comptant les indécidables comme potentiellement faux, les proportions observées vont de 0 à 3 % pour les directs et de 1 à 3 % pour les alias. Une concordance avec les anciens noms SEC est une preuve nominale; la pertinence économique d’un titre générique et la continuité de chaque action ne sont pas toutes vérifiées extérieurement. Les trois directs indécidables sont des titres génériques concernant AEHR, AUST et LABP; les deux alias indécidables concernent un palmarès sectoriel et Trump/DJT.

**Erreur certaine : Wyndham.** La ligne 130 du tirage, article `18804924`, doit être lue par son titre et sa date : « Wyndham Hotels & Resorts Announces ... Chief Administrative Officer », **15 décembre 2020**, est liée à **TNL#0**, CIK 1361658, Wyndham Destinations/Travel + Leisure. Wyndham Hotels & Resorts est alors **WH**, CIK **1722684**, société distincte après la scission. Le [communiqué de WH de février 2020](https://www.sec.gov/Archives/edgar/data/1722684/000172268420000004/exhibit99120191231.htm) confirme son nom et son symbole. La recherche exhaustive des alias TNL après juin 2018 trouve **un cas nominal sans ambiguïté de ce type**. Le mot commun historique `wyndham` ne suffit pas à identifier l’émetteur après scission.

**Recherche systématique de garde-fous trop faibles.** Parmi les alias acceptés, **576 citations** passent sans occurrence d’un jeton entier et **2 328** passent via un seul jeton faible de la liste ciblée (`bear`, `plus`, `acquisition`, `digital`, `industrial`, `york`, `equity`, etc.). Ce sont des ensembles d’alertes, pas 2 904 faux liens. Certains composés sans espace sont corrects. Mais le prédicat d’identité est effectivement faux lorsque `bear` de Baker Hughes correspond à **Bearish/Bears** dans les articles `11944242` et `12095538`, `aqua` d’Aqua America correspond à **AquaBounty** dans `11025947`, ou `acquisition` de l’ancien nom DCC Acquisition correspond à une acquisition d’Ellie Mae dans `13152795`. Ces titres ne prouvent pas à eux seuls l’absence de la société dans le corps inaccessible; ils prouvent que le contrôle nominal ne fait pas ce qu’il prétend.

**Nouvelle exception à la règle annoncée.** Pour **2 591 citations**, un candidat direct actif et un candidat alias actif ont des CIK différents. Le code n’examine les alias que si aucun direct n’est actif; il ne vérifie donc pas « sociétés différentes possibles = aucun lien » sur l’union des candidats. Il serait excessif de rejeter automatiquement ces 2 591 citations : beaucoup de directs peuvent être historiquement corrects. Il faut résoudre la période de validité du symbole et le nom d’émetteur, ou rejeter les cas non résolus. La comparaison de CIK manquants doit aussi être explicite : **9 258 titres du référentiel** n’ont pas de CIK, souvent hors actions de l’étude; plusieurs valeurs `None` ne prouvent pas un même émetteur.

**Le cas demandé LKFT/Gilead/Galapagos n’est pas une erreur démontrée.** `LKFT#0` porte le **CIK 1421876**, ancien nom **Galapagos NV**. Les **269 citations GLPG acceptées** mentionnent Galapagos; **33** mentionnent aussi Gilead. Le [6-K historique de Galapagos, juillet 2019](https://www.sec.gov/Archives/edgar/data/1421876/000117184319004585/exh_991.htm) est précisément un communiqué commun Gilead/Galapagos. Un titre sur leur essai ou collaboration peut légitimement concerner les deux sociétés. Aucun LKFT n’entre dans les 51 636 surprises finales. Le nom actuel différent n’est pas une raison suffisante de déclarer un mauvais CIK. Cela ne valide pas pour autant la continuité de la classe d’action ou la validité datée de tous ses alias.

**Coût des 94 133 refus.** Le tirage de 200 citations donne **16 correspondances nominales plausiblement justes**, **5 refus justifiés** et **179 indécidables** sur le titre seul. Parmi les 16 : BRP Group/BWIN, PQ Corporation/ECVT, AAM/DCH, I-MAB/NBP, DSW/DBI, MDC Partners/STGW, Gap/GAP, Wish/LOGC, First Republic/FRCB, et des continuités de fusion ou de marque plus difficiles comme WRK/SW et WWE/TKO. Les noms de trois lettres et les graphies à tiret sont notamment pénalisés. Les 5 refus justifiés comprennent quatre VIVO vers VivoPower alors que VIVO désigne Meridian, confirmé par la [pièce SEC de Meridian](https://www.sec.gov/Archives/edgar/data/794172/000119312522027756/d288801dex991.htm), et P/Pandora vers Pure Storage.

Le taux de correspondance nominale repérable est **8,00 %**, IC **[4,98 % ; 12,60 %]**, soit environ **7 531 citations** [4 692 ; 11 860] si cette détection se transpose à toute la strate. **Ce n’est pas un taux de vrais liens historiques prouvés** : les 179 indécidables, les fusions et l’absence de corps empêchent d’estimer ce taux. L’affirmation du rapport « souvent légitimes » n’est pas quantifiée par ces seules données. Une vraie mesure du coût historique exige le registre daté des symboles et des classes; relâcher le test à un mot commun récupérerait aussi les faux liens VIVO et P.

**Effet sur l’étude.** Un signal est envoyé à une autre société; inversement, l’exclusion des noms courts, alias et sociétés fusionnées change la couverture, surtout historique et disparue.

**Correction obligatoire.** Utiliser un registre `symbole, début, fin, CIK, classe`, avec noms historiques datés et normalisation des acronymes approuvés. Exiger une expression de nom distinctive en mots entiers, plusieurs mots si nécessaire, avec table explicite des scissions et homonymes. Réunir les candidats directs et alias pour détecter les conflits, puis résoudre par identité historique, jamais par liquidité future. Pour lancer rapidement le sous-échantillon principal, exclure les alias et conflits encore non résolus; garder leur coût dans le bilan d’inclusion. Ne pas réintroduire automatiquement les 94 133 refus.

### 4. Important : des commentaires de mouvements réalisés restent gardés; des prévisions restent des résultats

**Précision sur les 900 nouveaux titres à l’aveugle.** L’ancienne colonne est celle de l’audit antérieur, correctement identifiée comme antérieure aux corrections dans `TRI_NEWS.md`.

| Catégorie | Confirmés | Précision conservatrice | IC 95 % | Ancien audit |
|---|---:|---:|---|---:|
| Notes d’analystes | 150/150 | 100,00 % | [97,50 % ; 100,00 %] | 97,33 % |
| Faits sur une société | 109/150 | 72,67 % | [65,04 % ; 79,17 %] | 72,67 % |
| Résultats publiés | 142/150 | 94,67 % | [89,83 % ; 97,27 %] | 94,00 % |
| Remplissage / aperçu | 136/150 | 90,67 % | [84,94 % ; 94,36 %] | 86,00 % |
| Prévisions de la direction | 123/150 | 82,00 % | [75,08 % ; 87,32 %] | 76,67 % |
| Commentaires de marché | 145/150 | 96,67 % | [92,43 % ; 98,57 %] | 94,67 % |

Les **13 indécidables evergreen** sont des titres « Qn Earnings Insights » sans indication suffisante d’avant ou après publication. Leur précision compatible va de 136/150 à 149/150, avant incertitude d’échantillonnage. Le chiffre 90,67 % n’est pas une estimation de 14 erreurs certaines. L’amélioration apparente des analystes ne démontre pas une précision de 100 % en population : la borne inférieure est 97,50 %. Les catégories company_news et guidance restent les plus mélangées. Les intervalles se recouvrent largement avec les anciens; je ne revendique pas une amélioration statistiquement démontrée de chaque strate.

**Fuite de mouvement réalisé, définition stricte.** Cinq titres gardés sur les 600 décrivent explicitement un mouvement déjà réalisé. Trois autres portent sur des flux d’options ou un commentaire ambigu : ils donnent huit titres de genre marché au sens large, mais ne sont pas comptés comme trois preuves supplémentaires de réaction réalisée.

| Catégorie gardée | Mouvement réalisé | IC 95 % du taux par titre distinct | Articles du domaine neuf | Nombre d’articles estimé avec répétitions |
|---|---:|---|---:|---:|
| Notes d’analystes | 0/150 | [0,00 % ; 2,50 %] | 294,844 | 0 |
| Faits sur une société | 3/150 | [0,68 % ; 5,71 %] | 459,394 | 8,992 |
| Résultats publiés | 1/150 | [0,12 % ; 3,68 %] | 140,738 | 923 |
| Prévisions de la direction | 1/150 | [0,12 % ; 3,68 %] | 55,471 | 369 |

L’estimateur stratifié, qui tient compte des fréquences de chaque texte et du tirage uniforme de titres distincts, donne **10 284 articles** contaminés parmi **950 447 articles du domaine neuf**, soit **1,082 %**. Les **922 articles correspondant aux anciens titres d’audit** sont exclus du tirage neuf et ne sont pas directement estimés. L’ensemble gardé non vide compte **951 369 articles**; une ligne vide supplémentaire de company_news est exclue du scoring, d’où 951 370 avant cette exclusion.

Une borne conservatrice simultanée à environ 95 % pour l’ensemble complet est **[1 111 ; 78 967] articles** : intervalles exacts de Clopper-Pearson par strate avec Bonferroni, puis fréquences minimales/maximales possibles des textes et ajout des 922 anciens articles à la borne haute. Elle est large, notamment parce que zéro commentaire parmi 150 analystes ne démontre pas leur absence. Cette construction évite d’appliquer abusivement un IC binomial de titres uniques à des articles répétés. Le total naïf pondéré par effectifs d’articles serait 10 503; il n’est pas l’estimateur retenu.

**Exemples réels.** `614` du tirage : « AmTrust Shares Near Afternoon Highs, Up 1.4% ... » reste company_news. `714` : Applied DNA « Shares React Higher ... » reste company_news. `184` : Photronics « Shares Trade Lower After ... Outlook » reste guidance. `785` : « Crude Oil Rises Over 1%; Tapestry Posts Upbeat Earnings » reste earnings. Les deux premiers montrent des formes verbales manquantes; le dernier mêle un fait à un mouvement macro déjà réalisé.

**Prévisions et contenu externe.** Earnings contient « Orion ... On Track To Achieve Q3 And Q4 Sales ... » et « Lincoln ... Net Income And EBITDA Are Projected ... »; guidance contient des avis d’analystes externes et des titres de résultats suivis d’une prévision. Company_news contient encore aperçus, opinions et listes. Ces erreurs de catégorie ne signifient pas toutes une fausse ligne finale de BPA : les paires publiées disposent de filtres supplémentaires. Aucun annuel ou prévision sans résultat courant n’est confirmé parmi les 200 lignes finales relues. Les **212 mentions FY/annual** et **455 mots de prévision** dans la table finale constituent des listes d’alertes pour relecture ciblée; les cas examinés sont principalement des résultats trimestriels suivis d’une guidance. Ce ne sont pas des comptes d’erreurs certaines ni une validation exhaustive de ces deux listes.

**Vrai fait écarté par la correction.** EastGroup `784` du tirage : « Q2 FFO Excluding **Gain on** Involuntary Conversion ... » est classé commentaire par le motif général `gain on`. Il parle d’un gain comptable exclu du FFO, pas d’un cours. Une liste de verbes sans sujet ne suffit pas.

**Effet sur l’étude.** Un texte écrit après un mouvement peut faire attribuer au signal une information déjà incorporée. Les exclusions erronées changent aussi la population étudiée. La confusion des genres est moins grave dans le sous-échantillon de paires contrôlées que dans une étude de sentiment sur toutes les catégories.

**Correction précise.** Ajouter un indicateur indépendant de mouvement réalisé, sans l’écraser lorsque le titre cite aussi un résultat. Reconnaître `trade lower`, `react higher`, `near ... highs`, les listes de gainers/losers et mouvements d’indices/matières premières, en exigeant un sujet de marché; protéger les contextes `gain on` comptables. Identifier l’acteur d’une prévision et la clause, conserver des dimensions séparées de fait économique et format éditorial. Réévaluer sur des titres neufs après modification; les 900 de ce deuxième audit deviennent des exemples de développement.

### 5. Nouvelle régression : « Affirm » est interprété comme le verbe de prévision

**Mesure et exemple.** **16 titres** commençant par « Affirm Holdings Qn ... EPS » sont classés guidance et leurs valeurs effacées. **13** contiennent une paire lisible si le nom de société est remplacé par un identifiant neutre. `22875668` : « Affirm Holdings Q4 EPS $(0.48) Misses $(0.29) Estimate ... ». Le mot Affirm satisfait les motifs `affirms?` avant le résultat, dans le classement et dans `_pair`.

**Effet.** Perte systématique d’un émetteur et de certains formats; une correction des prévisions peut créer un biais d’échantillonnage sans changer l’exactitude des 51 636 lignes déjà retenues.

**Correction obligatoire.** Délimiter le préfixe nominal de l’émetteur avant de rechercher un verbe de discours; distinguer verbe, acteur et clause. Réparer à la fois le classement et l’interdiction de prévision dans le parseur, puis tester explicitement Affirm à côté de « company affirms outlook ». Régénérer le bilan d’inclusion. Un simple changement d’ordre des catégories ne corrige pas `_pair`.

### 6. Important : disponibilité conservatrice acceptable sous hypothèse, garde-fous encore incomplets

**Vérifié.** Les 51 636 lignes respectent exactement le maximum des deux horodatages. **25 929** ont `updated_at > created_at`, souvent d’une seconde; **163** dépassent une heure. **26 667**, soit **51,644 %**, précèdent l’acceptation SEC, et **383** la précèdent de plus de 24 heures. Il reste **469 relais explicitement tardifs**. Ces taux ne prouvent ni fuite ni première diffusion. Un communiqué peut précéder son dépôt; aucun calcul sur le cours n’est nécessaire pour constater cette distinction.

**Non vérifiable avec ces fichiers.** La fidélité des horodatages fournisseur à la version du titre, l’heure de réception effective et la préexistence de l’estimation citée restent non attestées. Les **28 sources de résultats ne valident aucune estimation d’avant annonce**. Le maximum ne certifie donc pas une première publication; il évite seulement d’utiliser volontairement une version actuelle avant son dernier horodatage déclaré. L’ancien consensus n’est pas requis pour étudier un écart textuellement cité, à condition de conserver ce nom et cette limite.

**Garde-fous.** La borne de création vérifie désormais `< 2025-01-01`, mais seulement après ouverture de tous les fichiers du glob. Il manque une borne explicite sur `updated_at`/`available_at`, sur les événements et sur les fichiers à ouvrir avant lecture. Une mise à jour de 2025 sur un article créé en 2024 pourrait donc entrer dans une exécution future. Les données projetées ici satisfont les deux bornes et n’ont pas ce défaut effectif. Un manifeste d’entrées avec hash de texte/version manque encore.

**Effet et correction.** Une étude à la seconde ou décrite comme stratégie disponible en 2018 resterait injustifiée. Pour l’étude rétrospective limitée, déclarer l’hypothèse des horodatages fournisseur, entrer à une ouverture de séance strictement postérieure à la disponibilité avec latence, exclure corrections et relais tardifs du principal, figer les versions et leur hash. Filtrer les noms de fichiers et toutes les dates avant lecture ou calcul; bloquer toute observation hors 2018-2024. Une archive de réception resterait nécessaire pour des revendications de vitesse ou de première diffusion.

### 7. Secondaire pour l’écart chiffré : le manifeste FinBERT reste partiellement déclaratif

Les **951 369 lignes scorées**, sans doublon d’identifiant, retrouvent exactement leurs probabilités par jointure du titre aux parties. Aucun décalage, aucune différence de probabilité, aucun label différent de l’argmax. Le contrôle complet des **1 281 297 titres distincts** retrouve leur catégorie stockée sans désaccord. Les AUC recalculées par rangs, indépendamment de la fonction auditée, reproduisent le JSON à l’arrondi machine :

| Contrôle textuel | Bons / mauvais | AUC FinBERT | AUC mots positifs |
|---|---:|---:|---:|
| eps_beat_vs_miss | 50,147 / 23,194 | 0.717304041 | 0.805883868 |
| upgrade_vs_downgrade | 25,158 / 30,246 | 0.939075099 | 0.963912583 |
| guidance_raise_vs_cut | 5,797 / 2,029 | 0.978422329 | 0.995564317 |

La baseline lexicale demandée a donc été ajoutée et reproduite. Elle dépasse encore FinBERT dans les trois contrôles. Cela n’atteste aucune lecture correcte de la base ou du trimestre. Le contrôle GPU de 500 titres du premier audit n’a pas été refait : ce second passage ne le demandait pas; la révision, les poids et la longueur de 64 jetons n’ont pas changé et les nouvelles jointures sont vérifiées.

La reprise utilise désormais `max(numéro)+1`, ce qui corrige l’écrasement en présence d’un trou. Le manifeste global contient révision, hash constant et longueur. Mais seule la révision est comparée : modifier `MAX_LENGTH`, le tokeniseur, le modèle ou le hash déclaré n’est pas bloqué, le manifeste est écrasé, et des parties existantes sans manifeste sont acceptées. Le hash est une constante déclarée, pas un calcul sur les poids chargés. Les parties n’ont pas chacune leur provenance vérifiée.

**Effet et correction.** Un mélange silencieux de configurations reste possible à la reprise, sans incident observé ici. Vérifier tous les paramètres et les poids effectifs avant de réutiliser les parties; refuser les parties sans provenance, conserver leurs hashes. Ajouter un contrôle sémantique sans les verbes servant eux-mêmes de vérité de terrain. FinBERT reste hors du signal principal de l’étude d’écart chiffré, donc cette dette ne bloque pas ce sous-échantillon si aucun score n’y est utilisé.

## Vérification de chaque famille de corrections du premier rapport

« Partielle » signifie que le mécanisme demandé existe mais ne garantit pas encore le comportement annoncé. Les mesures précédentes sont recalculées; je ne prends pas les nombres du rapport pour preuve.

| Correction demandée précédemment | État | Constat de ce passage |
|---|---|---|
| Conserver `updated_at`, prendre son maximum avec `created_at` | Appliquée | 0 incohérence sur les 51 636 lignes. |
| Archive de version, source, réception et hash | Partielle / manquante | Deux temps conservés, pas d’archive ni manifeste des versions reçues. Limite reconnue. |
| Exclure corrections; ne pas traiter les relais comme première annonce | Partielle | 0 correction finale; 469 relais tardifs restent admissibles. |
| Consensus horodaté ou nom limité « écart à l’estimation citée » | Appliquée pour le nom | Pas de consensus attesté; ne pas réintroduire le vocabulaire de vraie surprise. |
| Corriger BBT et rechercher les autres symboles réutilisés | Partielle | 101 BBT refusés; faux Wyndham et candidats directs/alias non réunis. |
| Historique daté des alias, émetteur et classe | Manquante | Les fenêtres couvrent l’action, pas chaque alias; anciens noms sans période. |
| Supprimer la liquidité future et stabiliser les égalités | Appliquée | Plus de champ de liquidité, choix lexical et temps+id déterministes. |
| Refuser ambiguïtés entre sociétés | Partielle | 19 rejetées, mais priorité direct contournant 2 591 conflits de candidats. |
| Virgules décimales, parenthèses, suffixes, devises et seuils | Largement appliquée | Nombres indépendants identiques; seuils abs(BPA) ≤100, écart ≤10, pas de K/M/B, ratio ventes [0,1;10]. Devise et unité ne sont pas encore des champs qualifiés. |
| Distinguer annuel, trimestre, prévision et acteur | Partielle, régression | Marqueur trimestriel imposé, mais pas de contrôle fiscal de la publication; Affirm perdu. |
| Séparer ajusté, GAAP et absence d’étiquette | Mal appliquée dans 121 lignes | Position du mauvais EPS ou fragment de nom propre. Base de l’estimation non attestée. |
| Indicateur indépendant de mouvement réalisé | Manquante | Une catégorie unique reste utilisée; 5 fuites strictes sur 600 titres gardés. |
| Ajouter motifs de mouvements et réduire les filtres éditoriaux trop larges | Partielle | `move/wobble/halt` ajoutés; cas `react/trade/near highs` manquants et `gain on` trop large. |
| Prévision externe ≠ prévision de direction; analyste identifié | Partielle | 150/150 notes cohérentes dans le nouveau tirage, mais acteurs externes dans guidance. |
| Construire la fenêtre asymétrique avant choix | Appliquée | Sélection indépendante identique; plus de `merge_asof` puis rejet. |
| Première paire admissible, horloge du signal, une publication par émetteur | Appliquée mécaniquement | 0 doublon, ordre stable reproduit, mais période et réalisé non validés. |
| Accord nom et période avec la publication | Partielle / manquante | Nom d’alias heuristique; trimestre fiscal non comparé. Deux recyclages prouvés. |
| Politique des classes d’actions et couverture des disparues | Partielle | Une clé émetteur; classe choisie lexicalement, pas de registre daté complet. Couverture par survie publiée. |
| Bilan par année, devise, base, action, survie et refus | Partielle | Année et survie ajoutées, base présente mais fautive; devise, raisons fines et coût complet non établis. |
| Geler dates et entrées; ne rien ouvrir après 2024 | Partielle | Assertion sur création, pas de garde avant ouverture ni de maximum sur mise à jour/événement. |
| Tests des contre-exemples avant étude | Partielle | **21 tests passent**, contre 15 auparavant; les nouveaux cas de cet audit ne sont pas couverts. |
| Manifeste modèle/tokeniseur/poids/longueur par partie | Partielle | Manifeste global vérifiant seulement révision; autres paramètres non vérifiés. |
| Reprise sans écrasement ni mélange | Partielle | Numérotation corrigée; provenance complète des anciennes parties non exigée. |
| Baseline lexicale et cas difficiles FinBERT | Partielle | Baseline ajoutée et reproduite; pas de nouveau contrôle dépourvu de verbes explicites. |
| Nouveau tirage après correction, avant rendements | Appliquée par cet audit | Anciens identifiants et textes exclus; les nouveaux tirages deviennent à leur tour des données de développement. |

Le diagnostic de sélection doit rester visible. Mon recalcul indépendant donne une part de BPA lisible parmi les titres earnings de **61,10 %, 57,83 %, 49,32 %, 46,08 %, 41,58 %, 52,48 % et 53,24 %** sur 2018-2024. La couverture finale des publications vaut **65,94 % pour les vivantes** (44 865/68 042) contre **53,24 % pour les disparues** (6 771/12 717). Ces nombres figurent dans `coverage.json`; les arrondis du rapport tiennent. Les retenus par année sont 6 483, 6 072, 5 818, 6 979, 7 880, 9 146 et 9 258 pour 2018-2024. La couverture globale actuelle est un taux de filtrage de publications du référentiel, pas une preuve de représentativité de toutes les annonces. La différence vivantes/disparues est publiée mais pas corrigée par un filtre de survie; c’est préférable. Une colonne `verb_conflict` commune au BPA et aux ventes peut exclure un BPA valide pour une contradiction de ventes : conserver des raisons séparées si l’objectif est exclusivement le BPA. Les 14 lignes finales avec plusieurs symboles bruts n’invalident pas automatiquement « une action » : `n_stocks` ne compte que les actions ordinaires/ADR reconnues. Clarifier cette définition et traiter les autres sociétés non reconnues avant d’en faire une garantie de titre mono-émetteur.

## Protocole acceptable, à figer sans lancer l’étude

1. **Objet.** Étude descriptive rétrospective de l’association entre l’**écart à l’estimation citée** et les résultats futurs prédéfinis. Ni consensus historique vérifié, ni vraie surprise économique sans réserve, ni promesse d’une stratégie déployable à l’époque. FinBERT ne définit pas le signal principal.
2. **Signal.** BPA réalisé moins estimation citée, en décimal exact et dans une même devise, unité et base comparables. Garder valeur et signe; ne pas diviser par un cours et ne pas fabriquer une SUE. Principale : base explicitement comparable, réalisée courante confirmée par source primaire. Séparer ajusté et GAAP; ne pas reclasser les non qualifiés en GAAP. Les 21 018 lignes actuellement étiquetées ajusté/GAAP ne sont qu’un maximum provisoire avant vérifications et nouvelles exclusions.
3. **Événement.** Une publication par CIK et période fiscale confirmée. Fenêtre [-72 h; +24 h] autour de l’acceptation SEC pour retrouver les candidats, appliquée avant sélection. Les dates SEC servent au rattachement rétrospectif, pas à prétendre une disponibilité antérieure au marché. Résoudre période et identité avant d’appliquer l’ordre `(available_at, id)`; une dépêche ne sert qu’à une publication. Une classe d’action primaire admissible par émetteur, choisie avec un registre historique et une règle gelée. Si la classe est indéterminable, exclure, sans choix par liquidité future.
4. **Disponibilité et entrée.** `available_at = max(created_at, updated_at)`, version et hash figés. Ajouter une **latence fixe de cinq minutes**, puis entrer uniquement à **la première ouverture de séance régulière américaine strictement postérieure à ce temps**, suivant le calendrier officiel et le fuseau de la place. Si ce temps est après l’ouverture, attendre l’ouverture suivante. Ne pas décaler le signal à l’heure SEC ou à une ancienne création. Cette convention conservatrice autorise une étude de continuation, pas la réaction instantanée à l’annonce. Aucun calcul d’entrée n’a été effectué dans cet audit.
5. **Exclusions fixées.** Corrections, relais tardifs explicites, prévisions, annuels, FFO ou métriques ne correspondant pas au BPA principal, trimestre/année non vérifiés, contradictions du couple de BPA, unité ou base non comparable, titre réutilisé suspect non résolu, identité ou classe ambiguë, commentaire explicite de mouvement déjà réalisé. Les titres mixtes résultat + mouvement sont exclus du principal. Conserver des analyses exploratoires séparées pour les non qualifiés, sans les réinjecter après examen des résultats. Ni la survie à fin 2024 ni une performance ultérieure ne servent à sélectionner.
6. **Groupes figés.** Trois signes : négatif, nul, positif. Comparaison principale positif contre négatif, zéros publiés descriptivement. Pas d’optimisation de seuil ou de groupes après ouverture des rendements. Présenter séparément GAAP/ajusté et les sept années; la survie à fin 2024 sert seulement au diagnostic rétrospectif de couverture, pas à une règle de décision historique.
7. **Résultats à préenregistrer.** Une fenêtre principale de **cinq séances**, deux secondaires de **une et vingt séances**, mêmes règles d’entrée et de sortie, en ne gardant que les observations dont toute la fenêtre finit au plus tard le 31 décembre 2024. Définir avant calcul la référence de marché, le traitement des radiations/fusions, des non-cotations et des coûts. Publier différences et IC, distribution complète, effectifs et exclusions, résultats nuls aussi bien que positifs. Inférence regroupée au moins par émetteur et date d’annonce; correction de multiplicité annoncée pour les comparaisons secondaires. Les fenêtres et statistiques sont proposées ici, **aucun rendement correspondant n’a été lu ou calculé**.
8. **Gel vérifiable.** Sauver versions du code, projections autorisées et hashes, règles, groupes, calendrier, sources primaires, signal et exclusions avant toute ouverture des résultats de marché. Publier un diagramme d’inclusion par année, base, unité, type d’action et survie, en gardant les non analysables. Ne pas retoucher les règles selon le signe des résultats. Toute correction de données après ouverture doit être annoncée et accompagnée des résultats avant/après, sans sélection du plus favorable.

**Corrections obligatoires restantes avant lancement :** valider période et réalisé courant, retirer les recyclages et Waterstone tant qu’ils ne sont pas corrigés depuis la source; réparer la base au bon couple; résoudre ou exclure les identités et classes ambiguës, notamment Wyndham et conflits direct/alias; réparer le traitement d’Affirm; ajouter l’exclusion indépendante des mouvements réalisés pour le principal; verrouiller toutes les dates et figer le protocole, ses données et les nouvelles tables. Recontrôler les régressions sur ces témoins, puis un nouveau tirage indépendant ou une validation primaire exhaustive du sous-échantillon retenu. Le registre historique complet peut être remplacé, pour ce lancement limité, par l’exclusion documentée de tous les cas non résolus; la couverture perdue doit être publiée.

**Réponse nette : NON aujourd’hui; OUI après ces corrections sur un sous-échantillon explicitement vérifié et avec l’horloge conservatrice ci-dessus.** L’absence de consensus historique n’interdit pas cette étude ainsi renommée; elle interdit son interprétation comme vraie surprise du consensus.

## Annexe : 28 nouvelles publications vérifiées sur sources publiques

La date ci-dessous est celle du document de publication contrôlé à partir du jour SEC; les jours concordent dans ces 28 cas. « Disparue » signifie seulement `alive_at_end == False` dans l’univers autorisé. Les montants sont des BPA de résultats, jamais des cours. Les différences de base mentionnées sont essentielles au contrôle, pas des estimations de rendement.

| Tirage | Société / symbole | Fin de période | Date | Vérification du réalisé |
|---|---|---|---|---|
| 144 | WSBF | 2017-12-31 | 2018-01-30 | ÉCHEC : 0,23 est le BPA Q4 2016; Q4 2017 donne 0,11 GAAP ou 0,21 hors effet fiscal. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1569994/000156999418000002/exhibit991.htm) |
| 51 | MCRN (disparue) | 2017-12-31 | 2018-02-20 | 0,59 ajusté; GAAP 0,05. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1637913/000163791318000002/exhibit991-q42017.htm) |
| 90 | TCO (disparue) | 2018-03-31 | 2018-04-26 | 0,30 GAAP; FFO distinct 0,88. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/890319/000089031918000079/a2018q18-kexhibit99.htm) |
| 120 | PINC | 2018-06-30 | 2018-08-23 | 0,70 ajusté pleinement distribué. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1577916/000119312518256321/d602231dex991.htm) |
| 121 | HOLX | 2018-12-29 | 2019-01-30 | 0,58 non-GAAP; GAAP 0,36. Base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/859737/000115752319000178/a51932569ex99_1.htm) |
| 64 | OLED | 2018-12-31 | 2019-02-21 | 0,40 GAAP; autre norme ASC 605 : 0,95. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1005284/000156459019003681/oled-ex991_6.htm) |
| 61 | SEMG (disparue) | 2018-12-31 | 2019-02-27 | -0,08 GAAP; parenthèses correctement lues. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1489136/000148913619000007/exh991ye2018earningspressr.htm) |
| 128 | STL (disparue) | 2019-03-31 | 2019-04-24 | 0,50 ajusté; GAAP 0,47. Base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1070154/000107015419000012/stlexhibit991033119.htm) |
| 52 | MMM | 2019-12-31 | 2020-01-28 | 1,95 ajusté hors litiges. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/66740/000110465920007328/tm205961d1_ex99-1.htm) |
| 159 | TRU | 2019-12-31 | 2020-02-18 | 0,75 ajusté; base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1552033/000155203320000012/exhibit99112312019.htm) |
| 186 | CAKE | 2020-03-31 | 2020-05-05 | 0,04 ajusté, résultats réalisés préliminaires, pas prévision. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/887596/000110465920056910/tm2018605d1_ex99-1.htm) |
| 158 | IVC (disparue) | 2020-09-30 | 2020-10-29 | -0,10 ajusté; GAAP -0,21. Base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/742112/000074211220000107/q32020exhibit991.htm) |
| 127 | T | 2020-12-31 | 2021-01-27 | 0,75 ajusté trimestriel; -0,75 annuel GAAP est un autre montant. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/732717/000073271721000009/t-4q2020exhibit991.htm) |
| 89 | MHO | 2020-12-31 | 2021-02-02 | 2,93 non affiché explicitement : 2,71 GAAP + 0,22 de dépréciation. Reconstitution plausible, non validation exacte. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/799292/000079929221000004/exhibit9914thqtr2020earnin.htm) |
| 130 | PAYC | 2020-12-31 | 2021-02-10 | 0,84 non-GAAP; GAAP 0,43. Base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1590955/000156459021005260/payc-ex991_6.htm) |
| 56 | OGS | 2021-03-31 | 2021-05-03 | 1,79 GAAP. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1587732/000158773221000042/ogsq12021earningsreleasene.htm) |
| 147 | APPH (disparue) | 2021-12-31 | 2022-02-24 | -0,88 GAAP. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1807707/000180770722000024/exhibit99q42021earningsrel.htm) |
| 166 | AZO | 2022-02-12 | 2022-03-01 | 22,30 GAAP, trimestre fiscal de 12 semaines. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/866787/000117184322001473/exh_991.htm) |
| 34 | RRR | 2022-06-30 | 2022-08-09 | 0,26 GAAP, action de classe A. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1653653/000156459022028746/d350316dex991.htm) |
| 91 | MP | 2022-09-30 | 2022-11-03 | 0,36 ajusté; GAAP 0,33. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1801368/000180136822000034/mpmcq32022er.htm) |
| 33 | MLKN | 2023-09-02 | 2023-09-26 | 0,37 ajusté; GAAP 0,22. Base absente du titre. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/66382/000006638223000076/mk8k_09022023ex991.htm) |
| 116 | INDB | 2023-09-30 | 2023-10-19 | 1,38 GAAP. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/776901/000077690123000213/exhibit991-indb09x30x2023e.htm) |
| 67 | SLCA (disparue) | 2023-09-30 | 2023-11-03 | 0,38 ajusté; GAAP 0,34. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1524741/000152474123000017/ex991_slcax20230930.htm) |
| 19 | AKTS | 2023-09-30 | 2023-11-13 | -0,27 perte nette non-GAAP; -0,26 est la perte opérationnelle, métrique différente. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1584754/000121390023085528/ea188109ex99-1_akoustis.htm) |
| 198 | ACU | 2023-12-31 | 2024-03-01 | 0,40 hors cession de lignes de produits. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/2098/000095017024023566/acu-ex99_1.htm) |
| 25 | EFTR (disparue) | 2023-12-31 | 2024-03-25 | -3,42 GAAP. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1828522/000119312524076494/d802072dex991.htm) |
| 75 | CNTA | 2023-12-31 | 2024-03-28 | -0,38 par action ordinaire. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1847903/000184790324000052/cntapr-q42023.htm) |
| 111 | GOEV | 2023-12-31 | 2024-04-01 | -1,73 ajusté après regroupement d’actions; conserver cette unité pour l’estimation. [Pièce SEC](https://www.sec.gov/Archives/edgar/data/1750153/000162828024014072/goev-20240401x8kexx991.htm) |

Les cinq témoins d’anomalie fiscale et les cinq titres anciens répétés disposent en plus de `quarter_primary.json`, `repetition_primary.json`, `aos_followup.json` et `followup2.json`. Les trois répétitions numériquement valides ne sont pas traitées comme des erreurs. Les identités Galapagos, Meridian et VivoPower sont documentées dans `identity_sources.json`. Les estimations de marché citées ne sont validées par aucune de ces pièces de résultat.

## Reproductibilité et limites restantes

`tests.txt` conserve la sortie de `PYTHONDONTWRITEBYTECODE=1 venv/bin/python tests/test_news_filter.py` : **21 tests, succès**. `quality.json` conserve les hashes SHA-256 des six fichiers audités, la reclassification complète, les contrôles de scores et les AUC; `selection.json` et `link_checks.json` conservent les reproductions indépendantes. Le rapport porte sur l’état de ces hashes, pas sur des modifications ultérieures.

Les scripts `prepare.py`, `manual_categories.py`, `links.py`, `surprises.py`, `targeted.py`, `selection.py`, `final_metrics.py`, `weighted_leakage.py`, `coverage.py` et `quality.py` utilisent les projections locales autorisées. L’analyseur indépendant et les exclusions de l’ancien audit sont copiés dans ce répertoire pour ne pas dépendre de sa présence. Les scripts HTTP sont séparés; les réponses utiles et leurs URL sont archivées en JSON. Pour reproduire les mesures sans refaire le réseau, garder les projections et les fichiers de jugements, puis exécuter depuis le dépôt :

```sh
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/surprises.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/targeted.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/selection.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/final_metrics.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/weighted_leakage.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/coverage.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/quality.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit2/write_report.py
```

Les jugements sémantiques ne sont pas une vérité automatique reproductible par une regex; ils sont consignés ligne par ligne pour contradiction. Le contrôle de 28 sources ne peut pas certifier les 51 636 réalisés. Les 179 refus indécidables et cinq liens indécidables demandent davantage que le titre et le référentiel issu du même fournisseur. L’heure réelle de réception, l’historique des versions et celui de l’estimation restent invérifiables avec les fichiers autorisés. Ces limites sont des limites de preuve explicites, et non des motifs pour ouvrir les rendements afin de choisir les corrections.
