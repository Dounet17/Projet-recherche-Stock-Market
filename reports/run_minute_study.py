"""Lancement unique de l'étude figée dans `reports/lab_2026-11/PROTOCOLE_RESULTATS_MINUTE.md`.

Vérifie d'abord les empreintes des données du gel. Avec `--dry-run`, s'arrête après les effectifs et les exclusions :
aucune barre et aucun rendement ne sont lus (seuls les filtres de prix et de liquidité, comme ailleurs dans le projet).

Écrit `data/events/minute_study/events.parquet` (non versionné) et `reports/lab_2026-11/minute_study/`.

Depuis la racine : venv/bin/python reports/run_minute_study.py [--dry-run]
"""

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import minute_study as ms
from events import holm
from universe_data import load_universe

EXPECTED = {
    "data/news/earnings_surprise_verified.parquet": "ca90aee8bb65fdf34ad1eb505efe659ef4c1378ccbf49ef917daddf87f5a8a83",
    "data/universe_clean/prices_dev.parquet": "c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15",
    "data/universe_clean/securities_dev.parquet": "d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161",
    "data/calendar.parquet": "87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03",
    "data/events/minute_bars": "86515248394c6ea0ec1cd2590ac456bed0097b770eb1dce4c51341c32f7b3c30",
    "data/events/minute_bars_extra": "7046342a25b1c21996faaef5681a90ea2e421a98420a11b922ae7de972f9df43",
}
BAR_DIRS = [ROOT / "data" / "events" / "minute_bars", ROOT / "data" / "events" / "minute_bars_extra"]
OUT = ROOT / "reports" / "lab_2026-11" / "minute_study"
OUT_DATA = ROOT / "data" / "events" / "minute_study"
HORIZONS = (1, 5, 20)
SCENARIOS = ("base", "optimistic", "pessimistic")
SPY_COST = 5e-4

# Partagés avec les processus de calcul (copiés au lancement par fork).
SESSIONS = None
FACTORS = {}
SPY_ID = None


def load_events():
    calendar = pd.read_parquet(ROOT / "data" / "calendar.parquet")
    sessions = ms.session_table(calendar)
    table = pd.read_parquet(ROOT / "data" / "news" / "earnings_surprise_verified.parquet")
    assert table.available_at.max() < pd.Timestamp("2025-01-01", tz="UTC"), "Période verrouillée"
    funnel = {"publications": len(table), "verified": int(table.verified.sum())}
    table = table[table.verified & table.security_active].copy()
    funnel["verified_and_listed"] = len(table)
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet").set_index("security_id")
    table["symbol"] = table.event_security.map(securities.symbol)
    table["available_ns"] = table.available_at.dt.tz_convert("UTC").dt.as_unit("ns").astype("int64")
    table["entry_idx"] = ms.entry_sessions(table.available_ns.to_numpy(), sessions.open_ns.to_numpy())
    table["placebo_idx"] = ms.placebo_sessions(table.available_ns.to_numpy(), sessions.close_ns.to_numpy())
    table = table[(table.entry_idx < len(sessions)) & (table.placebo_idx >= 0)].copy()
    funnel["entry_before_2025"] = len(table)
    entry = sessions.iloc[table.entry_idx]
    # Contrôles anti-fuite : l'entrée suit la dépêche d'au moins 5 minutes, la séance témoin la précède entièrement.
    assert (entry.open_ns.to_numpy() >= table.available_ns.to_numpy() + ms.LATENCY).all()
    assert (sessions.close_ns.to_numpy()[table.placebo_idx] <= table.available_ns.to_numpy()).all()
    table["entry_date"] = entry.date.to_numpy()
    assert table.entry_date.max() <= ms.LAST_DAY
    table["quarter"] = table.entry_date.dt.to_period("Q")
    table["positive"] = table.surprise > 0
    table["zero"] = table.surprise == 0
    table["before_open"] = table.available_at.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize() == table.entry_date
    return table, sessions, securities, funnel


def attach_daily(table):
    """Filtres et coûts connus avant l'entrée, puis fenêtres quotidiennes (rendements lus seulement si demandé)."""
    market = load_universe(symbols=set(table.symbol.dropna()))
    dates, columns = market.data.close.index, market.data.close.columns
    rows = dates.get_indexer(table.entry_date)
    cols = columns.get_indexer(table.event_security)
    table["in_daily"] = (rows > 0) & (cols >= 0)
    ok = table.in_daily.to_numpy()
    r, c = rows[ok], cols[ok]
    table["tradable"] = False
    table.loc[ok, "tradable"] = market.data.tradable.to_numpy()[r - 1, c]
    table["cost_bps"] = np.nan
    table.loc[ok, "cost_bps"] = market.data.cost_bps.to_numpy()[r, c].astype(float)
    table["liquidity"] = np.nan
    table.loc[ok, "liquidity"] = market.data.dollar_volume.to_numpy()[r - 1, c]
    table["liquid"] = table.liquidity >= ms.LIQUID
    return market, rows, cols


