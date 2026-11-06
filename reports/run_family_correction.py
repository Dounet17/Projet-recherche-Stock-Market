"""Calcule les p corrigées sur la famille complète des essais, à partir des journaux.

Deux familles sont publiées : les essais de prix seuls, et tous les essais du laboratoire.
À lancer après run_price_lab.py, run_price_robustness.py et run_social_lab.py.
Depuis la racine : venv/bin/python reports/run_family_correction.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import DEFAULT_COST_BPS, DEV_END, LAB_DIR, backtest, buy_hold_weights, load_panel, romano_wolf, romano_wolf_alpha
from price_lab import MEGACAPS, equal_weight

panel = load_panel()
bases = {}


def base_returns(name, cost_bps):
    """Référence au même coût que l'essai comparé."""
    key = (name, cost_bps)
    if key not in bases:
        if name == "megacap_equal":
            weights = equal_weight(MEGACAPS)(panel)
        elif name.startswith("equal_without_"):
            removed = name.removeprefix("equal_without_")
            weights = equal_weight(tuple(s for s in MEGACAPS if s != removed))(panel)
        else:
            weights = buy_hold_weights(panel, name)
        bases[key] = backtest(weights, panel, cost_bps=cost_bps).returns
    return bases[key]


def load_family(owner):
    ledger = pd.read_csv(LAB_DIR / f"ledger_{owner}.csv")
    returns, references = {}, {}
    for row in ledger.itertuples():
        path = LAB_DIR / "trials" / owner / f"{row.name}.parquet"
        returns[row.name] = pd.read_parquet(path, filters=[("date", "<=", pd.Timestamp(DEV_END))])["return"]
        references[row.name] = base_returns(row.benchmark, float(json.loads(row.params).get("cost_bps", DEFAULT_COST_BPS)))
    return pd.DataFrame(returns), pd.DataFrame(references)


def excess(returns, references):
    return np.log1p(returns) - np.log1p(references)


claude_returns, claude_refs = load_family("claude")
codex_returns, codex_refs = load_family("codex")
claude_excess_p = romano_wolf(excess(claude_returns, claude_refs))
claude_alpha_p = romano_wolf_alpha(claude_returns, claude_refs)
print("Famille prix :", claude_returns.shape[1], "essais", flush=True)

# Préfixes pour éviter toute collision de noms entre les deux journaux.
all_returns = pd.concat([claude_returns.add_prefix("claude:"), codex_returns.add_prefix("codex:")], axis=1)
all_refs = pd.concat([claude_refs.add_prefix("claude:"), codex_refs.add_prefix("codex:")], axis=1)
all_excess_p = romano_wolf(excess(all_returns, all_refs))
all_alpha_p = romano_wolf_alpha(all_returns, all_refs)
print("Famille complète :", all_returns.shape[1], "essais", flush=True)

family = pd.DataFrame({"rw_p_excess_all": all_excess_p, "rw_p_alpha_all": all_alpha_p})
family.index.name = "trial"
family.to_csv(LAB_DIR / "family_pvalues.csv")

results = pd.read_csv(LAB_DIR / "price/results.csv", index_col=0)
results["rw_p_excess"] = claude_excess_p.reindex(results.index)
results["rw_p_alpha"] = claude_alpha_p.reindex(results.index)
results.to_csv(LAB_DIR / "price/results.csv")
robust = pd.read_csv(LAB_DIR / "price/robustness.csv", index_col=0)
robust["rw_p"] = claude_excess_p.reindex("robust_" + robust.index).to_numpy()
robust["rw_p_alpha"] = claude_alpha_p.reindex("robust_" + robust.index).to_numpy()
robust.to_csv(LAB_DIR / "price/robustness.csv")

pd.set_option("display.width", 200, "display.max_rows", 100)
print("\nLes 12 plus faibles p d'excès, famille complète :")
print(family.sort_values("rw_p_excess_all").head(12).round(4).to_string())
print("\nLes 12 plus faibles p d'alpha, famille complète :")
print(family.sort_values("rw_p_alpha_all").head(12).round(4).to_string())
focus = ["claude:robust_mega_top3_lb126", "claude:megacap_top3_mom", "claude:TSLA__market_filter_qqq", "claude:robust_tsla_filter_QQQ_200", "claude:TSLA__vol_target_30", "codex:news_finbert_exit_5__5bps__zero"]
print("\nCandidates :")
print(family.reindex(focus).round(4).to_string())
