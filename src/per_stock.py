"""Applique une règle à chaque action et la compare au buy and hold de cette même action.

Une règle reçoit `data` et renvoie, par date et par titre, 1 pour être investi, 0 pour être en
liquidités, NaN pour ne rien changer. Chaque action forme son propre petit portefeuille, sans argent
partagé, selon les règles de `lab.backtest` : décision à la clôture, exécution à l'ouverture suivante
si elle est possible, frais selon la liquidité, sortie à la disparition du titre.

La moyenne des capitaux finaux est le résultat d'un portefeuille qui répartit l'argent à parts égales
au départ, sans jamais le déplacer d'une action à l'autre.
"""

import json

import numpy as np
import pandas as pd

import lab
from experiment import adjusted_p_values
from reference import month_start_rows


class Simulator:
    """Calculs communs à toutes les dates d'achat d'une même règle."""

    def __init__(self, signal, market, cost_multiplier=1.0, cash_returns=None):
        data = market.data
        self.columns = data.close.columns
        self.dates = data.dates
        self.signal = signal.reindex(index=self.dates, columns=self.columns).to_numpy(dtype=float)
        opens, closes = data.open.to_numpy(), data.close.to_numpy()
        marks = data.open.ffill().to_numpy()
        self.valid_open = np.isfinite(opens)
        self.marks, self.closes = marks, closes
        self.costs = data.cost_bps.to_numpy() / 10_000 * cost_multiplier
        self.last_row = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
        self.exits = market.exits.reindex(self.columns)
        # Position pendant la période t : l'ordre de la veille s'il est exécutable, sinon celle d'avant.
        wanted = np.full(self.signal.shape, np.nan)
        wanted[1:] = np.where(self.valid_open[1:], self.signal[:-1], np.nan)
        self.position = pd.DataFrame(wanted).ffill().fillna(0.0).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            growth = marks[1:] / marks[:-1]
        self.growth = np.where(np.isfinite(growth), growth, 1.0)
        # Rendement des liquidités sur la période t. Par défaut 0 %, comme dans le protocole.
        cash = np.zeros(len(self.dates)) if cash_returns is None else cash_returns.reindex(self.dates).fillna(0.0).to_numpy()
        self.cash = cash[:-1][:, None]

    def eligible(self, start):
        """Peut-on comparer la règle et le buy and hold pour cet achat ? Signal connu et ouverture valide."""
        return np.isfinite(self.signal[start - 1]) & self.valid_open[start]

    def paths(self, start, end, cols, scenario="base", always_invested=False):
        """Capital de chaque titre après chaque période de [start, end[ ; lignes = périodes, base 1.

        La dernière ligne inclut la vente finale à l'ouverture de `end`.
        """
        rows = np.arange(start, end)
        held = np.ones((len(rows), len(cols))) if always_invested else self.position[start:end][:, cols].copy()
        previous = np.vstack([np.zeros(len(cols)), held[:-1]])
        costs = self.costs[start:end][:, cols]
        cash = self.cash[start:end]
        factors = (held * self.growth[start:end][:, cols] + (1 - held) * (1 + cash)) * (1 - costs * np.abs(held - previous))
        exit_values = self.exits[scenario].to_numpy()[cols]
        last = self.last_row[cols]
        leaves = np.isfinite(exit_values) & (last < end)
        for j in np.flatnonzero(leaves):
            row = last[j] - start
            column = cols[j]
            final = self.closes[last[j], column] / self.marks[last[j], column] * (1 + exit_values[j])
            factors[row, j] = (final if held[row, j] else 1 + cash[row, 0]) * (1 - costs[row, j] * abs(held[row, j] - previous[row, j]))
            factors[row + 1:, j] = 1 + cash[row + 1:, 0]
            held[row + 1:, j] = 0.0   # après la sortie, l'argent est en liquidités
        wealth = np.cumprod(factors, axis=0)
        wealth[-1] *= np.where(leaves, 1.0, 1 - self.costs[end, cols] * held[-1])
        return wealth, leaves, held


def rule_table(simulator, starts, horizons):
    """Multiple de la règle par titre, date d'achat et horizon, sous les trois hypothèses de sortie."""
    months = month_start_rows(simulator.dates)
    periods = simulator.dates.to_period("M")
    frames = []
    for start in starts:
        cols = np.flatnonzero(simulator.eligible(start))
        if not len(cols):
            continue
        for horizon in horizons:
            if horizon == -1:
                end = len(simulator.dates) - 1
            else:
                later = months[periods[months] == periods[start] + horizon]
                if not len(later):
                    continue
                end = later[0]
            wealth, _, held = simulator.paths(start, end, cols)
            frame = {"start": simulator.dates[start], "horizon": horizon, "security_id": np.asarray(simulator.columns)[cols], "rule_base": wealth[-1], "invested_share": held.mean(axis=0), "switches": np.abs(np.diff(held, axis=0)).sum(axis=0)}
            for scenario in ("optimistic", "pessimistic"):
                frame[f"rule_{scenario}"] = simulator.paths(start, end, cols, scenario)[0][-1]
            frames.append(pd.DataFrame(frame))
    return pd.concat(frames, ignore_index=True)


