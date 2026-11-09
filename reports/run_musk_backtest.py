"""Lance le backtest Musk/TSLA sur les caches, sans réseau ni service payant.

Depuis la racine : venv/bin/python reports/run_musk_backtest.py
"""

import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from backtest import (DELAY_SECONDS, HOLD_MINUTES, INITIAL_CAPITAL, TEST_YEARS,
                      build_grid, event_rule, load_posts, simulate, summarize,
                      walk_forward)

OUT = ROOT / "reports" / "backtest_musk_2026-10-25"
OUT.mkdir(parents=True, exist_ok=True)
DATA = ROOT / "data"
calendar = pd.read_parquet(DATA / "calendar.parquet")
bars = {s: pd.read_parquet(DATA / f"{s}_1min.parquet").set_index("ts_utc").sort_index() for s in ("tsla", "qqq")}
posts = load_posts(DATA)
grid, price_columns, quality = build_grid(calendar, bars, posts)
pred, folds, coefficients = walk_forward(grid, price_columns)
days = pd.DatetimeIndex(calendar.loc[calendar.date.dt.year.isin(TEST_YEARS), "date"])
pred.to_parquet(OUT / "predictions.parquet", index=False)
folds.to_csv(OUT / "folds.csv", index=False)
coefficients.to_csv(OUT / "coefficients.csv", index=False)

metrics, daily_series, annual_rows = [], {}, []
for cost in (0, 2, 5, 10):
    for name in ("cash", "intraday_always_long", "prices", "prices_activity", "prices_finbert", "prices_jev"):
        if name == "cash":
            positions = np.zeros(len(pred), dtype=int)
        elif name == "intraday_always_long":
            positions = np.ones(len(pred), dtype=int)
        else:
            positions = pred[f"position_{name}"].to_numpy()
        curve = simulate(pred, positions, cost)
        summary = summarize(curve, days)
        daily = summary.pop("daily_returns")
        daily_series[f"{name}_cost{cost}"] = daily
        metrics.append({"strategy": name, "cost_bps_per_side": cost, **summary})
        if cost == 5:
            curve.to_parquet(OUT / f"curve_{name}.parquet", index=False)
            for year in TEST_YEARS:
                year_curve = curve[curve.entry_ts.dt.year == year]
                year_days = days[days.year == year]
                # Les facteurs sont indépendants du capital initial et se recomposent.
                year_curve = year_curve.copy()
                year_curve["equity"] = INITIAL_CAPITAL * year_curve.factor.cumprod()
                row = summarize(year_curve, year_days)
                row.pop("daily_returns")
                annual_rows.append({"strategy": name, "year": year, **row})

# Placement passif Tesla : garde aussi les nuits et les périodes hors grille.
passive_entry = days[0].tz_localize("America/New_York").replace(hour=9, minute=30).tz_convert("UTC")
passive_price = bars["tsla"].at[passive_entry, "open"]
passive_close_times = pd.DatetimeIndex(calendar.set_index("date").loc[days, "close"]).tz_localize("America/New_York").tz_convert("UTC") - pd.Timedelta(minutes=1)
passive_closes = bars["tsla"].close.reindex(passive_close_times)
if passive_closes.isna().any():
    raise ValueError("Clôture manquante pour la référence passive")
for cost in (0, 2, 5, 10):
    c = cost / 10000
    equity = INITIAL_CAPITAL / (1 + c) / passive_price * passive_closes.to_numpy()
    equity[-1] *= 1 - c
    daily = pd.Series(equity, index=days).pct_change()
    daily.iloc[0] = equity[0] / INITIAL_CAPITAL - 1
    full = np.r_[INITIAL_CAPITAL, equity]
    final = float(equity[-1])
    metrics.append({"strategy": "tsla_buy_hold", "cost_bps_per_side": cost, "final_capital": final, "total_return": final / INITIAL_CAPITAL - 1, "annualized_return": (final / INITIAL_CAPITAL) ** (252 / len(days)) - 1, "max_drawdown_grid": float((full / np.maximum.accumulate(full) - 1).min()), "sharpe_daily_rf0": float(np.sqrt(252) * daily.mean() / daily.std()), "round_trips": 1, "invested_interval_fraction": 1.0})
    daily_series[f"tsla_buy_hold_cost{cost}"] = daily

# Sensibilité descriptive : règle sociale fixe, sans entraînement ni ventes à découvert.
event_metrics, event_quality = [], {}
for horizon in (1, 5, 15, 60):
    ev, checks = event_rule(posts, bars["tsla"], calendar, horizon=horizon)
    ev.to_parquet(OUT / f"event_entries_{horizon}m.parquet", index=False)
    event_quality[horizon] = checks
    for cost in (0, 2, 5, 10):
        curve = simulate(ev, np.ones(len(ev), dtype=int), cost)
        summary = summarize(curve, days)
        summary.pop("daily_returns")
        event_metrics.append({"hold_minutes": horizon, "cost_bps_per_side": cost, "event_intervals": len(ev), **summary})

