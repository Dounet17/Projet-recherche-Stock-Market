# Verdict : ne pas lancer l’étude de la vraie surprise en l’état

Audit indépendant du 7 novembre 2026, branche `interface-web`, commit `b6ea6f1051b89e5ba9cbe261f566fcc8d6703e17`.

Les comptes et les scores FinBERT du rapport sont largement reproductibles. Cela ne valide pas leur interprétation causale. Le blocage décisif est l’absence de preuve de la disponibilité historique de la version du titre et de son estimation. J’ai aussi trouvé un rattachement certain à la mauvaise banque, jusque dans deux publications appariées, des prévisions prises pour des résultats et une fuite mesurable de commentaires de marché vers les catégories gardées. Le faible nombre d’erreurs arithmétiques du BPA ne résout aucun de ces trois problèmes.

Toutes les corrections doivent être arrêtées avant l’ouverture des rendements. L’étude pourra ensuite porter sur une surprise explicitement définie comme l’écart à l’estimation citée dans une version historiquement disponible, avec une horloge conservatrice. Elle ne pourra pas soutenir une réaction à la seconde de première diffusion avec les seuls fichiers actuels.

## Périmètre, méthode et limites de cet audit

J’ai utilisé uniquement les fichiers autorisés, avec une projection explicite sur les huit colonnes permises des événements. Aucun fichier de cours, de rendements, de SUE, de portefeuille, de holdout ou de trials n’a été ouvert. Aucun secret ni `.env` n’a été ouvert. Les observations locales analysées s’arrêtent au 31 décembre 2024. Tous les fichiers créés sont dans `/tmp/news-audit/` et aucune modification du dépôt n’est intentionnelle.

Incident à signaler pour une lecture stricte du protocole : le moteur de recherche a parfois renvoyé automatiquement des extraits non sollicités hors période ou mentionnant des cours et des performances. Ces extraits n’ont servi à aucun calcul ni aucune décision; aucun cours ou rendement de l’étude n’a été demandé ou ouvert. Je ne revendique donc pas une garantie de zéro exposition à tout extrait financier externe. Les vérifications retenues portent sur les documents historiques précis énumérés en annexe, pas sur ces résultats parasites. Les requêtes HTTP directes vers la SEC utilisent `MasterResearchNewsAudit/1.0 public academic research`, avec au moins 0,4 seconde entre requêtes séquentielles, soit moins de 8 requêtes par seconde.

La graine propre de l’audit est **735109**, différente de celle du rapport. Le tirage contient 150 titres distincts par catégorie, tous avec `n_stocks >= 1`, soit 900 articles. Les titres ont été imprimés sans leur catégorie et jugés selon une grille indépendante : mouvement déjà réalisé; aperçu/opinion/remplissage; résultat publié; prévision propre de la société; note/prévision externe d’analyste; fait/autre; indécidable. Le fichier de vérité de terrain et les jugements finaux sont conservés. Le contrôle des fuites utilise les **600 articles gardés** de ce tirage stratifié. Il n’est pas un échantillon simple de 600 articles de l’ensemble.

J’ai relu les 150 lignes de BPA du tirage `735111`, contrôlé 42 publications avec sources publiques réparties sur 2018-2024, dont 21 sociétés disparues à fin 2024, et examiné 106 liens, dont 100 vers des actions ordinaires ou ADR. Les 500 titres FinBERT sont tirés avec la graine `735116`. Les intervalles sont des Wilson bilatéraux à 95 %, conditionnels au jugement de ce seul relecteur. Ils ne quantifient pas l’incertitude sémantique du relecteur.

## Défauts classés par gravité

### Bloquant 1 : l’heure de disponibilité du titre et celle du consensus ne sont pas établies

**Faits mesurés.** Les 1 399 118 titres bruts et ceux de la table correspondent exactement, mais il s’agit du même état téléchargé, pas de deux versions historiques. `updated_at` est supprimé de `news_articles.parquet`. Dans le brut, 12 993 articles ont été mis à jour plus d’une heure après `created_at`, soit **0,93 %**, et 2 632 plus d’un jour après. Ce n’est pas le 1,4 % d’un échantillon cité par le rapport; ce dernier n’était pas un taux de population.

Sur les 76 036 titres à BPA analysé : 1 237 ont un décalage de mise à jour supérieur à une seconde, 989 supérieur à une minute, 243 supérieur à une heure et 11 supérieur à un jour. Il existe 521 titres commençant par `CORRECTION:` et 549 par `UPDATE:`. Les ensembles se recouvrent; ne pas additionner ces nombres. Parmi les publications effectivement appariées et avec BPA, 158 utilisent un article mis à jour plus d’une heure après sa création.

**Exemples réels.** Article `22768706`, C3.ai, BPA ajusté -0,22 contre -0,28 : créé le 1 septembre 2021 à 20:16:48 UTC, mis à jour le 7 septembre à 23:28:27 UTC, soit **147,19 heures** plus tard. L’article `13122326`, FLEETCOR, explique dans son titre de correction qu’un BPA GAAP de 3,33 avait été comparé à tort à une estimation non-GAAP avant remplacement par 2,78 contre 2,72. Pourtant `updated_at == created_at` dans ce fichier. Ce dernier cas peut être une nouvelle dépêche de correction créée séparément : il ne prouve pas à lui seul un antidatage. Il prouve que filtrer seulement les grands écarts de mise à jour ne suffit pas à identifier toutes les corrections.

**Comparaison à la SEC.** Je retrouve 61 059 publications couvertes, une médiane de **-26 secondes** entre dépêche sélectionnée et acceptation SEC, les déciles **-1,343 h / +0,725 h**, et **51,712 %** de dépêches antérieures au dépôt. Il y a 7 225 appariements à plus d’une heure avant le dépôt et 462 à plus de 24 heures avant. Ce sont des écarts au dépôt, pas à la première annonce publique. Le choix de la dépêche la plus proche du dépôt favorise mécaniquement des petits écarts; il ne mesure pas systématiquement la première dépêche.

Les avances sont plausibles. Dans les 42 vérifications, les communiqués d’Investors Bancorp du 25 janvier 2018, de Fiesta du 11 novembre 2021 et de Harte Hanks du 9 mai 2024 précèdent le jour de dépôt. J.B. Hunt publie le 16 juillet 2018, avec une dépêche à 07:09 ET et le dépôt à 17:14 ET. Nordstrom publie son communiqué le 21 novembre 2019 à 16:05 ET; le titre est créé à 16:06:08 ET, avant le dépôt à 16:37:24 ET. Cela explique un écart sans fuite. Le cas ON Semiconductor publié un samedi 27 avril 2019 a été vérifié : la pièce SEC indique bien le 27 avril, ce n’est pas une preuve de fuite.

