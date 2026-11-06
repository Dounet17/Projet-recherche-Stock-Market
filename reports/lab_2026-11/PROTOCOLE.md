# Protocole du laboratoire de stratégies (figé le 06/11/2026, avant tout essai)

## Question
Une stratégie peut-elle battre l'achat au début suivi de la simple attente (buy and hold), sur une période jamais regardée et après frais ?

## Découpage temporel
- 2016-2017 : préchauffage des indicateurs, aucune performance comptée.
- **Développement : 02/01/2018 au 31/12/2024.** Toute conception et tout choix de paramètres se font ici.
- **Validation verrouillée : 02/01/2025 au 30/10/2026.** Personne n'y touche pendant la recherche. Elle est lue une seule fois, à la fin, sur les stratégies déclarées à l'avance.

Le verrou est dans `lab.load_panel`. Il ne faut ni le contourner, ni lire `data/lab_daily_adjusted.parquet` directement, ni télécharger ou afficher un cours, une news ou une statistique postérieurs au 31/12/2024 pendant le développement.

## Règles de simulation (`src/lab.py`)
- Décision à la clôture de t, exécution à l'ouverture de t+1. Le moteur fait ce décalage.
- Prix ajustés des splits et dividendes, donc comparaison en rendement total.
- 5 points de base par côté, 10 en sensibilité. Sans levier ni vente à découvert dans l'analyse principale.
- Liquidités à 0 % dans l'analyse principale, ce qui défavorise les stratégies souvent hors marché. Sensibilité avec BIL (bons du Trésor).
- Capital de 10 000 USD. Fiscalité et EUR/USD non simulés, à signaler : une rotation fréquente serait plus taxée.

## Ce qui compte comme « battre »
Deux critères séparés, à toujours publier ensemble :
1. **Gagner plus** : capital final supérieur au buy and hold du même actif.
2. **Gagner mieux** : Sharpe supérieur (plus de gain par unité de risque), avec alpha positif.

Une stratégie moins risquée qui gagne moins ne bat pas le buy and hold sur le critère 1, il faut le dire ainsi.

Référence : le buy and hold du même actif. Pour une rotation entre plusieurs actifs : SPY et QQQ.

## Honnêteté statistique
- Chaque variante essayée est inscrite au journal avec `lab.record_trial`, y compris les échecs.
- p-values corrigées par `lab.romano_wolf` sur l'ensemble des essais.
- Univers figé dans `lab.UNIVERSE`. Les résultats sont publiés pour tous les actifs testés, pas uniquement les réussites.
- Les actions individuelles de l'univers sont des gagnantes connues de 2016-2024 (biais de survie), leurs résultats ne se généralisent pas.
- Chaque stratégie passe `lab.check_no_lookahead`.
- Aucune stratégie n'est retenue sur une seule année ou un seul actif sans le signaler.

## Déclaration finale
Chaque binôme déclare au plus 3 stratégies figées dans `reports/lab_2026-11/preregistration_<owner>.json` : nom, code, paramètres exacts, actifs, références. La validation n'est lancée qu'une fois les deux déclarations écrites et auditées par l'autre binôme, et les résultats sont tous publiés, bons ou mauvais.

## Dérogation décidée le 06/11/2026, avant lecture de la validation
Le fichier prix contient 3 stratégies et Codex n'en a déclaré aucune. Le coordinateur ajoute une 4e stratégie dans `preregistration_news_addendum.json`, soit une de plus que sa limite de 3. La limite totale de 6 reste respectée et la correction de Holm couvre les 4. Cet ajout ne satisfait pas la règle de sélection de Codex : il est exploratoire et décrit comme tel.

## Politique de transaction
Une ligne de poids vide signifie « aucun ordre ». Pour le ciblage de volatilité, la bande de 10 points se mesure sur un portefeuille fictif sans frais lancé au début de l'historique : c'est un signal. Au début d'une fenêtre, le portefeuille réel entre sur le dernier ordre connu. Une fenêtre glissante vend au plus tard à sa dernière ouverture, sans aucun prix postérieur.

## Limite des données sociales
Les posts de Musk s'arrêtent le 08/05/2025. Une stratégie sociale n'a donc que quatre mois de validation possible, sauf collecte nouvelle : ce n'est pas une preuve solide, à écrire tel quel.
