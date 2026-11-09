# À faire : IA de lecture des communiqués de résultats

Note du 08/11/2026, issue d'une proposition de l'utilisateur après la discussion des études H09 et H10.

**Statut : piste à faire, protocole à définir.** Cette note conserve l'idée ; elle ne fige pas de protocole et ne déclenche ni implémentation ni calcul de rendement. L'hypothèse devra être inscrite dans le registre avant tout calcul, avec un identifiant disponible au moment de l'inscription.

## Idée

Créer un système qui reçoit le communiqué de résultats d'une entreprise, en PDF, HTML ou texte, et estime la probabilité que **l'action de cette entreprise baisse** pendant une fenêtre future définie à l'avance. La cible initiale est l'action concernée, pas le marché entier.

Chaîne envisagée : **document publié → extraction des informations → probabilité de baisse → comparaison avec l'évolution réellement observée ensuite**.

Le format du fichier est secondaire. Il faut préserver les tableaux, les unités, la période comptable et la version du document effectivement disponible lors de sa publication.

## Informations à lire

- **Chiffre d'affaires** : montant des ventes, avec son évolution.
- **Bénéfices et BPA/EPS** : bénéfice total et bénéfice par action ; distinguer les chiffres comptables des chiffres ajustés pour retirer certains éléments exceptionnels.
- **Attentes des analystes** : écart entre résultat publié et estimation antérieure, uniquement si une source fiable et datée permet de connaître cette estimation avant l'annonce. Une estimation citée dans une dépêche n'est pas automatiquement un consensus vérifié.
- **Prévisions de la direction** : ce que l'entreprise annonce pour les prochains trimestres, notamment les révisions par rapport à ses précédentes prévisions.
- **Explications et éléments exceptionnels** : changements d'activité, difficultés ou événements qui modifient la lecture des chiffres.

Une entreprise peut annoncer des bénéfices en hausse et voir son action baisser si les attentes étaient encore plus élevées. Le modèle doit donc apprendre à interpréter les résultats dans leur contexte, plutôt qu'assimiler « bons résultats comptables » à « hausse de l'action ».

## Sortie envisagée

Privilégier une probabilité entre 0 et 100 %, puis éventuellement un résultat binaire avec un seuil fixé avant l'évaluation.

Exemple illustratif, **non figé** : « probabilité de baisse de l'action sur les cinq séances suivant le moment où l'on peut intervenir ». Il faudra préciser l'horizon, le prix de départ, le traitement d'un prix inchangé et le choix entre baisse absolue et sous-performance par rapport au marché.

Un score de 70 % ne signifie pas une baisse de 70 %. Il devrait correspondre à environ 70 baisses sur 100 situations comparables : c'est la **calibration**. Demander un pourcentage à un modèle de langage ne suffit pas à obtenir une probabilité calibrée.

## Architecture de départ proposée

1. Un modèle de langage existant, avec une version figée, extrait les informations du document. Chaque chiffre ou affirmation doit pouvoir être relié à son passage ou à son tableau source ; une donnée absente reste manquante.
2. Un petit classifieur apprend à relier ces informations aux mouvements ultérieurs de l'action et produit la probabilité de baisse.
3. Comparer l'information apportée par les **chiffres seuls**, le **titre de la dépêche** et le **document complet**, sur les mêmes événements, fenêtres et règles d'exécution.

L'entraînement d'un grand modèle de zéro n'est pas nécessaire pour cette première étude. Une sortie directe du modèle de langage pourrait être une variante distincte, à déclarer avant de l'essayer.

## Apprentissage et évaluation

Utiliser le mouvement futur comme réponse attendue est le principe de l'**apprentissage supervisé** : les documents anciens et les mouvements qui les ont suivis servent d'exemples. En revanche, le modèle évalué ne reçoit ni le mouvement futur de l'événement évalué, ni un texte qui le décrit après coup.

Deux questions doivent rester séparées :

- **Compréhension de la réaction initiale** : le document permet-il de prévoir la variation entre avant et après sa publication ? Cette variation peut déjà être passée lorsque le système répond.
- **Prévision exploitable** : reste-t-il un mouvement prévisible après réception du document, lecture, inférence et passage de l'ordre ? La mesure doit commencer au premier prix réellement accessible après ces délais.

