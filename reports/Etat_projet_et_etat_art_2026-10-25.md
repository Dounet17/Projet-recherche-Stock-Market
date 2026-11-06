# État du projet et état de l’art — 25 octobre 2026

Mise à jour après cet audit : un premier backtest a ensuite été réalisé à la demande de l’utilisateur. Voir [les résultats et le protocole](Backtest_Musk_Tesla_2026-10-25.md). Le présent document décrit l’état constaté avant cette implémentation.

Le projet a déjà une collecte exploitable et une première expérience Musk/Tesla exécutée. Il n’a pas encore de stratégie de trading validée sur un portefeuille réaliste. Le résultat encourageant à très court terme devient fragile lorsqu’on commence à mesurer ce qui resterait après la publication. La priorité est donc de consolider le protocole expérimental avant de multiplier les architectures.

Audit fondé sur les fichiers locaux, les sorties enregistrées des deux notebooks, un recalcul à partir des fichiers Parquet et une recherche bibliographique consultée le 25/10/2026. Aucun téléchargement de marché ni appel payant de classification effectué. La recherche ci-dessous est ciblée sur ce projet ; elle ne constitue pas une revue systématique exhaustive.

**Ce qui est réellement en place**

Le sujet officiel, repris dans `CLAUDE.md`, demande de comparer des stratégies heuristiques, adaptatives et hybrides, sur un indice et un budget virtuel de 10 000 €. La période retenue est 2018–2024. Le README décrit encore les prix journaliers via Yahoo Finance ; le travail local a évolué vers des prix à la minute via Alpaca.

La répartition documentée est : DavidTom sur Musk/Tesla, avec QQQ comme référence du Nasdaq-100 ; Dounet17 sur le Dow Jones, avec Trump envisagé comme source sociale. Tesla est une action individuelle, pas l’indice demandé : le lien entre cette étude complémentaire et l’évaluation sur indice doit être explicite dans le livrable.

| Élément | État vérifié localement |
|---|---|
| Collecte | `src/collect.py` : tweets Musk, barres Alpaca, news Benzinga et calendrier |
| Horodatage | `src/timeutils.py` : reconstruction depuis les identifiants et classement par séance |
| Sentiment | `src/sentiment.py` : FinBERT local et Jev via API |
| Notebook 01 | Collecte exécutée, 10 cellules de code avec numéro d’exécution, aucune erreur enregistrée |
| Notebook 02 | Comparaison FinBERT/Jev exécutée, 12 cellules de code avec numéro d’exécution, aucune erreur enregistrée ; conclusions encore à rédiger |
| Posts Musk | 78 807 au total, de novembre 2010 à mai 2025 ; 60 712 sur 2018–2024 |
| Échantillon Tesla | 2 894 posts hors retweets : 535 originaux, 189 citations, 2 170 réponses |
| Prix à la minute | 1 298 664 barres TSLA et 1 402 722 barres QQQ sur 2018–2024 |
| Autres données | 7 044 barres journalières pour TSLA/QQQ/SPY/DIA ; 28 432 news Tesla ; 28 publications de résultats sur 2018–2024 |
| Trump / Dow Jones | Sources étudiées dans les notes ; pas de dataset Trump ni d’expérience Trump dans les fichiers locaux examinés ; DIA est présent en journalier |
| Stratégies et portefeuille | Pas de moteur de backtest réaliste ni de comparaison exécutée couvrant les trois familles ; le notebook 01 trace seulement une référence passive |
| Tests logiciels | Pas de suite de tests automatisés trouvée dans le projet |

Aucun processus de collecte, de notebook ou d’entraînement identifiable n’était actif sur cette machine au moment de la vérification. Cela ne renseigne pas sur les travaux éventuels du binôme ailleurs.

L’essentiel du travail est encore local : Git ne suit actuellement que `README.md` et `requirements.txt`. Les dossiers `src/`, `notebooks/`, `reports/`, `research_notes/`, ainsi que `CLAUDE.md` et `.gitignore`, sont non suivis ; `requirements.txt` est modifié. Les données sont volontairement exclues de Git. Les instructions d’installation et l’environnement ne sont pas figés par un fichier de verrouillage.

**Ce que disent les expériences existantes**

Sur les 2 894 posts, 679 sont publiés en séance normale. L’exigence d’une fenêtre entière de 60 minutes après le post et d’au moins une minute depuis l’ouverture réduit l’analyse à **546 événements sur 351 jours**. Utiliser ce même échantillon pour tous les horizons facilite la comparaison mais exclut aussi des posts pourtant utilisables à +1 ou +5 minutes.

