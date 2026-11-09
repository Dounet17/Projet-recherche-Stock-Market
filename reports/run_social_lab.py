"""Reproduit les essais sociaux de développement, sans ouvrir la validation."""

import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
import social_lab as social

OUT = social.SOCIAL_DIR


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def pct(value):
    return f"{100 * value:.2f} %"


def markdown_table(frame, columns):
    text = ["| " + " | ".join(columns.values()) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for _, row in frame.iterrows():
        values = []
        for col in columns:
            value = row[col]
            if col in ("cagr", "max_drawdown", "annual_alpha", "annual_log_excess", "exposure"):
                values.append(pct(value))
            elif isinstance(value, (float, np.floating)):
                values.append(f"{value:,.3f}" if col != "final_capital" else f"{value:,.0f}")
            else:
                values.append(str(value))
        text.append("| " + " | ".join(values) + " |")
    return "\n".join(text)


def run(prepare_only=False):
    OUT.mkdir(parents=True, exist_ok=True)
    panel = lab.load_panel(symbols=["TSLA", "BIL"], end=lab.DEV_END)
    design = {
        "development_end": lab.DEV_END,
        "trials": {name: {"family": family, "description": description} for name, (family, description) in social.TRIALS.items()},
        "parameters": {"signal_window_sessions": 5, "past_quantile": 0.90, "past_window": 252,
                       "past_minimum": 126, "negative_sentiment_threshold": -0.10,
                       "other_topic_share": 0.75, "earnings_proxy_days": 91,
                       "trend_sessions": 200, "finbert_max_tokens": 128},
        "scenarios": [{"cost_bps": 5, "cash": "zero"}, {"cost_bps": 10, "cash": "zero"}, {"cost_bps": 5, "cash": "BIL_proxy"}],
        "selection_rule": "Hors contrôles : rendement supérieur à TSLA aux deux coûts, p corrigée <= 0.10 aux deux coûts, excès positif en 2022-2024 et au moins trois années positives; trois stratégies au maximum.",
        "ml_gate": "Pas de ML si aucune règle sociale simple ne franchit les critères de préinscription.",
    }
    design_path = OUT / "design.json"
    if design_path.exists():
        if json.loads(design_path.read_text(encoding="utf-8")) != design:
            raise RuntimeError("Le plan figé diffère du code : ne pas remplacer des essais silencieusement")
    else:
        save_json(design_path, design)
    social.prepare_news_cache(panel)
    if prepare_only:
        return
    frame = social.features(panel)
    frame.to_csv(OUT / "daily_features.csv", index_label="date")
    cutoff = social.close_times(panel.dates)[-1]
    posts, earnings, news = social.load_external(cutoff)
    source_metadata = {}
    for name, data in (("posts", posts), ("earnings", earnings), ("news", news)):
        source_metadata[name] = {"rows_before_cutoff": len(data), "sha256_filtered": hashlib.sha256(
            pd.util.hash_pandas_object(data, index=False).to_numpy().tobytes()).hexdigest()}
    source_metadata["posts"]["finbert_scored_rows"] = int(posts.p_positive.notna().sum())
    source_metadata["posts"]["jev_scored_rows"] = int(posts.impact_p_up.notna().sum())
    source_metadata["news"]["revision_fraction"] = float((news.updated_at > news.created_at).mean())
    source_metadata["code_sha256"] = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                      for name in ("src/lab.py", "src/social_lab.py", "reports/run_social_lab.py")}
    source_metadata["versions"] = {name: importlib.metadata.version(name)
                                  for name in ("numpy", "pandas", "pyarrow", "torch", "transformers")}
    source_metadata["finbert_snapshots_local"] = [path.name for path in sorted(
        (Path.home() / ".cache/huggingface/hub/models--ProsusAI--finbert/snapshots").glob("*"))]
    save_json(OUT / "sources.json", source_metadata)
    benchmarks = {cost: lab.backtest(lab.buy_hold_weights(panel, "TSLA"), panel, cost_bps=cost) for cost in (5, 10)}
    cash_bil = panel.open.BIL.shift(-1) / panel.open.BIL - 1
    rows, excess, daily, annual, checks = [], {}, {}, [], {}
    for variant, (family, _) in social.TRIALS.items():
        fn = lambda p, variant=variant: social.strategy_weights(p, variant)
        checks[variant] = lab.check_no_lookahead(fn, panel)
        weights = fn(panel)
        for cost, cash_name in ((5, "zero"), (10, "zero"), (5, "BIL_proxy")):
            name = f"{variant}__{cost}bps__{cash_name}"
            result = lab.backtest(weights, panel, cost_bps=cost,
                                  cash_returns=cash_bil if cash_name == "BIL_proxy" else None)
            benchmark = benchmarks[cost].returns
            params = {"variant": variant, "cost_bps": cost, "cash": cash_name,
                      "development_end": lab.DEV_END, "parameters": design["parameters"]}
            row = lab.record_trial(owner="codex", name=name, family=family, params=params,
                                   result=result, benchmark_symbol="TSLA", benchmark_returns=benchmark)
            comparison = lab.compare(result.returns, benchmark, n_boot=4000, mean_block=21, seed=0)
            row.update({"variant": variant, "cost_bps": cost, "cash": cash_name, **comparison})
            reference = lab.summarize(benchmarks[cost])
            row["beats_capital"] = row["final_capital"] > reference["final_capital"]
            row["higher_sharpe_positive_alpha"] = row["sharpe"] > reference["sharpe"] and row["annual_alpha"] > 0
            row["improves_drawdown"] = row["max_drawdown"] > reference["max_drawdown"]
            rows.append(row)
            excess[name] = np.log1p(result.returns) - np.log1p(benchmark)
            daily[name] = result.returns
            for year in range(2018, 2025):
                s = result.returns.loc[str(year)]
                b = benchmark.loc[s.index]
                annual.append({"name": name, "year": year, "strategy_return": float((1 + s).prod() - 1),
                               "benchmark_return": float((1 + b).prod() - 1),
                               "log_excess": float((np.log1p(s) - np.log1p(b)).sum())})
        print(f"Essai journalisé et causalité vérifiée : {variant}", flush=True)
    excess = pd.DataFrame(excess)
    corrected = lab.romano_wolf(excess, n_boot=4000, mean_block=21, seed=0)
    metrics = pd.DataFrame(rows)
    metrics["romano_wolf_p"] = metrics.name.map(corrected)
    metrics.to_csv(OUT / "metrics.csv", index=False)
    pd.DataFrame(daily).to_parquet(OUT / "daily_returns.parquet")
    annual = pd.DataFrame(annual)
    annual.to_csv(OUT / "annual_metrics.csv", index=False)
    corrected.to_csv(OUT / "corrected_pvalues.csv")
    save_json(OUT / "lookahead_checks.json", checks)
    main = metrics[(metrics.cash == "zero") & (metrics.cost_bps == 5)].sort_values("final_capital", ascending=False)
    selected = []
    for variant in social.TRIALS:
        if variant.startswith("control_"):
            continue
        cases = metrics[(metrics.variant == variant) & (metrics.cash == "zero")]
        beats = all(row.final_capital > lab.summarize(benchmarks[row.cost_bps])["final_capital"]
                    and row.romano_wolf_p <= 0.10 for row in cases.itertuples())
        primary = cases[cases.cost_bps == 5].iloc[0]
        annual_primary = annual[annual.name == primary["name"]]
        recent = excess.loc["2022":"2024", primary["name"]].sum()
        if beats and recent > 0 and (annual_primary.log_excess > 0).sum() >= 3:
            selected.append({"name": variant, "function": "social_lab.strategy_weights",
                             "parameters": {"variant": variant}, "fixed_parameters_in_code": design["parameters"],
                             "assets": ["TSLA"], "benchmark": "TSLA"})
    selected = selected[:3]
    preregistration = {
        "owner": "codex", "development_end": lab.DEV_END, "validation_read": False,
        "strategies": selected, "selection_rule": design["selection_rule"],
        "justification": "Aucune variante ne satisfait les critères figés de rendement, correction multiple et stabilité." if not selected else "Critères figés franchis en développement, sans garantie hors échantillon.",
        "holdout_data_needed": {
            "period": "2025-01-01 au 2026-10-30, collecte et ouverture réservées au coordinateur",
            "posts": "Posts Musk complets, identifiants int64, texte original et heures recalculées depuis les identifiants; compléter la couverture après mai 2025 sans utiliser les réactions futures.",
            "news": "News TSLA Benzinga avec identifiant, titre, created_at et updated_at; idéalement archives des versions pour garantir le texte disponible à chaque date, et FinBERT local avec le même modèle et 128 tokens.",
            "earnings": "Dates et EPS réellement publiés, consensus enregistré avant publication et preuves horodatées des annonces du calendrier; les règles actuelles de calendrier utilisent seulement dernier résultat +91 jours.",
            "prices_calendar": "Panel ajusté et calendrier de clôtures ouverts par lab.load_panel avec autorisation explicite, sans téléchargement effectué par Codex.",
            "required_for_empty_selection": False,
        },
    }
    save_json(lab.LAB_DIR / "preregistration_codex.json", preregistration)
    ledger = pd.read_csv(lab.LAB_DIR / "ledger_codex.csv")
    if set(ledger.name) != set(metrics.name):
        raise RuntimeError("Le journal contient des essais supplémentaires : les inclure dans la correction avant publication")
    write_report(metrics, main, annual, benchmarks, source_metadata, selected, len(ledger))
    best = main.iloc[0]
    proof = {"trials": len(ledger), "best_strategy": best.variant,
             "best_final_capital": float(best.final_capital), "best_corrected_p": float(best.romano_wolf_p),
             "selected_strategies": len(selected), "command": "venv/bin/python reports/run_social_lab.py"}
    save_json(OUT / "completion.json", proof)
    print(json.dumps(proof, ensure_ascii=False), flush=True)


