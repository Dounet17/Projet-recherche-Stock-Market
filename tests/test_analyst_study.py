"""Tests de l'étude des notes d'analystes sur des données inventées, valeurs calculées à la main. Aucun vrai cours.

Depuis la racine : venv/bin/python tests/test_analyst_study.py
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import analyst_study as an
import lab
import minute_study as ms


class Classification(unittest.TestCase):
    def test_rating_changes(self):
        self.assertEqual(an.classify("Citigroup Upgrades Barrick Gold to Buy, Announces $14 Price Target"), "upgrade")
        self.assertEqual(an.classify("Longbow Research Downgrades Hilton Worldwide Holdings to Neutral"), "downgrade")
        self.assertEqual(an.classify("UPDATE: JP Morgan downgrades Tesla to Underweight"), "downgrade")

    def test_both_words_are_refused(self):
        self.assertIsNone(an.classify("Analyst upgrades and downgrades for Monday"))

    def test_price_targets_need_maintains_or_reiterates(self):
        self.assertEqual(an.classify("Morgan Stanley Maintains Equal-Weight on Ameriprise Financial, Raises Price Target to $205"), "target_up")
        self.assertEqual(an.classify("Roth MKM Reiterates Neutral on BRC, Lowers Price Target to $3.5"), "target_down")
        self.assertIsNone(an.classify("10 Biggest Price Target Changes For Tuesday"))
        self.assertIsNone(an.classify("Benchmark Reiterates Buy on Proto Labs, Maintains $45 Price Target"))

    def test_upgrade_wins_over_a_target_cut_in_the_same_title(self):
        self.assertEqual(an.classify("B of A Upgrades X to Buy, Lowers Price Target to $38"), "upgrade")


class Selection(unittest.TestCase):
    def test_filters(self):
        articles = pd.DataFrame({
            "id": [1, 2, 3, 4, 5], "category": ["analyst"] * 4 + ["company_news"],
            "headline": ["A Upgrades X to Buy", "A Upgrades Y to Buy", "A Upgrades Z to Buy", "A Downgrades W to Sell", "A Upgrades X to Buy"],
            "n_stocks": [1, 2, 1, 1, 1], "correction": [False, False, True, False, False], "late_relay": False})
        links = pd.DataFrame({"id": [1, 2, 4, 4, 5], "security_id": ["X#0", "Y#0", "W#0", "WP#0", "X#0"], "link": "direct", "conflict": [False, False, False, False, False]})
        types = pd.Series({"X#0": "common", "Y#0": "common", "W#0": "adr", "WP#0": "preferred"})
        out = an.select_notes(articles, links, types)
        self.assertEqual(sorted(zip(out.id, out.security_id, out.kind)), [(1, "X#0", "upgrade"), (4, "W#0", "downgrade")])

    def test_same_day_notes(self):
        notes = pd.DataFrame({"id": [1, 2, 3, 4, 5], "security_id": ["X#0", "X#0", "Y#0", "Y#0", "Z#0"], "entry_idx": [10, 10, 10, 10, 11],
                              "kind": ["upgrade", "upgrade", "upgrade", "downgrade", "target_up"],
                              "available_at": pd.to_datetime(["2024-01-02 08:00", "2024-01-02 07:00", "2024-01-02 07:00", "2024-01-02 07:30", "2024-01-03 07:00"], utc=True)})
        out = an.collapse(notes, ("upgrade", "downgrade"))
        self.assertEqual(out.id.tolist(), [2])          # X : une seule ligne, la plus tôt ; Y : contradiction écartée
        self.assertEqual(an.collapse(notes, ("target_up", "target_down")).id.tolist(), [5])


class Clock(unittest.TestCase):
    def test_near_earnings_window(self):
        positions = {7: np.array([20, 50])}
        entries = np.array([18, 19, 21, 22, 49, 51, 52])
        # Publication à p - 2 ... p + 1 : 18 a la sienne 2 séances après (hors fenêtre), 52 deux séances avant (dedans).
        self.assertEqual(an.near_earnings([7] * 7, entries, positions).tolist(), [False, True, True, True, True, True, True])
        self.assertEqual(an.near_earnings([8, np.nan], np.array([20, 20]), positions).tolist(), [False, False])
        # 17 : publication 3 séances après l'entrée, hors exclusion ; 23 : publication 3 séances avant.
        self.assertEqual(an.near_earnings([7, 7], np.array([17, 23]), positions).tolist(), [False, False])

    def test_earnings_inside_the_held_window(self):
        positions = {7: np.array([40])}
        self.assertEqual(an.earnings_inside([7, 7, 7], np.array([21, 20, 41]), positions, hold=20).tolist(), [True, False, False])


class Portfolio(unittest.TestCase):
    def test_intervals_prolong_on_a_new_buy(self):
        self.assertEqual(an.holding_intervals([0, 5, 30], ["X", "X", "X"], hold=20), [("X", 0, 25), ("X", 30, 50)])
        self.assertEqual(an.holding_intervals([0, 20], ["X", "X"], hold=20), [("X", 0, 40)])

    def test_weights_change_only_when_the_set_changes(self):
        dates = pd.bdate_range("2024-01-01", periods=30)
        w = an.portfolio_weights([2, 2, 5], ["A", "B", "C"], dates, hold=10, cap=0.4)
        filled = w.dropna(how="all")
        self.assertEqual(filled.index.tolist(), [dates[2], dates[5], dates[12], dates[15]])
        self.assertEqual(filled.loc[dates[2]].tolist(), [0.4, 0.4, 0.0])
        self.assertAlmostEqual(filled.loc[dates[5]].sum(), 1.0)
        self.assertEqual(filled.loc[dates[12]].tolist(), [0.0, 0.0, 0.4])
        self.assertEqual(filled.loc[dates[15]].tolist(), [0.0, 0.0, 0.0])

    def test_held_exactly_hold_sessions_in_the_real_engine(self):
        """Décision à la clôture de la ligne 3 : achat à l'ouverture 4, vente à l'ouverture 4 + 20."""
        dates = pd.bdate_range("2024-01-01", periods=40)
        opens = pd.DataFrame({"A": 100 * 1.01 ** np.arange(40)}, index=dates)
        panel = lab.Panel(opens, opens, opens, opens, opens * 0 + 1e6)
        w = an.portfolio_weights([3], ["A"], dates, hold=20, cap=1.0)
        result = lab.backtest(w, panel, start=dates[0], end=dates[-1], cost_bps=0.0)
        held = result.returns[result.returns.abs() > 1e-12]
        self.assertEqual(len(held), 20)
        self.assertEqual(held.index[0], dates[4])
        self.assertAlmostEqual((1 + result.returns).prod(), 1.01 ** 20)


class Analysis(unittest.TestCase):
    def test_analysis_runs_on_a_fake_table(self):
        """Toute l'analyse sauf le portefeuille, remplacé : table inventée, effet planté sur A1."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        rng = np.random.default_rng(5)
        n = 6000
        days = pd.bdate_range("2018-01-02", "2024-12-31")
        table = pd.DataFrame({"id": np.arange(n), "family": rng.choice(["rating", "target"], n), "tradable": rng.random(n) < 0.9,
                              "near_earnings": rng.random(n) < 0.15, "entry_date": pd.DatetimeIndex(rng.choice(days, n)), "cik": rng.integers(0, 500, n),
                              "liquidity": rng.choice([5e6, 5e7, 5e8], n), "earnings_in_window": rng.random(n) < 0.3})
        table["positive"] = rng.random(n) < 0.5
        table["kind"] = np.where(table.family == "rating", np.where(table.positive, "upgrade", "downgrade"), np.where(table.positive, "target_up", "target_down"))
        table["liquid"] = table.liquidity >= ms.LIQUID
        table["calendar_covered"] = rng.random(n) < 0.9
        table["quarter"] = table.entry_date.dt.to_period("Q")
        noise = lambda: rng.normal(0, 0.05, n)
        for horizon in run.HORIZONS:
            for scenario in run.SCENARIOS:
                table[f"ab_{horizon}_{scenario}"] = noise() + (0.03 * table.positive if horizon == 20 else 0)
        for scenario in run.SCENARIOS:
            for name in ("net_ab_20", "ab_placebo", "ab_before"):
                table[f"{name}_{scenario}"] = noise()
        table["net_ab_20_double"] = noise()
        original = run.portfolio
        run.portfolio = lambda a3, market: {"p_one_sided": 0.4, "compare_vs_spy": {"annual_log_excess": -0.01},
                                            "strategy": {"final_capital": 9000.0}, "spy": {"final_capital": 24000.0}}
        try:
            report = run.analyze(table, a3=None, market=None)
        finally:
            run.portfolio = original
        a1 = report["confirmatory"]["A1"]
        self.assertEqual(a1["quarters"], 28)
        self.assertIn("newey_west", a1)                 # sensibilité séparée du résultat principal
        self.assertEqual(set(report["controls"]["exit_scenarios"]["A2"]), set(run.SCENARIOS))
        self.assertEqual(set(report["confirmatory"]), {"A1", "A2", "A3"})
        self.assertLess(report["confirmatory"]["A1"]["p_holm"], 0.01)
        self.assertGreater(report["confirmatory"]["A2"]["p_holm"], 0.01)
        self.assertEqual(len(report["secondary"]), 7)
        import json
        json.dumps(report, default=float)