def daily_returns(table, market, rows, cols):
    opens, closes = market.data.open.to_numpy(), market.data.close.to_numpy()
    last_rows = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
    spy_open = market.benchmarks.open["SPY"].to_numpy()
    spy_close = market.benchmarks.close["SPY"].ffill().to_numpy()
    ok = table.in_daily.to_numpy()
    for horizon in HORIZONS:
        end = rows[ok] + horizon - 1
        inside = end < closes.shape[0]
        spy = np.full(ok.sum(), np.nan)
        spy[inside] = spy_close[end[inside]] / spy_open[rows[ok][inside]] - 1
        for scenario in SCENARIOS:
            exits = market.exits[scenario].reindex(market.data.close.columns).to_numpy(dtype=float)
            value = ms.daily_window(opens, closes, rows[ok], cols[ok], horizon, exits, last_rows)
            table[f"ab_d{horizon}_{scenario}"] = np.nan
            table.loc[ok, f"ab_d{horizon}_{scenario}"] = value - spy


def load_session(day):
    frames = [pd.read_csv(path, usecols=["requested", "mode", "t", "o", "c"], dtype={"requested": str, "mode": str})
              for folder in BAR_DIRS if (path := folder / f"bars_{day:%Y-%m-%d}.csv.gz").exists()]
    if not frames:
        return {}
    bars = pd.concat(frames)
    bars = bars[bars["mode"] == "self"]
    bars["t"] = pd.to_datetime(bars.t, utc=True, format="ISO8601").dt.as_unit("ns").astype("int64")
    return {symbol: (g.t.to_numpy(), g.o.to_numpy(), g.c.to_numpy()) for symbol, g in bars.groupby("requested")}


def series(symbol, security, first, last, cache):
    """Barres des séances `first` à `last`, chaque séance multipliée par son facteur d'ajustement."""
    parts = []
    dates, values = FACTORS.get(security, (np.array([], dtype="datetime64[ns]"), np.array([])))
    for i in range(first, last + 1):
        day = SESSIONS.date.iloc[i]
        if day not in cache:
            cache[day] = load_session(day)
        if symbol in cache[day]:
            t, o, c = cache[day][symbol]
            k = np.searchsorted(dates, np.datetime64(day, "ns"))
            factor = values[k] if k < len(dates) and dates[k] == np.datetime64(day, "ns") else np.nan
            parts.append((t, o * factor, c * factor))
    if not parts:
        return ms.EMPTY
    return ms.Bars(*(np.concatenate([p[j] for p in parts]) for j in range(3)))


def run_chunk(rows):
    cache, results = {}, []
    for row in rows:
        entry = (int(SESSIONS.open_ns.iloc[row["entry_idx"]]), int(SESSIONS.close_ns.iloc[row["entry_idx"]]))
        placebo = (int(SESSIONS.open_ns.iloc[row["placebo_idx"]]), int(SESSIONS.close_ns.iloc[row["placebo_idx"]]))
        stock = series(row["symbol"], row["event_security"], row["placebo_idx"], row["entry_idx"], cache)
        spy = series("SPY", SPY_ID, row["placebo_idx"], row["entry_idx"], cache)
        measures = ms.measure_event(stock, spy, row["available_ns"], entry, placebo)
        assert measures["entry_delay_s"] != measures["entry_delay_s"] or measures["entry_delay_s"] >= 0
        results.append({"id": row["id"], **measures})
        if len(cache) > 6:
            for day in sorted(cache)[:-3]:
                del cache[day]
    return results


def minute_measures(table, securities, workers):
    global SESSIONS, FACTORS, SPY_ID
    SPY_ID = securities.index[(securities.symbol == "SPY") & (securities.security_type == "fund") & securities.alive_at_end][0]
    wanted = set(table.event_security) | {SPY_ID}
    prices = pd.read_parquet(ROOT / "data" / "universe_clean" / "prices_dev.parquet", columns=["security_id", "ts_utc", "close", "adj_close", "suspect_print"],
                             filters=[("security_id", "in", list(wanted))])
    prices["day"] = prices.ts_utc.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize().dt.as_unit("ns")
    prices["factor"] = (prices.adj_close / prices.close).where(~prices.suspect_print)
    FACTORS = {s: (g.day.to_numpy(), g.factor.to_numpy()) for s, g in prices.sort_values("day").groupby("security_id")}
    del prices
    ordered = table.sort_values(["entry_idx", "symbol"])[["id", "symbol", "event_security", "available_ns", "entry_idx", "placebo_idx"]].to_dict("records")
    chunks, current, last = [], [], None
    for row in ordered:
        if current and row["entry_idx"] != last and len(current) >= 300:
            chunks.append(current)
            current = []
        current.append(row)
        last = row["entry_idx"]
    chunks.append(current)
    with Pool(workers) as pool:
        found = [r for part in pool.imap_unordered(run_chunk, chunks) for r in part]
    return table.merge(pd.DataFrame(found), on="id", how="left")