**Ce qui reste invérifiable.** Aucun historique des versions par identifiant ni journal de réception ne permet d’établir que le titre actuel existait exactement à `created_at`. Une mise à jour peut concerner seulement le corps; je ne transforme donc pas les 243 mises à jour tardives en 243 fuites prouvées. Inversement, un horodatage inchangé ne certifie pas une version originale. Je n’ai trouvé aucun cas démontré où un chiffre de résultat serait présent avant sa toute première annonce publique; cela ne démontre pas son absence dans l’ensemble. L’heure habituelle d’un émetteur et l’heure SEC ne sont pas des bornes suffisantes pour prouver l’indisponibilité d’un chiffre.

La provenance, la base comptable et l’heure de gel des estimations citées ne sont attestées pour **aucune des 42 publications**. Le communiqué de la société confirme généralement le réalisé, pas le consensus d’avant annonce. Le nombre d’estimations du titre prouvées disponibles avant annonce est donc **0/42**, ce qui mesure une absence de preuve, pas un taux de consensus faux. On trouve aussi 1 242 titres à BPA qui annoncent explicitement un relais tardif, par exemple `Logitech International Late Yesterday Reported...`.

**Effet attendu.** Utiliser la version corrigée avec l’heure initiale peut injecter du futur. Utiliser un consensus mis à jour ou un relais tardif comme une surprise instantanée modifie le sens de l’événement. Un effet d’annonce anticipé ou déjà incorporé peut alors être attribué à tort au signal mesuré.

**Correction obligatoire.** Conserver `created_at`, `updated_at`, le texte, son hash, l’identifiant, la source et l’heure de réception/version. En l’absence d’archive de versions, prendre **`available_at = max(created_at, updated_at)`**, mettre en quarantaine `CORRECTION:` et les titres dont la version ne peut pas être prouvée, puis n’autoriser une entrée qu’après cette disponibilité et une latence fixée avant étude. Cette borne reste une hypothèse conservatrice, pas une preuve de première diffusion. Pour une étude de vitesse à la seconde, exiger une archive de flux ou renoncer à cette affirmation. Pour le consensus, obtenir une observation horodatée avant annonce et de même base; à défaut nommer le signal « écart à l’estimation citée dans la dépêche » et ne pas le présenter comme le consensus historique vérifié. L’absence de consensus historique ne se corrige pas par une valeur de marché.

### Grave 2 : un alias de symbole envoie les nouvelles à la mauvaise société

**Mesure indépendante.** J’ai reconstruit les liens depuis les symboles bruts, les alias et les intervalles de cotation. Je retrouve exactement **2 679 535 citations**, **158 026 inconnues**, **13 548 hors intervalle**, **3 558 ambiguïtés résolues par liquidité**, et **2 507 421 liens uniques**, avec **zéro différence** par rapport à `news_links.parquet`. Le code reproduit donc sa logique; cette logique peut être fausse.

**Erreur certaine.** Les **101 citations de `BBT`** de la période autorisée sont envoyées vers `BHLB#0`, CIK **1108134**, Berkshire Hills. Les titres concernent BB&T, CIK **92230**, devenue Truist. Au moins 44 sont des articles à un seul symbole, ce qui rend l’attribution non ambiguë. Exemple du tirage enrichi : `UBS Maintains Neutral on BB&T, Lowers Price Target to $52`, le 21 octobre 2019, lié à `BHLB#0`.

