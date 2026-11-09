"""Audit indépendant du moteur et vérifications des signaux sociaux quotidiens."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import lab
import social_lab as social


def make_panel(opens):
    dates = pd.bdate_range("2020-01-01", periods=len(opens))
    frame = pd.DataFrame({"TSLA": opens}, index=dates, dtype=float)
    return lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)


class EngineAudit(unittest.TestCase):
    def test_two_asset_drift_does_not_create_a_fictitious_trade(self):
        dates = pd.bdate_range("2020-01-01", periods=5)
        frame = pd.DataFrame({"A": [100, 100, 200, 200, 200], "B": [100] * 5}, index=dates)
        panel = lab.Panel(frame, frame, frame, frame, frame * 0 + 1000)
        weights = pd.DataFrame({"A": [0.5, 2 / 3, 2 / 3, 2 / 3, 2 / 3],
                                "B": [0.5, 1 / 3, 1 / 3, 1 / 3, 1 / 3]}, index=dates)
        result = lab.backtest(weights, panel, start=dates[1], end=dates[-1], cost_bps=0)
        self.assertAlmostEqual(result.turnover.iloc[1], 0)
        self.assertAlmostEqual((1 + result.returns).prod(), 1.5)

    def test_missing_internal_prices_must_not_disappear(self):
        panel = make_panel([100, 100, np.nan, 110, 121])
        with self.assertRaises(ValueError):
            lab.backtest(lab.buy_hold_weights(panel, "TSLA"), panel,
                         start=panel.dates[1], end=panel.dates[-1])

    def test_lookahead_cannot_hide_a_column_in_truncated_panel(self):
        panel = make_panel([100] * 30)

        def leaky(p):
            frame = pd.DataFrame({"TSLA": 0.0}, index=p.dates)
            if len(p.dates) == 30:
                frame["FUTURE"] = 1.0
            return frame

        with self.assertRaises(AssertionError):
            lab.check_no_lookahead(leaky, panel)

    def test_constant_positive_excess_has_small_corrected_p(self):
        excess = pd.DataFrame({"constant_edge": np.full(100, 0.125)})
        self.assertLess(lab.romano_wolf(excess, n_boot=199).iloc[0], 0.02)

    def test_cash_sharpe_comparison_is_finite(self):
        rng = np.random.default_rng(4)
        benchmark = pd.Series(rng.normal(0.0005, 0.02, 200))
        result = lab.compare(benchmark * 0, benchmark, n_boot=99)
        self.assertTrue(np.isfinite(result["sharpe_difference"]))
        self.assertTrue(np.isfinite(result["sharpe_diff_ci95"]).all())

    def test_alpha_bootstrap_refits_beta_for_each_pair_sample(self):
        rng = np.random.default_rng(5)
        benchmark = pd.Series(rng.normal(0.01, 0.01, 120))
        strategy = 0.0003 + 0.7 * benchmark + rng.normal(0, 0.005, 120)
        draws = lab._stationary_indices(120, 199, 7, np.random.default_rng(9))
        b, s = benchmark.to_numpy()[draws], strategy.to_numpy()[draws]
        centered_b = b - b.mean(axis=1, keepdims=True)
        centered_s = s - s.mean(axis=1, keepdims=True)
        beta = (centered_b * centered_s).sum(axis=1) / (centered_b ** 2).sum(axis=1)
        alpha = (s.mean(axis=1) - beta * b.mean(axis=1)) * lab.TRADING_DAYS
        result = lab.compare(strategy, benchmark, n_boot=199, mean_block=7, seed=9)
        np.testing.assert_allclose(result["alpha_ci95"], np.quantile(alpha, [0.025, 0.975]),
                                   rtol=1e-10, atol=1e-10)


class SocialChronology(unittest.TestCase):
    def test_after_close_weekend_and_milliseconds_map_to_next_session(self):
        dates = pd.DatetimeIndex(["2024-07-05", "2024-07-08", "2024-07-09"])
        closes = (dates + pd.Timedelta(hours=16)).tz_localize("America/New_York").tz_convert("UTC")
        times = pd.to_datetime(["2024-07-05 19:59:59.999Z", "2024-07-05 20:00:00.001Z",
                                "2024-07-07 12:00:00Z", "2024-07-08 21:00:00Z"], format="mixed")
        actual = social.available_days(times, dates, closes)
        pd.testing.assert_index_equal(actual, pd.DatetimeIndex([dates[0], dates[1], dates[1], dates[2]]).as_unit("ns"))

    def test_early_close_is_used(self):
        dates = pd.DatetimeIndex(["2024-07-03", "2024-07-05"])
        closes = social.close_times(dates)
        times = pd.to_datetime(["2024-07-03 17:00:00Z", "2024-07-03 17:01:00Z"])
        actual = social.available_days(times, dates, closes)
        pd.testing.assert_index_equal(actual, dates.as_unit("ns"))

    def test_external_sources_and_caches_receive_cutoffs(self):
        cutoff = pd.Timestamp("2024-12-31 21:00:00Z")
        times = pd.DatetimeIndex(["2024-12-30 12:00:00Z", "2025-01-02 12:00:00Z"])
        ids = ((times.as_unit("ms").asi8 - 1288834974657) << 22).astype("int64")
        raw_posts = pd.DataFrame({"id": ids, "ts_utc": times, "text": ["a", "b"], "kind": ["original"] * 2})
        raw_earnings = pd.DataFrame({"ts": times, "eps_estimate": [1.0] * 2, "eps_reported": [2.0] * 2})
        raw_news = pd.DataFrame({"id": [1, 2], "created_at": times, "updated_at": times,
                                 "headline": ["a", "b"]})
        seen = []

        def read(path, filters):
            seen.append((Path(path).name, filters))
            name = Path(path).name
            if name == "musk_posts.parquet":
                return raw_posts.copy()
            if name == "tsla_earnings.parquet":
                return raw_earnings.copy()
            if name == "tsla_news.parquet":
                return raw_news.copy()
            if name == "finbert_musk_tesla.parquet":
                return pd.DataFrame({"id": ids, "p_positive": [0.2] * 2, "p_negative": [0.1] * 2})
            return pd.DataFrame({"id": ids, "impact_p_up": [0.2] * 2, "impact_p_down": [0.1] * 2})

        with patch.object(social.pd, "read_parquet", side_effect=read):
            posts, earnings, news = social.load_external(cutoff)
        self.assertEqual((len(posts), len(earnings), len(news)), (1, 1, 1))
        self.assertEqual(len(seen), 5)
        self.assertTrue(all(filters for _, filters in seen))
        with self.assertRaises(PermissionError):
            social.load_external(pd.Timestamp("2025-01-02 21:00:00Z"))

    def test_earnings_surprise_waits_until_next_close(self):
        dates = pd.bdate_range("2024-01-02", periods=12)
        posts = pd.DataFrame({"ts_utc": pd.to_datetime([], utc=True), "text": pd.Series(dtype=str),
                              "p_positive": [], "p_negative": [], "impact_p_up": [], "impact_p_down": []})
        earnings = pd.DataFrame({"ts": [pd.Timestamp("2024-01-04 20:00", tz="America/New_York")],
                                 "eps_estimate": [1.0], "eps_reported": [2.0]})
        news = pd.DataFrame({"available_at": pd.to_datetime([], utc=True)})
        social._features.cache_clear()
        with patch.object(social, "load_external", return_value=(posts, earnings, news)):
            frame = social._features(tuple(dates), str(social.DATA_DIR), "/nonexistent-social-cache.parquet", False)
        self.assertFalse(frame.loc["2024-01-04", "earnings_positive20"])
        self.assertTrue(frame.loc["2024-01-05", "earnings_positive20"])
        panel = make_panel([100, 100, 100, 100, 200, 200, 200, 200, 200, 200, 200, 200])
        panel = lab.Panel(*(field.set_axis(dates) for field in (panel.open, panel.high, panel.low, panel.close, panel.volume)))
        with patch.object(social, "features", return_value=frame):
            weights = social.strategy_weights(panel, "earnings_positive_20")
        result = lab.backtest(weights, panel, start=dates[0], end=dates[-1], cost_bps=0)
        # La hausse entre la clôture admissible et l'ouverture d'entrée n'est pas capturée.
        self.assertEqual(result.weights.loc[dates[3], "TSLA"], 0)
        self.assertEqual(result.weights.loc[dates[4], "TSLA"], 1)
        self.assertAlmostEqual((1 + result.returns).prod(), 1)
        social._features.cache_clear()


if __name__ == "__main__":
    unittest.main()
