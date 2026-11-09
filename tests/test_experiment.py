"""Vérifie la brique d'expérience et que les résultats publiés du laboratoire ne changent pas."""

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import experiment
import lab
from lab import Panel
from experiment import expand_grid, random_like, run_experiment, top_n, untradable_share

TRIALS = lab.LAB_DIR / "trials" / "claude"


class Selection(unittest.TestCase):
    def setUp(self):
        self.idx = pd.bdate_range("2020-01-30", periods=4)  # 30/01, 31/01, 03/02, 04/02
        self.score = pd.DataFrame({"A": [3.0, 3, 1, 1], "B": [2.0, 2, 2, 2], "C": [1.0, 1, 3, 3], "D": [9.0, 9, 9, np.nan]}, index=self.idx)
        self.tradable = pd.DataFrame(True, index=self.idx, columns=self.score.columns)
        self.tradable["D"] = False

    def test_top_n_skips_untradable_and_trades_at_month_start(self):
        weights = top_n(self.score, 2, self.tradable)
        # Première ligne : premier jour disponible, puis premier jour de février.
        self.assertEqual(list(weights.notna().all(axis=1)), [True, False, True, False])
        self.assertEqual(weights.iloc[0].to_dict(), {"A": 0.5, "B": 0.5, "C": 0.0, "D": 0.0})
        self.assertEqual(weights.iloc[2].to_dict(), {"A": 0.0, "B": 0.5, "C": 0.5, "D": 0.0})

    def test_top_n_without_candidate_sells_everything(self):
        weights = top_n(self.score, 2, self.tradable & False)
        self.assertEqual(weights.iloc[0].sum(), 0.0)
        self.assertTrue(weights.iloc[0].notna().all())

    def test_random_like_keeps_calendar_and_weights_on_tradable(self):
        weights = top_n(self.score, 2, self.tradable)
        drawn = random_like(weights, self.tradable, seed=1)
        pd.testing.assert_series_equal(drawn.isna().all(axis=1), weights.isna().all(axis=1))
        self.assertTrue((drawn["D"].dropna() == 0).all())
        np.testing.assert_allclose(drawn.dropna().sum(axis=1), 1.0)
        pd.testing.assert_frame_equal(drawn, random_like(weights, self.tradable, seed=1))

    def test_untradable_share(self):
        weights = pd.DataFrame(0.0, index=self.idx, columns=self.score.columns)
        weights["A"], weights["D"] = 0.75, 0.25
        self.assertAlmostEqual(untradable_share(weights, self.tradable), 0.25)

    def test_grid(self):
        self.assertEqual(expand_grid({"a": [1, 2], "b": 3}), [{"a": 1, "b": 3}, {"a": 2, "b": 3}])


def tiny_market():
    """Trois titres sur 60 séances ; B fait faillite à la séance 30, avec trois hypothèses de sortie."""
    idx = pd.bdate_range("2020-01-01", periods=60)
    rng = np.random.default_rng(0)
    prices = pd.DataFrame(100 * np.exp(rng.normal(0, 0.01, (60, 3)).cumsum(axis=0)), index=idx, columns=["A", "B", "C"])
    prices.iloc[31:, 1] = np.nan
    tradable = prices.notna()
    data = SimpleNamespace(open=prices, close=prices, high=prices, low=prices, volume=prices * 0 + 1e6, tradable=tradable, cost_bps=pd.DataFrame(5.0, index=idx, columns=prices.columns), dates=idx)

    def truncate(last):
        cut = lambda f: f.loc[:pd.Timestamp(last)]
        return SimpleNamespace(**{**data.__dict__, "open": cut(prices), "close": cut(prices), "high": cut(prices), "low": cut(prices), "volume": cut(data.volume), "tradable": cut(tradable), "cost_bps": cut(data.cost_bps), "dates": cut(prices).index, "truncate": truncate})

    data.truncate = truncate
    exits = pd.DataFrame({"base": [np.nan, -1.0, np.nan], "optimistic": [np.nan, -0.5, np.nan], "pessimistic": [np.nan, -1.0, np.nan]}, index=prices.columns)
    bench_prices = pd.DataFrame({"SPY": 100 * 1.001 ** np.arange(60.0)}, index=idx)
    bench = Panel(bench_prices, bench_prices, bench_prices, bench_prices, bench_prices * 0 + 1e6)
    return SimpleNamespace(data=data, exits=exits, benchmarks=bench)


def only_b(data):
    weights = pd.DataFrame(0.0, index=data.close.index, columns=data.close.columns)
    weights["B"] = 1.0
    return weights.where(pd.Series(data.close.index == data.close.index[0], index=data.close.index), axis=0)


