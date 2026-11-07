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


def quarters_frame(rows):
    """rows : (fin de période, date de dépôt, EPS) ; un seul CIK, 1."""
    return pd.DataFrame({"cik": 1, "period_end": pd.to_datetime([r[0] for r in rows]), "filed": pd.to_datetime([r[1] for r in rows]),
                         "eps": [r[2] for r in rows], "eps_suspect": False})


class CausalEps(unittest.TestCase):
    """Relecture D1 à D3 : EPS construit à chaque dépôt avec les seuls dépôts connus, fractionnements sans dividendes."""

    BASE = [("2019-03-30", "2019-05-03", 1.0), ("2019-06-29", "2019-07-31", 1.0), ("2019-09-28", "2019-10-30", 1.0), ("2019-12-31", "2020-02-25", 1.0),
            ("2020-03-28", "2020-05-05", 1.0)]

    def column(self, rows, dates, multiplier=None):
        multiplier = np.ones(len(dates)) if multiplier is None else multiplier
        return pe.causal_ttm_column(quarters_frame(rows), dates.to_numpy().astype("datetime64[us]"), multiplier)

    def test_value_starts_the_session_after_the_fourth_filing(self):
        dates = pd.bdate_range("2020-01-02", "2020-12-31")
        out = pd.Series(self.column(self.BASE, dates), index=dates)
        self.assertTrue(np.isnan(out["2020-02-25"]))
        self.assertEqual(out["2020-02-26"], 4.0)

    def test_a_late_duplicate_with_a_shifted_end_does_not_change_the_past(self):
        """Cas WAT : un trimestre redéposé plus tard avec une fin décalée d'un jour."""
        dates = pd.bdate_range("2020-01-02", "2020-12-31")
        later = self.BASE + [("2019-03-31", "2020-09-01", 1.2), ("2019-06-30", "2020-09-01", 1.2)]
        full = pd.Series(self.column(later, dates), index=dates)
        known = pd.Series(self.column(self.BASE, dates), index=dates)
        cutoff = pd.Timestamp("2020-08-31")
        pd.testing.assert_series_equal(full[:cutoff], known[:cutoff])
        for day in dates[dates <= cutoff]:        # même réponse avec les seuls dépôts connus à chaque date
            truncated = [r for r in later if pd.Timestamp(r[1]) <= day]
            value = pd.Series(self.column(truncated, dates), index=dates)[day]
            self.assertTrue((np.isnan(value) and np.isnan(full[day])) or value == full[day])

    def test_latest_known_version_of_a_quarter_is_used(self):
        rows = self.BASE + [("2020-03-29", "2020-06-15", 2.0)]
        dates = pd.bdate_range("2020-01-02", "2020-12-31")
        out = pd.Series(self.column(rows, dates), index=dates)
        self.assertEqual(out["2020-06-12"], 4.0)
        self.assertEqual(out["2020-06-16"], 5.0)

    def test_expiry_200_days_after_the_last_period(self):
        dates = pd.bdate_range("2020-01-02", "2021-03-31")
        out = pd.Series(self.column(self.BASE, dates), index=dates)
        self.assertEqual(out["2020-10-14"], 4.0)          # 28/03/2020 + 200 jours = 14/10/2020
        self.assertTrue(np.isnan(out["2020-10-15"]))

    def test_split_keeps_the_raw_scale_and_zero_growth(self):
        """Bénéfice constant, fractionnement en deux le 01/09/2020 : EPS divisé par deux, croissance nulle."""
        dates = pd.bdate_range("2019-01-02", "2021-06-30")
        factor = np.where(dates < pd.Timestamp("2020-09-01"), 0.5, 1.0) * np.linspace(0.97, 1.0, len(dates))   # avec dividendes
        multiplier = pe.share_multiplier(factor.reshape(-1, 1))[:, 0]
        rows = [(e, f, 1.0) for e, f, _ in self.BASE[:4]] + [("2020-03-28", "2020-05-05", 1.0), ("2020-06-27", "2020-07-30", 1.0),
                                                          ("2020-09-26", "2020-10-29", 0.5), ("2020-12-31", "2021-02-24", 0.5)]
        eps = pd.Series(pe.causal_ttm_column(quarters_frame(rows), dates.to_numpy().astype("datetime64[us]"), multiplier), index=dates)
        self.assertAlmostEqual(eps["2020-08-31"], 4.0)
        # Le jour du fractionnement, le facteur porte aussi le petit glissement d'un dividende : approximation tolérée.
        self.assertAlmostEqual(eps["2020-09-01"], 2.0, places=3)    # même bénéfice, deux fois plus d'actions
        self.assertAlmostEqual(eps["2021-03-01"], 2.0, places=3)    # deux trimestres d'avant et deux d'après, à la même échelle
        frame = pd.DataFrame({"A": eps})
        data = pe.StudyData(open=frame, high=frame, low=frame, close=frame, volume=frame, raw_close=frame, dollar_volume=frame,
                            traded=frame.notna(), tradable=frame.notna(), cost_bps=frame * 0, eps_ttm=frame,
                            share_multiplier=pd.DataFrame({"A": multiplier}, index=dates))
        self.assertAlmostEqual(pe.growth(data).loc["2021-06-30", "A"], 0.0, places=3)

    def test_dividends_alone_leave_eps_unchanged(self):
        factor = np.linspace(0.5, 1.0, 400).reshape(-1, 1)          # glissement continu, aucun saut
        self.assertTrue((pe.share_multiplier(factor) == 1.0).all())

    def test_study_data_survives_truncation(self):
        data, dates = universe({"A": 1.0}, {"A": 1.0}, {"A": 10.0})
        study = pe.StudyData(**{f: getattr(data, f) for f in ("open", "high", "low", "close", "volume", "raw_close", "dollar_volume", "traded", "tradable", "cost_bps", "eps_ttm")},
                             share_multiplier=data.close * 0 + 1)
        cut = study.truncate(dates[100])
        self.assertIsInstance(cut, pe.StudyData)
        self.assertEqual(len(cut.share_multiplier), 101)

    @unittest.skipUnless((ROOT / "data" / "universe_clean" / "fundamentals_quarterly_dev.parquet").exists(), "données absentes")
    def test_real_cases_are_causal(self):
        """WAT, COHU, ATRO, PATK : la valeur à chaque coupure ne change pas quand on retire les dépôts futurs."""
        quarters = pd.read_parquet(ROOT / "data" / "universe_clean" / "fundamentals_quarterly_dev.parquet", columns=["cik", "period_end", "filed", "eps", "eps_suspect"])
        securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["security_id", "cik"]).set_index("security_id").cik
        ids = ["WAT#0", "COHU#0", "ATRO#0", "PATK#0"]
        dates = pd.bdate_range("2017-01-02", "2024-12-31")
        factor = np.ones((len(dates), len(ids)))
        full = pe.causal_eps_matrix(quarters, securities[ids], dates, factor)
        for cutoff in pd.to_datetime(["2018-03-01", "2019-12-02", "2021-09-01", "2024-12-02"]):
            known = pe.causal_eps_matrix(quarters[quarters.filed <= cutoff], securities[ids], dates, factor)
            pd.testing.assert_frame_equal(full.loc[:cutoff], known.loc[:cutoff])
        self.assertFalse(np.isnan(full.loc["2019-12-02", "WAT#0"]))   # WAT n'est plus effacé par les dépôts de 2020


