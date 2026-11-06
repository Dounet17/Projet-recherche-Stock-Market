"""Vérifie les dates d'événement, la surprise et le rendement, sur des cas calculés à la main."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from events import block_bootstrap_p, day_positions, forward_multiple, holm, match_announcements, newey_west_t, prior_quarter_groups, quarterly_spread, standardized_surprise, two_sided_p


class Dates(unittest.TestCase):
    def quarter(self):
        return pd.DataFrame({"cik": [1], "period_end": pd.to_datetime(["2024-06-30"]), "filed": pd.to_datetime(["2024-07-24"])})

    def test_takes_the_last_8k_not_the_deliveries_one(self):
        announcements = pd.DataFrame({"cik": [1, 1], "date": pd.to_datetime(["2024-07-02", "2024-07-23"])})
        self.assertEqual(match_announcements(self.quarter(), announcements).announced[0], pd.Timestamp("2024-07-23"))

    def test_same_day_counts_and_later_does_not(self):
        same = pd.DataFrame({"cik": [1], "date": pd.to_datetime(["2024-07-24"])})
        later = pd.DataFrame({"cik": [1], "date": pd.to_datetime(["2024-07-25"])})
        self.assertEqual(match_announcements(self.quarter(), same).announced[0], pd.Timestamp("2024-07-24"))
        self.assertTrue(pd.isna(match_announcements(self.quarter(), later).announced[0]))

    def test_8k_from_a_previous_quarter_is_refused(self):
        announcements = pd.DataFrame({"cik": [1], "date": pd.to_datetime(["2024-04-23"])})
        self.assertTrue(pd.isna(match_announcements(self.quarter(), announcements).announced[0]))

    def test_entry_is_always_the_next_session(self):
        dates = pd.DatetimeIndex(pd.to_datetime(["2024-07-22", "2024-07-23", "2024-07-24", "2024-07-26"]))
        pre, entry = day_positions(pd.to_datetime(["2024-07-23", "2024-07-25", "2024-07-26"]), dates)
        self.assertEqual(pre.tolist(), [0, 2, 2])
        self.assertEqual(entry.tolist(), [2, 3, 4])   # jour ouvert, jour fermé, dernier jour sans suite


class Surprise(unittest.TestCase):
    def setUp(self):
        self.ends = pd.date_range("2018-03-31", periods=14, freq="QE").to_numpy().astype("datetime64[ns]")
        self.filed = self.ends + np.timedelta64(30, "D")
        self.far = np.full(14, np.datetime64("2030-01-01", "ns"))
        self.eps = np.random.default_rng(0).normal(1, 0.3, 14)

    def test_needs_history(self):
        sue = standardized_surprise(self.ends, self.eps, self.filed, self.far)
        self.assertTrue(np.isnan(sue[:8]).all())
        self.assertTrue(np.isfinite(sue[8:]).all())

    def test_only_uses_earlier_figures(self):
        sue = standardized_surprise(self.ends, self.eps, self.filed, self.far)
        changed = self.eps.copy()
        changed[-1] = 500.0
        np.testing.assert_array_equal(standardized_surprise(self.ends, changed, self.filed, self.far)[:-1], sue[:-1])

    def test_scale_does_not_matter(self):
        np.testing.assert_allclose(standardized_surprise(self.ends, self.eps, self.filed, self.far), standardized_surprise(self.ends, self.eps * 4, self.filed, self.far))

    def test_current_figure_not_yet_filed_gives_nothing_unless_retrospective(self):
        decisions = self.filed.copy()     # décision le jour même du dépôt, donc avant lui
        self.assertTrue(np.isnan(standardized_surprise(self.ends, self.eps, self.filed, decisions)).all())
        self.assertTrue(np.isfinite(standardized_surprise(self.ends, self.eps, self.filed, decisions, current_known=True)[8:]).all())

    def test_late_filed_history_is_excluded(self):
        # Les quatre variations précédentes sont publiées très tard : à la date de décision, l'histoire manque.
        filed = self.filed.copy()
        filed[4:8] = np.datetime64("2029-01-01", "ns")
        decisions = self.filed + np.timedelta64(1, "D")
        sue = standardized_surprise(self.ends, self.eps, filed, decisions)
        self.assertTrue(np.isnan(sue[8]))


class Measures(unittest.TestCase):
    def test_forward_multiple_with_exit(self):
        opens = np.array([[100.0], [110.0], [120.0], [np.nan]])
        closes = np.array([[100.0], [110.0], [130.0], [np.nan]])
        marks = pd.DataFrame(opens).ffill().to_numpy()
        entry, cols = np.array([1]), np.array([0])
        self.assertAlmostEqual(forward_multiple(marks, opens, closes, entry, cols, 1, np.array([np.nan]), np.array([2]))[0], 120 / 110)
        self.assertEqual(forward_multiple(marks, opens, closes, entry, cols, 2, np.array([-1.0]), np.array([2]))[0], 0.0)

    def test_horizon_beyond_the_data_is_empty_even_for_an_exit(self):
        opens = np.array([[100.0], [110.0], [120.0], [np.nan]])
        marks = pd.DataFrame(opens).ffill().to_numpy()
        out = forward_multiple(marks, opens, opens, np.array([1]), np.array([0]), 9, np.array([-1.0]), np.array([2]))
        self.assertTrue(np.isnan(out[0]))

    def test_groups_use_only_the_previous_quarter(self):
        dates = list(pd.date_range("2020-01-10", periods=60)) + list(pd.date_range("2020-04-10", periods=60))
        frame = pd.DataFrame({"entry_date": dates, "sue": list(range(60)) + [1000.0] * 60})
        groups = prior_quarter_groups(frame)
        self.assertTrue(groups.iloc[:60].isna().all())
        self.assertEqual(groups.iloc[60:].unique().tolist(), [5])

    def test_spread_and_statistics(self):
        rng = np.random.default_rng(0)
        rows = []
        for quarter in pd.date_range("2018-01-15", periods=20, freq="QS"):
            for group in (1, 5):
                rows += [{"entry_date": quarter, "group": group, "x": rng.normal(0.05 if group == 5 else 0, 0.02)} for _ in range(30)]
        spread = quarterly_spread(pd.DataFrame(rows), "x")
        self.assertAlmostEqual(spread.mean(), 0.05, delta=0.005)
        self.assertLess(block_bootstrap_p(spread, n_boot=2000), 0.01)
        self.assertLess(two_sided_p(newey_west_t(spread), len(spread)), 0.01)
        self.assertGreater(block_bootstrap_p(rng.normal(0, 1, 30), n_boot=2000), 0.05)
        self.assertGreater(block_bootstrap_p(np.zeros(5) + np.array([1, -1, 1, -1, 0.0]), n_boot=100), 0)

    def test_holm(self):
        self.assertEqual(holm([0.01, 0.04, 0.03]).round(2).tolist(), [0.03, 0.06, 0.06])


if __name__ == "__main__":
    unittest.main()
