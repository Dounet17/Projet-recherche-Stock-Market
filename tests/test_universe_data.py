"""Calculs manuels synthétiques et contrôles descriptifs des données 2016-2024."""

import resource
import sys
import tempfile
import time
import unittest
from dataclasses import fields
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lab import DEV_END, Panel, load_panel
from universe_data import Universe, load_universe


def security(symbol="A", **changes):
    row = dict(security_id=f"{symbol}#0", symbol=symbol, security_type="common",
               too_short=False, alive_at_end=True, exit_return_base=np.nan,
               exit_return_optimistic=np.nan, exit_return_pessimistic=np.nan)
    row.update(changes)
    return row


def price_rows(symbol="A", closes=(10,) * 30, **columns):
    dates = pd.bdate_range("2020-01-02", periods=len(closes))
    rows = []
    for i, close in enumerate(closes):
        row = dict(security_id=f"{symbol}#0", ts_utc=dates[i].tz_localize("America/New_York").tz_convert("UTC"),
                   open=close, high=close, low=close, close=close, adj_close=close,
                   volume=100_000.0, traded=True, suspect_print=False)
        for name, values in columns.items():
            row[name] = values[i]
        rows.append(row)
    return rows


def write_dataset(path, rows, securities=None):
    path.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path / "prices_dev.parquet", index=False)
    pd.DataFrame([security()] if securities is None else securities).to_parquet(
        path / "securities_dev.parquet", index=False)


