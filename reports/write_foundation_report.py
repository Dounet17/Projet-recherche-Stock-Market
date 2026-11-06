"""Rédige le rapport uniquement lorsque les expériences prévues sont terminées."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "foundation_benchmark_2026-10-25"
forecast = pd.read_csv(OUT / "forecast_metrics.csv").set_index("strategy")
required = [f"{family}_{variant}" for family in ("chronos_synth", "timesfm3") for variant in ("univariate", "market", "finbert", "jev", "zero_jev")]
required += ["kronos_s1_univariate", "chronos2_univariate", "chronos2_market", "chronos2_jev"]
missing = sorted(set(required) - set(forecast.index))
pilot = pd.read_csv(OUT / "kit_pilot.csv")
if missing or len(pilot) != 36:
    raise RuntimeError(f"Expériences encore en cours : {missing}, KiT {len(pilot)}/36")
portfolio = pd.read_csv(OUT / "metrics.csv")
annual = pd.read_csv(OUT / "annual_returns.csv")
uncertainty = pd.read_csv(OUT / "social_uncertainty.csv")
reference = pd.read_parquet(ROOT / "reports" / "backtest_musk_2026-10-25" / "predictions.parquet")
matched = pd.read_csv(OUT / "pilot_matched_comparison.csv").set_index("strategy")
kit_meta = json.loads((OUT / "kit_pilot_metadata.json").read_text())
meta = json.loads((OUT / "metadata.json").read_text())
labels = {"chronos_synth_univariate": "Chronos-2-Synth : TSLA seul", "chronos_synth_market": "Chronos-2-Synth : TSLA + QQQ", "chronos_synth_finbert": "Chronos-2-Synth + FinBERT", "chronos_synth_jev": "Chronos-2-Synth + Jev", "timesfm3_univariate": "TimesFM-3 : TSLA seul", "timesfm3_market": "TimesFM-3 : TSLA + QQQ", "timesfm3_finbert": "TimesFM-3 + FinBERT", "timesfm3_jev": "TimesFM-3 + Jev", "chronos2_univariate": "Chronos-2 : TSLA seul", "chronos2_market": "Chronos-2 : TSLA + QQQ", "chronos2_jev": "Chronos-2 + Jev", "kronos_s1_univariate": "Kronos-small : OHLCV", "chronos_synth_zero_jev": "Chronos-2-Synth : contrôle social nul", "timesfm3_zero_jev": "TimesFM-3 : contrôle social nul"}


def percent(value):
    return f"{value * 100:+.2f} %"


def metric(name, rule, cost):
    return portfolio[(portfolio.strategy == name) & (portfolio.rule == rule) & (portfolio.cost_bps_per_side == cost)].iloc[0]


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in rows]
    return "\n".join(lines)


names = [n for n in labels if "zero_jev" not in n]
main_rows = []
for name in names:
    gross, net, margin = metric(name, "sign", 0), metric(name, "sign", 5), metric(name, "margin10bp", 5)
    main_rows.append([labels[name], f"{forecast.loc[name, 'accuracy'] * 100:.2f} %", percent(gross.total_return), percent(net.total_return), f"{net.final_capital:,.0f} USD", percent(margin.total_return)])

control_rows = []
for family in ("chronos_synth", "timesfm3"):
    for variant in ("market", "zero_jev", "jev"):
        name = f"{family}_{variant}"
        net = metric(name, "margin10bp", 5)
        control_rows.append([labels[name], f"{forecast.loc[name, 'accuracy'] * 100:.2f} %", percent(net.total_return), int(net.round_trips)])

interval_rows = []
for row in uncertainty[uncertainty.rule.eq("margin10bp")].itertuples():
    interval_rows.append([row.family, row.social_variant, row.control, f"{row.annualized_log_return_difference * 100:+.2f} points", f"[{row.ci95_low * 100:+.2f} ; {row.ci95_high * 100:+.2f}]"])

pilot_rows = []
for name in ["kit_pilot", "kronos_s1_univariate", "timesfm3_market", "chronos_synth_market", "chronos2_market", "always_up"]:
    row = matched.loc[name]
    label = "KiT (pilote)" if name == "kit_pilot" else "Direction toujours haussière" if name == "always_up" else labels[name]
    mae = "—" if pd.isna(row.mae_return) else f"{row.mae_return * 100:.3f} %"
    pilot_rows.append([label, int(row.rows), f"{row.accuracy * 100:.2f} %", mae])
kit_hits = int(((pilot.predicted_return > 0) == (pilot.actual_return > 0)).sum())
kit_ci = stats.binomtest(kit_hits, len(pilot)).proportion_ci()
runtime_rows = [[labels[n], f"{forecast.loc[n, 'inference_seconds']:.1f} s"] for n in names]
timesfm = (forecast.index.str.startswith("timesfm3"))
synth = (forecast.index.str.startswith("chronos_synth"))
env = json.loads((OUT / "environment.json").read_text())
old_accuracy = ((reference.prob_prices > .5) == (reference.asset_return > 0)).mean()
always_up = float((reference.asset_return > 0).mean())
naive_mae = float(reference.asset_return.abs().mean())
social_rows = int(reference.social_count_60.gt(0).sum())
main_net = portfolio[portfolio.strategy.isin(names) & portfolio.cost_bps_per_side.eq(5)]
outcome = "Aucune des configurations complètes testées n'est rentable après le coût central, y compris avec la règle d'abstention."
if main_net.total_return.gt(0).any():
    outcome = "Certaines configurations ont un rendement net positif dans ce protocole rétrospectif ; ce résultat exige une validation indépendante."
accuracy_range = f"{forecast.loc[names, 'accuracy'].min() * 100:.2f} % à {forecast.loc[names, 'accuracy'].max() * 100:.2f} %"

text = f'''# Essais des modèles préentraînés sur Musk / Tesla — 25 octobre 2026

**{outcome}** Les bonnes directions sur le benchmark complet vont de **{accuracy_range}**. Le score KiT de 24/36 appartient à un pilote distinct et ne constitue pas une validation hors préentraînement.

Les modèles ont été téléchargés, chargés et exécutés sur les données locales. TimesFM-3, Chronos-2-Synth, Chronos-2 et Kronos-small ont chacun des prévisions couvrant les **18 000 décisions de 2022–2024**. KiT a été exécuté sur **36 origines mensuelles distinctes**, dans un pilote séparé. Le détail chiffré ci-dessous permet de distinguer la qualité de prévision et la conséquence d'une règle de trading.

**Calcul effectivement réalisé sur AMD**

GPU détecté : **{meta['device']}**, 12 Go. Environnement isolé `.venv-forecast/`, **PyTorch {meta['torch']}**, ROCm/HIP **{meta['hip']}**, variable `HSA_OVERRIDE_GFX_VERSION=10.3.0`. Les modèles utilisent le périphérique PyTorch `cuda`, qui désigne ici le GPU AMD via ROCm. L'environnement initial `venv/` conserve son PyTorch CPU.

Le GPU a été observé à près de 100 % d'utilisation pendant les calculs. La variante KiT FP16 a produit des trajectoires finies et positives sur les cas évalués ; TimesFM, Chronos et le benchmark principal Kronos utilisent FP32. Un essai de vitesse Kronos en autocast FP16 n'a pas justifié de remplacer le calcul FP32 engagé. Ces essais numériques ne constituent pas une preuve de calibration financière.

**Protocole et limites de comparaison**

- Dates, exécutions et coûts repris du premier backtest : 753 séances, décisions toutes les 15 minutes, entrée après les informations disponibles, sorties 15 minutes plus tard, achat Tesla ou liquidités, sans levier ni vente à découvert, fractions d'action autorisées, pas de position de nuit.
- Dernier chandelier observé : celui qui commence à t−2 minutes et finit à t−1. Les tweets utilisés sont donc antérieurs d'au moins 60 secondes à l'entrée. Les prix d'exécution restent les ouvertures réelles à t et t+15.
- Prévisions de 17 ouvertures successives : première ouverture prévue à t−1, deuxième à t, dix-septième à t+15. Le signal compare les indices 1 et 16 de la trajectoire prévue. Le vrai cours d'entrée n'est pas utilisé pour construire le signal ; la réaction antérieure à l'entrée est exclue.
- Entrées TimesFM/Chronos : 128 barres de séance consécutives, pouvant traverser une nuit entre deux séances sans fabriquer de barres nocturnes. La cible est la série des ouvertures TSLA ; la variante marché ajoute les ouvertures QQQ historiques. Ces variantes ne reçoivent pas tous les champs OHLCV, contrairement à Kronos, qui utilise sa représentation native. Ce choix d'entrée est une limite du test de leur potentiel maximal.
- Les fenêtres contiennent les barres régulières ; les rares minutes historiques sans transaction sont représentées au dernier cours passé avec volume nul. Aucun prix d'exécution n'est ainsi fabriqué. Les 18 000 points d'entrée et sortie du test disposent de leurs prix réels.
- Les variables sociales sont uniquement historiques : nombre de posts dans les 60 minutes précédentes, sentiment FinBERT ou sentiment/impact/pertinence Jev. Aucun futur tweet ni futur prix QQQ n'est fourni. Le contrôle `zero_jev` garde le même nombre de canaux que Jev mais remplace les canaux sociaux par zéro.
- Poids préentraînés figés : aucun réentraînement annuel de ces modèles. La comparaison utilise les mêmes années évaluées que la régression logistique, mais les modes d'apprentissage et les représentations diffèrent. Le modèle Synth est annoncé comme entraîné uniquement sur des séries synthétiques ; les scores textuels eux-mêmes restent rétrospectifs.
- Kronos : une trajectoire par origine (valeur par défaut du dépôt), température 1 et top-p 0,9, graine 20261025 + début du lot. La variabilité entre graines n'est pas évaluée ; ce budget de tirage est une limite du test. Un premier calcul de trois trajectoires, plus coûteux, a été arrêté avant d'examiner ses résultats et n'entre pas dans les comparaisons finales. KiT : fenêtre native de {kit_meta['context']} barres, horizon natif de {kit_meta['native_horizon']} barres, {kit_meta['paths']} trajectoires et {kit_meta['euler_steps']} étapes Euler ; seules les prévisions nécessaires aux 15 minutes sont évaluées. Les budgets de calcul ne sont donc pas identiques.
- Deux règles publiées : achat si le rendement prévu est positif (`sign`), et achat seulement au-dessus de 0,10 % (`margin10bp`). La seconde marge correspond approximativement aux coûts centraux aller-retour ; elle n'a pas été optimisée sur ces résultats. Les scénarios de coût gardent les mêmes positions pour chaque règle.

**Résultats du benchmark complet**

Capital initial : 10 000 **USD**, sans simulation de conversion EUR/USD. Coût central : 5 points de base par côté, soit 0,05 % à l'achat et 0,05 % à la vente, couvrant hypothétiquement commissions, spread et glissement. Les prévisions ne sont pas des prix d'exécution garantis.

{table(['Variante', 'Bonne direction', 'Rendement brut, signe', 'Rendement net, signe', 'Capital net, signe', 'Rendement net, marge 0,10 %'], main_rows)}

Références sur ces mêmes dates : ancien modèle prix seuls **{old_accuracy * 100:.2f} %** de bonnes directions, −21,10 % sans frais et −82,45 % avec le coût central ; acheter systématiquement sur chaque intervalle correspond à une direction haussière correcte **{always_up * 100:.2f} %** du temps. Conserver Tesla depuis le début, nuits comprises, donne +5,40 % net, avec une exposition différente de celle des modèles intraday. Les liquidités sans intérêts restent à 10 000 USD.

L'erreur absolue moyenne d'une prévision de rendement nul est de **{naive_mae * 100:.3f} %** par intervalle. Les erreurs, corrélations, résultats annuels, pertes maximales et nombres d'allers-retours de tous les modèles sont dans les CSV associés. Une bonne précision du niveau de prix ne suffirait pas à établir une bonne prévision de rendement.

**Attribuer correctement l'effet social**

Un post classé figure dans la fenêtre sociale de **{social_rows} / 18 000 intervalles**, soit {social_rows / len(reference) * 100:.2f} %. L'ajout de canaux peut modifier les prévisions même quand ces canaux sont constants. Une amélioration avec un score social peut aussi venir d'une plus faible amplitude prévue, entraînant moins de transactions. Le contrôle nul permet de ne pas attribuer automatiquement cet effet au contenu des tweets.

{table(['Variante', 'Bonne direction', 'Rendement net, règle avec marge', 'Allers-retours'], control_rows)}

Pour les différences de portefeuille, des mois entiers sont rééchantillonnés ensemble entre variantes (3 000 tirages sur 36 mois). La statistique ci-dessous est une différence annualisée de rendements **logarithmiques**, exprimée en points ; elle n'est pas l'écart de rendement cumulé de la première table. Les intervalles sont exploratoires, sans correction globale pour toutes les variantes et tous les critères testés.

{table(['Famille', 'Score ajouté', 'Contrôle', 'Différence annualisée', 'Intervalle 95 %'], interval_rows)}

**KiT : pilote séparé, avec chevauchement du préentraînement**

Origines fixées avant l'examen des résultats : première séance de chaque mois à midi, heure de New York, sur 2022–2024. KiT produit des prévisions pour les 36 dates ; la table compare les autres modèles sur **ces mêmes dates**, pas sur leurs 18 000 décisions.

{table(['Modèle', 'Origines', 'Bonne direction', 'Erreur absolue moyenne de rendement'], pilot_rows)}

KiT : {kit_hits} bonnes directions sur 36 ; intervalle binomial à 95 % approximatif [{kit_ci.low * 100:.1f} % ; {kit_ci.high * 100:.1f} %], à lire avec prudence sur un échantillon aussi petit et rétrospectif. Aucun portefeuille KiT de trois ans n'est assimilé à celui des modèles complets.

Le checkpoint global téléchargé déclare une borne d'apprentissage au **{kit_meta['training_cutoff']}**, et son vocabulaire contient explicitement TSLA (identifiant {kit_meta['tsla_embedding_id']}). Les données 2022–2024 ne constituent donc pas une période démontrée hors préentraînement pour KiT. Son pilote vérifie le fonctionnement et décrit ses prévisions sur nos données ; il ne démontre pas une capacité à prévoir des événements inconnus. La même vérification de provenance reste nécessaire pour les autres modèles, notamment les classifieurs de texte. Le checkpoint KiT plus récent daté de 2026 et limité aux actions chinoises n'a pas été utilisé pour Tesla.

**Coût de calcul observé**

{table(['Variante complète', 'Temps d\'inférence cumulé observé'], runtime_rows)}

Pilote KiT : {pilot.seconds.sum():.1f} secondes cumulées pour les 36 origines. Ces mesures incluent l'attente liée aux autres expériences partageant le GPU ; elles ne forment pas un classement de vitesse isolé. Téléchargement et chargement sont exclus des temps d'inférence. Les calculs par lots sont adaptés à l'évaluation historique ; ils ne mesurent pas la latence complète de détection et d'exécution d'un ordre en direct.

**Lecture scientifique des résultats**

Les valeurs du tableau décrivent des modèles, entrées, horizons et règles précis. Il faut apprécier ensemble la précision, le rendement brut, les frais et l'exposition. Un taux proche de 50 % peut parfois correspondre à un signal économiquement utile si les gains et pertes sont asymétriques ; il ne suffit pas à lui seul pour valider ou invalider une stratégie. À l'inverse, une différence de capital après des milliers de transactions ne prouve pas que le modèle comprend mieux les tweets.

Cette comparaison est rétrospective : la période avait déjà été explorée avant les essais, et certains corpus de préentraînement peuvent recouvrir ces années. Les règles n'ont pas été sélectionnées pour maximiser un gain après inspection des résultats. Les variantes défavorables et les contrôles restent publiés. Les frais sont hypothétiques, les intérêts des liquidités, la fiscalité, la liquidité réelle et l'impact de marché ne sont pas modélisés. Les pertes maximales sont calculées aux points de valorisation, sans toutes les fluctuations internes à un intervalle.

**Reproduction et livrables**

- À partir du venv initial installé, `bash reports/setup_forecast_environment.sh` recrée la surcouche ROCm et télécharge les révisions exactes des poids et sources. Les données locales du projet restent nécessaires.
- Prévisions complètes : `HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_foundation_benchmark.py --family timesfm3 --batch-size 32` ; même commande avec `chronos_synth`, puis `chronos2 --variants univariate market jev`, et `kronos --variants univariate`.
- Contrôles : familles `timesfm3` et `chronos_synth`, option `--variants zero_jev`.
- KiT : `HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/run_kit_pilot.py --paths 8 --steps 16 --precision fp16`.
- Évaluation : `HSA_OVERRIDE_GFX_VERSION=10.3.0 .venv-forecast/bin/python reports/score_foundation_benchmark.py`, puis `... reports/write_foundation_report.py`.
- Tests : `.venv-forecast/bin/python -m unittest discover -s tests -v`.
- Versions des bibliothèques, empreintes des sources et des données de référence, révisions des poids et des dépôts : `foundation_benchmark_2026-10-25/metadata.json` et `environment.json`. Les poids et sources tierces sont conservés dans le cache Hugging Face et `data/vendor/`, exclus de Git.
- Les prédictions par lots sont persistées pour reprendre un calcul interrompu ; ne pas réutiliser ces caches après modification du protocole sans les régénérer.
- Résultats : `forecast_metrics.csv`, `metrics.csv`, `annual_returns.csv`, `social_uncertainty.csv`, `pilot_matched_comparison.csv`, `kit_pilot.csv`, `forecast_returns.parquet`, `daily_returns.csv`, courbes de capital et journaux.

![Courbes des portefeuilles simulés](foundation_benchmark_2026-10-25/equity.png)

Sources des modèles : [Google TimesFM](https://github.com/google-research/timesfm), [Chronos](https://github.com/amazon-science/chronos-forecasting), [Kronos](https://github.com/shiyu-coder/Kronos), [KiT](https://github.com/Luciferbobo/KiT). Les résultats locaux de ce rapport proviennent des fichiers produits par les scripts, et non des performances annoncées par leurs auteurs.
'''
path = ROOT / "reports" / "Resultats_modeles_preentraines_2026-10-25.md"
path.write_text(text)
print(path)
