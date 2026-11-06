"""Vérifie la chronologie, la comptabilité et les garde-fous statistiques du laboratoire."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lab import Panel, backtest, buy_hold_weights, check_no_lookahead, compare, load_panel, romano_wolf, summarize


def make_panel(opens):
    idx = pd.bdate_range("2020-01-01", periods=len(opens))
    op = pd.DataFrame({"A": opens}, index=idx, dtype=float)
    return Panel(op, op, op, op, op * 0 + 1000)


class Accounting(unittest.TestCase):
    def test_buy_hold_pays_two_sides(self):
        panel = make_panel([100, 110, 121, 133.1])
        result = backtest(buy_hold_weights(panel, "A"), panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=10)
        self.assertAlmostEqual((1 + result.returns).prod(), 133.1 / 110 * (1 - 1e-3) ** 2, places=9)

    def test_decision_at_close_only_earns_from_next_open(self):
        panel = make_panel([100, 200, 200, 200])
        weights = pd.DataFrame({"A": [1.0, 0, 0, 0]}, index=panel.dates)
        # Décidé à la clôture du jour 0 : achat à l'ouverture du jour 1 à 200, sans le doublement.
        result = backtest(weights, panel, start=panel.dates[0], end=panel.dates[-1], cost_bps=0)
        self.assertAlmostEqual((1 + result.returns).prod(), 1.0)

    def test_held_position_does_not_trade_again(self):
        panel = make_panel([100, 101, 102, 103, 104])
        result = backtest(buy_hold_weights(panel, "A"), panel, start=panel.dates[1], end=panel.dates[-1])
        self.assertAlmostEqual(result.turnover.iloc[0], 1)
        self.assertAlmostEqual(result.turnover.iloc[1:-1].abs().max(), 0)
        self.assertAlmostEqual(result.turnover.iloc[-1], 1)

    def test_rejects_leverage_and_short(self):
        panel = make_panel([100, 101, 102])
        for value in (1.5, -1.0):
            with self.assertRaises(ValueError):
                backtest(pd.DataFrame({"A": value}, index=panel.dates), panel, start=panel.dates[0], end=panel.dates[-1])

    def test_no_order_row_lets_positions_drift_without_fees(self):
        idx = pd.bdate_range("2020-01-01", periods=6)
        op = pd.DataFrame({"A": [100, 100, 110, 121, 133.1, 146.41], "B": 100.0}, index=idx)
        panel = Panel(op, op, op, op, op * 0 + 1000)
        weights = pd.DataFrame(np.nan, index=idx, columns=op.columns)
        weights.iloc[0] = [0.5, 0.5]
        result = backtest(weights, panel, start=idx[1], end=idx[-1], cost_bps=5)
        self.assertAlmostEqual(result.turnover.iloc[0], 1)
        self.assertAlmostEqual(result.turnover.iloc[1:-1].abs().max(), 0)
        # Sans rééquilibrage, le portefeuille vaut exactement la moyenne des deux actifs.
        expected = (0.5 * 146.41 / 100 + 0.5) * (1 - 5e-4) ** 2
        self.assertAlmostEqual((1 + result.returns).prod(), expected, places=4)

    def test_start_inside_a_cycle_uses_the_last_order(self):
        panel = make_panel([100, 100, 100, 110, 121])
        weights = pd.DataFrame({"A": [1.0, np.nan, np.nan, np.nan, np.nan]}, index=panel.dates)
        result = backtest(weights, panel, start=panel.dates[2], end=panel.dates[-1], cost_bps=0)
        self.assertAlmostEqual((1 + result.returns).prod(), 1.21)

    def test_summary_drawdown(self):
        panel = make_panel([100, 100, 50, 75, 75])
        result = backtest(buy_hold_weights(panel, "A"), panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=0)
        self.assertAlmostEqual(summarize(result)["max_drawdown"], -0.5)


class Guards(unittest.TestCase):
    def test_lookahead_check(self):
        rng = np.random.default_rng(0)
        panel = make_panel(100 * np.exp(rng.normal(0, 0.01, 300).cumsum()))
        leaky = lambda p: (p.close.shift(-1) > p.close).astype(float)
        full_sample = lambda p: (p.close > p.close.mean()).astype(float)
        causal = lambda p: (p.close > p.close.rolling(50).mean()).astype(float)
        for bad in (leaky, full_sample):
            with self.assertRaises(AssertionError):
                check_no_lookahead(bad, panel)
        self.assertTrue(check_no_lookahead(causal, panel))

    def test_held_position_without_price_is_refused(self):
        panel = make_panel([100, 100, np.nan, 110, 121])
        with self.assertRaises(ValueError):
            backtest(buy_hold_weights(panel, "A"), panel, start=panel.dates[1], end=panel.dates[-1])

    def test_holdout_is_locked_by_default(self):
        with self.assertRaises(PermissionError):
            load_panel(end="2025-06-01")


class Statistics(unittest.TestCase):
    def test_noise_is_not_significant_and_true_edge_is(self):
        rng = np.random.default_rng(1)
        idx = pd.bdate_range("2015-01-01", periods=2500)
        bench = pd.Series(rng.normal(3e-4, 0.01, 2500), index=idx)
        noise = pd.Series(rng.normal(3e-4, 0.01, 2500), index=idx)
        self.assertGreater(compare(noise, bench, n_boot=500)["excess_p_one_sided"], 0.05)
        self.assertLess(compare(bench + 1e-3, bench, n_boot=500)["excess_p_one_sided"], 0.01)

    def test_romano_wolf_penalizes_many_noise_trials(self):
        rng = np.random.default_rng(2)
        idx = pd.bdate_range("2015-01-01", periods=1500)
        frame = pd.DataFrame(rng.normal(0, 0.01, (1500, 40)), index=idx).add_prefix("noise_")
        frame["true"] = rng.normal(2e-3, 0.01, 1500)
        adjusted = romano_wolf(frame, n_boot=300)
        self.assertLess(adjusted["true"], 0.01)
        self.assertGreater(adjusted.drop("true").min(), 0.05)


if __name__ == "__main__":
    unittest.main()