class CreditAgencies(unittest.TestCase):
    """Changement de règle D8 : une agence de notation qui ouvre le titre note la dette, pas l'action."""

    def test_credit_ratings_are_refused(self):
        for title in ("Moody's Downgrades Teva To BA2, Outlook Stable", "UPDATE: Fitch Upgrades Ford to BBB",
                      "S&P Downgrades Eli Lilly Credit Rating From AA- To A+", "S&P Global Ratings Upgrades Securitizations Sponsored By Carvana",
                      "Hearing Moody's Upgrades Netflix Debt Rating", "DBRS Morningstar Downgrades X"):
            self.assertIsNone(an.classify(title), title)

    def test_notes_about_these_companies_are_kept(self):
        self.assertEqual(an.classify("Morgan Stanley Upgrades Moody's to Overweight"), "upgrade")
        self.assertEqual(an.classify("Citigroup Downgrades Abercrombie & Fitch to Sell"), "downgrade")
        self.assertEqual(an.classify("Wells Fargo Upgrades S&P Global to Overweight"), "upgrade")


class PortfolioClock(unittest.TestCase):
    def test_decision_needs_five_minutes_before_the_close(self):
        m = ms.MINUTE
        closes = np.array([1000 * m, 2000 * m])
        notes = [1000 * m - 6 * m, 1000 * m - 5 * m, 1000 * m - 5 * m + 1, 1000 * m - 1, 1000 * m]
        self.assertEqual(an.decision_sessions(notes, closes).tolist(), [0, 0, 1, 1, 1])

    def test_a_future_note_never_changes_a_past_decision(self):
        """AMAG, octobre 2020 : relèvement le 01/10 en séance, abaissement le 02/10 au matin, même entrée A1."""
        notes = pd.DataFrame({"id": [1, 2], "security_id": "AMAG#0", "kind": ["upgrade", "downgrade"], "entry_idx": [11, 11], "decision_idx": [10, 11],
                              "available_at": pd.to_datetime(["2020-10-01 16:27", "2020-10-02 10:35"], utc=True)})
        self.assertEqual(an.collapse(notes, ("upgrade", "downgrade")).id.tolist(), [])                       # A1 : contradiction
        with_future = an.collapse(notes, ("upgrade", "downgrade"), key="decision_idx")
        without = an.collapse(notes[notes.id == 1], ("upgrade", "downgrade"), key="decision_idx")
        self.assertEqual(with_future[with_future.decision_idx == 10].id.tolist(), without.id.tolist())

    def test_only_past_earnings_exclude_a_portfolio_buy(self):
        positions = {7: np.array([30])}
        decisions = np.array([28, 29, 30, 31, 32, 33])
        # Publication à 30 : connue pour les décisions 31 et 32 seulement ; ni le jour même, ni avant.
        self.assertEqual(an.past_earnings([7] * 6, decisions, positions).tolist(), [False, False, False, True, True, False])

    def test_calendar_coverage(self):
        self.assertEqual(an.calendar_covered([7, 8, np.nan], {7: np.array([1])}).tolist(), [True, False, False])