metrics = pd.DataFrame(metrics)
metrics.to_csv(OUT / "metrics.csv", index=False)
pd.DataFrame(annual_rows).to_csv(OUT / "annual_metrics.csv", index=False)
pd.DataFrame(event_metrics).to_csv(OUT / "event_metrics.csv", index=False)
daily_frame = pd.DataFrame(daily_series)
daily_frame.index.name = "day"
daily_frame.to_csv(OUT / "daily_returns.csv")

# Incertitude sur la différence appariée : bootstrap de mois entiers, non de trades.
rng = np.random.default_rng(0)
base = np.log1p(daily_frame.prices_cost5)
bootstrap = {}
for model in ("prices_finbert", "prices_jev"):
    diff = np.log1p(daily_frame[f"{model}_cost5"]) - base
    blocks = [g.to_numpy() for _, g in diff.groupby(diff.index.to_period("M"))]
    draws = []
    for _ in range(3000):
        sample = np.concatenate([blocks[i] for i in rng.integers(0, len(blocks), len(blocks))])
        draws.append(float(sample.mean() * 252))
    bootstrap[model] = {"annualized_paired_log_return_difference": float(diff.mean() * 252), "ci95_month_block_bootstrap": np.quantile(draws, [.025, .975]).tolist(), "resamples": 3000, "months": len(blocks)}

manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [DATA / f"{name}.parquet" for name in ("calendar", "tsla_1min", "qqq_1min", "musk_posts", "finbert_musk_tesla", "jev_musk_tesla")]}
metadata = {"initial_capital": INITIAL_CAPITAL, "accounting_currency": "USD; equivalent unités EUR uniquement si taux de change constant", "train_initial_years": [2018, 2021], "test_years": TEST_YEARS, "hold_minutes": HOLD_MINUTES, "information_delay_seconds": DELAY_SECONDS, "signal_threshold": .5, "costs_bps_per_side": [0, 2, 5, 10], "training": "Expanding window, refit each January, fixed logistic C=1, no tuning", "grid_quality": quality, "event_quality": event_quality, "paired_uncertainty": bootstrap, "data_sha256": manifest, "versions": {"python": sys.version.split()[0], "pandas": pd.__version__, "numpy": np.__version__, "sklearn": sklearn.__version__}, "limitations": ["Période historique déjà explorée ; évaluation rétrospective et non test final vierge", "Entraînement des classifieurs de texte potentiellement postérieur aux événements", "Cours de transaction par minute, pas cotations bid/ask ni exécutions garanties", "Les intervalles sans prix d'entrée ou de sortie exact sont exclus", "Drawdown à la grille pour les stratégies, quotidien pour le placement passif", "Intérêts du cash, fiscalité, EUR/USD, impact de marché non modélisés", "Pas de données Trump utilisées"]}
(OUT / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n")

labels = {"prices": "Prix seuls", "prices_finbert": "Prix + FinBERT", "prices_jev": "Prix + Jev", "tsla_buy_hold": "Tesla conservée", "intraday_always_long": "Tesla en séance (grille)"}
fig, axes = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
for name, label in labels.items():
    equity = INITIAL_CAPITAL * (1 + daily_frame[f"{name}_cost5"]).cumprod()
    axes[0].plot(equity.index, equity, label=label)
    if name in ("prices", "prices_finbert", "prices_jev"):
        axes[1].plot(equity.index, equity / np.maximum.accumulate(np.r_[INITIAL_CAPITAL, equity])[1:] - 1, label=label)
axes[0].axhline(INITIAL_CAPITAL, color="grey", lw=.8)
axes[0].set(ylabel="Capital simulé (USD)", title="Musk / Tesla : évaluation chronologique 2022–2024, coût 5 pb par côté")
axes[0].legend()
axes[1].set(ylabel="Perte depuis le sommet", xlabel="Date")
axes[1].legend()
fig.tight_layout()
fig.savefig(OUT / "equity.png", dpi=150)
plt.close(fig)
print(metrics[metrics.cost_bps_per_side.eq(5)].to_string(index=False))
print("\nRègle Jev après les posts, coût 5 pb par côté :")
print(pd.DataFrame(event_metrics).query("cost_bps_per_side == 5").to_string(index=False))
print("\nIncertitude appariée :", json.dumps(bootstrap, ensure_ascii=False))
print("\nRésultats :", OUT)