Ce défaut contamine aussi **deux appariements de publications de Berkshire Hills**, le 19 juillet et le 18 octobre 2018 : le premier reçoit `BB&T Q2 EPS $1.01, Inline...`, le second `BB&T Earlier Reported Q3 EPS $1.03 Beats $1 Estimate...`. L’erreur n’est donc pas seulement cosmétique. L’identité distincte des deux banques et la continuité BB&T vers Truist sont attestées par les pièces SEC historiques [BB&T/Truist](https://www.sec.gov/Archives/edgar/data/92230/000119312519309481/d845019d424b3.htm) et [Berkshire Hills](https://www.sec.gov/Archives/edgar/data/1108134/000114420419027204/tv522008_8k.htm).

**Contrôle manuel des liens.** Les 106 lignes comprennent 100 actions ordinaires/ADR et six autres instruments, qui sont identifiés séparément. Parmi les **100 liens d’actions**, 75 ont une correspondance nominale cohérente, 1 est certainement faux et 24 restent non résolus indépendamment : renommages, fusions, changements d’activité ou titre sans société explicite. Le tirage comprend une strate enrichie en changements de symboles, dont `UTX`, `CHKE`, `CNAT`, `MTSL`, `EARS`, `PEIX`, `DMPI`, `RIDE`, `BODY`, `PTIE`, `LIFE`, `MDCA`, `TIVC`, `MMC`, `OBNK`, `IINN`, ainsi que des identifiants segmentés comme `MDXG#1`, `CTV#1`, `EVER#1`.

Le **taux d’erreur certaine observé est 1/100**, mais le taux final de cet échantillon est borné entre **1 % et 25 %** tant que les 24 cas ne sont pas tranchés. Ce n’est pas une estimation du taux global, car l’échantillon est enrichi et une chaîne d’alias issue du même référentiel n’est pas une preuve indépendante de continuité. Un intervalle binomial sur 1/100 donnerait une fausse impression de validation. Les 24 cas exigent un historique indépendant par société et par action; certains noms actuels ne peuvent pas être expliqués sans documents de changements postérieurs à 2024, interdits ici.

**Liquidité et symboles inconnus.** Les 3 558 arbitrages utilisent une moyenne de liquidité du segment entier, connue seulement après une partie des articles; aucune égalité au maximum n’est observée. Cela peut utiliser de l’information future pour choisir la société. Surtout, les dates encadrent l’action entière, pas la période de validité de chacun de ses alias. Le cas BBT est compatible avec ce défaut. Parmi les inconnus, BTCUSD compte 13 314 citations, ETHUSD 10 150, DOGEUSD 4 305; mais aussi TCEHY 1 427, CURLF 1 328, RHHBY 1 099, TCNNF 1 078, VWAGY 1 054, SSNLF 989. Les motifs `USD` en suffixe ou `$` en préfixe représentent **51 995 citations (32,9 %)**, et cinq lettres terminées par F/Y **62 300 (39,4 %)**. Ce sont des indicateurs de crypto/FX ou de gré à gré, pas une validation instrument par instrument. Une grande partie relève ainsi probablement de marchés hors univers, pas nécessairement de sociétés disparues oubliées. Les citations ne sont pas des articles uniques et ne doivent pas être additionnées comme tels.

**Effet attendu.** Le signal d’une autre société est attribué à l’action étudiée; la couverture et l’association aux événements deviennent fausses. Le choix avec liquidité future peut modifier la sélection historique.

**Correction obligatoire.** Un historique `symbol, valid_from, valid_to, issuer_cik, security_id`, distinguant l’émetteur et la classe, avec contrôle du nom dans le titre. Corriger BBT et rechercher systématiquement tous les alias réutilisés. En cas d’ambiguïté de sociétés, exclure le lien ou le faire arbitrer par un identifiant historique; la liquidité ne doit départager que des classes correctement identifiées, avec une information disponible à la date. Publier les inconnus par type d’instrument et contrôler les 24 chaînes non établies avant leur admission.

### Grave 3 : l’analyse du BPA mélange quelques prévisions, périodes et unités

**Analyseur indépendant.** `surprise_audit.py` découpe les métriques puis les tokens de montants, reconnaît les parenthèses, les unités, les devises et les virgules décimales, et traite les verbes prospectifs. Il n’importe pas `parse_surprise` et est appliqué aux **149 269 titres earnings**, pas seulement à un échantillon. Il sert à trouver des divergences, pas de vérité économique universelle; les cas nouveaux ont encore besoin de validation de leur devise et de leur base.

| Mesure | BPA | Ventes |
|---|---:|---:|
| Paires du code audité | 76 036 | 81 394 |
| Paires de l’analyseur indépendant | 76 184 | 81 607 |
| Seulement dans l’analyseur indépendant | 154 | 223 |
| Seulement dans le code audité | 6 | 10 |
| Valeurs différentes quand les deux donnent une paire | 5 | 6 |
| Signes de surprise différents parmi ces paires | 3 | 4 |

**Erreurs certaines de nombres.** Cigna `15917500` donne `EPS $4.69 Beats $4,35 Est` : le code transforme **4,35 en 435**, puis conclut à une mauvaise surprise au lieu d’une bonne. Mercantile Bank `23434123`, 0,95 contre `0,85`, et Interface `25896806`, 0,47 contre `0,31`, inversent aussi le signe. Enterprise Products Partners `13071395` transforme `0,59` en **59**, et Baidu `21170080` transforme `1,89` en **189**, sans inversion du signe dans ces deux cas. Les cinq divergences de valeurs de BPA ont été relues. Cela donne un plancher vérifié de **3/76 036 = 0,00395 %** de signes numériques faux par rapport au titre, sans garantir la vérité économique du réalisé ou du consensus.

**Prévisions prises pour résultats.** Six titres à BPA sont rejetés par l’analyseur indépendant comme prospectifs, après relecture. `Home Depot Reaffirms FY19 ... EPS $10.03 vs $10.09 Estimate` (`13778276`) est une prévision, pas un résultat publié. Même problème pour MasTec, Wolverine, deux dépêches QIAGEN et Inter Parfums. `FORWARD` omet `Reaffirms`, `Raises`, `Lowers`, etc.; `EARNINGS` accepte un marqueur annuel suivi de BPA, et la lecture numérique accepte `vs` même après ces verbes prospectifs omis. Exclure les prévisions ne consiste pas seulement à chercher `Sees`.

**Périodes.** **178 BPA analysés**, dont 176 avec une action liée, ont un premier marqueur annuel et aucun premier marqueur trimestriel; par exemple `IAMGOLD Reports FY17 Adj. EPS $0.06 vs $0.08 Est.` et `Trilogy Metals Reports FY 2017 EPS $0.20 vs $(0.02) Est.`. Ce sont des titres annuels à mettre à part, pas tous des erreurs de la dépêche. Le problème apparaît quand ils sont traités comme BPA d’un trimestre. La couverture sélectionne 73 titres dont le premier marqueur de période est annuel, dont 60 avec BPA; c’est un signal de risque, pas un décompte prouvé de mauvais trimestres. Les périodes fiscales décalées ne sont pas des erreurs : le Q1 fiscal 2025 de PFGC est bien publié en novembre 2024 et correspond à la période close le 28 septembre 2024.

**Unités et devises.** Trois titres ont explicitement un suffixe milliard sur le BPA : Biogen `EPS $6.99B`, C.H. Robinson `EPS $1.34B`, Builders FirstSource `EPS $0.57B`. Le code stocke 6,99 milliards, 1,34 milliard et 570 millions par action. Le filtre `|BPA| > 100` ou `|écart BPA| > 10` signale 66 titres. Pour les ventes, **533/81 394 = 0,65 %** ont un rapport absolu réalisé/estimation hors [0,1;10]; **230** paires à unités différentes comportent une unité manquante. Exemple relu dans les 150 : Inter Parfums `18286002`, `Sales $160.60M Beat $160.60 Estimate`, produit un rapport d’un million. Une différence M/B peut être parfaitement correcte, ce n’est pas elle seule une erreur.

L’analyseur indépendant reconnaît **134 paires de BPA** avec une monnaie explicite non USD, et 174 de ventes, ignorées par le code initial dans ces formats. Il ne faut pas les réintroduire comme dollars américains : `C$`, `€`, `£`, pence et les ratios d’ADR exigent une unité commune dans les deux montants. Le simple symbole `$` d’un titre sur un émetteur canadien ne prouve pas CAD ou USD. Le code initial traite correctement les parenthèses dans les **22 206 titres** dont le BPA analysé suit un format négatif entre parenthèses; les divergences de valeurs trouvées ne proviennent pas de ce format.

**Ajusté ou comptable.** 122 titres analysés à BPA contiennent à la fois les marqueurs GAAP et ajusté; cela n’est pas une erreur en soi. Les 42 sources montrent surtout qu’un BPA sans étiquette n’est pas nécessairement GAAP : SPS Commerce 0,39 est non-GAAP contre 0,19 GAAP; Aaron’s 1,15 est ajusté contre -1,60 GAAP; Arcosa 0,40 est ajusté contre 0,19 GAAP; Hawaiian -0,90 est ajusté contre -0,72 GAAP; Blink -0,41 est ajusté contre -0,55 GAAP. L’article d’Investors Bancorp cite aussi un GAAP +0,02 alors que le communiqué annonce une perte de 0,02; son BPA ajusté 0,17 sélectionné est correct. Lire correctement la paire du titre ne suffit donc pas à choisir une base comptable.

**Contrôle manuel et estimation d’erreur.** Les **150 paires tirées au hasard** ont été relues : **0 erreur de signe arithmétique par rapport au titre**, intervalle Wilson **[0 %; 2,50 %]**. Ce résultat ne contredit pas les trois erreurs rares trouvées par examen exhaustif. Le contrôle de 150 titres ne permet pas de dire que le taux d’erreur économique, en tenant compte de la base et du consensus historique, est zéro : ces éléments restent insuffisamment attestés. Les 76 contradictions verbe/chiffres du rapport sont bien présentes, mais ne couvrent ni les unités aberrantes avec signe inchangé, ni les prévisions, ni les bases incompatibles. Dans le tirage, une contradiction sur les ventes de Laureate n’invalide pas automatiquement le BPA.

**Effet attendu.** Des extrêmes artificiels dominent un classement de surprise; une prévision peut être attribuée à une publication déjà passée; comparer ajusté et GAAP peut changer le signe économique sans aucune erreur arithmétique. Les omissions de devises et les filtres de plausibilité peuvent aussi changer la composition par émetteur et par année.

**Correction obligatoire avant gel.** Parser une structure avec période, exercice fiscal, unité, devise, base comptable, montant publié, consensus, sens du verbe et type réalisé/prévision. Exiger un marqueur trimestriel explicite pour l’étude trimestrielle; isoler les résultats annuels. Écarter les clauses prospectives avant toute extraction, y compris `Reaffirms`, `Raises`, `Lowers`, `Cuts`, `Maintains`, `Narrows`, et séparer les clauses du titre. Refuser automatiquement tout suffixe K/M/B sur un BPA exprimé par action. Mettre en revue, sans corriger silencieusement, `|BPA| > 100`, `|BPA-consensus| > 10`, une devise ou une unité différente/non attestée, une vente non positive, ou un rapport de ventes hors [0,1;10]. Normaliser les virgules décimales seulement quand elles ne peuvent pas être un séparateur de milliers; sinon rejeter. Tous ces seuils doivent être fixés maintenant et leurs exclusions publiées; ils peuvent retirer de vraies surprises extrêmes. Ne pas calculer une surprise relative avec division par un consensus nul ou presque nul. Conserver l’égalité à la précision du titre plutôt que déduire un signe caché du seul verbe.

### Grave 4 : les catégories gardées contiennent des commentaires de mouvements réalisés

Les précisions du tirage indépendant sont les suivantes. Les 14 titres indécidables sont comptés comme non confirmés dans la borne conservatrice de précision, pas comme erreurs certaines.

| Catégorie annoncée | Titres | Confirmés | Précision conservatrice | IC 95 % Wilson |
|---|---:|---:|---:|---|
| Commentaire de marché | 150 | 142 | 94,67 % | [89,83 % ; 97,27 %] |
| Remplissage / aperçu | 150 | 129 | 86,00 % | [79,54 % ; 90,66 %] |
| Résultats publiés | 150 | 141 | 94,00 % | [88,99 % ; 96,81 %] |
| Prévisions de la société | 150 | 115 | 76,67 % | [69,28 % ; 82,72 %] |
| Note d’analyste | 150 | 146 | 97,33 % | [93,34 % ; 98,96 %] |
| Fait sur une société | 150 | 109 | 72,67 % | [65,04 % ; 79,17 %] |

La définition « fait/autre » de la grille primaire inclut aussi six titres macroéconomiques ou sectoriels sans fait propre à une société, par exemple la loi sur la recherche médicale du cannabis, la politique de la Fed et les demandes d’allocations chômage. Si « faits sur une société » est entendu strictement, la précision company_news descend à **103/150 = 68,67 %**, IC Wilson **[60,86 %;75,55 %]**, contre 72,67 % pour la grille large. Cette sensibilité de définition est distincte des commentaires de mouvement, dont le taux ci-dessous ne change pas.

Les 14 indécidables sont des titres du genre `Q1 Earnings Insights`, tous dans evergreen : le titre seul ne dit pas s’il s’agit d’un aperçu ou d’un bilan après publication. Pour evergreen, la proportion compatible va donc de **86,0 % à 95,3 %**, avant l’incertitude d’échantillonnage. Les exemples sans ce problème donnent notamment sept erreurs certaines sur 150 evergreen.

Comparaison au rapport : notes d’analystes 97,3 % contre 100 % sur 30; résultats 94,0 % contre environ 96,7-98,3 % sur 60; prévisions 76,7 % contre 85 % sur 60; faits 72,7 % contre environ 76 % sur 46; commentaires 94,7 % contre 100 % sur 30. Les intervalles et les critères de jugement empêchent d’affirmer une dégradation statistiquement démontrée pour chaque catégorie. Le rapport est néanmoins trop optimiste s’il interprète ces catégories comme des faits homogènes.

| Catégorie gardée | Commentaires relus | IC 95 % du taux | Articles avec action | Nombre extrapolé |
|---|---:|---|---:|---:|
| Résultats publiés | 2/150 | [0,37 % ; 4,73 %] | 143 089 | 1 908 |
| Prévisions de la société | 3/150 | [0,68 % ; 5,71 %] | 55 862 | 1 117 |
| Note d’analyste | 0/150 | [0,00 % ; 2,50 %] | 298 245 | 0 |
| Fait sur une société | 10/150 | [3,66 % ; 11,84 %] | 465 581 | 31 039 |

L’estimation stratifiée est **34 064 commentaires** parmi 962 777 articles gardés, soit **3,54 %**. Ce n’est pas 15/600 appliqué à tout l’ensemble : chaque catégorie est pondérée par sa taille. L’incertitude est forte, surtout dans company_news; son seul taux de 6,67 % a un intervalle [3,66 %;11,84 %], soit environ 17 046 à 55 107 articles de cette catégorie. Aucun commentaire observé dans 150 analyst ne signifie pas qu’il n’y en a aucun : sa borne supérieure est 2,50 %.

**Exemples et mécanismes.** `NLS Pharmaceutics Shares Move Higher; ... FDA Acceptance ...` et `Newegg ... Shares Move Higher` restent company_news : la regex reconnaît `moving`, pas `move`. `UiPath Shares Wobble After Q3 Results...` et `Penske Automotive Group Falls After Q2 Earnings Miss` restent earnings. Le Nasdaq qui `Turns Higher` reste company_news. `A Peek Into The Markets: US Stock Futures ... Ahead Of Earnings` devient guidance à cause du mot earnings. Les comptages automatiques distincts trouvent **1 639** titres gardés avec `shares move higher/lower`, **1 193** débuts `Trading Halt:`, et **352** motifs de mouvement supplémentaires `wobble/slammed/tank/...`. Ces motifs sont des ensembles potentiellement recouvrants, pas trois estimations indépendantes du total.

**Autres résidus.** Le tirage montre des aperçus, Cramer, des listes WallStreetBets, de la dette, des dividendes, des avis externes classés comme guidance et un article sportif sans fait sur l’émetteur. Les familles de remplissage ciblées dans `metrics.py` correspondent à **5 417** articles gardés; **2 029** titres gardés mentionnent analystes et forecasts/guidance. Ces chiffres servent à cibler une relecture, ils ne sont pas tous des erreurs prouvées.

**Vrais faits écartés.** La règle générale `Here's Why` écarte `Here's Why Cargill Suspended Palm Oil Deal...`, un fait. `need to know` fait écarter le lancement du Model Y de Tesla et l’arrivée de XPeng en Suède/Pays-Bas. Ce motif écarte aussi cinq notes nominales d’analystes dans le tirage evergreen. À l’inverse, l’anticipation de cours `Why Beaten-Down Snap Stock Could Be Poised For A Reversal` n’est pas un commentaire de réaction déjà faite. L’ordre des règles confond parfois le genre éditorial et le contenu économique.

**Effet attendu.** Une news écrite parce que le cours vient de bouger peut fabriquer un lien apparent entre ton et mouvement. La contamination ne se résume pas à une atténuation du signal. Les exclusions de faits et d’analystes ne sont pas aléatoires non plus.

**Correction précise.** Mettre un indicateur indépendant `describes_realized_move`, prioritaire sur le type économique et conservé même si le titre contient un vrai fait. Ajouter `move/moves/moved`, `wobble`, `slammed`, les reprises/suspensions et les sujets nommés sans le mot stock; inclure les index et futures. Exiger que `Here's Why` ait pour objet un mouvement pour justifier une exclusion causale. Scinder « type de fait » et « format éditorial » : un aperçu n’est pas une prévision de la direction; une note n’est pas le résultat de la société. Refaire ensuite un tirage neuf, distinct de ces 900 titres maintenant utilisés pour proposer les règles.

### Important 5 : les 63 % et 76 % sont des taux d’appariement particuliers, pas une validation des événements

**Recalcul.** Les **80 759 publications**, **75,606 %** avec paire de BPA ou de ventes et **62,742 %** avec BPA sont reproduits exactement, ainsi que les taux annuels arrondis. Le dénominateur est un sous-ensemble avec acceptation SEC, délai de dépôt au plus 150 jours, puis dédoublonnage `cik, accepted_utc`. Il ne représente pas tous les communiqués de toutes les entreprises. Le filtrage retire **4 919 lignes** de classes ou observations partageant société et heure. Un même communiqué n’est pas compté une fois par classe dans ce dénominateur; c’est raisonnable pour une couverture d’émetteurs, mais pas suffisant pour attribuer un événement à une action.

**Bogue de fenêtre.** `merge_asof(direction='nearest', tolerance=3 jours)` choisit d’abord dans une fenêtre symétrique, puis rejette le candidat postérieur de plus d’un jour. Il peut ainsi jeter un candidat à +30 h alors qu’une dépêche admissible à -40 h existe. J’ai appliqué la fenêtre asymétrique [-72 h;+24 h] **avant** le choix : **zéro publication supplémentaire dans ces données**. Le défaut de logique existe, mais il n’explique pas les comptes actuels et ne doit pas être présenté comme une baisse mesurée de couverture.

**Choix de classe et de métrique.** Apparailler au niveau de l’émetteur avec les nouvelles de toutes ses classes fait passer la couverture à **77,258 %** et celle avec BPA à **64,530 %**, contre 75,606 % et 62,742 %. Un `drop_duplicates` qui retient arbitrairement une classe peut perdre une dépêche liée à une autre. Même à classe fixe, chercher n’importe quel BPA dans la fenêtre donne **63,200 %**, car la dépêche la plus proche peut n’avoir que des ventes.

**Plusieurs dépêches.** Parmi les fenêtres à paire exploitable, 2 085 contiennent plusieurs dépêches; le premier titre diffère du plus proche pour 776 événements, et 411 premiers titres exploitables n’ont pas de BPA alors qu’un suivant en a. En élargissant au **premier titre earnings, même sans paire lisible**, on trouve 71 922 événements, dont 15 040 à plusieurs articles. Le premier donne un BPA dans **49 189 cas**; dans **1 851 cas**, il n’en donne pas alors qu’un suivant en donnera un. La couverture au premier titre earnings est donc **60,908 % des 80 759 événements**, contre 63,200 % en attendant le premier BPA dans toute la fenêtre. Ce dernier peut être un moment de signal valide, à condition de le dater à ce moment, et non à la première publication.

**Contrôle externe de 42 publications.** L’annexe donne chaque société, période, date du communiqué, chiffre et source. **41 chiffres** ont été confirmés avec une base GAAP ou ajustée explicite dans la source; le 42e, Harte Hanks 0,10 ajusté, n’est pas attesté exactement sous cette forme dans la pièce : elle donne -0,02 GAAP et une charge de restructuration. Les **42 dates et périodes** ont été contrôlées; aucune erreur de trimestre n’a été trouvée dans ce tirage, avec réserve sur la base non attestée de Harte Hanks. Trois dates de communiqué diffèrent du jour SEC. Cela ne constitue pas une preuve générale d’absence de mauvais trimestre, et la sélection de paires déjà lisibles sous-représente les formats problématiques. Quatre sites ont refusé le téléchargement direct (HTTP 403); leurs extraits de communiqués accessibles par le moteur ont permis la comparaison, et les refus sont conservés.

**Effet attendu.** Choisir la dépêche la plus proche de la SEC, une classe arbitraire ou une dépêche ultérieure peut sélectionner une mesure différente de celle disponible au début de l’événement. Les deux faux appariements BBT démontrent qu’un petit écart de temps ne garantit même pas le bon émetteur. Les 42 cas incluent aussi des annonces groupées, par exemple les résultats de Casper avec un rachat : ce ne sont pas toujours des chocs de résultat isolés.

**Correction précise.** Définir l’événement par émetteur, période fiscale et type de publication, en exigeant un accord du nom et de la période du titre. Construire tous les candidats admissibles avant sélection. Pour le signal de surprise, retenir **la première version admissible qui contient le BPA et son estimation**, avec ordre stable `(available_at, id)`, puis une observation par émetteur/publication. Appliquer ensuite une règle explicite aux classes d’actions. Ne jamais choisir une dépêche après coup en fonction de la proximité SEC ou de sa complétude future. Garder les taux de couverture avant/après chaque exclusion.

### Important 6 : FinBERT est bien exécuté, son contrôle est surtout lexical

**Vérification complète des jointures.** Les dix parties contiennent **930 946 titres uniques**, sans doublon. La jointure par titre donne **962 776 articles**, comme le fichier scoré; aucun décalage de titre par identifiant et **zéro différence de probabilité** entre parties rejointes et fichier final. Le label stocké correspond à l’argmax pour tous les articles. Les valeurs du résumé de tri sont 962 777 / 930 947 parce qu’un titre vide est filtré au scoring; l’écart d’une ligne est expliqué, pas une perte cachée.

**Recalcul GPU demandé.** Les **500 titres aléatoires** ont été recalculés avec la révision exacte `4556d13015211d73dccd3fdd39d39232506f3e43`, des lots de 32 au lieu de 512 et longueur 64. **Zéro changement de label**, écart absolu maximal **0,00000418**, moyen **0,000000261**, compatible avec les différences numériques de lots GPU. L’ordre réel est **0 positif, 1 négatif, 2 neutre**, conforme au [config figé](https://huggingface.co/ProsusAI/finbert/blob/4556d13015211d73dccd3fdd39d39232506f3e43/config.json). Les 202 tenseurs du fichier historique et ceux du safetensors en cache plus récent sont exactement égaux, avec les mêmes clés. SHA-256 des poids historiques : `e15a7b5738df7f17553399b6d94c6e2ff69c89245d066e8e5d183f5803a554e3`.

**Troncature.** **6 693 titres sur 930 946, soit 0,719 %**, dépassent 64 jetons, avec un maximum de 179. Le programme ne lit que le début. Cette règle est reproduite, pas ignorée; un chiffre ou une restriction en fin de titre peut disparaître. L’audit n’a pas mesuré le changement de sentiment en passant à 128/256 jetons, car cela changerait l’expérience au lieu de vérifier l’exécution demandée.

| Contrôle | Bons / mauvais | AUC FinBERT recalculée | AUC présence de mots positifs seulement |
|---|---:|---:|---:|
| BPA au-dessus / en dessous | 50 976 / 23 592 | 0.716626886 | 0.805724316 |
| Relèvement / abaissement analyste | 25 353 / 30 403 | 0.939502290 | 0.964033155 |
| Prévision relevée / abaissée | 5 823 / 2 041 | 0.977812141 | 0.995590397 |

Le comparateur lexical vaut 1 si le titre contient `beat`, `beats`, `upgrade`, `upgrades`, `raises` ou `boosts`, 0 sinon; il ne lit aucun montant ni aucun cours. Il dépasse FinBERT dans **les trois contrôles**. Les labels de relèvement/abaissement sont eux-mêmes définis par ces mots; les AUC 0,94 et 0,98 sont donc un contrôle de lecture des formules, pas un test difficile de compréhension. Cela rejoint la limite déjà indiquée par le rapport, mais la baseline en donne une mesure beaucoup plus nette. Pour le BPA, mélanger une bonne surprise de ventes, un BPA manqué et une prévision peut expliquer un score positif; un score global n’est pas un parseur de surprise.

**Fuite par entraînement.** La [publication originale, section 4.2](https://arxiv.org/html/1908.10063v1) décrit Reuters TRC2 comme 2008-2010 et 46 143 documents sélectionnés, et Financial PhraseBank pour les labels. L’article est soumis le 27 août 2019. La fiche figée confirme PhraseBank et l’usage de ces trois labels. Cela appuie l’absence d’entraînement décrit sur les réactions 2018-2024, sans être un audit indépendant du manifeste exact des données des poids. Un modèle publié en 2019 et une révision de 2023 ne constituent pas un outil effectivement disponible début 2018; il faut distinguer un outil de mesure rétrospectif d’une stratégie historiquement déployable. Je n’ai pas inspecté FiQA ou d’autres données financières hors périmètre pour extrapoler le contenu exact de ces poids.

**Effet et correction.** Ne pas faire de l’AUC sémantique une garantie de lecture des nombres ou une promesse prédictive. Garder la révision, le tokeniseur, le hash des poids et la longueur dans les métadonnées de chaque partie. Ajouter des contrôles sans les verbes explicites, avec chiffres contradictoires et titres longs, avant toute extension de l’expérience. Pour l’étude de surprise, utiliser les chiffres qualifiés, pas le sentiment. L’exécution FinBERT actuelle ne nécessite pas une correction de labels.

### Important 7 : la couverture du parseur et le contenu éditorial changent dans le temps

La part de paires de BPA parmi tous les titres earnings passe de **60,34 % en 2018** à **42,17 % en 2022**, puis **52,92 % en 2024**. Le recul et le rebond ne sont pas ceux d’un parseur au format stable. Une variation de couverture ne prouve pas à elle seule un bogue; elle change la population observée.

Sur les articles earnings associés à une seule action ordinaire/ADR, la comparaison par survie est :

| Année | Articles disparus à fin 2024 | BPA lisible disparus | Articles vivants | BPA lisible vivants |
|---|---:|---:|---:|---:|
| 2018 | 4 858 | 60,56 % | 12 061 | 62,42 % |
| 2019 | 3 952 | 58,43 % | 12 441 | 59,49 % |
| 2020 | 3 601 | 48,76 % | 14 334 | 51,68 % |
| 2021 | 3 601 | 44,13 % | 17 777 | 48,74 % |
| 2022 | 3 185 | 39,43 % | 21 180 | 44,26 % |
| 2023 | 1 708 | 53,34 % | 20 578 | 55,04 % |
| 2024 | 397 | 56,93 % | 21 673 | 54,94 % |

En 2022, l’écart est de **4,82 points** au détriment des disparus; en 2024 l’effectif disparu n’est plus que 397 articles et le signe s’inverse. Conditionner sur la survie de fin 2024 sert ici à diagnostiquer la sélection, pas à définir une stratégie. La composition des catégories et la disponibilité des résumés changent aussi; les règles sur titres seuls ne rendent pas les populations comparables par magie.

**Effet attendu.** L’étude risque de comparer des années, des genres de titres, des types d’émetteurs et des bases de BPA différents au lieu d’une même mesure de surprise. La sélection sur lisibilité peut être liée à la taille, au marché ou à la disparition.

**Correction précise.** Publier le chemin d’inclusion par année, devise, base, type d’action et survie, avec le même parseur gelé. Garder un groupe non analysable et documenter les raisons de rejet. Exiger une analyse de robustesse prédéfinie par année et disponibilité, sans choisir ensuite le découpage qui rend l’étude favorable. Ne pas filtrer les sociétés disparues pour améliorer artificiellement la qualité.

### Secondaire 8 : tests rassurants mais garde-fous et reprise incomplets

La commande demandée **`venv/bin/python tests/test_news_filter.py` passe : 15 tests**. Le classement a été recalculé sur les 1 281 297 titres distincts : **zéro désaccord** avec la table. Les identifiants d’articles et les liens uniques n’ont pas de doublon, les dix fichiers FinBERT sont continus, et les 61 059 articles sélectionnés dans la couverture sont distincts. Aucun non-déterminisme effectif n’a été constaté avec les fichiers figés. Il n’y a pas d’égalité de liquidité au maximum dans les ambiguïtés.

Les tests ne couvrent pas les virgules décimales, suffixes de milliards sur BPA, clauses `Reaffirms`, symbole BBT, ni les règles trop larges d’analystes. Le motif initial de note d’analyste admet un nom quelconque suivi de `Initiates/Reiterates/...`, sans nom de courtier ni notation : `Quoin Pharmaceuticals Initiates Pediatric Clinical Study...` est classé analyst, et `Hasbro Reiterates FY23 Adj. EPS Outlook...` aussi. `Worksport Unveils Upgraded SOLIS Technology ... Market Reach` est pris pour une recommandation. Les règles de résultats et de guidance ont des interactions de même nature. Un script qui passe ces 15 exemples n’est donc pas une validation de précision.

Les scripts de production n’appliquent pas une borne explicite au 31 décembre 2024 quand ils lisent tous les fichiers de news, ni une borne supérieure aux événements. Les données courantes respectent la période, mais une arrivée de fichiers 2025 modifierait silencieusement l’expérience. `drop_duplicates` de classe et les tris sur un seul temps laissent aussi les choix de représentant dépendre de l’ordre d’entrée en cas d’égalité. Enfin la reprise FinBERT utilise `len(parts)` comme numéro suivant et ne vérifie pas la révision dans chaque partie : une partie manquante peut entraîner un écrasement de numéro existant, et une révision mélangée ne serait pas bloquée. Ce sont des défauts de garde-fou, pas des incidents observés ici.

**Correction précise.** Ajouter des régressions ciblées sur les exemples fautifs, fixer les bornes de dates et l’ordre des égalités, valider les clés de jointure et écrire un manifeste d’entrées et de modèle. Exiger une notation/objective de cours ou un acteur de courtage identifié avant `analyst`. Pour la reprise, sélectionner le premier numéro libre ou un identifiant de partie fondé sur son contenu, vérifier les métadonnées et refuser tout mélange de révision.

## Annexe : publications contrôlées et sources

Une ligne par publication, sélection indépendante des rendements. Les symboles sont ceux du référentiel; certains sont différents du symbole historique de la dépêche. Le signe du BPA ci-dessous est celui du réalisé, pas celui de sa surprise. Les dates de sources sont les dates de communiqué, non les dates de dépôt SEC.

| # | Société / symbole | Fin de période | Communiqué | BPA du titre | Contrôle et source |
|---|---|---|---|---:|---|
| 0 | ISBC | 2017-12-31 | 2018-01-25 | 0.17 | ajusté; GAAP -0.02 et non +0.02 du titre; [source](https://www.sec.gov/Archives/edgar/data/1594012/000159401218000008/pressrelease123117.htm) |
| 1 | CA | 2017-12-31 | 2018-01-30 | 0.75 | non-GAAP, GAAP -0.23; [source](https://www.sec.gov/Archives/edgar/data/356028/000115752318000151/a51750686ex99_1.htm) |
| 2 | SPSC | 2018-03-31 | 2018-04-26 | 0.39 | non-GAAP, GAAP 0.19; base non indiquée dans le titre; [source](https://investors.spscommerce.com/news-releases/news-release-details/sps-commerce-reports-first-quarter-2018-financial-results) |
| 3 | JBHT | 2018-06-30 | 2018-07-16 | 1.37 | GAAP; dépôt SEC 10 heures après la dépêche; [source](https://investor.jbhunt.com/news/2018/07-16-2018-064028903) |
| 4 | EBSB | 2018-06-30 | 2018-07-24 | 0.27 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/1600125/000156459018017299/ebsb-ex99_6.htm) |
| 5 | PFGC | 2018-09-29 | 2018-11-07 | 0.34 | ajusté; GAAP 0.27, base absente du titre; [source](https://investors.pfgc.com/press-releases/press-release-details/2018/Performance-Food-Group-Company-Reports-First-Quarter-Fiscal-2019-Results/default.aspx) |
| 6 | BALL | 2019-03-31 | 2019-05-02 | 0.49 | comparable; GAAP 0.34; ticker historique BLL; [source](https://www.sec.gov/Archives/edgar/data/9389/000000938919000020/bll-20190502xex99.htm) |
| 7 | AGN | 2019-06-30 | 2019-08-06 | 4.38 | non-GAAP; GAAP -5.37; [source](https://www.sec.gov/Archives/edgar/data/1578845/000114420419037749/tv526820_ex99-1.htm) |
| 8 | LTHM | 2019-06-30 | 2019-08-06 | 0.12 | ajusté; GAAP 0.11, base absente du titre; [source](https://www.sec.gov/Archives/edgar/data/1742924/000174292419000037/liventex991063019.htm) |
| 9 | MFA | 2019-09-30 | 2019-11-06 | 0.2 | GAAP et core égaux; [source](https://www.sec.gov/Archives/edgar/data/1055160/000110465919060300/tm1921988d1_ex99-1.htm) |
| 10 | BCEI | 2019-09-30 | 2019-11-06 | 1.42 | ajusté; base absente du titre; [source](https://www.sec.gov/Archives/edgar/data/1509589/000150958919000107/exhibit99109-30x19.htm) |
| 11 | JWN | 2019-11-02 | 2019-11-21 | 0.81 | GAAP; communiqué 16:05 ET; [source](https://press.nordstrom.com/news-releases/news-release-details/nordstrom-reports-third-quarter-2019-earnings) |
| 12 | MTRX | 2019-12-31 | 2020-02-05 | 0.19 | ajusté, GAAP -1.04; [source](https://investors.matrixservicecompany.com/news-releases/news-release-details/matrix-service-company-reports-second-quarter-2020-results) |
| 13 | EIGI | 2019-12-31 | 2020-02-06 | 0.07 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/1237746/000119312520026142/d844489dex991.htm) |
| 14 | AAN | 2019-12-31 | 2020-02-20 | 1.15 | non-GAAP; GAAP -1.60, base absente du titre; [source](https://www.sec.gov/Archives/edgar/data/706688/000070668820000008/a2019q4exhibit991fourt.htm) |
| 15 | RP | 2020-06-30 | 2020-07-30 | 0.49 | non-GAAP; GAAP 0.11, base absente du titre; [source](https://www.businesswire.com/news/home/20200730005988/en/RealPage-Reports-Second-Quarter-2020-Financial-Results) |
| 16 | CNK | 2020-09-30 | 2020-11-05 | -1.25 | GAAP; [source](https://ir.cinemark.com/news-events/press-releases/detail/475/cinemark-holdings-inc-reports-results-for-the-third) |
| 17 | AOUT | 2020-10-31 | 2020-12-15 | 0.77 | non-GAAP; GAAP 0.52; Q2 fiscal 2021; [source](https://www.sec.gov/Archives/edgar/data/1808997/000156459020057146/aout-ex991_33.htm) |
| 18 | WAL | 2021-06-30 | 2021-07-15 | 2.17 | GAAP; ajusté 2.29; [source](https://www.sec.gov/Archives/edgar/data/1212545/000121254521000146/pressrelease-6302021.htm) |
| 19 | PARR | 2021-06-30 | 2021-08-04 | -0.81 | ajusté; GAAP -1.84; [source](https://www.sec.gov/Archives/edgar/data/821483/000082148321000054/a20210630991earningsreleas.htm) |
| 20 | VRTV | 2021-09-30 | 2021-11-03 | 2.54 | GAAP dilué; [source](https://www.sec.gov/Archives/edgar/data/1599489/000110465921133374/tm2131636d1_ex99-1.htm) |
| 21 | FOA | 2021-09-30 | 2021-11-08 | 0.39 | ajusté; GAAP dilué 0.22; titre CORRECTION; [source](https://www.sec.gov/Archives/edgar/data/1828937/000119312521323050/d238938dex991.htm) |
| 22 | FRGI | 2021-10-03 | 2021-11-11 | -0.09 | ajusté; base absente du titre; jour du communiqué antérieur au dépôt; [source](https://www.businesswire.com/news/home/20211111006030/en/Fiesta-Restaurant-Group-Inc.-Reports-Third-Quarter-2021-Results) |
| 23 | CSPR | 2021-09-30 | 2021-11-15 | -0.61 | GAAP; émission du communiqué confirmée par 8-K tm2132922d1_ex99-1; [source](https://www.sec.gov/Archives/edgar/data/1598674/000159867421000097/cspr-20210930.htm) |
| 24 | ACA | 2021-12-31 | 2022-02-23 | 0.4 | ajusté; GAAP 0.19, base absente du titre; [source](https://www.sec.gov/Archives/edgar/data/1739445/000173944522000010/exh991earningsrelease12312.htm) |
| 25 | RS | 2022-03-31 | 2022-04-28 | 8.42 | non-GAAP; GAAP 8.33; [source](https://investor.reliance.com/news-events/press-releases/detail/145/reliance-steel-aluminum-co-reports-first-quarter-2022-financial-results) |
| 26 | HA | 2022-06-30 | 2022-07-26 | -0.9 | ajusté; GAAP -0.72, base absente du titre; [source](https://www.sec.gov/Archives/edgar/data/1172222/000117222222000061/exhibit991q22022.htm) |
| 27 | ALIM | 2022-06-30 | 2022-07-27 | -0.45 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/1267602/000126760222000039/alim-20220727xex99_1.htm) |
| 28 | IRTC | 2022-09-30 | 2022-11-01 | -0.63 | ajusté; GAAP -0.71 dans le même titre; [source](https://investors.irhythmtech.com/news/news-details/2022/iRhythm-Technologies-Announces-Third-Quarter-2022-Financial-Results/default.aspx) |
| 29 | VTNR | 2022-09-30 | 2022-11-08 | 0.28 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/890447/000158069522000092/ex99-1.htm) |
| 30 | SGEN | 2022-12-31 | 2023-02-15 | -0.8 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/1060736/000106073623000007/ex-9912022q4.htm) |
| 31 | VTNR | 2022-12-31 | 2023-02-28 | 0.56 | GAAP; [source](https://www.sec.gov/Archives/edgar/data/890447/000183988223005011/ex99-1.htm) |
| 32 | BLNK | 2022-12-31 | 2023-02-28 | -0.41 | ajusté; GAAP -0.55, base absente du titre; communiqué 16:40 ET; [source](https://www.globenewswire.com/news-release/2023/02/28/2617728/0/en/blink-charging-announces-record-fourth-quarter-and-year-end-2022-results.html) |
| 33 | GRPN | 2023-03-31 | 2023-05-10 | -0.95 | GAAP; non-GAAP -0.65; [source](https://www.sec.gov/Archives/edgar/data/1490281/000149028123000054/a2023q18-kxexhibit991.htm) |
| 34 | ELF | 2023-06-30 | 2023-08-01 | 1.1 | ajusté; GAAP 0.93; Q1 fiscal 2024; [source](https://investor.elfbeauty.com/stock-and-financial/press-releases/landing-news/2023/08-01-2023-073710693) |
| 35 | TAST | 2023-10-01 | 2023-11-09 | 0.16 | ajusté; GAAP 0.20; [source](https://www.sec.gov/Archives/edgar/data/809248/000080924823000116/ex991q3-2023.htm) |
| 36 | CVLY | 2024-03-31 | 2024-04-25 | 0.44 | GAAP; ajusté 0.45; [source](https://www.sec.gov/Archives/edgar/data/806279/000089710124000141/codorus240466_ex99-1.htm) |
| 37 | SBOW | 2024-03-31 | 2024-05-01 | 2.09 | ajusté; [source](https://www.sec.gov/Archives/edgar/data/351817/000035181724000077/sbow_ex991-1q2024.htm) |
| 38 | RPC | 2024-03-31 | 2024-05-08 | 0.21 | ANI ajusté; GAAP 0.04; ticker historique PX; [source](https://www.globenewswire.com/news-release/2024/05/08/2878195/0/en/P10-Reports-First-Quarter-2024-Earnings-Results.html) |
| 39 | STER | 2024-03-31 | 2024-05-09 | 0.19 | ajusté; GAAP -0.09; [source](https://www.sec.gov/Archives/edgar/data/1645070/000164507024000073/ex991ster-2024331xearnings.htm) |
| 40 | HHS | 2024-03-31 | 2024-05-09 | 0.1 | BPA ajusté arrondi plausible, non explicitement publié à 0.10; GAAP -0.02; [source](https://www.sec.gov/Archives/edgar/data/45919/000004591924000024/a20240509ex991earningsq1-24.htm) |
| 41 | PFGC | 2024-09-28 | 2024-11-06 | 1.16 | ajusté; GAAP 0.69; Q1 fiscal 2025 publié en 2024; [source](https://investors.pfgc.com/press-releases/press-release-details/2024/Performance-Food-Group-Company-Reports-First-Quarter-Fiscal-2025-Results/default.aspx) |

Les précisions de temps publiques vérifiées directement dans les extraits comprennent Nordstrom le 21 novembre 2019 à 16:05 ET, Blink le 28 février 2023 à 16:40 ET, et P10 le 8 mai 2024 à 16:05 ET. Dans ces trois cas la dépêche sélectionnée est postérieure au communiqué. Les 39 autres contrôles ne certifient pas tous une seconde de première publication : une date journalière de communiqué est une preuve moins forte qu’un journal de diffusion.

## Reproduction et résultats conservés

Les scripts ne font aucune lecture de prix, de rendement ou de SUE. Exécuter depuis la racine avec `PYTHONDONTWRITEBYTECODE=1`; ils écrivent uniquement dans `/tmp/news-audit/`. Les snapshots locaux de travail ne contiennent que les colonnes autorisées.

```bash
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/initial.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/raw_audit.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/manual_categories.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/surprise_audit.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/coverage_audit.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/link_audit.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/full_link_check.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/more_checks.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/finalize_reviews.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/add_link_sample.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/metrics.py
PYTHONDONTWRITEBYTECODE=1 HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python /tmp/news-audit/finbert_audit.py
PYTHONDONTWRITEBYTECODE=1 HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python /tmp/news-audit/weights_compare.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/report.py
PYTHONDONTWRITEBYTECODE=1 venv/bin/python /tmp/news-audit/validate_report.py
```

`category_review.csv` conserve les 900 jugements; `manual_surprise150_review.csv` les 150 contrôles de BPA; `manual_link106_review.csv` les liens et leurs limites; `publication42_review.csv` les rapprochements publics; `publication_sources.tsv`, `primary_extracts.json` et `fetch_primary.py` conservent les références et extraits. Les tables de divergences, alias, mises à jour, premiers articles et les sorties JSON permettent de retrouver chaque décompte. Les jugements humains ne sont pas recréés par un algorithme; ils sont des données de cet audit. Les documents web peuvent changer et les HTTP 403 sont consignés.

## Réponse finale

**Non, on ne peut pas lancer en l’état une étude confirmatoire de la vraie surprise immédiatement disponible.** Il faut obligatoirement, avant de consulter un rendement : corriger les alias et les deux événements d’autre société; geler une définition temporelle prouvée ou conservatrice de la version; qualifier le consensus et sa base; isoler trimestriel/annuel et réalisé/prévision; rejeter ou arbitrer les unités et nombres incohérents; retirer les commentaires de mouvements; retenir une seule première paire admissible par publication; puis refaire un contrôle neuf et figer le protocole et ses exclusions.

Après ces corrections, **oui pour une étude rétrospective explicitement limitée à l’écart cité dans une dépêche disponible au moment retenu**, avec une entrée postérieure vérifiable. **Non pour prétendre à une réaction à la seconde de la première annonce ou à un consensus d’avant annonce authentifié tant que ces deux historiques manquent.** Les vérifications FinBERT sont satisfaisantes pour l’exécution et ne lèvent pas ces blocages.