class Delisting(unittest.TestCase):
    def test_a_delisted_stock_leaves_the_plan_and_the_rest_is_rebalanced(self):
        dates = pd.bdate_range("2024-01-01", periods=40)
        w = an.portfolio_weights([2, 2, 12], ["A", "B", "B"], dates, hold=20, cap=1.0, last_rows={"A": 7, "B": 39})
        filled = w.dropna(how="all")
        self.assertEqual(filled.index.tolist(), [dates[2], dates[8], dates[32]])
        self.assertEqual(filled.loc[dates[2]].tolist(), [0.5, 0.5])
        self.assertEqual(filled.loc[dates[8]].tolist(), [0.0, 1.0])     # A sorti à la ligne 7 : B seul ensuite
        self.assertEqual(filled.loc[dates[32]].tolist(), [0.0, 0.0])

    def test_no_buy_after_the_last_listing(self):
        dates = pd.bdate_range("2024-01-01", periods=30)
        w = an.portfolio_weights([10], ["A"], dates, hold=5, last_rows={"A": 8})
        self.assertTrue(w.dropna(how="all").empty)


def fake_market(dates, opens, exits=None):
    """Marché inventé au format de `load_universe`, coûts nuls, tout achetable."""
    from types import SimpleNamespace
    from universe_data import Universe
    columns = opens.columns
    ones = pd.DataFrame(1.0, index=dates, columns=columns)
    data = Universe(open=opens, high=opens, low=opens, close=opens, volume=ones * 1e6, raw_close=opens, dollar_volume=ones * 1e9,
                    traded=ones.astype(bool), tradable=ones.astype(bool), cost_bps=ones * 0.0)
    bench = pd.DataFrame({"SPY": 100.0, "QQQ": 100.0, "BIL": 100.0}, index=dates)
    benchmarks = lab.Panel(bench, bench, bench, bench, bench * 0 + 1e6)
    exits = exits if exits is not None else pd.DataFrame(np.nan, index=columns, columns=["base", "optimistic", "pessimistic"])
    return SimpleNamespace(data=data, benchmarks=benchmarks, exits=exits, securities=pd.DataFrame(index=columns))


