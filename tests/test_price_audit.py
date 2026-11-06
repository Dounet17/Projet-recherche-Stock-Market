"""Audit croisé : les tests rouges reproduisent les défauts sans modifier la piste prix."""

import ast
from functools import lru_cache
import json
import re
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
import price_lab as price


def make_panel(periods=7):
    dates = pd.bdate_range("2020-01-02", periods=periods)
    frame = pd.DataFrame({"A": 100 * 1.1 ** np.maximum(np.arange(periods) - 1, 0),
                          "B": 100.0}, index=dates)
    return lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)


def source_ast(name):
    return ast.parse((ROOT / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def preregistration():
    return json.loads((lab.LAB_DIR / "preregistration_claude.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def development_evidence():
    """Réutilise seulement les essais déjà exécutés, sans lancer de nouvelle recherche."""
    panel = lab.load_panel(end=lab.DEV_END)
    ledger = pd.read_csv(lab.LAB_DIR / "ledger_claude.csv")
    main = pd.read_csv(lab.LAB_DIR / "price/results.csv").set_index("name")
    robustness = pd.read_csv(lab.LAB_DIR / "price/robustness.csv").set_index("name")
    bases = {}
    excess = {}
    returns = {}
    for row in ledger.itertuples():
        if row.benchmark not in bases:
            if row.benchmark == "megacap_equal":
                weights = price.equal_weight(price.MEGACAPS)(panel)
            elif row.benchmark.startswith("equal_without_"):
                removed = row.benchmark.removeprefix("equal_without_")
                weights = price.equal_weight(tuple(s for s in price.MEGACAPS if s != removed))(panel)
            else:
                weights = lab.buy_hold_weights(panel, row.benchmark)
            bases[row.benchmark] = lab.backtest(weights, panel).returns
        path = lab.LAB_DIR / "trials/claude" / f"{row.name}.parquet"
        series = pd.read_parquet(path, filters=[("date", "<=", pd.Timestamp(lab.DEV_END))])["return"]
        returns[row.name] = series
        excess[row.name] = np.log1p(series) - np.log1p(bases[row.benchmark])
    corrected = lab.romano_wolf(pd.DataFrame(excess), n_boot=4000, mean_block=21, seed=0)
    return panel, ledger, main, robustness, bases, returns, corrected


class ConfirmedPriceBugs(unittest.TestCase):
    def test_monthly_hold_must_not_rebalance_inside_the_month(self):
        panel = make_panel()
        weights = price.equal_weight(("A", "B"))(panel)
        result = lab.backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=0)
        # Entrée et liquidation exclues : aucune nouvelle décision mensuelle n'existe ici.
        self.assertAlmostEqual(float(result.turnover.iloc[1:-1].sum()), 0.0)

    def test_band_must_prevent_small_trades_caused_by_drift(self):
        panel = make_panel()
        raw = pd.Series(0.5, index=panel.dates)
        weights = price.single_asset(panel, "A", price._with_band(raw, band=0.10))
        result = lab.backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=0)
        # Le poids dérive d'environ 2.4 points, donc reste dans la bande de 10 points.
        self.assertAlmostEqual(float(result.turnover.iloc[1:-1].sum()), 0.0)

    def test_rsi_without_losses_is_one_hundred(self):
        close = pd.Series(np.arange(1.0, 12.0))
        self.assertEqual(price.rsi(close, 2).iloc[-1], 100.0)

    def test_alpha_correction_refits_beta_in_each_bootstrap_sample(self):
        rng = np.random.default_rng(5)
        benchmark = pd.Series(rng.normal(0.01, 0.01, 120))
        strategy = 0.0003 + 0.7 * benchmark + rng.normal(0, 0.005, 120)
        comparison = lab.compare(strategy, benchmark, n_boot=199, mean_block=7, seed=9)
        # Le script ne calcule plus de résidu à bêta fixe : la correction passe par le moteur.
        assignments = [node for node in ast.walk(source_ast("reports/run_price_lab.py"))
                       if isinstance(node, ast.Assign) and any(
                           isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name)
                           and target.value.id == "alpha" for target in node.targets)]
        self.assertEqual(len(assignments), 0)
        actual = lab.romano_wolf_alpha(strategy.to_frame("candidate"), benchmark.to_frame("candidate"), n_boot=199, mean_block=7, seed=9).iloc[0]
        self.assertAlmostEqual(actual, comparison["alpha_p_one_sided"], places=12)

    def test_multiple_testing_family_includes_initial_and_robustness_trials(self):
        _, ledger, _, robust, _, _, corrected = development_evidence()
        self.assertEqual(len(ledger), len(corrected))
        name = "mega_top3_lb126"
        self.assertAlmostEqual(robust.loc[name, "rw_p"], corrected["robust_" + name], places=12)

    def test_preregistered_calls_are_standalone_python_expressions(self):
        for entry in preregistration()["strategies"]:
            with self.subTest(strategy=entry["name"]):
                try:
                    expression = ast.parse(entry["call"], mode="eval")
                except SyntaxError as exc:
                    self.fail(f"Appel figé inexécutable : {entry['call']} ({exc.msg})")
                factory = eval(compile(expression, "preregistered_call", "eval"),
                               {"__builtins__": {}, "price_lab": price, "MEGACAPS": price.MEGACAPS})
                self.assertTrue(callable(factory))

    def test_risk_success_requires_positive_alpha_as_in_protocol(self):
        risk = next(item for item in preregistration()["strategies"] if item["name"] == "tsla_vol_target_30")
        self.assertIn("alpha", risk["success"].lower(),
                      "Le critère gagner mieux du protocole impose Sharpe supérieur ET alpha positif")

    def test_preregistered_statistical_rule_has_an_explicit_significance_level(self):
        registration = preregistration()
        level = registration.get("significance_level")
        if isinstance(level, (float, int)):
            self.assertTrue(0 < level < 1)
        else:
            self.assertIsNotNone(re.search(r"(?:0[.,]\d+|\d+\s*%)", registration["statistics"]),
                                 "Le seuil de décision statistique doit être fixé avant la validation")


class SecondAuditRegressions(unittest.TestCase):
    def test_band_ignores_price_moves_before_execution(self):
        # Ordre 50 % à la clôture 100, exécuté à 200 : le poids détenu reste 50 % le lendemain.
        dates = pd.bdate_range("2020-01-02", periods=6)
        close = pd.Series([100, 200, 200, 200, 200, 200], index=dates, dtype=float)
        target = pd.Series([0.50, 0.65, 0.65, 0.65, 0.65, 0.65], index=dates)
        orders = price._with_band(target, band=0.10, close=close, open_=close)
        self.assertEqual(orders.iloc[0], 0.50)
        self.assertEqual(orders.iloc[1], 0.65)
        self.assertTrue(orders.iloc[2:].isna().all())

    def test_band_signal_matches_engine_positions(self):
        rng = np.random.default_rng(3)
        dates = pd.bdate_range("2020-01-02", periods=400)
        close = pd.Series(100 * np.exp(rng.normal(0, 0.03, 400).cumsum()), index=dates)
        open_ = close.shift(1).fillna(100) * np.exp(rng.normal(0, 0.02, 400))
        frame_o, frame_c = open_.to_frame("A"), close.to_frame("A")
        panel = lab.Panel(frame_o, frame_c, frame_c, frame_c, frame_c * 0 + 1000)
        target = (0.3 / price.realized_vol(close)).clip(upper=1.0)
        orders = price._with_band(target, close=close, open_=open_)
        weights = price.single_asset(panel, "A", orders)
        result = lab.backtest(weights, panel, start=dates[0], end=dates[-1], cost_bps=0)
        # Poids à l'ouverture après ordre, valorisé à la clôture : comparable au signal du moteur.
        held = result.weights["A"] * (close / open_) / (result.weights["A"] * (close / open_) + 1 - result.weights["A"])
        gaps = (target - held).abs()
        inside = orders.shift(0).isna() & target.notna()
        self.assertLess(float(gaps[inside].iloc[:-1].max()), 0.10 + 1e-9)

    def test_constant_positive_alpha_is_significant(self):
        rng = np.random.default_rng(1)
        benchmark = pd.Series(rng.normal(0.001, 0.02, 300))
        strategy = 0.5 * benchmark + 0.001
        self.assertEqual(lab.romano_wolf_alpha(strategy.to_frame("s"), benchmark.to_frame("s"), n_boot=199).iloc[0], 0.0)

    def test_window_does_not_use_prices_after_its_end(self):
        dates = pd.bdate_range("2020-01-02", periods=6)
        frame = pd.DataFrame({"A": [100, 100, 100, 100, 200, 200]}, index=dates, dtype=float)
        panel = lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)
        capital = lab.window_final_capital(lab.buy_hold_weights(panel, "A"), panel, dates[1], dates[3], cost_bps=0)
        self.assertAlmostEqual(capital, 10_000.0)

    def test_family_reference_uses_the_trial_cost(self):
        source = (ROOT / "reports/run_family_correction.py").read_text(encoding="utf-8")
        self.assertIn('json.loads(row.params).get("cost_bps"', source)
        self.assertIn("cost_bps=cost_bps", source)