def write_report(metrics, main, annual, benchmarks, sources, selected, count):
    best = main.iloc[0]
    benchmark = lab.summarize(benchmarks[5])
    risk_better = main[main.higher_sharpe_positive_alpha]
    best_at_ten = metrics[(metrics.variant == best.variant) & (metrics.cash == "zero") & (metrics.cost_bps == 10)].iloc[0]
    text = ["# Recherche sociale, news et résultats trimestriels sur Tesla", "",
            f"Développement uniquement : 02/01/2018 au 31/12/2024. Validation 2025-2026 jamais ouverte. {count} essais journalisés, soit 15 règles et contrôles dans trois scénarios. {len(selected)} stratégie(s) préinscrite(s).", "",
            f"La variante au capital le plus élevé à 5 pb est `{best.variant}` : {best.final_capital:,.0f} USD contre {benchmark['final_capital']:,.0f} USD pour TSLA conservée, avec p corrigée {best.romano_wolf_p:.3f}. Ces observations de développement ne démontrent aucun avantage hors échantillon.", "",
            f"Cette règle conserve TSLA sauf lorsque la moyenne FinBERT des titres sur cinq séances est inférieure à -0.10 avec au moins trois titres classés. Elle améliore les estimations ponctuelles du CAGR ({pct(best.cagr)} contre {pct(benchmark['cagr'])}), du Sharpe ({best.sharpe:.3f} contre {benchmark['sharpe']:.3f}) et du drawdown ({pct(best.max_drawdown)} contre {pct(benchmark['max_drawdown'])}). À 10 pb elle atteint encore {best_at_ten.final_capital:,.0f} USD, avec p corrigée {best_at_ten.romano_wolf_p:.3f}. Son excès annuel de log-rendement a un intervalle bootstrap à 95 % de [{pct(best.excess_ci95[0])}; {pct(best.excess_ci95[1])}], incluant zéro. Son alpha a une p brute de {best.alpha_p_one_sided:.3f}, sans correction multiple, et le gain de Sharpe une p brute de {best.sharpe_diff_p_one_sided:.3f}. Ce sont des pistes exploratoires incertaines; le résultat négatif porte sur la preuve statistique, sans démontrer l'absence de tout signal social.", "",
            "## Lecture des mesures", "",
            "On part de 10 000 USD. Le CAGR est le rendement composé moyen par an. Le Sharpe rapporte le rendement moyen aux variations du portefeuille : plus haut est préférable à risque comparable. Le drawdown mesure la plus forte chute depuis un sommet; il est calculé aux ouvertures, pas à l'intérieur des séances. L'alpha est le rendement annuel restant après estimation de l'exposition aux variations quotidiennes de TSLA. Une p corrigée faible serait une indication contre le hasard après prise en compte de tous les essais; elle ne garantit ni rentabilité future ni absence de biais de données. Une p de 0.10 n'est pas une preuve solide. Les liquidités ont un rendement nul dans l'analyse principale.", "",
            "## Audit indépendant du moteur", "",
            "Lecture de CLAUDE.md, du protocole, du moteur, de ses tests et du rapport intraday antérieur avant toute stratégie. Cinq défauts reproduits par cinq tests en échec dans tests/test_social_lab.py, transmis au coordinateur par la question msg_4b35443c23f8, puis corrigés exclusivement par lui dans src/lab.py :", "",
            "- Les périodes avec un trou de prix interne disparaissaient avant le contrôle de valorisation. Le test impose désormais le refus d'une position impossible à valoriser.",
            "- Le contrôle de causalité ignorait les colonnes absentes des panels tronqués. Le test d'une colonne ajoutée seulement sur le panel complet détecte désormais la fuite.",
            "- Romano-Wolf donnait p = 1 à un avantage constant strictement positif. Le cas dégénéré est désormais traité selon son signe.",
            "- La comparaison d'une stratégie intégralement en liquidités produisait un Sharpe et un intervalle NaN. La convention Sharpe nul est désormais commune aux fonctions.",
            "- Le bootstrap de l'alpha gardait le bêta global. Chaque tirage réestime maintenant pente et intercept. Le scénario synthétique avait un intervalle incorrect [0.039875; 0.493717], contre [-0.076818; 0.620118] après réajustement, ce qui changeait l'inclusion de zéro.", "",
            "Autres points contrôlés : les poids du jour sont décalés une fois par le moteur et gagnent seulement de l'ouverture suivante à celle d'après; achat initial et liquidation finale paient les frais; la dérive des poids évite de facturer un rééquilibrage fictif d'une position entièrement en TSLA ou d'un panier à deux actifs dont la cible suit exactement les poids dérivés; le drawdown inclut le capital initial; bootstrap stationnaire apparié avec blocs moyens de 21 séances; tests unilatéraux centrés sous l'hypothèse nulle; verrou refusant load_panel(end > 2024) sans autorisation. Aucun autre défaut confirmé dans le périmètre audité. Les cinq tests de régression restent dans tests/test_social_lab.py. Le test causal par troncature est un contrôle utile, pas une preuve contre toute erreur sémantique de source.", "",
            "## Données et chronologie", "",
            f"Chargements Parquet filtrés à la clôture du dernier jour du panel, jamais lecture directe des prix : {sources['posts']['rows_before_cutoff']} posts hors retweets, {sources['posts']['finbert_scored_rows']} avec FinBERT et {sources['posts']['jev_scored_rows']} avec Jev; {sources['news']['rows_before_cutoff']} news; {sources['earnings']['rows_before_cutoff']} publications de résultats, y compris le préchauffage. Les empreintes portent uniquement sur les lignes autorisées, voir sources.json. Les compteurs de likes et de partages sont exclus car mesurés après publication.", "",
            "Les heures de Musk sont vérifiées par la formule de l'identifiant Twitter, en entier 64 bits. Chaque post et news entre au premier jour dont la clôture est postérieure à sa disponibilité : nuit, week-end et séance écourtée passent à la prochaine clôture. Le calendrier local fournit les clôtures réelles; 16 h New York sert seulement avant sa couverture. La news est disponible au maximum de created_at et updated_at : un titre révisé n'est jamais exploité avant sa mise à jour. Les changements antérieurs de titre restent inconnus : les versions originales ne sont pas reconstruites et une source rétrospective peut rester incomplète.", "",
            f"{100*sources['news']['revision_fraction']:.1f} % des news ont une mise à jour postérieure à leur création. FinBERT local sur CPU utilise seulement les titres, ProsusAI/finbert, 128 tokens maximum, sans réentraînement. Le cache est dans social/news_finbert.parquet pour respecter la liste de fichiers autorisés, plutôt que créer un nouveau fichier dans data/. Jev utilise exclusivement le cache existant : aucun appel payant, aucun accès à .env. Les scores sociaux manquants ne deviennent pas des opinions neutres : aucune abstention n'est déclenchée sans score. Les caches Musk couvrent seulement le sous-ensemble Tesla constitué antérieurement; les thèmes extérieurs proviennent d'une règle lexicale sur tous les posts disponibles hors retweets.", "",
            "Une surprise de bénéfice ne peut agir qu'à la clôture du lendemain de publication au plus tôt, même lorsque l'heure de source paraît antérieure à la fermeture. L'entrée se produit donc au plus tôt à l'ouverture encore suivante. Les EPS arrondis sont comparés directement et les estimations manquantes exclues; les pourcentages de surprise aberrants sur petites bases ne sont pas utilisés. Le consensus EPS est rétrospectif et sa version exacte d'avant publication n'est pas garantie. Les dates futures réelles de publication ne sont jamais utilisées pour anticiper : aucune archive ne prouve ici quand elles étaient annoncées. Le substitut de calendrier est exclusivement la dernière publication connue plus 91 jours calendaires; il ne prétend pas connaître la prochaine date réelle.", "",
            "## Recherche figée et comparaison principale", "",
            "Le plan dans design.json fixe les 15 règles avant les rendements. Les paramètres ne sont pas balayés : fenêtres de 5 séances pour posts/news, seuil négatif -0.10, quantile à 90 % sur les 252 valeurs antérieures avec 126 observations minimum, part de sujets extérieurs à Tesla > 75 %, tendance moyenne de 200 clôtures. Les règles de news attendent 126 observations depuis le début effectif de couverture. Une moyenne de sentiment porte sur les seuls messages classés. Aucun modèle ML n'est entraîné si les règles simples ne justifient pas une poursuite. Toutes les fonctions passent lab.check_no_lookahead sur cinq troncatures et leurs données externes sont coupées à chaque troncature. Le dernier rendement finit à l'ouverture du 31/12/2024 : le moteur ne consomme pas l'ouverture du 02/01/2025 pour compléter la dernière séance.", "",
            "Le contrôle moitié TSLA sert à voir si un risque moindre vient seulement d'une exposition moindre. Le contrôle tendance isole l'apport social des deux hybrides. Ils sont inclus dans la correction multiple. Les p corrigées ci-dessous concernent l'excès de log-rendement face au buy and hold, avec lab.romano_wolf sur les 45 essais ensemble, 4 000 tirages et blocs moyens de 21 séances. Les sensibilités de coûts et de liquidités sont donc aussi incluses. Il ne s'agit pas de p corrigées de l'alpha ou du Sharpe : leurs intervalles appariés, avec bêta réajusté pour l'alpha, sont dans metrics.csv. Aucun test d'alpha à bêta figé ne fonde la sélection.", ""]
    columns = {"variant": "Règle", "final_capital": "Capital USD", "cagr": "CAGR", "sharpe": "Sharpe",
               "max_drawdown": "Drawdown", "annual_alpha": "Alpha/an", "romano_wolf_p": "p corrigée"}
    for cost in (5, 10):
        table = metrics[(metrics.cash == "zero") & (metrics.cost_bps == cost)].copy()
        base = {"variant": "BUY_HOLD_TSLA", **lab.summarize(benchmarks[cost]), "annual_alpha": 0.0, "romano_wolf_p": 1.0}
        table = pd.concat([pd.DataFrame([base]), table], ignore_index=True)
        text.extend([f"### {cost} pb par côté, liquidités à 0 %", "", markdown_table(table, columns), ""])
    text.extend(["### Sensibilité : rendement des liquidités approché par BIL", "",
                 "BIL est un fonds de bons du Trésor à court terme. Cette sensibilité crédite son rendement aux liquidités sans frais supplémentaires de rotation du fonds; c'est une approximation favorable aux stratégies souvent hors marché. Le benchmark reste TSLA conservée avec 5 pb par côté. Tous les essais de cette sensibilité sont journalisés.", "",
                 markdown_table(metrics[metrics.cash == "BIL_proxy"], columns), "",
                 "## Stabilité, échecs et limites", ""])
    stability = []
    for row in main.itertuples():
        data = annual[annual.name == row.name]
        early = data[data.year <= 2021].log_excess.sum()
        late = data[data.year >= 2022].log_excess.sum()
        stability.append({"variant": row.variant, "early_log_excess": f"{early:.3f}", "late_log_excess": f"{late:.3f}",
                          "positive_years": int((data.log_excess > 0).sum()), "exposure": row.exposure})
    text.extend([markdown_table(pd.DataFrame(stability), {"variant": "Règle", "early_log_excess": "Excès log 2018-2021",
                 "late_log_excess": "Excès log 2022-2024", "positive_years": "Années positives /7", "exposure": "Exposition"}), "",
                 "Les excès par sous-période sont des sommes de log-rendements, pas des pourcentages simples. 2022-2024 était déjà explorée dans le projet : ce découpage décrit la stabilité chronologique mais ne constitue pas une validation finale vierge. Les années sont découpées dans le portefeuille continu; elles ne simulent pas un nouvel achat indépendant au 1er janvier.", "",
                 "Les fenêtres avant une date approximative peuvent rater la publication réelle. Les règles après résultat manquent volontairement la réaction immédiate et peuvent sortir après la baisse. Les filtres d'activité confondent sujet et régime de marché : un pic ne dit pas si le titre montera ou baissera. Les scores financiers sont peu adaptés à l'ironie et à la politique; la règle lexicale de sujets reste grossière. Le sentiment des news peut résumer une variation déjà réalisée. Les stratégies en liquidités évitent certaines baisses mais ratent aussi les fortes hausses de TSLA, qui sont concentrées dans quelques périodes. Les frais sont hypothétiques : 5 pb = 0.05 % par montant acheté ou vendu, 10 pb double ce taux. Les sorties et entrées restent largement moins fréquentes que les essais intraday abandonnés.", "",
                 "Le seuil fixé de 75 % de posts explicitement liés à Twitter ou à la politique hors Tesla ne s'active jamais dans le développement. L'essai musk_other_exit_5 reproduit donc le buy and hold, et hybrid_musk_trend_200 reproduit le contrôle de tendance. Ces doublons sont conservés dans le journal et la correction. Ce résultat montre l'inadéquation de ce détecteur lexical à ce seuil, sans réfuter un éventuel effet des sujets extérieurs à Tesla. Aucun seuil n'est ensuite assoupli pour chercher un gain.", "",
                 f"Les deux critères du protocole restent distincts. À 5 pb, {int(main.beats_capital.sum())} règle(s) ont un capital supérieur à TSLA; {len(risk_better)} ont simultanément un Sharpe supérieur et un alpha positif au niveau des estimations ponctuelles : {', '.join(risk_better.variant) or 'aucune'}. La baisse maximale est aussi publiée pour chaque règle. Réduire la perte maximale en gagnant moins ne satisfait pas le premier critère. Les intervalles de Sharpe et d'alpha dans metrics.csv indiquent leur incertitude; aucune p corrigée sur ces deux mesures ne fonde ici une revendication de supériorité ajustée au risque. La sélection volontairement stricte exige une preuve de développement sur le capital avant de consommer la validation.", "",
                 "Les données rétrospectives peuvent être corrigées après les faits. La date d'apprentissage des classifieurs n'est pas auditée : une contamination temporelle reste possible. Aucun rendement futur des likes, du consensus révisé ou de nouvelles versions de titres ne doit être interprété comme une information historique certaine. Les résultats de TSLA, gagnante connue choisie pour le projet, ne se généralisent pas à un univers d'actions. Les drawdowns aux ouvertures sous-estiment potentiellement les pertes intrajournalières. Fiscalité, change EUR/USD, prix bid/ask et impact de marché ne sont pas simulés. La comptabilité est en USD, pas un placement réel de 10 000 EUR.", "",
                 "## Préinscription et reproduction", "",
                 ("La préinscription est vide : aucune règle n'a franchi les critères fixés. Il est préférable de conserver ce résultat négatif de développement que d'ouvrir la validation pour chercher un gagnant." if not selected else "Les règles ayant franchi les critères sont figées dans preregistration_codex.json. Elles attendent l'audit croisé et une validation unique par le coordinateur."), "",
                 "Les données nécessaires après 2024 sont décrites dans holdout_data_needed : posts complets avec identifiants exacts, titres Benzinga et historique de versions, résultats avec consensus daté, prix et calendrier. Aucune collecte de cette période n'est faite ici. La couverture sociale déjà annoncée jusqu'à mai 2025 serait trop courte pour une conclusion forte, même si elle était ouverte.", "",
                 "Reproduction : `venv/bin/python reports/run_social_lab.py`. Sans cache, cette commande effectue FinBERT sur CPU à partir des poids déjà présents localement; elle n'utilise pas le réseau. Les relances remplacent les mêmes noms d'essai, sans doubler leur compte. Vérification obligatoire : `venv/bin/python -m unittest tests.test_lab tests.test_social_lab`. Les preuves sont dans tests_output.txt, completion.json, corrected_pvalues.csv, metrics.csv et le journal ../ledger_codex.csv.", ""])
    (OUT / "RAPPORT.md").write_text("\n".join(text), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare-news-only", action="store_true")
    args = parser.parse_args()
    run(args.prepare_news_only)