Observer une baisse après la publication ne prouve pas que le document l'a causée. Comparer également l'évolution de l'action à celle du marché sur les mêmes dates.

Évaluer d'abord la qualité des prédictions et leur calibration, avec un témoin prédisant systématiquement la classe la plus fréquente dans l'apprentissage. Puis, dans un protocole de portefeuille distinct et préenregistré, vérifier si ces prédictions améliorent le capital après frais face au buy and hold du même univers. Un bon taux de bonnes directions ne garantit pas un gain : l'ampleur des pertes et des gains compte aussi.

## Lien avec l'existant et données candidates

- [H09 — événements de résultats](RESULTATS_EVENEMENTS.md) utilisait surtout des chiffres comptables et soulignait leur disponibilité parfois trop tardive.
- [H10 — dépêches à la minute](RESULTATS_DEPECHES_MINUTE.md) exploitait les surprises de résultats citées dans les dépêches. Ce n'était pas un modèle apprenant à interpréter le document complet.
- Des communiqués ont déjà été récupérés dans `data/events/exhibits/` pour vérifier des chiffres : voir [TRI_NEWS.md](TRI_NEWS.md). Leur couverture, leur contenu et leurs heures de disponibilité restent à auditer pour cette nouvelle utilisation.
- Autres données candidates : `data/news/`, `data/sec/`, `data/events/eight_k_times/`, les barres de `data/events/minute_bars/` et `minute_bars_extra/`, ainsi que `data/universe_clean/` pour une évaluation quotidienne.
- Cette piste pourrait ensuite fournir une variable au modèle hybride H17. Elle ne constitue pas une validation ni un remplacement automatique des autres pistes.

## Conditions avant tout test

1. Inscrire l'hypothèse dans `registre_hypotheses.csv`, avec **`inspiree_de_resultats_vus = oui`**, la source de l'idée, les périodes et le nombre maximal de variantes. Contrôler le registre avec `venv/bin/python src/registry.py` ; le futur lanceur devra appeler `registry.require("Hxx")` avec l'identifiant attribué.
2. Figer la cible, les délais, les règles d'entrée, l'horizon, les modèles, les témoins, les critères de succès et la correction des comparaisons multiples. Faire auditer le protocole et le code avant lancement.
3. Séparer chronologiquement apprentissage et évaluation ; aucun mélange aléatoire des dates. Les réponses d'apprentissage doivent être entièrement connues avant la période évaluée. Les versions d'un même document ne doivent pas être réparties entre apprentissage et évaluation.
4. **2018–2024 reste du développement exploratoire pour cette idée. Ne pas réutiliser 2025–2026 pour retester des règles ajustées et ne pas lire les dossiers `*holdout_*`.** La confirmation demandera des données futures recueillies après le gel, selon un calendrier à définir.
5. Documenter le préentraînement des modèles : un modèle récent peut connaître les conséquences d'un ancien communiqué. Lui demander d'ignorer le futur, ou retirer le nom de l'entreprise, ne garantit pas l'absence de mémorisation.
6. Respecter les horodatages et versions : ne jamais utiliser le champ `accepted` erroné des 8-K ; utiliser `accepted_new_york` ou `filing_date` avec une entrée prudente. L'acceptation SEC peut être postérieure à la diffusion du communiqué. `available_at` des news reste une borne, pas une preuve de première diffusion.
7. Pour les données chiffrées complémentaires : EPS causal via `pe.causal_eps_matrix`, respect de `filed` et des opérations sur titres. Pour les simulations : filtres sur prix et volumes bruts, `suspect_print` manquant, frais et sensibilités, trois hypothèses de sortie de cote. Les barres minute corrigées doivent être jointes avec les bons symboles historiques.

## Référence de la discussion

[Lopez-Lira et Tang, *Can ChatGPT Forecast Stock Price Movements?*, version du 28 octobre 2025](https://arxiv.org/abs/2304.07619v6) distinguent la réaction initiale non négociable des mouvements ultérieurs. Leur travail porte sur les titres de news ; il ne valide pas directement le système de lecture de documents proposé ici.