class VerifiedPriceProperties(unittest.TestCase):
    def test_monthly_decisions_do_not_use_the_rest_of_the_month(self):
        dates = pd.bdate_range("2020-01-02", periods=70)
        frame = pd.DataFrame({"A": np.arange(len(dates), dtype=float)}, index=dates)
        full = price.monthly_hold(frame)
        partial = price.monthly_hold(frame.iloc[:37])
        pd.testing.assert_frame_equal(full.iloc[:37], partial)

    def test_state_machine_is_causal_and_entry_wins_a_tie(self):
        dates = pd.bdate_range("2020-01-02", periods=4)
        enter = pd.Series([False, True, False, True], index=dates)
        leave = pd.Series([False, False, True, True], index=dates)
        expected = pd.Series([0.0, 1.0, 0.0, 1.0], index=dates)
        pd.testing.assert_series_equal(price._state_machine(enter, leave), expected)
        pd.testing.assert_series_equal(price._state_machine(enter, leave).iloc[:3],
                                       price._state_machine(enter.iloc[:3], leave.iloc[:3]))

    def test_momentum_does_not_replace_filtered_ranks_with_lower_ranks(self):
        dates = pd.bdate_range(end="2021-03-01", periods=300)
        # A est la plus forte sur 5 jours mais reste sous sa moyenne longue.
        a = np.r_[np.full(290, 200.0), np.arange(10.0, 20.0)]
        b = np.arange(100.0, 400.0)
        frame = pd.DataFrame({"A": a, "B": b}, index=dates)
        panel = lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)
        raw = price.momentum_top(("A", "B"), top=1, lookback=5, trend_filter=True)(panel)
        # La règle classe avant le filtre : c'est sa définition, pas un défaut de causalité.
        self.assertEqual(raw.iloc[-1].sum(), 0.0)
        self.assertTrue(lab.check_no_lookahead(
            price.momentum_top(("A", "B"), top=1, lookback=5, trend_filter=True), panel))
        self.assertTrue((raw.sum(axis=1) <= 1).all())

    def test_ml_purge_keeps_all_training_targets_before_annual_boundary(self):
        dates = pd.bdate_range("2016-01-04", periods=900)
        values = 100 * np.exp(np.sin(np.arange(len(dates)) / 7) * 0.1 + np.arange(len(dates)) * 0.001)
        frame = pd.DataFrame({"TSLA": values, "SPY": values, "QQQ": values}, index=dates)
        panel = lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)
        fits = []

        class Recorder:
            def fit(self, x, y):
                fits.append(x.index)
                return self

            def predict_proba(self, x):
                return np.tile([0.4, 0.6], (len(x), 1))

        with patch.object(price, "make_model", side_effect=lambda _: Recorder()):
            price.ml_strategy("TSLA", "logistic")(panel)
        self.assertEqual(len(fits), 2)
        for train, year in zip(fits, (2018, 2019)):
            boundary = dates[dates.year == year][0]
            last_target_open = dates[dates.get_loc(train[-1]) + price.ML_HORIZON + 1]
            self.assertLess(last_target_open, boundary)
        with patch.object(price, "make_model", side_effect=lambda _: Recorder()):
            self.assertTrue(lab.check_no_lookahead(price.ml_strategy("TSLA", "logistic"), panel))

    def test_equal_without_references_exclude_the_same_removed_asset(self):
        dates = pd.bdate_range("2020-01-02", periods=5)
        frame = pd.DataFrame(100.0, index=dates, columns=price.MEGACAPS)
        panel = lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)
        for removed in price.MEGACAPS:
            subset = tuple(symbol for symbol in price.MEGACAPS if symbol != removed)
            # ffill : les lignes vides signifient « aucun ordre » entre deux échéances.
            weights = price.equal_weight(subset)(panel).ffill()
            self.assertTrue((weights[removed] == 0).all())
            np.testing.assert_allclose(weights[list(subset)], 1 / len(subset))
            np.testing.assert_allclose(weights.sum(axis=1), 1.0)


if __name__ == "__main__":
    unittest.main()