def add_derived(table):
    cost = table.cost_bps / 1e4
    for name in ("h1", "late", "placebo", "extended", *(f"open_{m}m" for m in ms.SHORT_WINDOWS)):
        table[f"ab_{name}"] = table[name] - table[f"{name}_spy"]
    table["net_h1"] = (1 + table.h1) * (1 - cost) ** 2 - 1
    table["net_ab_h1"] = table.net_h1 - table.h1_spy
    table["net_ab_h1_double"] = (1 + table.h1) * (1 - 2 * cost) ** 2 - 1 - table.h1_spy
    table["net_ab_extended"] = (1 + table.extended) * (1 - 2 * cost) ** 2 - 1 - table.extended_spy
    for name in [*(f"wire_{m}m" for m in ms.WIRE_POINTS), "open", "open_30m_mark", "close"]:
        table[f"ab_cum_{name}"] = table[f"cum_{name}"] - table[f"cum_{name}_spy"]


def spread_test(frame, value):
    return ms.summarize(ms.quarterly_spread(frame, value)) | {"events_positive": int(frame[value].notna()[frame.positive].sum()), "events_negative": int(frame[value].notna()[~frame.positive].sum())}


def mean_test(frame, value):
    return ms.summarize(ms.quarterly_mean(frame, value)) | {"events": int(frame[value].notna().sum())}


def describe(frame, value, by):
    out = {}
    for key, part in frame.groupby(by):
        means = part.groupby("positive")[value].agg(["mean", "count"])
        if True in means.index and False in means.index:
            out[str(key)] = {"positive": float(means.loc[True, "mean"]), "negative": float(means.loc[False, "mean"]), "spread": float(means.loc[True, "mean"] - means.loc[False, "mean"]),
                             "n_positive": int(means.loc[True, "count"]), "n_negative": int(means.loc[False, "count"])}
    return out


