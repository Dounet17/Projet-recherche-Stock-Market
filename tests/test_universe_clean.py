"""Cas construits à la main pour les règles de nettoyage."""

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from universe_clean import add_adjusted_returns, classify_security, exit_returns, find_aliases, flag_suspect_prints, group_aliases, reconstruct_quarterly_eps, split_segments

DAYS = pd.date_range("2020-01-01", periods=800, freq="B", tz="UTC")


def series(symbol, prices, volumes):
    return pd.DataFrame({"symbol": symbol, "ts_utc": DAYS[:len(prices)], "adj_close": prices, "close": prices, "volume": volumes})


def test_ghost_tail_removed_and_last_trade_kept():
    panel = series("GONE", [50.0] * 10 + [70.0] + [70.0] * 100, [1000] * 11 + [0] * 100)
    clean, cuts = split_segments(panel)
    assert len(clean) == 11 and clean.close.iloc[-1] == 70.0 and cuts.empty


def test_thin_stock_keeps_short_no_trade_days():
    volumes = [100, 0, 0, 100, 0, 100] * 5
    panel = series("THIN", [10.0] * 30, volumes)
    clean, cuts = split_segments(panel)
    assert len(clean) == 30 and clean.segment.nunique() == 1 and not clean.traded.all() and cuts.empty


def test_reused_symbol_is_cut_in_two():
    prices = [100.0] * 50 + [100.0] * 300 + [20.0] * 50
    panel = series("LB", prices, [1000] * 50 + [0] * 300 + [500] * 50)
    clean, cuts = split_segments(panel)
    assert clean.segment.tolist() == [0] * 50 + [1] * 50 and len(cuts) == 1


def test_long_halt_with_small_price_change_stays_one_security():
    prices = [100.0] * 50 + [100.0] * 70 + [103.0] * 50
    clean, cuts = split_segments(series("HALT", prices, [1000] * 50 + [0] * 70 + [500] * 50))
    assert clean.segment.nunique() == 1 and cuts.empty and len(clean) == 170


def test_medium_gap_with_big_jump_is_cut():
    prices = [100.0] * 50 + [100.0] * 70 + [40.0] * 50
    clean, cuts = split_segments(series("JUMP", prices, [1000] * 50 + [0] * 70 + [500] * 50))
    assert clean.segment.nunique() == 2 and len(cuts) == 1


def test_split_during_gap_is_not_a_jump():
    panel = series("SPLT", [50.0] * 50 + [50.0] * 70 + [51.0] * 50, [1000] * 50 + [0] * 70 + [500] * 50)
    panel["close"] = [100.0] * 50 + [100.0] * 70 + [51.0] * 50
    assert split_segments(panel)[0].segment.nunique() == 1


def _with_ids(frame):
    frame = frame.assign(traded=frame.volume > 0)
    frame["security_id"] = frame.symbol + "#0"
    return frame


def test_aliases_found_despite_different_adjusted_prices():
    rng = np.random.default_rng(0)
    prices = 100 + rng.normal(size=100).cumsum()
    volumes = rng.integers(1000, 100000, 100)
    fb = series("FB", prices, volumes)
    meta = series("META", prices, volumes).assign(adj_close=prices * 0.99)
    other = series("GOOG", prices + 1, volumes)
    frame = _with_ids(pd.concat([fb, meta, other]))
    pairs = find_aliases(frame)
    assert {tuple(sorted(p)) for p in zip(pairs.security_a, pairs.security_b)} == {("FB#0", "META#0")}
    grouped = group_aliases(pairs, {"FB#0": 60, "META#0": 100})
    assert grouped.values.tolist() == [["FB#0", "META#0"]]


def test_share_classes_are_not_aliases():
    rng = np.random.default_rng(1)
    prices = 100 + rng.normal(size=100).cumsum()
    a = series("GOOG", prices, rng.integers(1000, 100000, 100))
    b = series("GOOGL", prices, rng.integers(1000, 100000, 100))
    assert find_aliases(_with_ids(pd.concat([a, b]))).empty


def test_adjustment_level_removed_but_returns_kept():
    frame = series("WHLR", [1000.0, 2000.0, 1000.0], [10, 10, 10]).assign(close=[2.0, 4.0, 2.0], security_id="W", traded=True)
    out = add_adjusted_returns(frame)
    assert out.adj_close.iloc[-1] == 2.0 and out.ret_adj.iloc[1] == 1.0


def test_return_skips_no_trade_day():
    frame = series("T", [10.0, 10.0, 12.0], [10, 0, 10]).assign(security_id="T")
    frame["traded"] = frame.volume > 0
    out = add_adjusted_returns(frame)
    assert np.isnan(out.ret_adj.iloc[1]) and abs(out.ret_adj.iloc[2] - 0.2) < 1e-12