FinBERT et Jev donnent le même sentiment sur **54,6 %** des posts ; le kappa de Cohen vaut **0,202**, soit un accord limité après prise en compte de l’accord dû au hasard. FinBERT classe **81,8 %** des textes comme neutres. Sans annotation humaine, ce désaccord ne permet pas de désigner le meilleur lecteur de tweets.

Le score Jev `impact`, qui demande explicitement l’effet attendu sur TSLA, est corrélé à la réaction relative TSLA–QQQ à l’horizon appelé « +1 minute » : Spearman **0,1275**, p = **0,00285**. Cette corrélation ne réapparaît pas à +5, +15 ou +60 minutes. Le taux de bonne direction à +1 minute est de **55,8 % sur 231 prises de position**, avec p = **0,087** au test binomial enregistré : ce critère ne franchit pas le seuil de 5 %.

Le notebook mesure une réaction totale depuis un prix antérieur au post. Il ne mesure pas un prix auquel on aurait pu acheter après lecture du message. Pour un post à 14:52:28, le point « +1 » utilise la clôture de la barre 14:53, connue vers 14:54 : l’étiquette ne représente donc pas exactement 60 secondes après publication.

J’ai reproduit les calculs et ajouté deux sensibilités sur les mêmes événements :

| Mesure du signal Jev `impact`, horizon étiqueté +1 | Corrélation | p brute | p corrigée pour 12 corrélations | Rendement relatif signé moyen sur 231 positions, avant frais |
|---|---:|---:|---:|---:|
| Réaction totale du notebook, depuis avant le post | 0,1275 | 0,00285 | 0,0341 | 0,0485 % |
| Départ à la clôture de la minute du post | 0,0980 | 0,0221 | 0,2648 | 0,0267 % |
| Départ à l’ouverture de la minute suivante | 0,1065 | 0,0128 | 0,1534 | 0,0263 % |

La correction de Bonferroni multiplie ici la p-value par 12 : trois scores fois quatre horizons. Le résultat initial reste sous 5 % dans cette famille de tests ; les variantes après publication n’y restent pas. Cette correction ne couvre pas tous les essais du notebook, notamment les taux de bonne direction et les sous-groupes, ni les sensibilités ajoutées par cet audit.

Ces variantes restent exploratoires : l’ouverture de la minute suivante n’est pas un prix d’exécution garanti, le délai disponible depuis le post varie, et les calculs ne comprennent ni spread, ni frais, ni contraintes de portefeuille. Le rendement signé combine le sens annoncé et la différence TSLA–QQQ ; ce n’est pas le rendement d’un portefeuille de 10 000 € financé et exécuté. Ces résultats ne prouvent ni une rentabilité ni une absence définitive de signal.

**Limites à traiter avant de conclure**

- **Dépendance entre événements.** 172 des 546 posts suivent un autre événement retenu de moins d’une heure ou exactement une heure. Les fenêtres peuvent se recouvrir ; les p-values usuelles supposant des observations indépendantes sont à réévaluer avec regroupement par jour ou par épisode et rééchantillonnage par blocs.
- **Référence de marché.** Soustraire directement QQQ suppose implicitement une sensibilité de TSLA au marché égale à 1. Il faut comparer avec une sensibilité estimée uniquement avant chaque événement. QQQ contient aussi Tesla : il n’est pas une référence complètement indépendante.
- **Événements concurrents.** Les news et dates de résultats sont collectées mais ne sont pas encore utilisées pour contrôler les mouvements autour des tweets. Examiner aussi la tendance avant publication et des horaires témoins comparables : un tweet peut commenter une information déjà intégrée au prix.
- **Prix manquants.** Aucun doublon d’horodatage dans les deux séries et aucune barre de référence manquante pour les 546 événements. En revanche, TSLA manque à 1 point de sortie à +5, 2 à +15 et 3 à +60 ; le notebook propage le dernier cours sans limite d’ancienneté. Des interruptions de cotation peuvent rendre cette propagation trompeuse.
- **Textes connus rétrospectivement.** Les 2 894 dates de tweets concordent avec les identifiants. En revanche, 16 780 des 28 432 news ont une mise à jour postérieure à leur création : leur texte téléchargé aujourd’hui ne doit pas être supposé disponible tel quel à `created_at`. Ce risque concerne une future stratégie sur news, pas le signal actuel fondé sur les tweets.
- **Contamination des modèles.** Le cache Jev indique `jev-1.13.0`, mais le code appelle `jev-latest`. Ni le prompt ni la révision FinBERT ne font partie de la clé du cache, fondée sur l’identifiant du tweet. Les dates et contenus d’entraînement des versions utilisées doivent être documentés ; une séparation chronologique du dataset ne suffit pas si le modèle connaît déjà les événements testés.
- **Population sélectionnée.** Les réponses représentent 75 % de l’échantillon, souvent sans contexte de conversation. Le filtre par mots-clés ignore des messages indirectement pertinents. Les nombres plus anciens dans `CLAUDE.md` décrivent parfois un autre état de collecte et ne doivent pas remplacer les comptes recalculés.
- **Latence.** Le notebook rapporte environ 0,020 s par post pour FinBERT sur CPU et 0,241 s pour Jev sur 20 exemples. Ce sont des mesures enregistrées, pas une mesure actuelle de la chaîne complète détection–inférence–ordre. Des prix à la minute ne permettent pas de valider un avantage de quelques centaines de millisecondes.

