"""Évalue les trajectoires déjà calculées ; aucun réglage sur les résultats."""

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import balanced_accuracy_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from backtest import simulate, summarize
from foundation_benchmark import OUT, predicted_trade_return, prepare_inputs

reference, inputs = prepare_inputs()
days = pd.DatetimeIndex(reference.day.drop_duplicates())
actual = reference.asset_return.to_numpy()
target = actual > 0
results, forecasts, timings, details, daily_returns = [], {}, [], [], {}
for file in sorted(OUT.glob("predictions_*.npz")):
    saved = np.load(file)
    if int(saved["n"]) != len(reference):
        continue  # Les profils d'installation ne deviennent jamais des résultats complets.
    name = file.stem.removeprefix("predictions_")
    predicted = predicted_trade_return(saved["paths"])
    forecasts[name] = predicted
    decision = predicted > 0
    details.append({"strategy": name, "rows": len(predicted), "accuracy": float((decision == target).mean()), "balanced_accuracy": float(balanced_accuracy_score(target, decision)), "spearman": float(stats.spearmanr(predicted, actual).statistic), "mae_return": float(np.abs(predicted - actual).mean()), "rmse_return": float(np.sqrt(np.mean((predicted - actual) ** 2))), "predicted_positive_fraction": float(decision.mean()), "social_subset_accuracy": float((decision[reference.social_count_60.gt(0)] == target[reference.social_count_60.gt(0)]).mean()), "inference_seconds": float(saved["seconds"])})
    for rule, threshold in (("sign", 0.0), ("margin10bp", .001)):
        # Marge fixe égale au coût central aller-retour, aucun seuil optimisé sur le test.
        positions = (predicted > threshold).astype(int)
        for cost in (0, 2, 5, 10):
            curve = simulate(reference, positions, cost)
            summary = summarize(curve, days)
            daily = summary.pop("daily_returns")
            key = f"{name}_{rule}_cost{cost}"
            daily_returns[key] = daily
            results.append({"strategy": name, "rule": rule, "threshold": threshold, "cost_bps_per_side": cost, **summary})
            if cost == 5:
                curve.to_parquet(OUT / f"curve_{name}_{rule}.parquet", index=False)
                for year in (2022, 2023, 2024):
                    year_ret = daily[daily.index.year == year]
                    timings.append({"strategy": name, "rule": rule, "year": year, "return": float((1 + year_ret).prod() - 1)})

metrics = pd.DataFrame(results)
metrics.to_csv(OUT / "metrics.csv", index=False)
pd.DataFrame(details).to_csv(OUT / "forecast_metrics.csv", index=False)
pd.DataFrame(timings).to_csv(OUT / "annual_returns.csv", index=False)
pd.DataFrame(forecasts).to_parquet(OUT / "forecast_returns.parquet", index=False)
daily = pd.DataFrame(daily_returns)
daily.to_csv(OUT / "daily_returns.csv", index_label="day")

# Différences appariées de richesse : resampling par mois entiers.
rng = np.random.default_rng(20261025)
uncertainty = []
for family in ("timesfm3", "chronos_synth", "chronos2"):
    for social in ("finbert", "jev"):
        for rule in ("sign", "margin10bp"):
            for control in (["market", "zero_jev"] if social == "jev" else ["market"]):
                left, right = f"{family}_{social}_{rule}_cost5", f"{family}_{control}_{rule}_cost5"
                if left not in daily or right not in daily:
                    continue
                difference = np.log1p(daily[left]) - np.log1p(daily[right])
                blocks = [g.to_numpy() for _, g in difference.groupby(difference.index.to_period("M"))]
                draws = [np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))]).mean() * 252 for _ in range(3000)]
                low, high = np.quantile(draws, [.025, .975])
                uncertainty.append({"family": family, "social_variant": social, "control": control, "rule": rule, "annualized_log_return_difference": float(difference.mean() * 252), "ci95_low": float(low), "ci95_high": float(high), "months": len(blocks), "resamples": 3000})
pd.DataFrame(uncertainty).to_csv(OUT / "social_uncertainty.csv", index=False)

