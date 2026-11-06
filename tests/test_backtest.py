"""Vérifie la chronologie et la comptabilité, sans entraîner les modèles."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from backtest import build_grid, simulate, social_features


def intervals(starts, ends, prices_in, prices_out):
    return pd.DataFrame({"entry_ts": pd.to_datetime(starts, utc=True), "exit_ts": pd.to_datetime(ends, utc=True), "entry_price": prices_in, "exit_price": prices_out, "day": pd.Timestamp("2024-01-02")})


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.grid = intervals(["2024-01-02 15:00", "2024-01-02 15:15"], ["2024-01-02 15:15", "2024-01-02 15:30"], [100, 110], [110, 121])

    def test_cash_stays_cash(self):
        self.assertEqual(simulate(self.grid, [0, 0], cost_bps=10).equity.iloc[-1], 10000)

    def test_contiguous_position_pays_one_round_trip(self):
        curve = simulate(self.grid, [1, 1], cost_bps=10)
        self.assertEqual(int(curve.buy.sum()), 1)
        self.assertEqual(int(curve.sell.sum()), 1)
        self.assertAlmostEqual(curve.equity.iloc[-1], 10000 / 1.001 * 1.21 * .999)

    def test_gap_forces_liquidation(self):
        self.grid.loc[1, "entry_ts"] += pd.Timedelta(minutes=1)
        curve = simulate(self.grid, [1, 1], cost_bps=10)
        self.assertEqual(int(curve.buy.sum()), 2)
        self.assertAlmostEqual(curve.equity.iloc[-1], 10000 * (1.1 * .999 / 1.001) ** 2)

    def test_overlap_is_rejected(self):
        self.grid.loc[1, "entry_ts"] -= pd.Timedelta(minutes=1)
        with self.assertRaises(ValueError):
            simulate(self.grid, [1, 1])

    def test_costs_reduce_wealth(self):
        self.assertLess(simulate(self.grid, [1, 1], 10).equity.iloc[-1], simulate(self.grid, [1, 1], 0).equity.iloc[-1])


class AvailabilityTests(unittest.TestCase):
    def test_future_and_too_recent_posts_cannot_change_decision(self):
        times = pd.to_datetime(["2024-01-02 14:00", "2024-01-02 14:59", "2024-01-02 14:59:30", "2024-01-02 15:01"], utc=True, format="mixed")
        posts = pd.DataFrame({"ts_utc": times})
        for col in ["fb_score", "jev_sent_score", "jev_impact_score", "jev_relevant_p"]:
            posts[col] = [99., 0.2, 1000., 1000.]
        entries = pd.to_datetime(["2024-01-02 15:00"], utc=True)
        a = social_features(entries, posts)
        b = social_features(entries, posts.iloc[:2])
        pd.testing.assert_frame_equal(a, b)
        self.assertEqual(a.social_count_60.iloc[0], 2)
        self.assertAlmostEqual(a.social_jev_impact_score_last.iloc[0], .2)

    def test_prices_after_decision_do_not_change_features(self):
        index = pd.date_range("2024-01-02 12:00", "2024-01-02 22:00", freq="min", tz="UTC")
        frame = pd.DataFrame({"open": 100 + np.arange(len(index)) / 100, "close": 100 + np.arange(len(index)) / 100}, index=index)
        cal = pd.DataFrame({"date": [pd.Timestamp("2024-01-02")], "open": [pd.Timestamp("2024-01-02 09:30")], "close": [pd.Timestamp("2024-01-02 16:00")]})
        posts = pd.DataFrame({"ts_utc": pd.to_datetime([], utc=True), "fb_score": [], "jev_sent_score": [], "jev_impact_score": [], "jev_relevant_p": []})
        a, columns, _ = build_grid(cal, {"tsla": frame, "qqq": frame}, posts)
        changed = frame.copy()
        changed.loc[changed.index >= pd.Timestamp("2024-01-02 14:59", tz="UTC"), "close"] *= 7
        b, _, _ = build_grid(cal, {"tsla": changed, "qqq": changed}, posts)
        decision = a.entry_ts.eq(pd.Timestamp("2024-01-02 15:00", tz="UTC"))
        pd.testing.assert_frame_equal(a.loc[decision, columns], b.loc[decision, columns])
        self.assertFalse(a.loc[~decision, columns].equals(b.loc[~decision, columns]))

    def test_no_post_means_zero_social_features(self):
        posts = pd.DataFrame({"ts_utc": pd.to_datetime([], utc=True), "fb_score": [], "jev_sent_score": [], "jev_impact_score": [], "jev_relevant_p": []})
        result = social_features(pd.to_datetime(["2024-01-02 15:00"], utc=True), posts)
        self.assertTrue((result.to_numpy() == 0).all())


if __name__ == "__main__":
    unittest.main()
