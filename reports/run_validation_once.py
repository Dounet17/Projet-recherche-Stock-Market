"""Validation unique 2025-2026 des quatre stratégies figées.

Refuse de tourner si les empreintes ont changé ou si un résultat existe déjà.
Depuis la racine : venv/bin/python reports/run_validation_once.py
"""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
import price_lab
import social_lab

OUT = lab.LAB_DIR / "validation"
RESULT = OUT / "validation_results.json"
if RESULT.exists():
    raise SystemExit("Validation déjà effectuée : relance refusée")

prereg = json.loads((lab.LAB_DIR / "preregistration_claude.json").read_text(encoding="utf-8"))
addendum = json.loads((lab.LAB_DIR / "preregistration_news_addendum.json").read_text(encoding="utf-8"))
for registration in (prereg, addendum):
    for path, expected in registration["code_sha256"].items():
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != expected:
            raise SystemExit(f"Empreinte différente pour {path} : validation refusée")

HOLDOUT_DATA = ROOT / "data" / "lab_holdout"
panel = lab.load_panel(end=lab.HOLDOUT_END, allow_holdout=True)
START, END = lab.HOLDOUT_START, lab.HOLDOUT_END
ALPHA = prereg["significance_level"]
cash = panel.open["BIL"].shift(-1) / panel.open["BIL"] - 1


def news_weights(p):
    return social_lab.strategy_weights(p, "news_finbert_exit_5", data_dir=HOLDOUT_DATA, cache_path=HOLDOUT_DATA / "news_finbert.parquet", allow_holdout=True)


weights = {
    "megacap_top3_mom": price_lab.momentum_top(price_lab.MEGACAPS, top=3, lookback=126, trend_filter=True)(panel),
    "tsla_filter_qqq_200": price_lab.single_strategy("market_filter_qqq", "TSLA")(panel),
    "tsla_vol_target_30": price_lab.single_strategy("vol_target_30", "TSLA")(panel),
    "news_finbert_exit_5": news_weights(panel),
}
references = {
    "megacap_equal": price_lab.equal_weight(price_lab.MEGACAPS)(panel),
    "TSLA": lab.buy_hold_weights(panel, "TSLA"),
    "QQQ": lab.buy_hold_weights(panel, "QQQ"),
    "SPY": lab.buy_hold_weights(panel, "SPY"),
}
primary = {"megacap_top3_mom": ("megacap_equal", "excess_p_one_sided"), "tsla_filter_qqq_200": ("TSLA", "excess_p_one_sided"), "tsla_vol_target_30": ("TSLA", "sharpe_diff_p_one_sided"), "news_finbert_exit_5": ("TSLA", "excess_p_one_sided")}


def run(w, cost, cash_returns=None):
    return lab.backtest(w, panel, start=START, end=END, cost_bps=cost, cash_returns=cash_returns)


base = {(name, cost): run(w, cost) for name, w in references.items() for cost in (5, 10)}
report = {"window": [START, END], "days": len(base[("TSLA", 5)].returns), "references": {name: {str(cost): lab.summarize(base[(name, cost)]) for cost in (5, 10)} for name in references}, "strategies": {}}

raw_p = {}
for name, w in weights.items():
    ref_name, test = primary[name]
    entry = {"primary_reference": ref_name, "primary_test": test, "costs": {}}
    for cost in (5, 10):
        result = run(w, cost)
        stats = lab.summarize(result)
        comparison = lab.compare(result.returns, base[(ref_name, cost)].returns, n_boot=4000, mean_block=21, seed=0)
        entry["costs"][str(cost)] = {**stats, **comparison}
    entry["with_bil_cash_5bps"] = lab.summarize(run(w, 5, cash))["final_capital"]
    entry["secondary_vs"] = {other: lab.compare(run(w, 5).returns, base[(other, 5)].returns, n_boot=4000, mean_block=21, seed=0) for other in ("QQQ", "SPY")}
    raw_p[name] = entry["costs"]["5"][test]
    report["strategies"][name] = entry

