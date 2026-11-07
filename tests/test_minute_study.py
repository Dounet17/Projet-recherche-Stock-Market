"""Tests de l'étude à la minute sur des données inventées, valeurs calculées à la main. Aucun vrai cours n'est lu.

Depuis la racine : venv/bin/python tests/test_minute_study.py
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import minute_study as ms

M = ms.MINUTE


def ns(text):
    """Heure de New York -> ns UTC."""
    return pd.Timestamp(text, tz="America/New_York").tz_convert("UTC").value


def bars(rows):
    """rows : (heure de New York, ouverture, clôture)."""
    return ms.Bars([ns(t) for t, _, _ in rows], [o for _, o, _ in rows], [c for _, _, c in rows])


CALENDAR = pd.DataFrame({
    "date": pd.to_datetime(["2024-03-07", "2024-03-08", "2024-03-11", "2024-11-29"]),
    "open": pd.to_datetime(["2024-03-07 09:30", "2024-03-08 09:30", "2024-03-11 09:30", "2024-11-29 09:30"]),
    "close": pd.to_datetime(["2024-03-07 16:00", "2024-03-08 16:00", "2024-03-11 16:00", "2024-11-29 13:00"]),
})


class Clock(unittest.TestCase):
    def setUp(self):
        self.sessions = ms.session_table(CALENDAR)

    def entry(self, when):
        return self.sessions.date.iloc[ms.entry_sessions([ns(when)], self.sessions.open_ns.to_numpy())[0]]

    def placebo(self, when):
        return self.sessions.date.iloc[ms.placebo_sessions([ns(when)], self.sessions.close_ns.to_numpy())[0]]

    def test_units_are_nanoseconds(self):
        self.assertEqual(self.sessions.open_ns.iloc[0], pd.Timestamp("2024-03-07 14:30", tz="UTC").value)

    def test_wire_before_925_enters_the_same_day(self):
        self.assertEqual(self.entry("2024-03-08 09:25:00"), pd.Timestamp("2024-03-08"))
        self.assertEqual(self.entry("2024-03-08 07:00"), pd.Timestamp("2024-03-08"))

    def test_wire_after_925_waits_for_the_next_session(self):
        self.assertEqual(self.entry("2024-03-08 09:25:01"), pd.Timestamp("2024-03-11"))
        self.assertEqual(self.entry("2024-03-08 11:00"), pd.Timestamp("2024-03-11"))

    def test_friday_after_close_enters_monday(self):
        self.assertEqual(self.entry("2024-03-08 16:05"), pd.Timestamp("2024-03-11"))

    def test_placebo_is_the_last_finished_session(self):
        self.assertEqual(self.placebo("2024-03-08 16:05"), pd.Timestamp("2024-03-08"))
        self.assertEqual(self.placebo("2024-03-08 15:59"), pd.Timestamp("2024-03-07"))
        self.assertEqual(self.placebo("2024-03-11 07:00"), pd.Timestamp("2024-03-08"))

    def test_half_day_closes_at_13h(self):
        last = self.sessions.iloc[-1]
        self.assertEqual(last.close_ns - last.open_ns, int(3.5 * 60) * M)


class Trades(unittest.TestCase):
    OPEN, CLOSE = ns("2024-03-08 09:30"), ns("2024-03-08 16:00")

    def spy(self):
        return bars([("2024-03-08 09:30", 500, 501), ("2024-03-08 09:31", 501, 502), ("2024-03-08 15:59", 505, 510)])

    def test_open_to_close_and_spy_on_the_same_minutes(self):
        stock = bars([("2024-03-08 09:30", 10, 10.5), ("2024-03-08 12:00", 10.5, 11), ("2024-03-08 15:59", 11, 12)])
        r, spy, entry = ms.trade(stock, self.spy(), self.OPEN, self.CLOSE)
        self.assertAlmostEqual(r, 12 / 10 - 1)
        self.assertAlmostEqual(spy, 510 / 500 - 1)
        self.assertEqual(entry, self.OPEN)

    def test_bars_before_entry_and_after_close_are_ignored(self):
        stock = bars([("2024-03-08 09:29", 1, 1), ("2024-03-08 09:31", 10, 10), ("2024-03-08 15:58", 10, 11), ("2024-03-08 16:00", 11, 99)])
        r, spy, entry = ms.trade(stock, self.spy(), self.OPEN, self.CLOSE)
        self.assertAlmostEqual(r, 0.1)
        self.assertEqual(entry, ns("2024-03-08 09:31"))
        # SPY : entrée à la barre de 9 h 31, sortie à la dernière barre commencée avant ou à 15 h 58.
        self.assertAlmostEqual(spy, 502 / 501 - 1)

    def test_no_bar_in_the_first_six_minutes_means_no_trade(self):
        stock = bars([("2024-03-08 09:36", 10, 10), ("2024-03-08 15:59", 10, 11)])
        r, _, entry = ms.trade(stock, self.spy(), self.OPEN, self.CLOSE)
        self.assertTrue(np.isnan(r))
        self.assertIsNone(entry)
        stock = bars([("2024-03-08 09:35", 10, 10), ("2024-03-08 15:59", 10, 11)])
        self.assertAlmostEqual(ms.trade(stock, self.spy(), self.OPEN, self.CLOSE)[0], 0.1)

    def test_late_entry_at_0935(self):
        stock = bars([("2024-03-08 09:30", 10, 10), ("2024-03-08 09:37", 11, 11), ("2024-03-08 15:59", 11, 12.1)])
        r, _, entry = ms.trade(stock, self.spy(), self.OPEN + ms.LATE_START, self.CLOSE)
        self.assertAlmostEqual(r, 12.1 / 11 - 1)
        self.assertEqual(entry, ns("2024-03-08 09:37"))

    def test_single_bar_uses_its_own_open_and_close(self):
        stock = bars([("2024-03-08 09:30", 10, 10.2)])
        self.assertAlmostEqual(ms.trade(stock, self.spy(), self.OPEN, self.CLOSE)[0], 0.02)

    def test_known_price_needs_a_finished_bar(self):
        stock = bars([("2024-03-08 09:30", 10, 11), ("2024-03-08 09:31", 11, 12)])
        self.assertEqual(stock.known_at(ns("2024-03-08 09:31")), 11)
        self.assertEqual(stock.known_at(ns("2024-03-08 09:31:59")), 11)
        self.assertEqual(stock.known_at(ns("2024-03-08 09:32")), 12)
        self.assertTrue(np.isnan(stock.known_at(ns("2024-03-08 09:30:30"))))


class Event(unittest.TestCase):
    """Dépêche le jeudi 07/03 à 16 h 10, séance témoin le 07/03, entrée le 08/03. Split 2 pour 1 entre les deux."""

    def setUp(self):
        factor_thursday, factor_friday = 0.5, 1.0   # prix ajusté = prix brut x facteur
        thursday = [("2024-03-07 09:30", 198, 199), ("2024-03-07 15:59", 199, 200), ("2024-03-07 16:20", 210, 210), ("2024-03-07 17:00", 212, 214)]
        friday = [("2024-03-08 08:00", 106, 107), ("2024-03-08 09:30", 108, 108), ("2024-03-08 09:45", 109, 109.5),
                  ("2024-03-08 10:10", 110, 111), ("2024-03-08 15:59", 112, 113)]
        rows = [(t, o * factor_thursday, c * factor_thursday) for t, o, c in thursday] + friday
        self.stock = bars(rows)
        self.spy = bars([("2024-03-07 09:30", 398, 399), ("2024-03-07 15:59", 400, 400), ("2024-03-07 16:00", 400, 400), ("2024-03-07 16:20", 400, 402),
                         ("2024-03-07 17:00", 402, 402), ("2024-03-08 08:00", 402, 402), ("2024-03-08 09:30", 404, 404),
                         ("2024-03-08 10:00", 404, 404), ("2024-03-08 15:59", 404, 408)])
        self.out = ms.measure_event(self.stock, self.spy, ns("2024-03-07 16:10"), (ns("2024-03-08 09:30"), ns("2024-03-08 16:00")),
                                    (ns("2024-03-07 09:30"), ns("2024-03-07 16:00")))

    def test_main_window(self):
        self.assertAlmostEqual(self.out["h1"], 113 / 108 - 1)
        self.assertAlmostEqual(self.out["h1_spy"], 408 / 404 - 1)
        self.assertEqual(self.out["entry_delay_s"], 0)

    def test_short_windows_and_late_entry(self):
        self.assertAlmostEqual(self.out["open_30m"], 109.5 / 108 - 1)
        self.assertAlmostEqual(self.out["open_60m"], 111 / 108 - 1)
        # Aucune barre entre 9 h 35 et 9 h 41 : pas d'entrée tardive, selon la règle des 6 minutes.
        self.assertTrue(np.isnan(self.out["late"]))

    def test_extended_hours_buy_after_latency_sell_at_open(self):
        # Barre de 16 h 20 : première barre au moins 5 minutes après 16 h 10, prix ajusté 105.
        self.assertAlmostEqual(self.out["extended"], 108 / 105 - 1)
        self.assertAlmostEqual(self.out["extended_spy"], 404 / 400 - 1)

    def test_decomposition_is_split_adjusted(self):
        base = 100.0   # 200 bruts le jeudi, divisés par deux
        self.assertAlmostEqual(self.out["cum_wire_5m"], 100 / base - 1)        # rien de neuf à 16 h 15
        self.assertAlmostEqual(self.out["cum_wire_30m"], 105 / base - 1)       # barre de 16 h 20 terminée
        self.assertAlmostEqual(self.out["cum_wire_60m"], 107 / base - 1)       # la barre de 17 h est finie à 17 h 01
        self.assertAlmostEqual(self.out["cum_open"], 108 / base - 1)
        self.assertAlmostEqual(self.out["cum_open_30m_mark"], 109.5 / base - 1)
        self.assertAlmostEqual(self.out["cum_close"], 113 / base - 1)
        self.assertAlmostEqual(self.out["cum_close_spy"], 408 / 400 - 1)

    def test_placebo_uses_only_the_previous_session(self):
        self.assertAlmostEqual(self.out["placebo"], 100 / 99 - 1)
        self.assertAlmostEqual(self.out["placebo_spy"], 400 / 398 - 1)

    def test_missing_factor_gives_no_return(self):
        stock = bars([("2024-03-08 09:30", np.nan, np.nan), ("2024-03-08 15:59", np.nan, np.nan)])
        out = ms.measure_event(stock, self.spy, ns("2024-03-07 16:10"), (ns("2024-03-08 09:30"), ns("2024-03-08 16:00")),
                               (ns("2024-03-07 09:30"), ns("2024-03-07 16:00")))
        self.assertTrue(np.isnan(out["h1"]))

    def test_wire_inside_the_session_has_no_extended_trade(self):
        out = ms.measure_event(self.stock, self.spy, ns("2024-03-08 09:28"), (ns("2024-03-08 09:30"), ns("2024-03-08 16:00")),
                               (ns("2024-03-07 09:30"), ns("2024-03-07 16:00")))
        self.assertTrue(np.isnan(out["extended"]))

    def test_largest_minute_move(self):
        self.assertAlmostEqual(self.out["largest_minute_move"], 113 / 111 - 1, places=6)


class Daily(unittest.TestCase):
    def test_window_with_exit_and_gap(self):
        opens = np.array([[10, 20], [11, 21], [12, np.nan], [13, np.nan]], dtype=float)
        closes = np.array([[10.5, 20.5], [11.5, 21.5], [np.nan, np.nan], [13.5, np.nan]], dtype=float)
        exits = np.array([np.nan, -0.5])
        last_rows = np.array([3, 1])
        r = ms.daily_window(opens, closes, np.array([0, 0]), np.array([0, 1]), 3, exits, last_rows)
        self.assertAlmostEqual(r[0], 11.5 / 10 - 1)                 # trou : dernier cours connu
        self.assertAlmostEqual(r[1], 21.5 / 20 * 0.5 - 1)            # disparu à la ligne 1, sortie de -50 %
        self.assertTrue(np.isnan(ms.daily_window(opens, closes, np.array([2]), np.array([0]), 3, exits, last_rows)[0]))

    def test_one_session_is_open_to_close(self):
        opens = np.array([[10.0]]); closes = np.array([[11.0]])
        self.assertAlmostEqual(ms.daily_window(opens, closes, np.array([0]), np.array([0]), 1, np.array([np.nan]), np.array([0]))[0], 0.1)


class Statistics(unittest.TestCase):
    def frame(self, effect, seed=0, quarters=12, per=40):
        rng = np.random.default_rng(seed)
        rows = []
        for q in range(quarters):
            for i in range(per):
                positive = i % 2 == 0
                rows.append({"quarter": pd.Period("2018Q1") + q, "positive": positive, "value": rng.normal(effect if positive else 0, 0.01),
                             "date": pd.Timestamp("2018-01-02") + pd.Timedelta(days=q * 91 + i % 5), "cik": i % 17})
        return pd.DataFrame(rows)

    def test_quarterly_spread_by_hand(self):
        frame = pd.DataFrame({"quarter": pd.PeriodIndex(["2018Q1"] * 4 + ["2018Q2"] * 2, freq="Q"), "positive": [True, True, False, False, True, False],
                              "value": [0.03, 0.01, -0.01, 0.01, 0.05, 0.02]})
        spread = ms.quarterly_spread(frame, "value")
        self.assertAlmostEqual(spread.iloc[0], 0.02)
        self.assertAlmostEqual(spread.iloc[1], 0.03)

    def test_summary_detects_an_effect_and_not_noise(self):
        strong = ms.summarize(ms.quarterly_spread(self.frame(0.01), "value"))
        noise = ms.summarize(ms.quarterly_spread(self.frame(0.0), "value"))
        self.assertLess(strong["p"], 0.001)
        self.assertGreater(noise["p"], 0.05)
        self.assertLess(strong["ci_low"], strong["mean"])
        self.assertLess(strong["mean"], strong["ci_high"])

    def test_sign_placebo(self):
        self.assertLess(ms.sign_placebo_p(self.frame(0.01), "value", draws=200), 0.01)
        # Sous l'hypothèse nulle, p < 0,05 arrive une fois sur vingt : seuil large pour un test déterministe.
        self.assertGreater(ms.sign_placebo_p(self.frame(0.0), "value", draws=200), 0.01)

    def test_two_way_cluster_with_singletons_is_hc0(self):
        rng = np.random.default_rng(1)
        x = rng.integers(0, 2, 200).astype(float)
        y = 0.5 * x + rng.normal(size=200)
        beta, t = ms.two_way_cluster(y, x, np.arange(200), np.arange(200) + 1000)
        design = np.column_stack([np.ones(200), x])
        inverse = np.linalg.inv(design.T @ design)
        b = inverse @ design.T @ y
        e = y - design @ b
        hc0 = inverse @ (design.T * e**2) @ design @ inverse
        self.assertAlmostEqual(beta, b[1])
        self.assertAlmostEqual(t, b[1] / np.sqrt(hc0[1, 1]))

    def test_two_way_cluster_constant_only(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        beta, _ = ms.two_way_cluster(y, None, ["a", "a", "b", "b"], [1, 2, 1, 2])
        self.assertAlmostEqual(beta, 2.5)

    def test_portfolio_compounds_and_idles(self):
        days = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        returns = pd.Series([0.10, 0.30, -0.5], index=pd.to_datetime(["2024-01-02", "2024-01-02", "2024-01-04"]))
        final, path = ms.portfolio(returns, days)
        self.assertAlmostEqual(final, 10_000 * 1.2 * 1.0 * 0.5)


class Runner(unittest.TestCase):
    """Chaîne du script de lancement sur de faux fichiers : lecture CSV, mode `current` écarté, facteurs par séance."""

    def test_run_chunk_on_fake_files(self):
        import gzip
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_minute_study as run
        header = "requested,returned,mode,t,o,h,l,c,v,n,vw\n"
        thursday = header + "ACME,ACME,self,2024-03-07T14:30:00Z,198,0,0,199,1,1,1\nACME,ACME,self,2024-03-07T20:59:00Z,199,0,0,200,1,1,1\n" \
            "SPY,SPY,self,2024-03-07T14:30:00Z,400,0,0,400,1,1,1\nSPY,SPY,self,2024-03-07T20:59:00Z,400,0,0,400,1,1,1\n"
        friday = header + "ACME,ACME,self,2024-03-08T14:30:00Z,108,0,0,108,1,1,1\nACME,ACME,current,2024-03-08T20:58:00Z,1,0,0,1,1,1,1\n" \
            "ACME,ACME,self,2024-03-08T20:59:00Z,112,0,0,113,1,1,1\nSPY,SPY,self,2024-03-08T14:30:00Z,404,0,0,404,1,1,1\nSPY,SPY,self,2024-03-08T20:59:00Z,404,0,0,408,1,1,1\n"
        with tempfile.TemporaryDirectory() as folder:
            main, extra = Path(folder) / "main", Path(folder) / "extra"
            main.mkdir(); extra.mkdir()
            with gzip.open(main / "bars_2024-03-07.csv.gz", "wt") as f:
                f.write(thursday)
            with gzip.open(extra / "bars_2024-03-08.csv.gz", "wt") as f:
                f.write(friday)
            day = lambda d: np.datetime64(d, "ns")
            run.BAR_DIRS = [main, extra]
            run.SESSIONS = ms.session_table(CALENDAR)
            run.FACTORS = {"ACME#0": (np.array([day("2024-03-07"), day("2024-03-08")]), np.array([0.5, 1.0])),
                           "SPY#0": (np.array([day("2024-03-07"), day("2024-03-08")]), np.array([1.0, 1.0]))}
            run.SPY_ID = "SPY#0"
            row = {"id": 1, "symbol": "ACME", "event_security": "ACME#0", "available_ns": ns("2024-03-07 16:10"), "entry_idx": 1, "placebo_idx": 0}
            out = run.run_chunk([row])[0]
        self.assertAlmostEqual(out["h1"], 113 / 108 - 1)          # la ligne `current` de 15 h 58 est ignorée
        self.assertAlmostEqual(out["h1_spy"], 408 / 404 - 1)
        self.assertAlmostEqual(out["cum_open"], 108 / 100 - 1)    # 200 bruts le jeudi, facteur 0,5
        self.assertAlmostEqual(out["placebo"], 100 / 99 - 1)

    def test_analysis_runs_on_a_fake_table(self):
        """L'analyse complète doit tourner sans erreur avant le lancement unique : table inventée, effet planté sur H1."""
        from types import SimpleNamespace
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "reports"))
        import run_minute_study as run
        rng = np.random.default_rng(4)
        days = pd.bdate_range("2018-01-02", "2024-12-31")
        n = 3000
        entry = pd.DatetimeIndex(rng.choice(days, n)).sort_values()
        positive = rng.random(n) < 0.75
        table = pd.DataFrame({"id": np.arange(n), "principal": rng.random(n) < 0.5, "tradable": rng.random(n) < 0.9, "zero": False,
                              "positive": positive, "liquidity": rng.choice([5e6, 5e7, 5e8], n), "cost_bps": rng.choice([5.0, 15.0, 40.0], n),
                              "entry_date": entry, "cik": rng.integers(0, 400, n), "basis": rng.choice(["adjusted", "gaap"], n), "before_open": rng.random(n) < 0.5,
                              "symbol": "X", "largest_minute_move": rng.random(n) * 0.1, "entry_delay_s": 0.0})
        table["liquid"] = table.liquidity >= ms.LIQUID
        table["quarter"] = table.entry_date.dt.to_period("Q")
        noise = lambda: rng.normal(0, 0.02, n)
        for name in ("h1", "late", "placebo", "extended", "open_30m", "open_60m"):
            table[name] = noise() + (0.01 * positive if name == "h1" else 0)
            table[f"{name}_spy"] = noise() / 4
        for name in ("wire_5m", "wire_30m", "wire_60m", "open", "open_30m_mark", "close"):
            table[f"cum_{name}"] = noise() + 0.03 * (positive - 0.5)
            table[f"cum_{name}_spy"] = noise() / 4
        for horizon in run.HORIZONS:
            for scenario in run.SCENARIOS:
                table[f"ab_d{horizon}_{scenario}"] = noise()
        run.add_derived(table)
        sessions = pd.DataFrame({"date": days})
        spy = pd.DataFrame({"SPY": np.linspace(250, 580, len(days))}, index=days)
        market = SimpleNamespace(benchmarks=SimpleNamespace(open=spy, close=spy * 1.001))
        report = run.analyze(table, sessions, market)
        self.assertEqual(set(report["confirmatory"]), {"H1", "H2", "H3"})
        self.assertLess(report["confirmatory"]["H1"]["p_holm"], 0.05)
        self.assertGreater(report["controls"]["sign_placebo_p"]["H2"], 0.01)
        self.assertEqual(len(report["secondary"]), 9)
        self.assertAlmostEqual(report["decomposition"]["all"]["close"]["share_of_close_spread"], 1.0)
        self.assertGreater(report["portfolio_usd"]["spy_buy_and_hold"], 10_000)
        import json
        json.dumps(report, default=float)



class Hashes(unittest.TestCase):
    def test_mismatch_stops(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "bars_2024-01-02.csv.gz").write_bytes(b"a")
            (Path(folder) / "x.parquet").write_bytes(b"b")
            expected = {".": ms.folder_sha256(folder), "x.parquet": ms.file_sha256(Path(folder) / "x.parquet")}
            ms.check_hashes(expected, folder)
            (Path(folder) / "x.parquet").write_bytes(b"c")
            with self.assertRaises(RuntimeError):
                ms.check_hashes(expected, folder)

    def test_folder_hash_matches_the_shell_recipe(self):
        import hashlib
        import subprocess
        with tempfile.TemporaryDirectory() as folder:
            for name, content in (("bars_2024-01-03.csv.gz", b"y"), ("bars_2024-01-02.csv.gz", b"x")):
                (Path(folder) / name).write_bytes(content)
            shell = subprocess.run("ls bars_*.csv.gz | sort | xargs sha256sum | sha256sum", shell=True, cwd=folder, capture_output=True, text=True).stdout[:64]
            self.assertEqual(ms.folder_sha256(folder), shell)


if __name__ == "__main__":
    unittest.main()
