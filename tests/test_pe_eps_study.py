"""Tests des stratégies EPS et P/E sur des données inventées, valeurs calculées à la main. Aucun vrai cours.

Depuis la racine : venv/bin/python tests/test_pe_eps_study.py
"""

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
import pe_eps_study as pe
from universe_data import Universe


def universe(eps_now, eps_past, prices, liquidity=None, tradable=None, periods=330):
    """Univers inventé : EPS constant par période (avant / après la ligne 260), cours constant par titre."""
    dates = pd.bdate_range("2018-01-02", periods=periods)
    columns = list(eps_now)
    eps = pd.DataFrame({c: np.r_[np.full(260, eps_past[c]), np.full(periods - 260, eps_now[c])] for c in columns}, index=dates)
    close = pd.DataFrame({c: np.full(periods, prices[c], dtype=float) for c in columns}, index=dates)
    ones = close * 0 + 1.0
    liq = pd.DataFrame({c: np.full(periods, (liquidity or {}).get(c, 1e8)) for c in columns}, index=dates)
    trad = ones.astype(bool) if tradable is None else pd.DataFrame({c: np.full(periods, tradable.get(c, True)) for c in columns}, index=dates)
    data = Universe(open=close, high=close, low=close, close=close, volume=ones * 1e6, raw_close=close, dollar_volume=liq,
                    traded=ones.astype(bool), tradable=trad, cost_bps=ones * 0.0, eps_ttm=eps)
    return data, dates


class Days(unittest.TestCase):
    def test_first_session_of_quarter_months(self):
        index = pd.bdate_range("2018-02-26", "2018-06-05")
        days = pe.decision_days(index)
        self.assertEqual(index[days.to_numpy()].tolist(), [pd.Timestamp("2018-03-01"), pd.Timestamp("2018-06-01")])

    def test_holidays_shift_to_the_first_real_session(self):
        index = pd.DatetimeIndex(["2018-08-31", "2018-09-04", "2018-09-05"])   # 03/09/2018 férié
        self.assertEqual(pe.decision_days(index).tolist(), [False, True, False])


class Rules(unittest.TestCase):
    def setUp(self):
        self.eps_past = {"A": 1.0, "B": 1.0, "C": 2.0, "D": -1.0, "E": 1.0}
        self.eps_now = {"A": 1.5, "B": 3.0, "C": 2.2, "D": 1.0, "E": -0.5}
        self.prices = {"A": 30.0, "B": 90.0, "C": 22.0, "D": 10.0, "E": 10.0}

    def test_growth_and_eligibility(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices)
        day = dates[-1]
        g = pe.growth(data).loc[day]
        self.assertAlmostEqual(g["A"], 0.5)
        self.assertAlmostEqual(g["B"], 2.0)
        self.assertAlmostEqual(g["C"], 0.1)
        ok = pe.eligible(data).loc[day]
        self.assertEqual(ok.to_dict(), {"A": True, "B": True, "C": True, "D": False, "E": False})   # D : perte un an avant ; E : perte

    def test_eps_one_year_ago_is_the_value_known_then(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices)
        # Ligne 329 : l'EPS d'il y a 252 séances est celui de la ligne 77, l'ancien (1,0) ; aujourd'hui 1,5.
        self.assertEqual(pe.growth(data).iloc[-1]["A"], 0.5)
        self.assertTrue(np.isnan(pe.growth(data).iloc[100]["A"]))      # pas encore un an d'historique
        self.assertEqual(pe.growth(data).iloc[255]["A"], 0.0)           # les deux EPS sont encore l'ancien

    def test_liquidity_rank_and_tradable(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices, liquidity={"A": 3e8, "B": 2e8, "C": 1e8}, tradable={"B": False})
        ok = pe.eligible(data, liquid=1).loc[dates[-1]]
        self.assertEqual(ok[["A", "B", "C"]].tolist(), [True, False, False])

    def test_growth_strategy_picks_the_top_on_decision_days_only(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices)
        w = pe.growth_strategy(data, top=2)
        filled = w.dropna(how="all")
        self.assertTrue(pe.decision_days(dates)[filled.index].all())
        last = filled.iloc[-1]
        self.assertEqual(last[last > 0].sort_index().to_dict(), {"A": 0.5, "B": 0.5})   # croissances 2,0 et 0,5 contre 0,1

    def test_combined_score_by_hand(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices)
        sectors = {"A": "Money", "B": "Money", "C": "Shops", "D": "Shops", "E": "Shops"}
        score, allowed = pe.combined_score(data, sectors)
        day = dates[pe.decision_days(dates).to_numpy()][-1]
        # Croissance : C 0,1 < A 0,5 < B 2,0 -> centiles 1/3, 2/3, 1. E/P dans le secteur : Money A 0,05 < B 0,0333 ? non :
        # A 1,5/30 = 0,05 et B 3/90 = 0,0333 -> A 1, B 0,5 ; Shops : C seul -> 1.
        self.assertAlmostEqual(score.loc[day, "A"], (2 / 3 + 1) / 2)
        self.assertAlmostEqual(score.loc[day, "B"], (1 + 0.5) / 2)
        self.assertAlmostEqual(score.loc[day, "C"], (1 / 3 + 1) / 2)
        self.assertTrue(np.isnan(score.loc[day, "D"]))
        w = pe.combined_strategy(data, sectors, top=1).loc[day]
        self.assertEqual(w[w > 0].index.tolist(), ["A"])

    def test_unknown_sector_is_left_out_of_e2_and_its_control(self):
        data, dates = universe(self.eps_now, self.eps_past, self.prices)
        sectors = {"A": "Money", "B": "unknown", "C": "Shops"}
        day = dates[pe.decision_days(dates).to_numpy()][-1]
        self.assertTrue(np.isnan(pe.combined_score(data, sectors)[0].loc[day, "B"]))
        control = pe.control_strategy(data, sectors).loc[day]
        self.assertEqual(control[control > 0].sort_index().to_dict(), {"A": 0.5, "C": 0.5})
        self.assertEqual(int((pe.control_strategy(data).loc[day] > 0).sum()), 3)

    def test_no_lookahead_with_the_lab_check(self):
        rng = np.random.default_rng(1)
        data, dates = universe({c: 1.0 for c in "ABCDEFG"}, {c: 1.0 for c in "ABCDEFG"}, {c: 10.0 for c in "ABCDEFG"}, periods=520)
        eps = pd.DataFrame(np.exp(rng.normal(0, 0.3, (520, 7))).cumprod(axis=0) * 0 + rng.uniform(0.5, 2, (520, 7)), index=dates, columns=list("ABCDEFG"))
        data = Universe(**{**{f: getattr(data, f) for f in ("open", "high", "low", "close", "volume", "raw_close", "dollar_volume", "traded", "tradable", "cost_bps")}, "eps_ttm": eps})
        sectors = dict(zip("ABCDEFG", ["X", "X", "Y", "Y", "Y", "Z", "Z"]))
        for fn in (lambda d: pe.growth_strategy(d, top=3), lambda d: pe.combined_strategy(d, sectors, top=3), lambda d: pe.control_strategy(d, sectors)):
            self.assertTrue(lab.check_no_lookahead(fn, data))


