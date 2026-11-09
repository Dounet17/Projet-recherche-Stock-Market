"""Attentes calculées à la main, avant lecture du moteur étendu.

Une ligne rapporte l'ouverture du jour à la suivante ; la liquidation à la
dernière ouverture est composée dans la dernière période (présentation historique
confirmée par le coordinateur). Aucun exemple ne lit les données réelles.
"""

import inspect
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lab import Panel, backtest


def make_panel(opens, closes=None):
    dates = pd.bdate_range("2020-01-01", periods=len(next(iter(opens.values()))))
    opening = pd.DataFrame(opens, index=dates, dtype=float)
    closing = opening.copy() if closes is None else pd.DataFrame(closes, index=dates, dtype=float)
    return Panel(opening, closing.copy(), closing.copy(), closing, closing * 0 + 1000)


@unittest.skipUnless("exits" in inspect.signature(backtest).parameters,
                     "en attente : lab.backtest n'accepte pas encore exits")
class Lifecycle(unittest.TestCase):
    def run_case(self, panel, orders, exits, cost_bps=0, **kwargs):
        weights = pd.DataFrame(np.nan, index=panel.dates, columns=panel.open.columns)
        for row, values in orders.items():
            weights.iloc[row] = values
        return backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1],
                        cost_bps=cost_bps, exits=pd.Series(exits, dtype=float), **kwargs)

    def assert_returns(self, result, expected):
        # Les calculs manuels gardent une case de liquidation séparée ; seule
        # leur présentation est fusionnée, sans modifier le capital final.
        expected = [*expected[:-2], (1 + expected[-2]) * (1 + expected[-1]) - 1]
        np.testing.assert_allclose(result.returns, expected, atol=1e-12, rtol=1e-12)

    def test_bankruptcy_entire_capital_stays_zero(self):
        panel = make_panel({"A": [100, 100, 90, np.nan, np.nan, np.nan]},
                           {"A": [100, 100, 45, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {0: [1]}, {"A": -1})
        # 1 -> 0,9 -> 0 ; le capital nul reste nul sans division par zéro.
        self.assert_returns(result, [-0.1, -1, 0, 0, 0])
        np.testing.assert_allclose((1 + result.returns).cumprod(), [.9, 0, 0, 0])

    def test_bankruptcy_half_portfolio(self):
        panel = make_panel({"A": [100, 100, 90, np.nan, np.nan, np.nan], "B": [100] * 6},
                           {"A": [100, 100, 45, np.nan, np.nan, np.nan], "B": [100] * 6})
        result = self.run_case(panel, {0: [.5, .5]}, {"A": -1, "B": np.nan})
        # A vaut 0,45 et B vaut 0,50 avant la faillite : perte de 0,45 / 0,95.
        self.assert_returns(result, [-.05, -.45 / .95, 0, 0, 0])
        self.assertAlmostEqual((1 + result.returns).prod(), .5)

    def test_cash_merger_two_percent(self):
        panel = make_panel({"A": [100, 100, 110, np.nan, np.nan, np.nan]},
                           {"A": [100, 100, 120, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {0: [1]}, {"A": .02})
        # Paiement final = 120 * 1,02 = 122,40 pour une entrée à 100.
        self.assert_returns(result, [.1, 122.4 / 110 - 1, 0, 0, 0])
        self.assertAlmostEqual((1 + result.returns).prod(), 1.224)

    def test_distress_minus_fifty_five_percent(self):
        panel = make_panel({"A": [100, 100, 110, np.nan, np.nan, np.nan]},
                           {"A": [100, 100, 120, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {0: [1]}, {"A": -.55})
        # 120 * 0,45 = 54, soit 0,54 fois le capital initial.
        self.assert_returns(result, [.1, 54 / 110 - 1, 0, 0, 0])
        self.assertAlmostEqual((1 + result.returns).prod(), .54)

    def test_buy_at_last_session_open(self):
        panel = make_panel({"A": [100, 100, 100, np.nan, np.nan, np.nan]},
                           {"A": [100, 100, 110, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {1: [1]}, {"A": .02})
        self.assert_returns(result, [0, .122, 0, 0, 0])

    def test_order_after_last_session_has_no_effect(self):
        panel = make_panel({"A": [100, 100, 110, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {2: [1]}, {"A": .02}, cost_bps=100)
        self.assert_returns(result, [0, 0, 0, 0, 0])
        np.testing.assert_allclose(result.turnover, 0)

    def test_hole_blocks_sale_until_next_valid_open(self):
        panel = make_panel({"A": [100, 100, np.nan, np.nan, 120, 120]})
        result = self.run_case(panel, {0: [1], 1: [0], 3: [0]}, {"A": np.nan}, cost_bps=10)
        # Achat à 100 ; vente impossible aux jours 2 et 3 ; reprise à 120.
        # Deux frais de 0,1 %, aucune facturation de l'ordre bloqué.
        self.assert_returns(result, [-.001, 0, .2, -.001, 0])
        np.testing.assert_allclose(result.turnover, [1, 0, 0, 1], atol=1e-12)
        self.assertAlmostEqual((1 + result.returns).prod(), .999 * 1.2 * .999)

    def test_blocked_buy_does_not_spend_cash(self):
        panel = make_panel({"A": [100, 100, np.nan, 120, 120, 120]})
        result = self.run_case(panel, {1: [1]}, {"A": np.nan}, cost_bps=100)
        # L'ordre du jour 1 n'est pas exécuté au jour 2, ni reporté au jour 3.
        self.assert_returns(result, [0, 0, 0, 0, 0])
        np.testing.assert_allclose(result.turnover, 0)

    def test_blocked_position_scales_other_targets_proportionally(self):
        panel = make_panel({"A": [100, 100, np.nan, 100, 100, 100],
                            "B": [100, 100, 100, 200, 200, 200],
                            "C": [100, 100, 100, 100, 100, 100]})
        result = self.run_case(panel, {0: [.6, 0, 0], 1: [0, .3, .1]},
                               {"A": np.nan, "B": np.nan, "C": np.nan})
        # 60 % bloqués dans A, demande 30:10 dans B:C ; elle tient exactement
        # dans les 40 % libres et B double, soit un capital final de 1,30.
        self.assert_returns(result, [0, .3, 0, 0, 0])
        # Variante : 60 % demandés dans B et 20 % dans C sont ramenés à 30:10.
        scaled = self.run_case(panel, {0: [.6, 0, 0], 1: [0, .6, .2]},
                               {"A": np.nan, "B": np.nan, "C": np.nan})
        self.assert_returns(scaled, [0, .3, 0, 0, 0])

    def test_asset_and_date_costs_include_final_liquidation(self):
        panel = make_panel({"A": [100] * 6, "B": [100] * 6})
        costs = pd.DataFrame({"A": [999, 10, 777, 777, 777, 30],
                              "B": [999, 20, 777, 777, 777, 50]}, index=panel.dates)
        result = self.run_case(panel, {0: [.25, .75]}, {"A": np.nan, "B": np.nan}, costs)
        # Entrée : 0,25*10 + 0,75*20 = 17,5 pb ; sortie : 45 pb.
        self.assert_returns(result, [-.00175, 0, 0, 0, -.0045])
        self.assertAlmostEqual((1 + result.returns).prod(), .99825 * .9955)

    def test_exit_does_not_charge_a_sale(self):
        panel = make_panel({"A": [100, 100, 100, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {0: [1]}, {"A": .02}, cost_bps=100)
        self.assert_returns(result, [-.01, .02, 0, 0, 0])
        np.testing.assert_allclose(result.turnover, [1, 0, 0, 0])

    def test_empty_rows_hold_through_exit_and_keep_cash(self):
        panel = make_panel({"A": [100, 100, 110, np.nan, np.nan, np.nan], "B": [100] * 6})
        result = self.run_case(panel, {0: [.5, .5]}, {"A": .02, "B": np.nan})
        # 0,50*1,10*1,02 + 0,50 = 1,061 ; aucune réallocation après sortie.
        self.assert_returns(result, [.05, .011 / 1.05, 0, 0, 0])
        self.assertAlmostEqual((1 + result.returns).prod(), 1.061)

    def test_last_open_before_hole_values_exit(self):
        panel = make_panel({"A": [100, 100, np.nan, np.nan, np.nan, np.nan]},
                           {"A": [100, 100, 110, np.nan, np.nan, np.nan]})
        result = self.run_case(panel, {0: [1]}, {"A": .02})
        self.assert_returns(result, [0, .122, 0, 0, 0])

    def test_short_is_forbidden_in_lifecycle_mode(self):
        panel = make_panel({"A": [100] * 6})
        with self.assertRaises(ValueError):
            self.run_case(panel, {0: [1]}, {"A": np.nan}, allow_short=True)

    def test_none_keeps_missing_price_error(self):
        panel = make_panel({"A": [100, 100, np.nan, 110, 110, 110]})
        weights = pd.DataFrame({"A": [1, np.nan, np.nan, np.nan, np.nan, np.nan]}, index=panel.dates)
        with self.assertRaises(ValueError):
            backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=5, exits=None)

    def test_none_keeps_historical_scalar_cost_accounting(self):
        panel = make_panel({"A": [100, 100, 110, 121, 133.1, 146.41]})
        weights = pd.DataFrame({"A": [1, np.nan, np.nan, np.nan, np.nan, np.nan]}, index=panel.dates)
        historical = backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=5)
        explicit = backtest(weights, panel, start=panel.dates[1], end=panel.dates[-1], cost_bps=5, exits=None)
        # Quatre hausses de 10 %, achat et liquidation à 5 pb chacun.
        expected = [.9995 * 1.1 - 1, .1, .1, .1, -.0005]
        self.assert_returns(historical, expected)
        self.assert_returns(explicit, expected)
        self.assertAlmostEqual((1 + explicit.returns).prod(), 1.4641 * .9995 ** 2)

    def test_end_inside_complete_panel_excludes_next_open_gain(self):
        panel = make_panel({"A": [100, 100, 100, 100, 100, 200]})
        weights = pd.DataFrame({"A": [1, np.nan, np.nan, np.nan, np.nan, np.nan]}, index=panel.dates)
        result = backtest(weights, panel, start=panel.dates[1], end=panel.dates[4],
                          cost_bps=0, exits=pd.Series({"A": np.nan}))
        # Fin au jour 4 : vente à 100, le doublement du jour 5 est hors fenêtre.
        self.assertAlmostEqual((1 + result.returns).prod(), 1.0)

    def test_final_liquidation_cost_is_validated_too(self):
        panel = make_panel({"A": [100] * 6})
        costs = pd.DataFrame({"A": [5, 5, 5, 5, 5, np.nan]}, index=panel.dates)
        with self.assertRaises(ValueError):
            self.run_case(panel, {0: [1]}, {"A": np.nan}, costs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
