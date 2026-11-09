"""Vérifie le modèle : pas de fuite, faillites vues à l'entraînement, signal retrouvé, bruit non inventé."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
from ml_rank import diagnose, features, forward_multiples, make_strategy, percentile_ranks, yearly_training_rows
from universe_data import Universe

FAST = {"max_iter": 40, "min_samples_leaf": 20}


def universe(closes):
    frame = lambda values: pd.DataFrame(values, index=closes.index, columns=closes.columns)
    valid = closes.notna()
    return Universe(closes, closes, closes, closes, frame(1e6) * valid, closes, frame(1e7) * valid.astype(float), valid, valid, frame(5.0))


def random_closes(stocks=60, days=900, seed=0, drift=None):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2016-01-04", periods=days)
    returns = rng.normal(0, 0.02, (days, stocks))
    if drift is not None:
        returns = returns + drift
    return pd.DataFrame(100 * np.exp(returns.cumsum(axis=0)), index=dates, columns=[f"S{i}" for i in range(stocks)])


def no_exit(closes):
    return pd.Series(np.nan, index=closes.columns), closes.apply(lambda c: c.last_valid_index())


class Helpers(unittest.TestCase):
    def test_ranks(self):
        out = percentile_ranks(np.array([1.0, np.nan, 3.0, 2.0, 9.0]), np.array([True, True, True, True, False]))
        np.testing.assert_allclose(out[[0, 2, 3]], [0.0, 1.0, 0.5])
        self.assertTrue(np.isnan(out[1]) and np.isnan(out[4]))

    def test_training_only_uses_finished_months(self):
        ends = np.array(["2017-11-02", "2017-12-04", "2018-01-03", "NaT"], dtype="datetime64[ns]")
        self.assertEqual(yearly_training_rows(ends, 2018).tolist(), [0, 1])

    def test_target_period_and_exit(self):
        dates = pd.bdate_range("2020-01-30", "2020-03-31")
        closes = pd.DataFrame({"A": 100.0, "B": 100.0, "C": 100.0}, index=dates)
        closes.loc["2020-02-05":, "A"] = 50.0    # A chute après l'achat du 03/02 ; garde la position
        closes.loc["2020-02-20":, "B"] = np.nan  # B fait faillite pendant le mois visé
        closes.loc["2020-02-02":, "C"] = np.nan  # C disparaît avant l'achat
        data = universe(closes)
        exits = pd.Series({"A": np.nan, "B": -1.0, "C": 0.0})
        last = closes.apply(lambda c: c.last_valid_index())
        rows, ends, multiples = forward_multiples(data, exits, last)
        # Décision du 03/02, achat le 04/02, fin à l'ouverture du lendemain de la décision de mars (03/03).
        i = list(dates[rows]).index(pd.Timestamp("2020-02-03"))
        self.assertEqual(ends[i], np.datetime64("2020-03-03"))
        self.assertAlmostEqual(multiples[i, 0], 0.5)
        self.assertEqual(multiples[i, 1], 0.0)
        self.assertTrue(np.isnan(multiples[i, 2]))

    def test_features_only_use_the_past(self):
        closes = random_closes(stocks=5, days=400)
        full = universe(closes)
        cut = full.truncate(closes.index[300])
        for name, frame in features(cut).items():
            pd.testing.assert_frame_equal(frame, features(full)[name].iloc[:301], obj=name)


class Learning(unittest.TestCase):
    def test_no_lookahead_after_retraining(self):
        closes = random_closes(stocks=40, days=800)
        exits, last = no_exit(closes)
        strategy = make_strategy(exits, last, model_params=FAST, first_test_year=2017)
        self.assertTrue(lab.check_no_lookahead(lambda d: strategy(d, top=5), universe(closes), cutoffs=[closes.index[560], closes.index[720]]))

    def test_changing_the_future_changes_nothing_before(self):
        closes = random_closes(stocks=40, days=800)
        exits, last = no_exit(closes)
        strategy = make_strategy(exits, last, model_params=FAST, first_test_year=2017)
        changed = closes.copy()
        changed.iloc[700:] = changed.iloc[700:] * 3
        before = strategy(universe(closes), top=5).iloc[:700]
        after = strategy(universe(changed), top=5).iloc[:700]
        pd.testing.assert_frame_equal(before, after)

    def test_a_real_pattern_is_found_and_noise_is_not_invented(self):
        # Les actions qui ont monté sur 21 jours continuent : signal planté, à retrouver hors échantillon.
        rng = np.random.default_rng(5)
        dates = pd.bdate_range("2016-01-04", periods=1000)
        returns = np.zeros((1000, 120))
        returns[0] = rng.normal(0, 0.01, 120)
        for t in range(1, 1000):
            past = returns[max(0, t - 21):t].sum(axis=0)
            returns[t] = 0.02 * np.sign(past) * 0.3 + rng.normal(0, 0.02, 120)
        planted = pd.DataFrame(100 * np.exp(returns.cumsum(axis=0)), index=dates, columns=[f"S{i}" for i in range(120)])
        noise = random_closes(stocks=120, days=1000, seed=9)
        results = {}
        for label, closes in (("planted", planted), ("noise", noise)):
            exits, last = no_exit(closes)
            keep = {}
            make_strategy(exits, last, model_params=FAST, first_test_year=2017, keep=keep)(universe(closes), top=10)
            results[label] = self.monthly_ic(keep["scores"], universe(closes), exits, last)
        self.assertGreater(results["planted"], 0.2)
        self.assertLess(abs(results["noise"]), 0.08)

    @staticmethod
    def monthly_ic(scores, data, exits, last):
        rows, _, multiples = forward_multiples(data, exits, last)
        values = []
        for i, row in enumerate(rows):
            p = scores.to_numpy()[row]
            known = np.isfinite(p) & np.isfinite(multiples[i])
            if known.sum() > 20:
                values.append(pd.Series(p[known]).corr(pd.Series(multiples[i][known]), method="spearman"))
        return float(np.mean(values))


if __name__ == "__main__":
    unittest.main()
