"""Vérifie que le calcul action par action donne exactement ce que donnerait le moteur de backtest."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "reports"))
import lab
from lab import Panel
from per_stock import Simulator, equal_weight_result, risk_by_stock, rule_table
from reference import month_start_rows


def tiny_market():
    dates = pd.bdate_range("2020-01-15", "2020-06-30")
    rng = np.random.default_rng(3)
    closes = pd.DataFrame(100 * np.exp(rng.normal(0, 0.03, (len(dates), 3)).cumsum(axis=0)), index=dates, columns=["A", "B", "C"])
    closes.loc["2020-04-15":, "B"] = np.nan     # B disparaît
    closes.loc["2020-05-11":"2020-05-13", "C"] = np.nan   # trou de cotation
    costs = pd.DataFrame(np.where(dates.day.to_numpy()[:, None] % 2 == 0, 10.0, 30.0) * np.ones((len(dates), 3)), index=dates, columns=closes.columns)
    data = SimpleNamespace(open=closes * 1.002, close=closes, high=closes, low=closes, volume=closes * 0 + 1, cost_bps=costs, dates=dates)
    exits = pd.DataFrame({"base": [np.nan, -0.4, np.nan], "optimistic": [np.nan, -0.1, np.nan], "pessimistic": [np.nan, -1.0, np.nan]}, index=closes.columns)
    return SimpleNamespace(data=data, exits=exits)


def toy_signal(data):
    average = data.close.rolling(5, min_periods=4).mean()
    return (data.close > average).astype(float).where(average.notna() & data.close.notna())


def engine_multiple(market, signal, security, start, end, scenario):
    data = market.data
    panel = Panel(data.open, data.high, data.low, data.close, data.volume)
    weights = pd.DataFrame(np.nan, index=data.dates, columns=data.close.columns)
    known = signal[security].notna()
    weights.loc[known] = 0.0
    weights.loc[known, security] = signal.loc[known, security]
    result = lab.backtest(weights, panel, start=start, end=end, cost_bps=data.cost_bps, exits=market.exits[scenario])
    return float((1 + result.returns).prod())


class SameAsEngine(unittest.TestCase):
    def test_every_line_matches_the_backtest(self):
        market = tiny_market()
        signal = toy_signal(market.data)
        simulator = Simulator(signal, market)
        table = rule_table(simulator, month_start_rows(market.data.dates), (-1, 1, 3))
        self.assertGreater(len(table), 15)
        months = market.data.dates[month_start_rows(market.data.dates)]
        for line in table.itertuples():
            end = market.data.dates[-1] if line.horizon == -1 else months[months.to_period("M") == line.start.to_period("M") + line.horizon][0]
            for scenario, value in (("base", line.rule_base), ("optimistic", line.rule_optimistic), ("pessimistic", line.rule_pessimistic)):
                self.assertAlmostEqual(value, engine_multiple(market, signal, line.security_id, line.start, end, scenario), places=10, msg=f"{line.security_id} {line.start} {line.horizon} {scenario}")

    def test_always_invested_is_the_buy_and_hold(self):
        market = tiny_market()
        simulator = Simulator(toy_signal(market.data), market)
        start = month_start_rows(market.data.dates)[0]
        cols = np.flatnonzero(simulator.eligible(start))
        wealth, _, _ = simulator.paths(start, len(market.data.dates) - 1, cols, always_invested=True)
        always = pd.DataFrame(1.0, index=market.data.dates, columns=market.data.close.columns)
        for j, col in enumerate(cols):
            name = market.data.close.columns[col]
            self.assertAlmostEqual(wealth[-1, j], engine_multiple(market, always, name, market.data.dates[start], market.data.dates[-1], "base"), places=10)

    def test_treasury_cash_matches_the_backtest(self):
        market = tiny_market()
        signal = toy_signal(market.data)
        cash = pd.Series(1e-4, index=market.data.dates)
        simulator = Simulator(signal, market, cash_returns=cash)
        start = month_start_rows(market.data.dates)[0]
        cols = np.flatnonzero(simulator.eligible(start))
        data = market.data
        panel = Panel(data.open, data.high, data.low, data.close, data.volume)
        wealth, _, _ = simulator.paths(start, len(data.dates) - 1, cols)
        for j, col in enumerate(cols):
            name = data.close.columns[col]
            known = signal[name].notna()
            weights = pd.DataFrame(np.nan, index=data.dates, columns=data.close.columns)
            weights.loc[known] = 0.0
            weights.loc[known, name] = signal.loc[known, name]
            result = lab.backtest(weights, panel, start=data.dates[start], end=data.dates[-1], cost_bps=data.cost_bps, cash_returns=cash, exits=market.exits["base"])
            self.assertAlmostEqual(wealth[-1, j], float((1 + result.returns).prod()), places=10, msg=name)

    def test_cash_earns_nothing_and_costs_nothing(self):
        market = tiny_market()
        signal = toy_signal(market.data) * 0.0
        simulator = Simulator(signal, market)
        start = month_start_rows(market.data.dates)[0]
        cols = np.flatnonzero(simulator.eligible(start))
        wealth, _, held = simulator.paths(start, len(market.data.dates) - 1, cols)
        np.testing.assert_allclose(wealth, 1.0)
        self.assertEqual(held.sum(), 0)

    def test_exposure_and_turnover_in_dollars(self):
        dates = pd.bdate_range("2020-01-01", periods=3)
        # A double puis reste ; B sort au bout d'une période, à 0.
        wealth = np.array([[2.0, 0.0], [2.0, 0.0], [2.0, 0.0]])
        held = np.array([[1.0, 1.0], [1.0, 0.0], [1.0, 0.0]])
        result = equal_weight_result(wealth, held, np.array([False, True]), dates)
        self.assertEqual(result.weights.exposure.tolist(), [1.0, 1.0, 1.0])
        # Achat de tout au départ, aucune vente à la sortie de B, vente de A à la fin.
        self.assertEqual(result.turnover.tolist(), [1.0, 0.0, 1.0])

    def test_held_is_zero_after_an_exit(self):
        market = tiny_market()
        simulator = Simulator(toy_signal(market.data), market)
        start = month_start_rows(market.data.dates)[0]
        cols = np.flatnonzero(simulator.eligible(start))
        _, leaves, held = simulator.paths(start, len(market.data.dates) - 1, cols, always_invested=True)
        self.assertTrue(leaves.any())
        self.assertEqual(held[-1, leaves].sum(), 0.0)

    def test_risk(self):
        sharpe, drawdown = risk_by_stock(np.array([[1.0], [0.5], [1.0]]))
        self.assertAlmostEqual(drawdown[0], -0.5)
        self.assertEqual(risk_by_stock(np.ones((3, 1)))[0][0], 0.0)


@unittest.skipUnless((ROOT / "data" / "universe_clean" / "prices_dev.parquet").exists(), "grand dataset absent")
class RealData(unittest.TestCase):
    def test_real_lines_match_the_backtest(self):
        from run_step3_sma200 import sma200
        from universe_data import load_universe

        market = load_universe(symbols=("AAPL", "SIVB", "TWTR", "GME", "BBBY"))
        signal = sma200(market.data)
        simulator = Simulator(signal, market)
        months = month_start_rows(market.data.dates)
        starts = months[market.data.dates[months].isin(pd.to_datetime(["2018-01-02", "2020-04-01", "2022-06-01"]))]
        table = rule_table(simulator, starts, (-1,))
        self.assertGreaterEqual(len(table), 8)
        for line in table.itertuples():
            self.assertAlmostEqual(line.rule_base, engine_multiple(market, signal, line.security_id, line.start, market.data.dates[-1], "base"), places=9, msg=f"{line.security_id} {line.start}")


if __name__ == "__main__":
    unittest.main()