if (OUT / "kit_pilot.csv").exists():
    kit = pd.read_csv(OUT / "kit_pilot.csv")
    chosen = kit.reference_index.to_numpy(dtype=int)
    pilot_rows = []
    for name, predicted in {**{k: v[chosen] for k, v in forecasts.items()}, "kit_pilot": kit.predicted_return.to_numpy()}.items():
        observed = actual[chosen]
        pilot_rows.append({"strategy": name, "rows": len(chosen), "accuracy": float(((predicted > 0) == (observed > 0)).mean()), "mae_return": float(np.abs(predicted - observed).mean()), "spearman": float(stats.spearmanr(predicted, observed).statistic)})
    pilot_rows.append({"strategy": "always_up", "rows": len(chosen), "accuracy": float((actual[chosen] > 0).mean()), "mae_return": None, "spearman": None})
    pd.DataFrame(pilot_rows).to_csv(OUT / "pilot_matched_comparison.csv", index=False)

baseline_folder = ROOT / "reports" / "backtest_musk_2026-10-25"
baseline = pd.read_csv(baseline_folder / "daily_returns.csv", index_col="day", parse_dates=True)
fig, axes = plt.subplots(2, 1, figsize=(12, 9), sharex=True)
for name in ("chronos_synth_market", "chronos_synth_jev", "timesfm3_market", "timesfm3_jev", "kronos_s1_univariate"):
    for ax, rule in zip(axes, ("sign", "margin10bp")):
        key = f"{name}_{rule}_cost5"
        if key in daily:
            equity = 10000 * (1 + daily[key]).cumprod()
            ax.plot(equity.index, equity, label=name)
for ax, rule in zip(axes, ("sign", "margin10bp")):
    for name, label in (("prices_cost5", "Ancien modèle prix seuls"), ("tsla_buy_hold_cost5", "Tesla conservée")):
        ax.plot(baseline.index, 10000 * (1 + baseline[name]).cumprod(), ls="--", alpha=.65, label=label)
    ax.axhline(10000, color="grey", lw=.8)
    ax.set(title=f"Règle {rule} — 5 pb par côté", ylabel="Capital simulé (USD)")
    ax.legend(fontsize=7, ncol=2)
fig.suptitle("Modèles préentraînés : comparaison rétrospective Tesla 2022–2024")
fig.tight_layout()
fig.savefig(OUT / "equity.png", dpi=150)
plt.close(fig)

models = json.loads((ROOT / "data" / "forecast_models.json").read_text())
for value in models.values():
    value.pop("local_path", None)
repos = {}
for name in ("timesfm", "Kronos", "KiT"):
    repos[name] = subprocess.check_output(["git", "-C", str(ROOT / "data" / "vendor" / name), "rev-parse", "HEAD"], text=True).strip()
import torch
metadata = {"model_revisions": models, "source_revisions": repos, "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu", "torch": torch.__version__, "hip": torch.version.hip, "python": platform.python_version(), "packages": {k: importlib.metadata.version(k) for k in ("timesfm", "chronos-forecasting", "pandas", "numpy", "transformers")}, "reference_predictions_sha256": hashlib.sha256((baseline_folder / "predictions.parquet").read_bytes()).hexdigest(), "code_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / "src" / "foundation_benchmark.py", ROOT / "src" / "backtest.py", Path(__file__)]}, "rows": len(reference), "test_years": [2022, 2023, 2024], "zero_shot": True, "context_regular_bars": 128, "information_delay_seconds": 60, "target": "prix d'ouverture prévus à t et t+15 ; signal construit sans prix d'exécution réel", "rule_sign": "achat si rendement prévu > 0", "rule_margin10bp": "achat si rendement prévu > 0,001 ; seuil fixé sans optimisation", "costs_bps_per_side": [0, 2, 5, 10], "kronos_sample_count": 1, "seed": 20261025, "cross_learning_between_origins": False, "pretraining_warning": "Évaluation rétrospective ; l'historique peut figurer dans le préentraînement. KiT connaît l'instrument TSLA et sa borne d'apprentissage est 2025-12-31.", "main_complete_models": list(forecasts), "kit_scope": "pilote mensuel séparé, non assimilable au backtest complet"}
(OUT / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")
print("Prévisions :")
print(pd.DataFrame(details).to_string(index=False))
print("\nPortefeuilles, coût 5 pb par côté :")
print(metrics[metrics.cost_bps_per_side.eq(5)].to_string(index=False))