**État de l’art pertinent pour ce projet**

La littérature distingue la compréhension d’un texte, la réaction contemporaine du marché, la prévision d’un rendement encore à venir et le gain après coûts. Les méthodes récentes combinent extraction de sentiment ou d’événements, données de prix et modèles de décision ; aucune référence ci-dessous n’établit un modèle universellement supérieur sur le cas Musk/TSLA à la minute.

| Référence et statut | Résultat utile et conséquence pour le projet |
|---|---|
| [Xu et Cohen, StockNet, ACL 2018](https://aclanthology.org/P18-1183/) — article de conférence | Combine textes Twitter et historique des prix dans un modèle temporel. Point de départ pour tester l’apport des textes au-delà des seuls prix ; ne valide pas une exécution intraminute. |
| [PyFin-sentiment, 2023](https://doi.org/10.1016/j.jjimei.2023.100171) — article de revue, résumé consulté | Sur leurs 10 000 tweets annotés, une régression logistique adaptée au vocabulaire financier dépasse notamment FinBERT. Justifie une référence simple spécialisée et un petit jeu annoté localement ; résultat sur le sentiment, pas sur la rentabilité. |
| [FinBen, NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/file/adb1d9fa8be4576d28703b396b82ba1b-Paper-Datasets_and_Benchmarks_Track.pdf) — benchmark évalué en conférence | Les capacités d’extraction et d’analyse textuelle des LLM ne se traduisent pas uniformément en bonnes prévisions. Comparer chaque tâche séparément plutôt qu’utiliser un score financier global comme preuve de performance boursière. |
| [Cunha, Lobão et Alves, 2025](https://cjssp.uni-corvinus.hu/index.php/cjssp/article/view/977) — article de revue | Étude directement liée à Musk/Tesla : 3 158 tweets sur dix ans, 33 événements sélectionnés, modèles CAPM et à cinq facteurs. Ne trouve pas d’effet significatif permettant de soutenir des rendements anormaux réguliers. Fréquence journalière : ne tranche pas le cas intraminute. |
| [Filippou et al., 2025](https://doi.org/10.1016/j.jimonfin.2025.103343) — Journal of International Money and Finance, résumé et présentation éditeur consultés | Les tweets Trump informatifs sur la macroéconomie et le commerce présentent un signal sur les devises, avec contrôles d’annonces macroéconomiques. Le résultat ne se transpose pas directement au Dow Jones ; il motive un classement par thèmes plutôt qu’un sentiment générique. |
| [Scharnowski, 2 mars 2026](https://onlinelibrary.wiley.com/doi/full/10.1111/jfir.70049) — Journal of Financial Research, texte consulté | Sur les tweets présidentiels et des données à très haute fréquence, les ajustements apparaissent en fractions de seconde ; volatilité et liquidité réagissent brièvement. L’effet directionnel moyen est très court. C’est une objection empirique à l’idée qu’une réaction humaine lente laisserait nécessairement un gain disponible sur un ETF liquide. |
| [Lopez-Lira et Tang, version JFE octobre 2026](https://doi.org/10.1016/j.jfineco.2026.104335), [prépublication accessible](https://arxiv.org/abs/2304.07619) | Les LLM peuvent extraire une information prédictive des titres de presse ; les auteurs distinguent expressément réaction initiale non négociable et dérive ultérieure. Les taux proches de 90 % concernent des journées de portefeuille et la réaction initiale : ils ne sont pas une précision par tweet pour une stratégie exécutable. |
| [FinTSB, révision juin 2026](https://arxiv.org/abs/2502.18834) — benchmark, référence de revue indiquée sur arXiv | Standardise l’évaluation et intègre notamment frais et contraintes de marché. Utile pour structurer la comparaison des modèles de prix ; ne constitue pas à lui seul un benchmark réseaux sociaux. |
| [Xue et al., septembre 2026](https://arxiv.org/abs/2608.17223) — prépublication annonçant une acceptation EMNLP 2026 | Audit de 16 combinaisons de modèles et représentations : dans leur corpus, un découpage aléatoire gonfle fortement les scores comparé au chronologique. Les signaux conservés sont spécifiques à certains événements et ne se transfèrent pas automatiquement à un autre corpus. |

En complément, un [mémoire de Princeton daté d’avril 2026](https://theses-dissertations.princeton.edu/entities/publication/b3506b16-95f9-437c-82f0-3480f60066af/full) est très proche du sujet : Trump, Musk et Biden, SPY/QQQ, FinBERT/VADER et fenêtres intraday. Son résumé rapporte des effets généralement modestes. Il s’agit d’un mémoire de premier cycle dont le texte est restreint, à distinguer des articles de revue ci-dessus.

Pour élargir les classifieurs, [FinTwitBERT-sentiment](https://huggingface.co/StephanAkkerman/FinTwitBERT-sentiment) cible explicitement les tweets financiers. Sa fiche décrit un préentraînement sur dix millions de tweets et un ajustement supervisé. C’est un candidat de comparaison, pas une preuve de supériorité sur Musk ; les dates d’entraînement et les éventuels doublons avec le corpus de test restent à auditer. La revue [The New Quant, octobre 2025](https://arxiv.org/abs/2510.05533) fournit une carte plus large : événements, sentiment, recherche documentaire, séries temporelles et agents, en insistant sur les coûts, la latence et les fuites temporelles.

**Suite recommandée, par ordre de valeur scientifique**

1. **Formaliser deux questions séparées.** « Les posts sont-ils associés à une réaction anormale de prix ou de volatilité ? » puis « Le texte ajoute-t-il un signal exploitable après réception, au-delà des prix et après coûts ? ». Fixer un horizon principal, des critères et les variantes avant de relancer les comparaisons.
2. **Consolider l’étude d’événement existante.** Contrôler news et résultats, tester des fenêtres avant publication et des horaires témoins, traiter les épisodes de tweets proches, estimer la sensibilité au marché avant événement et fournir des intervalles d’incertitude par blocs. Séparer originaux, réponses et citations. Conserver explicitement les interruptions de cotation et l’ancienneté des prix.
3. **Construire une comparaison minimale.** Même cible, même période, mêmes règles : achat-conservation de l’indice et liquidités ; moyennes mobiles/Bollinger ; modèle simple sur les prix ; texte seul ; prix + texte. Une régression logistique ou un modèle d’arbres est un premier candidat raisonnable avec seulement quelques centaines d’événements. Mesurer ensuite si un modèle plus complexe apporte réellement quelque chose.
4. **Vérifier le texte.** Annoter par exemple 200–300 posts pour distinguer pertinence TSLA, sentiment et effet attendu, sans regarder les rendements futurs. Comparer FinBERT, Jev et une référence adaptée aux tweets. Figer versions, prompts et empreintes des données. Les annotations mesurent la qualité de lecture ; les rendements mesurent une autre tâche.
5. **Évaluer chronologiquement.** Apprendre sur le passé et avancer dans le temps, avec une séparation autour des fenêtres qui se recouvrent. Toute transformation et tout seuil sont ajustés sur l’apprentissage. La période 2018–2024 ayant déjà été examinée globalement, un nouveau découpage de cette période ne devient pas un test final vierge. Prévoir des données encore non examinées ou une collecte prospective avec modèle figé, et documenter la contamination potentielle du préentraînement.
6. **Simuler un portefeuille.** Exécuter uniquement après disponibilité du signal, modéliser spread, glissement de prix, frais, taille des positions et positions simultanées. À la minute, comparer des délais conservateurs ; une hypothèse en secondes exige des données plus fines. Rapporter rendement net, pire perte depuis un sommet (« drawdown »), rendement rapporté au risque (« Sharpe »), rotation, nombre de transactions et incertitude. Définir aussi le traitement EUR/USD du budget annoncé en euros.
7. **Étendre à Trump/Dow Jones.** Construire le corpus Twitter/Truth Social et les prix intraday DIA, puis des thèmes comme droits de douane, commerce ou politique monétaire. Si les composants du Dow Jones sont étudiés, utiliser leur appartenance historique. Présenter clairement ce volet sur indice et le volet complémentaire Musk/TSLA.

Un résultat négatif robuste constituerait un résultat scientifique utile. À ce stade, le constat défendable est : **un petit signal rétrospectif apparaît dans la réaction immédiate, mais aucun avantage net après publication n’est établi**.

**Reproduction de l’audit**

Depuis la racine du projet : `venv/bin/python reports/audit_cached_results.py`. Le script relit seulement les caches locaux et produit `reports/audit_metrics_2026-10-25.json`. Il reproduit les 12 corrélations originales et calcule deux variantes après publication. Il n’exécute pas les cellules de classification ni la mesure de latence du notebook, qui rappellerait l’API Jev. Les vérifications présentées ici ne remplacent pas le futur backtest ni une nouvelle validation hors échantillon.