class FullRun(unittest.TestCase):
    def run_in_tmp(self, strategy, **kwargs):
        market = tiny_market()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(lab, "LAB_DIR", Path(folder)):
            return run_experiment(strategy, market, start="2020-01-02", end="2020-03-24", **kwargs), Path(folder)

    def test_scenarios_differ_for_a_bankrupt_position(self):
        table, _ = self.run_in_tmp(only_b, name="b", family="test", n_random=2)
        row = table.iloc[0]
        self.assertEqual(row.final_capital, 0.0)
        self.assertEqual(row.final_capital_pessimistic, 0.0)
        self.assertGreater(row.final_capital_optimistic, 0.0)
        self.assertTrue(np.isfinite(row.annual_log_excess))

    def test_grid_is_fully_logged(self):
        def strategy(data, top=1):
            return top_n(data.close.pct_change(5, fill_method=None), top, data.tradable)

        market = tiny_market()
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(lab, "LAB_DIR", Path(folder)):
            table = run_experiment(strategy, market, name="mom", family="test", start="2020-01-02", end="2020-03-24", n_random=2, top=[1, 2])
            ledger = pd.read_csv(Path(folder) / "ledger_universe.csv")
            self.assertEqual(set(ledger.name), {"mom__top=1", "mom__top=2"})
            self.assertTrue((Path(folder) / "experiments" / "mom.csv").exists())
        self.assertTrue(table.romano_wolf_p.notna().all())
        self.assertEqual(table.untradable_share.max(), 0.0)

    def test_leaky_strategy_is_refused(self):
        def leaky(data):
            return top_n(data.close.shift(-5) / data.close, 1, data.tradable, rebalance=lambda i: pd.Series(True, index=i))

        with self.assertRaises(AssertionError):
            self.run_in_tmp(leaky, name="leak", family="test", n_random=0)

    def test_holdout_is_refused(self):
        with self.assertRaises(PermissionError):
            run_experiment(only_b, tiny_market(), name="x", family="test", end="2025-06-01")


@unittest.skipUnless((ROOT / "data" / "universe_clean" / "prices_dev.parquet").exists(), "grand dataset absent")
class RealDisappearances(unittest.TestCase):
    """Position unique tenue jusqu'au bout : le capital final se calcule à la main."""

    @classmethod
    def setUpClass(cls):
        from universe_data import load_universe

        cls.market = load_universe()

    def multiple(self, security, start="2022-01-03"):
        data = self.market.data
        weights = pd.DataFrame(np.nan, index=data.dates, columns=data.close.columns)
        decision = data.dates[data.dates.get_loc(pd.Timestamp(start)) - 1]
        weights.loc[decision] = 0.0
        weights.loc[decision, security] = 1.0
        result = lab.backtest(weights, data, start=start, cost_bps=0.0, exits=self.market.exits["base"])
        return float((1 + result.returns).prod())

    def test_bankruptcy_loses_everything(self):
        self.assertEqual(self.multiple("SIVB#0"), 0.0)

    def test_buyout_pays_close_plus_exit(self):
        data, exit_return = self.market.data, self.market.exits.loc["TWTR#0", "base"]
        expected = data.close["TWTR#0"].dropna().iloc[-1] / data.open["TWTR#0"].loc["2022-01-03"] * (1 + exit_return)
        self.assertAlmostEqual(self.multiple("TWTR#0"), expected, places=9)


@unittest.skipUnless(TRIALS.exists() and lab.DATA_FILE.exists(), "résultats du laboratoire absents")
class PublishedResultsUnchanged(unittest.TestCase):
    """Les résultats publiés doivent se reproduire à l'identique avec le moteur étendu."""

    def test_rules_and_rotations(self):
        from price_lab import ROTATIONS, single_strategy

        panel = lab.load_panel()
        cases = {f"{s}__{r}": single_strategy(r, s) for s in ("TSLA", "SPY", "AAPL") for r in ("sma200", "golden_cross", "vol_target_30", "bollinger_reversion")}
        cases.update({name: fn for name, fn in ROTATIONS.items() if (TRIALS / f"{name}.parquet").exists()})
        checked = 0
        for name, fn in cases.items():
            path = TRIALS / f"{name}.parquet"
            if not path.exists():
                continue
            saved = pd.read_parquet(path)["return"]
            fresh = lab.backtest(fn(panel), panel).returns
            np.testing.assert_array_equal(fresh.to_numpy(), saved.to_numpy(), err_msg=name)
            checked += 1
        print(f"\nrésultats publiés reproduits à l'identique : {checked}")
        self.assertGreaterEqual(checked, 12)


if __name__ == "__main__":
    unittest.main()
