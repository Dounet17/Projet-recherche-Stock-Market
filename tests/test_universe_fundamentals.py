"""Vérifie le BPA sur 12 mois : date de disponibilité, fractionnements et trimestres manquants."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from universe_data import load_universe, ttm_eps_column


def quarters(ends, filed, eps):
    return pd.DataFrame({"period_end": pd.to_datetime(ends), "filed": pd.to_datetime(filed), "eps": eps})


ENDS = ["2020-03-31", "2020-06-30", "2020-09-30", "2020-12-31"]
FILED = ["2020-05-01", "2020-08-03", "2020-11-02", "2021-02-01"]


class TtmEps(unittest.TestCase):
    def setUp(self):
        self.dates = pd.bdate_range("2020-01-01", "2021-12-31").to_numpy()

    def at(self, series, day):
        return series[np.searchsorted(self.dates, np.datetime64(day))]

    def test_only_available_the_day_after_the_last_filing(self):
        out = ttm_eps_column(quarters(ENDS, FILED, [1.0, 2, 3, 4]), self.dates, np.ones(len(self.dates)))
        self.assertTrue(np.isnan(self.at(out, "2021-02-01")))
        self.assertEqual(self.at(out, "2021-02-02"), 10.0)

    def test_two_for_one_split_halves_the_eps(self):
        # Fractionnement 2 pour 1 le 01/03/2021 : le facteur double, le BPA par action est divisé par 2.
        factor = np.where(self.dates < np.datetime64("2021-03-01"), 0.5, 1.0)
        out = ttm_eps_column(quarters(ENDS, FILED, [1.0, 2, 3, 4]), self.dates, factor)
        self.assertEqual(self.at(out, "2021-02-26"), 10.0)
        self.assertEqual(self.at(out, "2021-03-01"), 5.0)

    def test_split_between_two_filings_uses_each_scale(self):
        # Les trois premiers sont publiés avant le fractionnement, le dernier après, déjà à la nouvelle échelle.
        factor = np.where(self.dates < np.datetime64("2021-01-04"), 0.5, 1.0)
        out = ttm_eps_column(quarters(ENDS, FILED, [2.0, 2, 2, 1]), self.dates, factor)
        self.assertEqual(self.at(out, "2021-02-02"), 4.0)

    def test_missing_quarter_gives_nothing(self):
        out = ttm_eps_column(quarters(["2020-03-31", "2020-06-30", "2020-12-31", "2021-03-31"], ["2020-05-01", "2020-08-03", "2021-02-01", "2021-05-03"], [1.0, 1, 1, 1]), self.dates, np.ones(len(self.dates)))
        self.assertTrue(np.isnan(out).all())

    def test_figure_expires(self):
        out = ttm_eps_column(quarters(ENDS, FILED, [1.0, 2, 3, 4]), self.dates, np.ones(len(self.dates)))
        self.assertEqual(self.at(out, "2021-07-19"), 10.0)  # fin de période + 200 jours
        self.assertTrue(np.isnan(self.at(out, "2021-07-20")))


@unittest.skipUnless((ROOT / "data" / "universe_clean" / "prices_dev.parquet").exists(), "grand dataset absent")
class RealCompanies(unittest.TestCase):
    def test_tesla_figures_around_the_2022_split(self):
        eps = load_universe(symbols=("TSLA",), fundamentals=True).data.eps_ttm["TSLA#0"]
        # T4 2022 1,07 + T1 2023 0,73 + T2 0,78 + T3 0,53, ordres de grandeur connus et cités de mémoire.
        self.assertAlmostEqual(eps.loc["2023-12-29"], 3.11, delta=0.1)
        # Fractionnement 3 pour 1 le 25/08/2022, sans nouvelle publication entre ces deux dates.
        self.assertAlmostEqual(eps.loc["2022-09-01"] / eps.loc["2022-08-24"], 1 / 3, places=3)


if __name__ == "__main__":
    unittest.main()