class Launcher(unittest.TestCase):
    def test_portfolios_through_run_variant(self):
        sys.path.insert(0, str(ROOT / "reports"))
        import run_pe_eps_study as run
        periods = 320
        data, dates = universe({"A": 2.0, "B": 1.1}, {"A": 1.0, "B": 1.0}, {"A": 10.0, "B": 10.0}, periods=periods)
        rising = pd.DataFrame({"A": 10 * 1.001 ** np.arange(periods), "B": np.full(periods, 10.0)}, index=dates)
        data = Universe(**{**{f: getattr(data, f) for f in ("volume", "raw_close", "dollar_volume", "traded", "tradable", "cost_bps", "eps_ttm")},
                           "open": rising, "high": rising, "low": rising, "close": rising})
        bench = pd.DataFrame({"SPY": 100.0, "QQQ": 100.0, "BIL": 100.0}, index=dates)
        market = SimpleNamespace(data=data, benchmarks=lab.Panel(bench, bench, bench, bench, bench * 0 + 1e6),
                                 exits=pd.DataFrame(np.nan, index=["A", "B"], columns=["base", "optimistic", "pessimistic"]))
        e1 = run.run_one("E1", pe.growth_strategy(data, top=1), market)[0]
        control = run.run_one("control", pe.control_strategy(data), market)[0]
        first = dates[pe.decision_days(dates).to_numpy()]
        first = first[first >= dates[260]][0]
        # E1 achète A seul à l'ouverture qui suit la première décision où A est éligible, et le garde ; le témoin moitié A.
        held = 1.001 ** (len(dates) - 1 - dates.get_loc(first) - 1)
        self.assertAlmostEqual(lab.summarize(e1)["final_capital"], 10_000 * held, places=2)
        self.assertGreater(lab.summarize(e1)["final_capital"], lab.summarize(control)["final_capital"])


class DryRun(unittest.TestCase):
    @unittest.skipUnless((ROOT / "data" / "universe_clean" / "fundamentals_quarterly_dev.parquet").exists(), "données absentes")
    def test_dry_run_reads_no_return(self):
        sys.path.insert(0, str(ROOT / "reports"))
        import run_pe_eps_study as run
        def forbidden(*args, **kwargs):
            raise AssertionError("appel interdit pendant l'essai à blanc")
        saved = (run.run_one, run.run_variant, lab.backtest, lab.record_trial, lab.compare)
        run.run_one = run.run_variant = lab.backtest = lab.record_trial = lab.compare = forbidden
        try:
            funnel = run.main(["--dry-run"])
        finally:
            run.run_one, run.run_variant, lab.backtest, lab.record_trial, lab.compare = saved
        self.assertEqual(funnel["decision_days"], 28)
        self.assertEqual(funnel["held"]["E1"]["min"], 100)


if __name__ == "__main__":
    unittest.main()
