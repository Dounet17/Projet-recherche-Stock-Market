"""Vérifie que la table de référence donne exactement ce que donnerait le moteur de backtest."""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
from lab import Panel
from reference import annualized, rolling_annual, buy_hold_table, cohort_statistics, month_start_rows, parse_french_csv, parse_sic_definitions, sector_of


def tiny_market():
    dates = pd.bdate_range("2020-01-15", "2020-06-30")
    rng = np.random.default_rng(0)
    prices = pd.DataFrame(100 * np.exp(rng.normal(0, 0.02, (len(dates), 3)).cumsum(axis=0)), index=dates, columns=["A", "B", "C"])
    prices.loc["2020-04-15":, "B"] = np.nan      # B fait faillite
    prices.loc["2020-05-11":"2020-05-13", "C"] = np.nan  # trou de cotation
    opens = prices * 1.001
    tradable = prices.notna()
    costs = pd.DataFrame(np.where(dates.day.to_numpy()[:, None] % 2 == 0, 10.0, 30.0) * np.ones((len(dates), 3)), index=dates, columns=prices.columns)
    data = SimpleNamespace(open=opens, close=prices, high=prices, low=prices, volume=prices * 0 + 1, tradable=tradable, cost_bps=costs, dollar_volume=prices * 1e4, dates=dates)
    exits = pd.DataFrame({"base": [np.nan, -1.0, np.nan], "optimistic": [np.nan, -0.5, np.nan], "pessimistic": [np.nan, -1.0, np.nan]}, index=prices.columns)
    return SimpleNamespace(data=data, exits=exits)


def engine_multiple(market, security, start, end, scenario):
    data = market.data
    panel = Panel(data.open, data.high, data.low, data.close, data.volume)
    weights = pd.DataFrame(np.nan, index=data.dates, columns=data.close.columns)
    decision = data.dates[data.dates.get_loc(start) - 1]
    weights.loc[decision] = 0.0
    weights.loc[decision, security] = 1.0
    result = lab.backtest(weights, panel, start=start, end=end, cost_bps=data.cost_bps, exits=market.exits[scenario])
    return float((1 + result.returns).prod())


class SameAsEngine(unittest.TestCase):
    def test_every_line_matches_the_backtest(self):
        market = tiny_market()
        table = buy_hold_table(market, horizons=(None, 1, 3))
        self.assertGreater(len(table), 20)
        rows = month_start_rows(market.data.dates)
        target = market.data.dates[rows]
        for line in table.itertuples():
            if line.horizon == -1:
                end = market.data.dates[-1]
            else:
                end = target[target.to_period("M") == line.start.to_period("M") + line.horizon][0]
            for scenario in ("base", "optimistic", "pessimistic"):
                self.assertAlmostEqual(getattr(line, scenario), engine_multiple(market, line.security_id, line.start, end, scenario), places=10, msg=f"{line.security_id} {line.start} {line.horizon} {scenario}")

    def test_bankruptcy_counts_as_a_total_loss(self):
        table = buy_hold_table(tiny_market(), horizons=(None,))
        self.assertTrue((table[table.security_id == "B"].base == 0).all())
        self.assertTrue((table[table.security_id == "B"].optimistic > 0).all())

    def test_not_bought_after_its_last_session(self):
        table = buy_hold_table(tiny_market(), horizons=(None,))
        self.assertLessEqual(table[table.security_id == "B"].start.max(), pd.Timestamp("2020-04-15"))

    def test_zero_median_is_a_total_annual_loss(self):
        table = pd.DataFrame({"start": pd.Timestamp("2020-01-01"), "horizon": -1, "base": [0.0, 0.0, 0.0], "exited": True, "nominal_years": 2.0})
        self.assertEqual(cohort_statistics(table).iloc[0]["median_annual"], -1.0)

    def test_statistics(self):
        table = pd.DataFrame({"start": pd.Timestamp("2020-01-01"), "horizon": -1, "base": [0.0, 1.0, 2.0, 5.0], "exited": [True, False, False, False], "nominal_years": 2.0})
        row = cohort_statistics(table).iloc[0]
        self.assertEqual(row["mean"], 2.0)
        self.assertEqual(row["median"], 1.5)
        self.assertEqual(row["share_loss"], 0.25)
        self.assertAlmostEqual(row["mean_annual"], 2 ** 0.5 - 1)


@unittest.skipUnless((ROOT / "data" / "universe_clean" / "prices_dev.parquet").exists(), "grand dataset absent")
class RealData(unittest.TestCase):
    def test_real_lines_match_the_backtest(self):
        from universe_data import load_universe

        market = load_universe(symbols=("AAPL", "SIVB", "TWTR", "BCEI", "WLL", "GME"))
        table = buy_hold_table(market, horizons=(None,))
        sample = table[table.start.isin(pd.to_datetime(["2017-03-01", "2018-01-02", "2021-06-01"]))]
        self.assertGreaterEqual(len(sample), 10)
        for line in sample.itertuples():
            expected = engine_multiple(market, line.security_id, line.start, market.data.dates[-1], "base")
            self.assertAlmostEqual(line.base, expected, places=9, msg=f"{line.security_id} {line.start}")


class FrenchFiles(unittest.TestCase):
    def test_nothing_after_the_lock_is_kept(self):
        text = "This file\n\n  Average Value Weighted Returns -- Daily\n,Guns,Oil\n20241231,1.00,-99.99\n20250102,5.00,5.00\n\n  Average Equal Weighted Returns -- Daily\n,Guns,Oil\n20241231,2.00,3.00\n20250102,5.00,5.00\n\nCopyright\n"
        sections = parse_french_csv(text)
        self.assertEqual(set(sections), {"value", "equal"})
        self.assertEqual(sections["value"].index.max(), pd.Timestamp("2024-12-31"))
        self.assertEqual(sections["value"].iloc[0, 0], 0.01)
        self.assertTrue(np.isnan(sections["value"].iloc[0, 1]))
        self.assertEqual(sections["equal"].iloc[0, 1], 0.03)

    def test_annualized_uses_the_real_duration(self):
        index = pd.date_range("2000-01-01", "2002-01-01", freq="D")
        daily = pd.Series((1.21 ** (1 / (len(index) - 1))) - 1, index=index)
        daily.iloc[0] = 0.0
        self.assertAlmostEqual(annualized(daily), 0.1, places=3)  # 731 jours valent 2,0014 années
        rolled = rolling_annual(daily, 1)
        self.assertEqual(rolled.index[0], pd.Timestamp("2001-01-01"))
        self.assertAlmostEqual(rolled.iloc[-1], 0.1, places=3)

    def test_sic_sectors(self):
        ranges, names = parse_sic_definitions(" 1 Guns   Defense\n          3760-3769 Missiles\n 2 Oil    Petroleum\n          1300-1300 Oil\n 3 Other  Almost Nothing\n")
        self.assertEqual(names, ["Guns", "Oil", "Other"])
        self.assertEqual(list(sector_of([3760, 1300, 9999, None], ranges)), ["Guns", "Oil", "Other", "unknown"])


if __name__ == "__main__":
    unittest.main()
