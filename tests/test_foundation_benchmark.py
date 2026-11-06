"""Contrôles légers de l'alignement des prévisions, sans charger de poids."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from foundation_benchmark import epoch_nanoseconds, historical_covariates, predicted_trade_return


class ForecastTimingTests(unittest.TestCase):
    def test_microsecond_and_nanosecond_indices_encode_the_same_real_time(self):
        dates = pd.to_datetime(["2022-01-03 14:43:00"], utc=True)
        from_us = epoch_nanoseconds(dates.as_unit("us"))
        from_ns = epoch_nanoseconds(dates.as_unit("ns"))
        np.testing.assert_array_equal(from_us, from_ns)
        self.assertEqual(pd.to_datetime(from_us[0], utc=True), dates[0])

    def test_zero_control_preserves_market_and_removes_social_information(self):
        x = np.arange(128 * 11, dtype=np.float32).reshape(128, 11)
        control = historical_covariates(x, "zero_jev")
        actual = historical_covariates(x, "jev")
        self.assertEqual(list(control), list(actual))
        np.testing.assert_array_equal(control["var_5"], actual["var_5"])
        for key in ["var_6", "var_8", "var_9", "var_10"]:
            self.assertTrue((control[key] == 0).all())

    def test_excludes_price_move_before_entry(self):
        paths = np.full((1, 17), 121.)
        paths[0, 0], paths[0, 1] = 100., 110.
        self.assertAlmostEqual(predicted_trade_return(paths)[0], .1)

    def test_pre_entry_prediction_cannot_change_signal(self):
        paths = np.full((1, 17), 100.)
        before = predicted_trade_return(paths)
        paths[0, 0] = 200.
        np.testing.assert_array_equal(before, predicted_trade_return(paths))

    def test_missing_or_negative_predictions_are_rejected(self):
        for value in [np.nan, -1., 0.]:
            paths = np.ones((1, 17))
            paths[0, 16] = value
            with self.assertRaises(ValueError):
                predicted_trade_return(paths)


if __name__ == "__main__":
    unittest.main()