# Correction de Holm sur les quatre hypothèses déclarées.
ordered = sorted(raw_p, key=raw_p.get)
holm, running = {}, 0.0
for rank, name in enumerate(ordered):
    running = max(running, min(1.0, (len(ordered) - rank) * raw_p[name]))
    holm[name] = running

for name, entry in report["strategies"].items():
    ref_name = entry["primary_reference"]
    checks = []
    for cost in ("5", "10"):
        s, r = entry["costs"][cost], report["references"][ref_name][cost]
        if name == "tsla_vol_target_30":
            checks.append(s["sharpe"] > r["sharpe"] and s["annual_alpha"] > 0 and s["max_drawdown"] > r["max_drawdown"])
        else:
            checks.append(s["final_capital"] > r["final_capital"] and s["sharpe"] > r["sharpe"])
    entry["raw_p"], entry["holm_p"] = raw_p[name], holm[name]
    entry["economic_success"] = bool(all(checks))
    entry["statistical_proof"] = bool(holm[name] < ALPHA)

# Résultat secondaire et descriptif : tests d'un an, un départ par mois.
starts = pd.date_range("2025-01-01", "2025-10-01", freq="MS")
spans = [(s, s + pd.DateOffset(years=1) - pd.Timedelta(days=1)) for s in starts]
rolling = {}
for name, w in weights.items():
    reference = references[primary[name][0]]
    caps = np.array([lab.window_final_capital(w, panel, s, e) for s, e in spans])
    refs = np.array([lab.window_final_capital(reference, panel, s, e) for s, e in spans])
    rolling[name] = {"tests": len(spans), "share_beats_reference": float((caps > refs).mean()), "median_final": float(np.median(caps)), "reference_median_final": float(np.median(refs)), "worst_final": float(caps.min()), "reference_worst_final": float(refs.min())}
report["rolling_1y_monthly_descriptive"] = rolling

series = {name: run(w, 5).returns for name, w in weights.items()}
series.update({f"bh_{name}": base[(name, 5)].returns for name in references})
frame = pd.DataFrame(series)
OUT.mkdir(parents=True, exist_ok=True)
frame.to_csv(OUT / "daily_returns.csv")
RESULT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

print(json.dumps({k: v for k, v in report.items() if k in ("window", "days")}))
for name in references:
    r = report["references"][name]
    print(f"{name}: 5pb {r['5']['final_capital']:.0f} Sharpe {r['5']['sharpe']:.3f} DD {r['5']['max_drawdown']:.3f} | 10pb {r['10']['final_capital']:.0f}")
for name, e in report["strategies"].items():
    a, b = e["costs"]["5"], e["costs"]["10"]
    print(f"\n{name} (réf {e['primary_reference']}, test {e['primary_test']})")
    print(f"  5pb capital {a['final_capital']:.0f} Sharpe {a['sharpe']:.3f} DD {a['max_drawdown']:.3f} beta {a['beta']:.3f} alpha {a['annual_alpha']:.3f} expo {a['exposure']:.2f} turn/an {a['turnover_per_year']:.1f}")
    print(f"  10pb capital {b['final_capital']:.0f} Sharpe {b['sharpe']:.3f} | BIL 5pb {e['with_bil_cash_5bps']:.0f}")
    print(f"  excès {a['annual_log_excess']:.3f} IC {np.round(a['excess_ci95'], 3).tolist()} | diff Sharpe {a['sharpe_difference']:.3f} IC {np.round(a['sharpe_diff_ci95'], 3).tolist()}")
    print(f"  p brute {e['raw_p']:.4f} p Holm {e['holm_p']:.4f} | économique {e['economic_success']} | statistique {e['statistical_proof']}")
    print(f"  contre QQQ capital écart {e['secondary_vs']['QQQ']['annual_log_excess']:.3f} | contre SPY {e['secondary_vs']['SPY']['annual_log_excess']:.3f}")
    print("  glissant 1 an :", {k: round(v, 2) for k, v in rolling[name].items()})