def analyze(table, sessions, market):
    main = table[table.principal & table.tradable & ~table.zero]
    broad = table[table.tradable & ~table.zero]
    liquid = main[main.liquid]
    report = {}
    confirm = {"H1": spread_test(main, "ab_h1"), "H2": spread_test(main, "ab_d5_base"), "H3": mean_test(main[main.positive], "net_ab_h1")}
    for name, p in zip(confirm, holm([c["p"] for c in confirm.values()])):
        confirm[name]["p_holm"] = float(p)
    report["confirmatory"] = confirm
    secondary = {
        "S1_open_30m": spread_test(main, "ab_open_30m"), "S2_open_60m": spread_test(main, "ab_open_60m"),
        "S3_daily_1": spread_test(main, "ab_d1_base"), "S4_daily_20": spread_test(main, "ab_d20_base"),
        "S5_entry_0935": spread_test(main, "ab_late"),
        "S6_extended_spread": spread_test(liquid, "ab_extended"), "S7_extended_long_net": mean_test(liquid[liquid.positive], "net_ab_extended"),
        "S8_verified_H1": spread_test(broad, "ab_h1"), "S9_verified_H2": spread_test(broad, "ab_d5_base"),
    }
    for name, p in zip(secondary, holm([s["p"] for s in secondary.values()])):
        secondary[name]["p_holm_secondary"] = float(p)
    report["secondary"] = secondary

    report["controls"] = {
        "placebo_previous_session": spread_test(main, "ab_placebo"),
        "sign_placebo_p": {"H1": ms.sign_placebo_p(main, "ab_h1"), "H2": ms.sign_placebo_p(main, "ab_d5_base")},
        "two_way_cluster_t": {
            "H1": ms.two_way_cluster(main.ab_h1, main.positive, main.entry_date, main.cik)[1],
            "H2": ms.two_way_cluster(main.ab_d5_base, main.positive, main.entry_date, main.cik)[1],
            "H3": ms.two_way_cluster(main[main.positive].net_ab_h1, None, main[main.positive].entry_date, main[main.positive].cik)[1],
        },
        "exit_scenarios_H2": {s: spread_test(main, f"ab_d5_{s}")["mean"] for s in SCENARIOS},
        "exit_scenarios_S4": {s: spread_test(main, f"ab_d20_{s}")["mean"] for s in SCENARIOS},
        "H3_double_costs": mean_test(main[main.positive], "net_ab_h1_double"),
        "no_entry_bar": int(main.entry_delay_s.isna().sum()),
    }

    # Portefeuille de 10 000 USD : achats de H3, de l'ouverture à la clôture.
    days = sessions.date[(sessions.date >= "2018-01-02") & (sessions.date <= ms.LAST_DAY)]
    buys = main[main.positive & main.net_h1.notna()]
    cost = buys.cost_bps / 1e4
    final, _ = ms.portfolio(pd.Series(buys.net_h1.to_numpy(), index=buys.entry_date), days)
    final_double, _ = ms.portfolio(pd.Series(((1 + buys.h1) * (1 - 2 * cost) ** 2 - 1).to_numpy(), index=buys.entry_date), days)
    spy_open, spy_close = market.benchmarks.open["SPY"], market.benchmarks.close["SPY"]
    first, last = days.iloc[0], days.iloc[-1]
    traded = pd.DatetimeIndex(sorted(set(buys.entry_date)))
    intraday = spy_close.reindex(traded) / spy_open.reindex(traded) * (1 - SPY_COST) ** 2
    report["portfolio_usd"] = {"strategy": final, "strategy_double_costs": final_double, "spy_buy_and_hold": float(10_000 * spy_close[last] / spy_open[first] * (1 - SPY_COST) ** 2),
                               "spy_intraday_same_days": float(10_000 * intraday.prod()), "days_with_trades": len(traded)}

    points = [*(f"wire_{m}m" for m in ms.WIRE_POINTS), "open", "open_30m_mark", "close"]
    decomposition = {}
    for label, frame, names in (("all", main, points[3:]), ("liquid", liquid, points)):
        means = frame.groupby("positive")[[f"ab_cum_{p}" for p in names]].mean()
        spread = means.loc[True] - means.loc[False]
        decomposition[label] = {p: {"positive": float(means.loc[True, f"ab_cum_{p}"]), "negative": float(means.loc[False, f"ab_cum_{p}"]),
                                    "share_of_close_spread": float(spread[f"ab_cum_{p}"] / spread["ab_cum_close"])} for p in names}
    report["decomposition"] = decomposition
    tiers = pd.cut(main.liquidity, [0, 1e7, 1e8, np.inf], labels=["1-10M", "10-100M", ">=100M"])
    report["descriptive"] = {value: {"year": describe(main, value, main.entry_date.dt.year), "basis": describe(main, value, main.basis),
                                     "liquidity": describe(main, value, tiers), "before_open": describe(main, value, main.before_open)}
                             for value in ("ab_h1", "ab_d5_base")}
    report["zero_surprise"] = {"events": int((table.principal & table.tradable & table.zero).sum()),
                               "mean_ab_h1": float(table.loc[table.principal & table.tradable & table.zero, "ab_h1"].mean())}
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    ms.check_hashes(EXPECTED, ROOT)
    print("Empreintes conformes au gel.", flush=True)
    global SESSIONS
    table, SESSIONS, securities, funnel = load_events()
    market, rows, cols = attach_daily(table)
    principal = table[table.principal]
    funnel |= {"in_daily_universe": int(table.in_daily.sum()), "tradable": int(table.tradable.sum()),
               "principal": len(principal), "principal_tradable": int(principal.tradable.sum()),
               "principal_tradable_nonzero": int((principal.tradable & ~principal.zero).sum()),
               "principal_tradable_positive": int((principal.tradable & principal.positive).sum()),
               "principal_tradable_negative": int((principal.tradable & ~principal.positive & ~principal.zero).sum()),
               "principal_tradable_liquid": int((principal.tradable & principal.liquid & ~principal.zero).sum()),
               "principal_tradable_before_open": int((principal.tradable & principal.before_open & ~principal.zero).sum())}
    print(json.dumps(funnel, indent=1), flush=True)
    if args.dry_run:
        print("Essai à blanc : arrêt avant toute lecture de barre ou de rendement.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    daily_returns(table, market, rows, cols)
    table = minute_measures(table, securities, args.workers)
    add_derived(table)
    extremes = table[table.largest_minute_move > ms.EXTREME_MOVE][["id", "symbol", "entry_date", "largest_minute_move", "principal"]]
    extremes.to_csv(OUT / "extreme_minute_moves.csv", index=False)
    report = {"funnel": funnel, "extreme_minute_moves": len(extremes), **analyze(table, SESSIONS, market)}
    table.drop(columns=["quarter"]).to_parquet(OUT_DATA / "events.parquet", index=False)
    (OUT / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(report, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
