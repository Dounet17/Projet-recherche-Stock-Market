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
    def test_decision_is_the_first_close_after_the_note(self):
        closes = np.array([100, 200, 300])
        self.assertEqual(an.decision_sessions([50, 100, 150, 300], closes).tolist(), [0, 1, 1, 3])

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
        table["quarter"] = table.entry_date.dt.to_period("Q")
        noise = lambda: rng.normal(0, 0.05, n)
        for horizon in run.HORIZONS:
            for scenario in run.SCENARIOS:
                table[f"ab_{horizon}_{scenario}"] = noise() + (0.03 * table.positive if horizon == 20 else 0)
        for name in ("net_ab_20", "net_ab_20_double", "ab_placebo", "ab_before"):
            table[name] = noise()
        run.portfolio = lambda table, market: {"p_one_sided": 0.4, "compare_vs_spy": {"annual_log_excess": -0.01},
                                               "strategy": {"final_capital": 9000.0}, "spy": {"final_capital": 24000.0}}
        report = run.analyze(table, market=None)
        self.assertEqual(set(report["confirmatory"]), {"A1", "A2", "A3"})
        self.assertLess(report["confirmatory"]["A1"]["p_holm"], 0.01)
        self.assertGreater(report["confirmatory"]["A2"]["p_holm"], 0.01)
        self.assertEqual(len(report["secondary"]), 7)
        import json
        json.dumps(report, default=float)


if __name__ == "__main__":
    unittest.main()
