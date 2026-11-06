"""Étape 3 : moyenne mobile sur 200 séances, action par action, contre le buy and hold de cette action.

Règle figée avant le premier lancement, une seule variante journalisée : investi si la clôture dépasse
la moyenne des 200 dernières séances (au moins 180 valides), sinon en liquidités à 0 %. Vérifiée chaque
jour. Achats les premiers jours de bourse des mois, de janvier 2018 à fin 2024, avec les mêmes titres
achetables que la table de référence. Le rapport principal porte sur « toutes achetables ».

Depuis la racine : venv/bin/python reports/run_step3_sma200.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
from experiment import adjusted_p_values
from per_stock import Simulator, equal_weight_result, equal_weight_returns, risk_by_stock, rule_table
from reference import month_start_rows
from universe_data import load_universe

NAME = "step3_sma200_by_stock"
OUT = lab.LAB_DIR / "per_stock"
DATA = ROOT / "data" / "per_stock"
TIERS = {"top500": 500, "top1000": 1000, "all": None}


def sma200(data, window=200, min_valid=180):
    average = data.close.rolling(window, min_periods=min_valid).mean()
    return (data.close > average).astype(float).where(average.notna() & data.close.notna())


if __name__ == "__main__":
    for folder in (OUT, DATA):
        folder.mkdir(parents=True, exist_ok=True)
    market = load_universe()
    lab.check_no_lookahead(sma200, market.data)
    print("Contrôle anti-fuite réussi", flush=True)
    signal = sma200(market.data)
    simulator = Simulator(signal, market)
    doubled = Simulator(signal, market, cost_multiplier=2.0)
    bil = market.benchmarks.open["BIL"]
    treasury = Simulator(signal, market, cash_returns=bil.shift(-1) / bil - 1)
    months = month_start_rows(market.data.dates)
    starts = months[market.data.dates[months] >= pd.Timestamp("2018-01-01")]
    horizons = (-1, 12, 36, 60)
    table = rule_table(simulator, starts, horizons)
    reference = pd.read_parquet(ROOT / "data" / "reference" / "buy_hold_by_cohort.parquet")
    merged = table.merge(reference, on=["start", "horizon", "security_id"], how="inner")
    print(f"{len(table):,} lignes règle, {len(merged):,} comparées au buy and hold ; hors table de référence : {len(table) - len(merged):,}", flush=True)
    merged.to_parquet(DATA / f"{NAME}.parquet", index=False)

    rows = []
    for tier, limit in TIERS.items():
        subset = merged if limit is None else merged[merged.liquidity_rank <= limit]
        group = subset.groupby(["start", "horizon"])
        stats = pd.DataFrame({
            "count": group.size(),
            "mean_rule": group.rule_base.mean(), "mean_bh": group.base.mean(),
            "median_rule": group.rule_base.median(), "median_bh": group.base.median(),
            "mean_rule_optimistic": group.rule_optimistic.mean(), "mean_rule_pessimistic": group.rule_pessimistic.mean(),
            "mean_bh_optimistic": group.optimistic.mean(), "mean_bh_pessimistic": group.pessimistic.mean(),
            "share_rule_wins": subset.assign(w=subset.rule_base > subset.base).groupby(["start", "horizon"]).w.mean(),
            "share_rule_loss": subset.assign(w=subset.rule_base < 1).groupby(["start", "horizon"]).w.mean(),
            "share_bh_loss": subset.assign(w=subset.base < 1).groupby(["start", "horizon"]).w.mean(),
            "invested": group.invested_share.mean(), "switches": group.switches.mean(), "years": group.nominal_years.first(),
        }).reset_index()
        stats["tier"] = tier
        rows.append(stats)
    cohorts = pd.concat(rows, ignore_index=True)
    cohorts["mean_rule_annual"] = cohorts.mean_rule ** (1 / cohorts.years) - 1
    cohorts["mean_bh_annual"] = cohorts.mean_bh ** (1 / cohorts.years) - 1
    cohorts["median_rule_annual"] = cohorts.median_rule ** (1 / cohorts.years) - 1
    cohorts["median_bh_annual"] = cohorts.median_bh ** (1 / cohorts.years) - 1
    cohorts["switches_per_year"] = cohorts.switches / cohorts.years
    cohorts.to_csv(OUT / f"{NAME}_cohorts.csv", index=False)
    summary = cohorts[cohorts.horizon != -1].groupby(["tier", "horizon"]).agg(cohorts=("start", "count"), mean_rule_annual=("mean_rule_annual", "mean"), mean_bh_annual=("mean_bh_annual", "mean"), median_rule_annual=("median_rule_annual", "mean"), median_bh_annual=("median_bh_annual", "mean"), share_rule_wins=("share_rule_wins", "mean"), worst_share=("share_rule_wins", "min"), best_share=("share_rule_wins", "max"), cohorts_rule_mean_wins=("mean_rule", lambda x: float("nan")), invested=("invested", "mean"), switches_per_year=("switches_per_year", "mean")).reset_index()
    wins = cohorts[cohorts.horizon != -1].assign(w=lambda f: f.mean_rule > f.mean_bh).groupby(["tier", "horizon"]).w.mean().to_numpy()
    summary["cohorts_rule_mean_wins"] = wins
    summary.to_csv(OUT / f"{NAME}_summary.csv", index=False)

    # Achat de janvier 2018 conservé jusqu'à fin 2024 : portefeuille, risque et frais doublés.
    start = int(starts[0])
    end = len(market.data.dates) - 1
    window = market.data.dates[start:end]
    spy = lab.backtest(lab.buy_hold_weights(market.benchmarks, "SPY"), market.benchmarks, start=window[0], exits=pd.Series(dtype=float))
    fixed = merged[(merged.start == window[0]) & (merged.horizon == -1)].set_index("security_id")
    position = {c: i for i, c in enumerate(simulator.columns)}
    report = {}
    primary = None
    for tier, limit in TIERS.items():
        chosen = fixed if limit is None else fixed[fixed.liquidity_rank <= limit]
        cols = np.array([position[s] for s in chosen.index])
        rule, leaves, held = simulator.paths(start, end, cols)
        hold, _, hold_held = simulator.paths(start, end, cols, always_invested=True)
        rule_x2 = doubled.paths(start, end, cols)[0]
        hold_x2 = doubled.paths(start, end, cols, always_invested=True)[0]
        rule_bil = treasury.paths(start, end, cols)[0]
        np.testing.assert_allclose(hold[-1], chosen.base.to_numpy(), atol=1e-9)
        rule_sharpe, rule_dd = risk_by_stock(rule)
        hold_sharpe, hold_dd = risk_by_stock(hold)
        rule_returns, hold_returns = equal_weight_returns(rule, window), equal_weight_returns(hold, window)
        result = equal_weight_result(rule, held, leaves, window)
        hold_result = equal_weight_result(hold, hold_held, leaves, window)
        report[tier] = {
            "stocks": len(chosen), "rule": lab.summarize(result), "buy_hold": lab.summarize(hold_result), "spy": lab.summarize(spy),
            "vs_own_buy_hold": lab.compare(rule_returns, hold_returns, n_boot=4000), "vs_spy": lab.compare(rule_returns, spy.returns, n_boot=4000),
            "share_rule_wins": float((chosen.rule_base > chosen.base).mean()),
            "share_rule_wins_pessimistic": float((chosen.rule_pessimistic > chosen.pessimistic).mean()),
            "share_rule_wins_cost_x2": float((rule_x2[-1] > hold_x2[-1]).mean()),
            "mean_rule_bil": float(rule_bil[-1].mean()), "median_rule_bil": float(np.median(rule_bil[-1])), "share_rule_wins_bil": float((rule_bil[-1] > hold[-1]).mean()),
            "bil_vs_own_buy_hold": lab.compare(equal_weight_returns(rule_bil, window), hold_returns, n_boot=4000),
            "sharpe_rule_bil": lab.summarize(lab.Result(equal_weight_returns(rule_bil, window), result.weights, result.turnover))["sharpe"],
            "mean_rule_cost_x2": float(rule_x2[-1].mean()), "mean_bh_cost_x2": float(hold_x2[-1].mean()),
            "mean_rule_optimistic": float(chosen.rule_optimistic.mean()), "mean_rule_pessimistic": float(chosen.rule_pessimistic.mean()), "mean_bh_optimistic": float(chosen.optimistic.mean()), "mean_bh_pessimistic": float(chosen.pessimistic.mean()),
            "share_better_sharpe": float((rule_sharpe > hold_sharpe).mean()), "median_sharpe_rule": float(np.median(rule_sharpe)), "median_sharpe_bh": float(np.median(hold_sharpe)),
            "share_smaller_drawdown": float((rule_dd > hold_dd).mean()), "median_drawdown_rule": float(np.median(rule_dd)), "median_drawdown_bh": float(np.median(hold_dd)),
            "median_ratio": float(np.nanmedian(chosen.rule_base / chosen.base.where(chosen.base > 0))),
            "share_rule_beats_spy": float((chosen.rule_base > (1 + spy.returns).prod()).mean()),
        }
        if limit is None:
            primary = (result, rule_returns)
    (OUT / f"{NAME}_january2018.json").write_text(json.dumps(report, indent=1))

    extra = {"unit": "portefeuille à parts égales, achat du 02/01/2018, toutes achetables", "stocks": report["all"]["stocks"], "benchmark_final": report["all"]["spy"]["final_capital"], "own_buy_hold_final": report["all"]["buy_hold"]["final_capital"], "share_rule_wins": report["all"]["share_rule_wins"], "excess_vs_own_buy_hold": report["all"]["vs_own_buy_hold"]["annual_log_excess"], "excess_vs_own_p": report["all"]["vs_own_buy_hold"]["excess_p_one_sided"]}
    lab.record_trial("universe", NAME, "heuristic", {"window": 200, "min_valid": 180, "check": "daily", "mode": "per_stock"}, primary[0], "SPY", spy.returns, extra=extra)

    # Correction des essais multiples : sur tout le journal, contre SPY.
    report["romano_wolf_p_vs_spy_all_trials"] = adjusted_p_values("universe", spy.returns).round(4).to_dict()
    (OUT / f"{NAME}_january2018.json").write_text(json.dumps(report, indent=1))
    print("p corrigées :", report["romano_wolf_p_vs_spy_all_trials"])

    # Par secteur et par date d'achat, sur 5 ans.
    sectors = pd.read_parquet(ROOT / "data" / "reference" / "sectors.parquet")
    five = merged[merged.horizon == 60].merge(sectors[["sector12"]], left_on="security_id", right_index=True)
    by_sector = five.groupby("sector12").agg(lines=("base", "size"), share_rule_wins=("base", lambda x: float("nan")), mean_rule=("rule_base", "mean"), mean_bh=("base", "mean"), median_rule=("rule_base", "median"), median_bh=("base", "median")).reset_index()
    by_sector["share_rule_wins"] = five.assign(w=five.rule_base > five.base).groupby("sector12").w.mean().to_numpy()
    by_sector.to_csv(OUT / f"{NAME}_sectors.csv", index=False)

    pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 200)
    print(summary.round(3).to_string())
    for tier in TIERS:
        r = report[tier]
        print(f"\n{tier} ({r['stocks']} titres), achat 02/01/2018 :")
        for key in ("rule", "buy_hold", "spy"):
            print(f"  {key:9s}", {k: round(r[key][k], 3) for k in ("final_capital", "cagr", "sharpe", "max_drawdown", "exposure", "turnover_per_year")})
        print("  contre son buy and hold", {k: (round(v, 3) if isinstance(v, float) else [round(x, 3) for x in v]) for k, v in r["vs_own_buy_hold"].items()})
        print("  contre SPY", {k: round(r["vs_spy"][k], 3) for k in ("annual_log_excess", "excess_p_one_sided", "sharpe_difference", "beta", "annual_alpha", "alpha_p_one_sided")})
        print("  ", {k: round(v, 3) for k, v in r.items() if isinstance(v, float)})
    print(by_sector.round(3).to_string())
    print(cohorts[(cohorts.tier == "all") & (cohorts.horizon == 12)][["start", "count", "mean_rule", "mean_bh", "share_rule_wins", "invested"]].iloc[::6].round(3).to_string())