class FullPortfolio(unittest.TestCase):
    def test_a3_through_run_variant(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        dates = pd.bdate_range("2018-01-02", periods=60)
        opens = pd.DataFrame({"A#0": 100 * 1.01 ** np.arange(60), "B#0": 50.0}, index=dates)
        market = fake_market(dates, opens)
        a3 = pd.DataFrame({"decision_row": [3], "security_id": ["A#0"], "tradable_a3": [True], "past_earnings": [False]})
        written = []
        saved = (lab.record_trial, run.reference_buy_and_hold)
        lab.record_trial = lambda *args, **kwargs: written.append(args[1])
        run.reference_buy_and_hold = lambda: {"base": 16_000.0}
        try:
            out = run.portfolio(a3, market)
        finally:
            lab.record_trial, run.reference_buy_and_hold = saved
        self.assertEqual(written, [run.TRIAL_NAME])                # journal intercepté, rien d'écrit
        # 10 % investis pendant 20 séances à +1 % par jour, le reste en liquidités à 0 %, SPY immobile.
        self.assertAlmostEqual(out["strategy"]["final_capital"], 10_000 * (0.9 + 0.1 * 1.01 ** 20), places=4)
        self.assertAlmostEqual(out["spy"]["final_capital"], 10_000 * (1 - 0.0005) ** 2, places=4)   # SPY paie 5 pb par côté
        self.assertEqual(out["buys"], 1)


class Launcher(unittest.TestCase):
    def table(self, n=2):
        return pd.DataFrame({"in_daily": True, "row": [70, 80][:n], "col": [0, 0][:n], "cost_bps": 10.0, "before_row": [69, 79][:n]})

    def test_daily_windows_scenarios_and_costs(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        dates = pd.bdate_range("2018-01-02", periods=160)
        opens = pd.DataFrame({"A#0": 100.0 * 1.001 ** np.arange(160)}, index=dates)
        market = fake_market(dates, opens)
        table = self.table()
        run.daily_returns(table, market)
        expected = 1.001 ** 19 - 1                                   # ouverture = clôture dans ce marché inventé
        self.assertAlmostEqual(table.ab_20_base[0], expected)
        self.assertAlmostEqual(table.net_ab_20_pessimistic[0], (1 + expected) * (1 - 0.001) ** 2 - 1)
        self.assertAlmostEqual(table.ab_before_base[0], expected)      # 20 séances finies à la ligne 69
        self.assertAlmostEqual(table.ab_placebo_base[0], expected)
        self.assertAlmostEqual(table.ab_60_base[0], 1.001 ** 59 - 1)
        early = pd.DataFrame({"in_daily": True, "row": [30], "col": [0], "cost_bps": 10.0, "before_row": [29]})
        run.daily_returns(early, market)
        self.assertTrue(np.isnan(early.ab_placebo_base[0]))          # pas 60 séances d'historique

    def test_window_after_2024_is_missing(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        dates = pd.bdate_range("2018-01-02", periods=40)
        market = fake_market(dates, pd.DataFrame({"A#0": 100.0}, index=dates))
        table = pd.DataFrame({"in_daily": True, "row": [30], "col": [0], "cost_bps": 10.0, "before_row": [29]})
        run.daily_returns(table, market)
        self.assertTrue(np.isnan(table.ab_20_base[0]))
        self.assertFalse(np.isnan(table.ab_5_base[0]))


class Statistics(unittest.TestCase):
    def test_headline_is_the_plain_t_with_its_own_interval(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        from scipy import stats
        rng = np.random.default_rng(2)
        quarters = pd.period_range("2018Q1", periods=28, freq="Q")
        frame = pd.DataFrame({"quarter": np.repeat(quarters, 3), "positive": True, "v": rng.normal(0.01, 0.02, 84)})
        out = run.mean_test(frame, "v", require=True)
        x = frame.groupby("quarter").v.mean()
        se = x.std(ddof=1) / np.sqrt(28)
        self.assertAlmostEqual(out["t"], x.mean() / se)
        self.assertAlmostEqual(out["p"], 2 * stats.t.sf(abs(x.mean() / se), 27))
        self.assertAlmostEqual(out["ci_low"], x.mean() - stats.t.ppf(0.975, 27) * se)
        self.assertNotEqual(out["t"], out["newey_west"]["t"])

    def test_a_missing_quarter_stops_a_confirmatory_test(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        quarters = pd.period_range("2018Q1", periods=27, freq="Q")
        frame = pd.DataFrame({"quarter": quarters, "positive": True, "v": np.linspace(0, 1, 27)})
        with self.assertRaises(RuntimeError):
            run.mean_test(frame, "v", require=True)

    def test_holm_mixing_one_and_two_sided_p(self):
        from events import holm
        self.assertEqual([round(v, 6) for v in holm([0.01, 0.04, 0.03])], [0.03, 0.06, 0.06])


class DryRun(unittest.TestCase):
    @unittest.skipUnless((Path(__file__).resolve().parents[1] / "data" / "news" / "news_articles.parquet").exists(), "données absentes")
    def test_dry_run_reads_no_return(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_analyst_study as run
        def forbidden(*args, **kwargs):
            raise AssertionError("appel interdit pendant l'essai à blanc")
        saved = (run.daily_returns, run.portfolio, run.analyze, lab.backtest, lab.record_trial)
        run.daily_returns = run.portfolio = run.analyze = lab.backtest = lab.record_trial = forbidden
        try:
            funnel = run.main(["--dry-run"])
        finally:
            run.daily_returns, run.portfolio, run.analyze, lab.backtest, lab.record_trial = saved
        self.assertGreater(funnel["main_upgrades"], 10_000)
        self.assertGreater(funnel["credit_agency_titles_refused"], 0)


if __name__ == "__main__":
    unittest.main()