class SyntheticUniverse(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name)

    def load(self, **kwargs):
        return load_universe(path=self.path, benchmarks=(), **kwargs)

    def test_adjusted_open_high_low_and_raw_price(self):
        rows = price_rows(closes=[20, 40], open=[18, 44], high=[24, 48], low=[16, 36], adj_close=[10, 10])
        write_dataset(self.path, rows)
        data = self.load().data
        self.assertIsInstance(data, Panel)
        self.assertIsInstance(data, Universe)
        np.testing.assert_allclose(data.open["A#0"], [9, 11])
        np.testing.assert_allclose(data.high["A#0"], [12, 12])
        np.testing.assert_allclose(data.low["A#0"], [8, 9])
        np.testing.assert_allclose(data.close["A#0"], [10, 10])
        np.testing.assert_allclose(data.raw_close["A#0"], [20, 40])
        self.assertIsNone(data.dates.tz)
        self.assertEqual(data.dates.name, "date")
        self.assertEqual(data.dates[0], pd.Timestamp("2020-01-02"))

    def test_untraded_suspect_and_absent_rows(self):
        rows = price_rows(closes=[10] * 13)
        rows[10].update(traded=False, volume=0)
        rows[11].update(suspect_print=True)
        rows.pop()
        rows += price_rows(symbol="B", closes=[10] * 13)
        write_dataset(self.path, rows, [security(), security("B")])
        data = self.load(symbols=["A"]).data
        for field in ("open", "high", "low", "close", "volume"):
            self.assertTrue(getattr(data, field)["A#0"].iloc[10:].isna().all())
        self.assertEqual(data.raw_close["A#0"].iloc[10], 10)
        self.assertTrue(data.raw_close["A#0"].iloc[11:].isna().all())
        self.assertFalse(data.traded["A#0"].iloc[10])
        self.assertTrue(data.traded["A#0"].iloc[11])
        self.assertFalse(data.traded["A#0"].iloc[12])
        self.assertFalse(data.tradable["A#0"].iloc[10:].any())
        self.assertEqual(len(data.dates), 13)
        self.assertEqual(data.dollar_volume["A#0"].iloc[10], 1_000_000)

    def test_untraded_zero_counts_in_liquidity_median(self):
        rows = price_rows(closes=[10] * 20)
        for row in rows[10:]:
            row.update(traded=False, volume=0)
        write_dataset(self.path, rows)
        data = self.load().data
        # Dix montants de 1 M$ et dix zéros : médiane = 0,5 M$.
        self.assertEqual(data.dollar_volume.iloc[-1, 0], 500_000)
        self.assertEqual(data.raw_close.iloc[-1, 0], 10)

    def test_suspect_does_not_count_as_zero_in_median(self):
        rows = price_rows(closes=[10] * 20)
        for row in rows[10:]:
            row.update(suspect_print=True)
        write_dataset(self.path, rows)
        data = self.load().data
        self.assertEqual(data.dollar_volume.iloc[-1, 0], 1_000_000)

    def test_aberrant_open_only_masks_open_and_boundaries_are_valid(self):
        rows = price_rows(closes=[12] * 15, open=[12] * 10 + [2784, 3, 4, 36, 36.01])
        write_dataset(self.path, rows)
        data = self.load().data
        np.testing.assert_allclose(data.open.iloc[10:, 0], [np.nan, np.nan, 4, 36, np.nan], equal_nan=True)
        np.testing.assert_allclose(data.close.iloc[10:, 0], 12)
        self.assertTrue(data.tradable.iloc[10:, 0].all())

    def test_cumulative_suspect_gain_neutralization_keeps_real_drop(self):
        closes = [10, 999, 20, 24, 999, 48, 60, .1, 6, 7]
        rows = price_rows(closes=closes, suspect_print=[False, True, False, False, True,
                                                      False, False, True, False, False])
        write_dataset(self.path, rows)
        data = self.load().data
        expected = [10, np.nan, 10, 12, np.nan, 12, 15, np.nan, 1.5, 1.75]
        for field in ("open", "high", "low", "close"):
            np.testing.assert_allclose(getattr(data, field).iloc[:, 0], expected, equal_nan=True)
        # La correction ne touche ni le filtre de prix brut ni la liquidité.
        self.assertEqual(data.raw_close.iloc[5, 0], 48)

    def test_untraded_hole_does_not_neutralize_gain(self):
        write_dataset(self.path, price_rows(closes=[10, 10, 20], traded=[True, False, True]))
        np.testing.assert_allclose(self.load().data.close.iloc[:, 0], [10, np.nan, 20], equal_nan=True)

    def test_multiple_suspects_before_resume_are_counted_once(self):
        write_dataset(self.path, price_rows(closes=[10, 99, 999, 40, 44],
                                            suspect_print=[False, True, True, False, False]))
        np.testing.assert_allclose(self.load().data.close.iloc[:, 0],
                                   [10, np.nan, np.nan, 10, 11], equal_nan=True)

    def test_no_previous_valid_price_does_not_invent_one(self):
        write_dataset(self.path, price_rows(closes=[99, 20, 22], suspect_print=[True, False, False]))
        np.testing.assert_allclose(self.load().data.close.iloc[:, 0], [np.nan, 20, 22], equal_nan=True)

    def test_tradable_uses_raw_price_and_inclusive_thresholds(self):
        rows = price_rows(closes=[5] * 11 + [4.99], adj_close=[.01] * 12, volume=[200_000] * 12)
        write_dataset(self.path, rows)
        data = self.load().data
        np.testing.assert_array_equal(data.tradable.iloc[:, 0], [False] * 9 + [True, True, False])
        self.assertEqual(data.dollar_volume.iloc[9, 0], 1_000_000)
        self.assertFalse(self.load(min_dollar_volume=1_000_001).data.tradable.to_numpy().any())
        self.assertFalse(self.load(min_price=5.01).data.tradable.to_numpy().any())

    def test_costs_use_previous_close_information_and_exact_buckets(self):
        amounts = {"A": 100_000_000, "B": 10_000_000, "C": 1_000_000, "D": 999_999}
        rows = []
        for symbol, amount in amounts.items():
            rows += price_rows(symbol, closes=[10] * 12, volume=[amount / 10] * 12)
        write_dataset(self.path, rows, [security(s) for s in amounts])
        data = self.load().data
        # Au jour 9, la première médiane existe mais l'ouverture est encore à 100 pb.
        np.testing.assert_array_equal(data.cost_bps.iloc[:10], 100)
        np.testing.assert_array_equal(data.cost_bps.iloc[10], [5, 15, 40, 100])
        self.assertFalse(data.cost_bps.isna().to_numpy().any())
        changed = [dict(row) for row in rows]
        for row in changed:
            if row["ts_utc"] == rows[10]["ts_utc"]:
                row["volume"] *= 1000
        write_dataset(self.path, changed, [security(s) for s in amounts])
        pd.testing.assert_series_equal(data.cost_bps.iloc[10], self.load().data.cost_bps.iloc[10])

    def test_filters_metadata_exits_and_benchmarks(self):
        stocks = [security(), security("B", security_type="adr", alive_at_end=False,
                                       exit_return_base=-1., exit_return_optimistic=-.5,
                                       exit_return_pessimistic=-1.),
                  security("SHORT", too_short=True), security("SPY", security_type="fund")]
        rows = sum([price_rows(s["symbol"]) for s in stocks], [])
        write_dataset(self.path, rows, stocks)
        market = load_universe(path=self.path, benchmarks=("SPY",))
        self.assertEqual(list(market.data.close.columns), ["A#0", "B#0"])
        self.assertEqual(list(market.benchmarks.close.columns), ["SPY"])
        self.assertEqual(list(market.exits.columns), ["base", "optimistic", "pessimistic"])
        self.assertTrue(market.exits.loc["A#0"].isna().all())
        np.testing.assert_allclose(market.exits.loc["B#0"], [-1, -.5, -1])
        self.assertTrue(market.data.dates.equals(market.benchmarks.dates))
        self.assertEqual(list(self.load(symbols=["B"]).data.close.columns), ["B#0"])
        self.assertEqual(list(self.load(types=("fund",)).data.close.columns), ["SPY#0"])
        self.assertFalse(any(hasattr(market.data, name) for name in
                             ("last_trade", "alive_at_end", "exit_return_base", "mean_dollar_volume")))
        with self.assertRaisesRegex(ValueError, "QQQ.*fonds vivant"):
            load_universe(path=self.path, benchmarks=("QQQ",))

    def test_benchmarks_obey_the_same_price_rules(self):
        rows = price_rows("SPY", closes=[20, 999, 40, 44], adj_close=[10, 499.5, 20, 22],
                          open=[18, 999, 10000, 44], suspect_print=[False, True, False, False])
        write_dataset(self.path, rows, [security("SPY", security_type="fund")])
        market = load_universe(path=self.path, types=("fund",), benchmarks=("SPY",))
        for name in ("open", "high", "low", "close", "volume"):
            np.testing.assert_allclose(getattr(market.data, name).iloc[:, 0],
                                       getattr(market.benchmarks, name).iloc[:, 0], equal_nan=True)
        np.testing.assert_allclose(market.benchmarks.close.SPY, [10, np.nan, 10, 11], equal_nan=True)
        self.assertTrue(np.isnan(market.benchmarks.open.SPY.iloc[2]))

    def test_holdout_lock_precedes_every_read_and_matches_lab(self):
        with patch("pandas.read_parquet", side_effect=AssertionError("Lecture interdite")):
            with self.assertRaises(PermissionError) as universe_error:
                self.load(end="2025-01-01")
            with self.assertRaises(PermissionError) as lab_error:
                load_panel(end="2025-01-01")
        self.assertEqual(str(universe_error.exception), str(lab_error.exception))
        write_dataset(self.path, price_rows())
        self.assertEqual(len(self.load(end="2025-01-01", allow_holdout=True).data.dates), 30)

    def test_truncate_cuts_every_matrix_and_keeps_future_columns(self):
        rows = price_rows() + price_rows("B")[20:]
        write_dataset(self.path, rows, [security(), security("B")])
        full = self.load().data
        truncated = full.truncate(full.dates[12])
        self.assertIsInstance(truncated, Universe)
        for field in fields(Universe):
            expected = getattr(full, field.name).iloc[:13]
            pd.testing.assert_frame_equal(getattr(truncated, field.name), expected)
            self.assertEqual(list(getattr(truncated, field.name).columns), ["A#0", "B#0"])

    def test_prefix_invariance_with_end_filter_and_physically_cut_files(self):
        rows = price_rows(closes=[10] * 12 + [999, 20, 24] + [24] * 15,
                          suspect_print=[False] * 12 + [True] + [False] * 17)
        rows += price_rows("B")[20:]
        stocks = [security(), security("B")]
        # Un ordre de stockage différent ne change pas le calendrier.
        write_dataset(self.path, rows[::-1], stocks)
        full = self.load().data
        for position in (8, 12, 13, 18, 25):
            cutoff = full.dates[position]
            partial = self.load(end=cutoff).data
            cropped = self.path / f"cut_{position}"
            write_dataset(cropped, [row for row in rows if
                                     row["ts_utc"].tz_convert("America/New_York").tz_localize(None) <= cutoff], stocks)
            physical = load_universe(path=cropped, benchmarks=()).data
            for name in ("close", "tradable", "cost_bps", "dollar_volume"):
                expected = getattr(full.truncate(cutoff), name)
                pd.testing.assert_frame_equal(getattr(partial, name), expected)
                pd.testing.assert_frame_equal(getattr(physical, name), expected)