def risk_by_stock(wealth):
    """Sharpe et pire chute de chaque titre, à partir de ses chemins de capital."""
    full = np.vstack([np.ones(wealth.shape[1]), wealth])
    with np.errstate(divide="ignore", invalid="ignore"):
        returns = full[1:] / full[:-1] - 1
        returns = np.where(np.isfinite(returns), returns, 0.0)
        std = returns.std(axis=0, ddof=1)
        sharpe = np.where(std > 1e-12, returns.mean(axis=0) / std * np.sqrt(lab.TRADING_DAYS), 0.0)
    drawdown = (full / np.maximum.accumulate(full, axis=0) - 1).min(axis=0)
    return sharpe, drawdown


def equal_weight_result(wealth, held, leaves, dates):
    """Résultat du portefeuille à parts égales, exposition et rotation pondérées en dollars.

    Une sortie n'est pas une vente : elle ne compte pas dans la rotation. Après la période finale, ce
    qui est encore en position est vendu à la dernière ouverture.
    """
    before = np.vstack([np.ones(wealth.shape[1]), wealth[:-1]])
    total = before.sum(axis=1)
    exposure = (before * held).sum(axis=1) / total
    previous = np.vstack([np.zeros(held.shape[1]), held[:-1]])
    # La ligne qui suit une sortie remet held à 0 sans transaction.
    gone = (held == 0) & (previous == 1) & (np.cumsum(held[::-1], axis=0)[::-1] == 0) & leaves[None, :]
    turnover = (before * np.abs(held - previous) * ~gone).sum(axis=1) / total
    turnover[-1] += (wealth[-1] * held[-1] * ~leaves).sum() / wealth[-1].sum()
    return lab.Result(equal_weight_returns(wealth, dates), pd.DataFrame({"exposure": exposure}, index=dates), pd.Series(turnover, index=dates, name="turnover"))


def equal_weight_returns(wealth, dates):
    """Rendement quotidien du portefeuille à parts égales au départ, jamais rééquilibré."""
    level = np.r_[1.0, wealth.mean(axis=1)]
    return pd.Series(level[1:] / level[:-1] - 1, index=dates, name="return")


def _excess_sharpe(returns, risk_free):
    excess = returns - risk_free
    return float(excess.mean() / excess.std(ddof=1) * np.sqrt(lab.TRADING_DAYS))


OUT = lab.LAB_DIR / "per_stock"
DATA = lab.ROOT / "data" / "per_stock"
TIERS = {"top500": 500, "top1000": 1000, "all": None}


def evaluate_rule(rule, market, name, params, family="heuristic"):
    """Compare une règle au buy and hold de chaque action et l'inscrit au journal, réussie ou non.

    Écrit tous les détails dans `reports/lab_2026-11/per_stock/` et renvoie le bilan de l'achat de
    janvier 2018 et le résumé par horizon.
    """
    NAME = name
    for folder in (OUT, DATA):
        folder.mkdir(parents=True, exist_ok=True)
    lab.check_no_lookahead(rule, market.data)
    print("Contrôle anti-fuite réussi", flush=True)
    signal = rule(market.data)
    simulator = Simulator(signal, market)
    doubled = Simulator(signal, market, cost_multiplier=2.0)
    bil = market.benchmarks.open["BIL"]
    risk_free = bil.shift(-1) / bil - 1
    treasury = Simulator(signal, market, cash_returns=risk_free)
    months = month_start_rows(market.data.dates)
    starts = months[market.data.dates[months] >= pd.Timestamp("2018-01-01")]
    horizons = (-1, 12, 36, 60)
    table = rule_table(simulator, starts, horizons)
    reference = pd.read_parquet(lab.ROOT / "data" / "reference" / "buy_hold_by_cohort.parquet")
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
            # Au-delà du taux sans risque : sinon, l'intérêt des bons passerait pour un Sharpe et un alpha.
            "bil_vs_own_buy_hold": lab.compare(equal_weight_returns(rule_bil, window) - risk_free.reindex(window), hold_returns - risk_free.reindex(window), n_boot=4000),
            "excess_sharpe_rule_bil": _excess_sharpe(equal_weight_returns(rule_bil, window), risk_free.reindex(window)),
            "excess_sharpe_buy_hold": _excess_sharpe(hold_returns, risk_free.reindex(window)),
            "excess_sharpe_rule_cash0": _excess_sharpe(rule_returns, risk_free.reindex(window)),
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
    lab.record_trial("universe", NAME, family, params, primary[0], "SPY", spy.returns, extra=extra)

    # Correction des essais multiples : sur tout le journal, contre SPY.
    report["romano_wolf_p_vs_spy_all_trials"] = adjusted_p_values("universe", spy.returns).round(4).to_dict()
    (OUT / f"{NAME}_january2018.json").write_text(json.dumps(report, indent=1))
    print("p corrigées :", report["romano_wolf_p_vs_spy_all_trials"])

    # Par secteur et par date d'achat, sur 5 ans.
    sectors = pd.read_parquet(lab.ROOT / "data" / "reference" / "sectors.parquet")
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
    return report, summary