def test_spike_is_flagged():
    frame = series("S", [10.0, 10.0, 25.0, 10.0, 10.0], [10] * 5).assign(security_id="S")
    frame["traded"] = True
    flagged = flag_suspect_prints(add_adjusted_returns(frame))
    assert flagged.tolist() == [False, False, True, False, False]


def test_classification():
    assert classify_security("TQQQ", "ProShares UltraPro QQQ", True) == "fund"
    # FB appartient aujourd'hui à un fonds : ce nom ne s'applique pas à l'ancienne Facebook.
    assert classify_security("FB", "ProShares S&P 500 Dynamic Buffer ETF", False, {"sic": "7370", "10-K": 8}) == "common"
    assert classify_security("ZVV", None, False) == "test"
    assert classify_security("X", None, False, {"sic": "6770", "10-K": 1}) == "spac"
    assert classify_security("BABA", "Alibaba Group", False, {"sic": "5961", "20-F": 8}) == "adr"
    assert classify_security("GONE", None, False) == "unknown"
    assert classify_security("AAPL", "Apple Inc. Common Stock", True) == "common"


def test_filings_during_listing_beat_a_later_fund_name():
    # LAZR : Luminar jusqu'en 2024, puis symbole repris par un fonds, seul nom connu en 2026.
    assert classify_security("LAZR", "Tema Photonics & Optical ETF", True, {"sic": "3714", "10-K": 4}, "filing_prefix") == "common"
    assert classify_security("EEM", "iShares MSCI Emerging Markets ETF", True, {"sic": "6726", "10-K": 0}, "ticker") == "fund"


def test_extreme_jump_after_bankruptcy_is_flagged():
    frame = series("BCEI", [0.5, 0.5, 39.2, 39.0], [10] * 4).assign(security_id="B")
    frame["traded"] = True
    assert flag_suspect_prints(add_adjusted_returns(frame)).tolist() == [False, False, True, False]


def test_q4_rescales_quarters_filed_before_a_split():
    # Forme de TSLA 2022 : T1 et T2 publiés avant un fractionnement 3 pour 1, exercice publié après.
    rows = [{"cik": 1, "start": "2022-01-01", "end": "2022-03-31", "value": 3.0, "filed": "2022-04-25"}, {"cik": 1, "start": "2022-04-01", "end": "2022-06-30", "value": 3.0, "filed": "2022-07-25"}, {"cik": 1, "start": "2022-07-01", "end": "2022-09-30", "value": 1.0, "filed": "2022-10-24"}, {"cik": 1, "start": "2022-01-01", "end": "2022-12-31", "value": 4.0, "filed": "2023-01-31"}]
    splits = pd.DataFrame({"cik": [1], "date": [pd.Timestamp("2022-08-25")], "factor": [1 / 3]})
    out = reconstruct_quarterly_eps(pd.DataFrame(rows), splits)
    assert abs(out[out.source == "q4_derived"].eps.iloc[0] - 1.0) < 1e-6


def test_exit_assumptions():
    assert exit_returns("worthless") == (-1.0, -1.0, -1.0)
    assert exit_returns("cash_merger", 0.01) == (0.01, 0.01, 0.01)
    assert exit_returns("unknown_distress")[0] == -0.55


def test_q4_is_deduced_and_available_at_annual_filing():
    rows = []
    for start, end, value, filed in (("2022-01-01", "2022-03-31", 1.0, "2022-05-01"), ("2022-04-01", "2022-06-30", 2.0, "2022-08-01"), ("2022-07-01", "2022-09-30", 3.0, "2022-11-01"), ("2022-01-01", "2022-12-31", 10.0, "2023-02-15")):
        rows.append({"cik": 1, "start": start, "end": end, "value": value, "filed": filed})
    out = reconstruct_quarterly_eps(pd.DataFrame(rows))
    q4 = out[out.source == "q4_derived"].iloc[0]
    assert q4.eps == 4.0 and q4.filed == pd.Timestamp("2023-02-15") and len(out) == 4


def test_q4_from_nine_months():
    rows = [{"cik": 1, "start": "2022-01-01", "end": "2022-09-30", "value": 6.0, "filed": "2022-11-01"}, {"cik": 1, "start": "2022-01-01", "end": "2022-12-31", "value": 10.0, "filed": "2023-02-15"}]
    assert reconstruct_quarterly_eps(pd.DataFrame(rows)).eps.tolist() == [4.0]


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(unittest.FunctionTestCase(f) for n, f in sorted(globals().items()) if n.startswith("test_"))


if __name__ == "__main__":
    unittest.main()