@unittest.skipUnless((ROOT / "data/universe_clean/prices_dev.parquet").is_file(),
                     "data/universe_clean absent")
class RealUniverse(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        started = time.perf_counter()
        cls.market = load_universe()
        elapsed = time.perf_counter() - started
        peak_mib = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        print(f"\nload_universe() : {elapsed:.3f} s ; pic RAM processus : {peak_mib:.1f} MiB", flush=True)

    def test_default_columns_and_tradability(self):
        data = self.market.data
        self.assertEqual(data.close.shape[1], 8123)
        self.assertFalse((data.tradable & data.close.isna()).to_numpy().any())
        self.assertFalse(data.cost_bps.isna().to_numpy().any())
        self.assertLessEqual(data.dates.max(), pd.Timestamp(DEV_END))

    def test_bcei_has_no_gain_across_bankruptcy(self):
        close = self.market.data.close["BCEI#0"].loc["2017-04-20":"2017-05-05"].dropna()
        returns = close.pct_change(fill_method=None)
        resumed = close.loc["2017-05-01":].index[0]
        print(f"BCEI : rendement à la reprise du {resumed.date()} = {returns.loc[resumed]:.12g}", flush=True)
        self.assertLessEqual(returns.loc[resumed], 1e-12)

    def test_sivb_stops_on_march_ninth(self):
        self.assertTrue(self.market.data.close.loc["2023-03-10":, "SIVB#0"].isna().all())
        self.assertEqual(self.market.data.close["SIVB#0"].last_valid_index(), pd.Timestamp("2023-03-09"))

    def test_source_quality_diagnostics(self):
        data = self.market.data
        source = pd.read_parquet(
            ROOT / "data/universe_clean/prices_dev.parquet",
            columns=["security_id", "ts_utc", "open", "close", "adj_close", "traded", "suspect_print"],
            filters=[("ts_utc", "<=", pd.Timestamp(DEV_END, tz="America/New_York").tz_convert("UTC")),
                     ("security_id", "in", list(data.close.columns))])
        valid = source.traded.to_numpy() & ~source.suspect_print.to_numpy()
        ratio = source.open.to_numpy() / source.close.to_numpy()
        bad_open = valid & ((ratio < 1 / 3) | (ratio > 3))
        codes, timestamps = pd.factorize(source.ts_utc)
        dates = pd.DatetimeIndex(timestamps).tz_convert("America/New_York").tz_localize(None).normalize()
        rows = data.dates.get_indexer(dates)[codes]
        cols = data.close.columns.get_indexer(source.security_id)
        normalized = data.close.to_numpy()[rows, cols]
        changed = valid & ~np.isclose(normalized, source.adj_close.to_numpy(), rtol=1e-12, atol=0)
        events = 0
        suspect_ids = source.loc[source.suspect_print, "security_id"].unique()
        for _, group in source.loc[source.security_id.isin(suspect_ids)].groupby("security_id", sort=False):
            group = group.sort_values("ts_utc")
            original = group.adj_close.to_numpy()
            good = np.flatnonzero(group.traded.to_numpy() & ~group.suspect_print.to_numpy()
                                  & np.isfinite(original))
            resumed = np.unique(np.searchsorted(good, np.flatnonzero(group.suspect_print), side="right"))
            resumed = resumed[(resumed > 0) & (resumed < len(good))]
            previous, following = good[resumed - 1], good[resumed]
            events += int((original[following] > original[previous]).sum())
            loaded = normalized[source.index.get_indexer(group.index)]
            self.assertTrue((loaded[following] <= loaded[previous] * (1 + 1e-12)).all())
        print(f"Univers par défaut : ouvertures aberrantes={bad_open.sum()} séances sur "
              f"{source.loc[bad_open, 'security_id'].nunique()} titres ; neutralisation="
              f"{events} reprises, {changed.sum()} séances ajustées sur "
              f"{source.loc[changed, 'security_id'].nunique()} titres", flush=True)
        # Aucune renormalisation ici : exposer la dépendance du niveau ajusté à
        # la fin du titre plutôt que la dissimuler dans un chargement tronqué.
        aapl = source.loc[source.security_id == "AAPL#0"].sort_values("ts_utc")
        at_cutoff = aapl.loc[aapl.ts_utc <= pd.Timestamp("2020-12-31", tz="America/New_York")].iloc[-1]
        last = aapl.iloc[-1]
        prefix_scale = at_cutoff.close / at_cutoff.adj_close
        final_scale = last.close / last.adj_close
        print(f"AAPL, niveau adj_close normalisé en fin de titre : facteur au 31/12/2020="
              f"{prefix_scale:.12g}, facteur au 31/12/2024={final_scale:.12g} ; "
              "couper le fichier conserve ses valeurs, recalculer le nettoyage les changerait", flush=True)

    @unittest.skipUnless((ROOT / "data/lab_daily_adjusted.parquet").is_file(), "panel historique absent")
    def test_aapl_and_spy_daily_returns_match_historical_panel(self):
        # Ce fichier se lit exclusivement par le verrou de lab.load_panel.
        reference = load_panel(symbols=["AAPL", "SPY"], end=DEV_END)
        for symbol, close in (("AAPL", self.market.data.close["AAPL#0"]),
                              ("SPY", self.market.benchmarks.close["SPY"])):
            pair = pd.concat([close.pct_change(fill_method=None),
                              reference.close[symbol].pct_change(fill_method=None)], axis=1).dropna()
            correlation = pair.iloc[:, 0].corr(pair.iloc[:, 1])
            median_error = (pair.iloc[:, 0] - pair.iloc[:, 1]).abs().median()
            print(f"{symbol} : n={len(pair)}, corrélation={correlation:.12f}, "
                  f"écart absolu médian={median_error:.12g}", flush=True)
            self.assertGreater(len(pair), 1500)
            self.assertGreater(correlation, .995)
            self.assertLess(median_error, 1e-4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