class LauncherRules(unittest.TestCase):
    def test_no_order_before_2018(self):
        sys.path.insert(0, str(ROOT / "reports"))
        import run_pe_eps_study as run
        data, dates = universe({"A": 2.0}, {"A": 1.0}, {"A": 10.0}, periods=520)
        fake = Universe(**{f: getattr(data, f).set_axis(pd.bdate_range("2017-06-01", periods=520)) for f in ("open", "high", "low", "close", "volume", "raw_close", "dollar_volume", "traded", "tradable", "cost_bps", "eps_ttm")})
        w = run.from_2018(pe.control_strategy)(fake)
        self.assertGreaterEqual(w.dropna(how="all").index.min(), pd.Timestamp("2018-01-02"))
        self.assertTrue(pe.control_strategy(fake).dropna(how="all").index.min() < pd.Timestamp("2018-01-02"))

    def test_holdings_drop_empty_and_zero_weights(self):
        sys.path.insert(0, str(ROOT / "reports"))
        import run_pe_eps_study as run
        dates = pd.bdate_range("2018-02-26", "2018-06-05")
        w = pd.DataFrame(np.nan, index=dates, columns=["A", "B", "C"])
        w.loc["2018-03-01"] = [1.0, 0.0, 0.0]
        w.loc["2018-06-01"] = [0.5, 0.5, 0.0]
        held = run.holdings(w)
        self.assertEqual(sorted(zip(held.date.dt.strftime("%m-%d"), held.security_id)), [("03-01", "A"), ("06-01", "A"), ("06-01", "B")])

    def test_full_launch_on_a_fake_market(self):
        """Toute la branche de lancement : quatre portefeuilles, P1/P2, trois secondaires, journal intercepté."""
        sys.path.insert(0, str(ROOT / "reports"))
        import tempfile
        import run_pe_eps_study as run
        periods = 600
        dates = pd.bdate_range("2017-06-01", periods=periods)
        names = [f"S{i}#0" for i in range(8)]
        rng = np.random.default_rng(3)
        prices = pd.DataFrame(10 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, (periods, 8)), axis=0)), index=dates, columns=names)
        eps = pd.DataFrame(np.r_[np.ones((300, 8)), np.tile(np.linspace(1.1, 2.0, 8), (periods - 300, 1))], index=dates, columns=names)
        ones = prices * 0 + 1.0
        data = pe.StudyData(open=prices, high=prices, low=prices, close=prices, volume=ones * 1e6, raw_close=prices, dollar_volume=ones * 1e8,
                            traded=ones.astype(bool), tradable=ones.astype(bool), cost_bps=ones * 5.0, eps_ttm=eps, share_multiplier=ones)
        bench = pd.DataFrame({"SPY": 100 * 1.0002 ** np.arange(periods), "QQQ": 100.0, "BIL": 100 * 1.00005 ** np.arange(periods)}, index=dates)
        market = SimpleNamespace(data=data, benchmarks=lab.Panel(bench, bench, bench, bench, bench * 0 + 1e6),
                                 exits=pd.DataFrame(np.nan, index=names, columns=["base", "optimistic", "pessimistic"]), securities=pd.DataFrame(index=names))
        written = []
        saved = (run.study_market, run.load_sectors, run.ms.check_hashes, lab.record_trial, run.adjusted_p_values, run.OUT)
        run.study_market = lambda: (market, eps)
        run.load_sectors = lambda: pd.Series(["X", "X", "Y", "Y", "Z", "Z", "Z", "unknown"], index=names)
        run.ms.check_hashes = lambda *a, **k: None
        lab.record_trial = lambda *a, **k: written.append(a[1])
        run.adjusted_p_values = lambda owner, returns: pd.Series({name: 0.5 for name in run.TRIALS.values()})
        with tempfile.TemporaryDirectory() as folder:
            run.OUT = Path(folder)
            try:
                old = pe.TOP
                pe.TOP = 3
                report = run.main([])
            finally:
                pe.TOP = old
                run.study_market, run.load_sectors, run.ms.check_hashes, lab.record_trial, run.adjusted_p_values, run.OUT = saved
            self.assertTrue((Path(folder) / "summary.json").exists())
        self.assertEqual(sorted(written), sorted(run.TRIALS.values()))
        self.assertEqual(set(report["confirmatory"]), {"P1", "P2"})
        self.assertEqual(set(report["secondary"]), {"S1_E1_vs_SPY", "S2_E2_vs_SPY", "S3_control_E1_vs_SPY"})
        for name in ("E1", "E2", "control_E1", "control_E2"):
            self.assertIn("beta_vs_spy", report["portfolios"][name])
            self.assertIn(name, report["sector_weights"])


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
