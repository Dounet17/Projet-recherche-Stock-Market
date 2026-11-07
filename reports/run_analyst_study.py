"""Lancement unique de l'étude figée dans `reports/lab_2026-11/PROTOCOLE_NOTES_ANALYSTES.md`.

Vérifie d'abord les empreintes des données du gel. Avec `--dry-run`, s'arrête après les effectifs et les exclusions :
aucun rendement n'est lu (seuls les filtres de prix et de liquidité, comme ailleurs dans le projet).

Écrit `data/events/analyst_study/events.parquet` (non versionné), `reports/lab_2026-11/analyst_study/` et une ligne
au journal des essais `ledger_universe.csv`.

Depuis la racine : venv/bin/python reports/run_analyst_study.py [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import analyst_study as an
import lab
import minute_study as ms
from events import holm
from experiment import run_variant
from universe_data import load_universe

EXPECTED = {
    "data/news/news_articles.parquet": "39a98efe473c46e2b3a0d701d4533a42f0e3ccb070111a14488786c8a12d6038",
    "data/news/news_links.parquet": "4d7fe4152650453164a641ee2ebb0f190319857578a0b5ca78e600fd3c80f161",
    "data/universe_clean/prices_dev.parquet": "c5aedca65969b2867935fd2a6fe328f00462afd45a052f6383b3713cf3d5be15",
    "data/universe_clean/securities_dev.parquet": "d2f01bd582c3687e8f5c67e4721e0fe478edf85215979cd6bf14dd38129f3161",
    "data/events/earnings_events.parquet": "f2da57a43b9bdda8ab455121480968259d385b4d516450cbb5808aae6c2cca12",
    "data/calendar.parquet": "87d0bbb94b61e3f5d48d45bf5065ba921f45c5506bf2b03ebf683bf80cc76f03",
}
OUT = ROOT / "reports" / "lab_2026-11" / "analyst_study"
OUT_DATA = ROOT / "data" / "events" / "analyst_study"
HORIZONS = (1, 5, 20, 60)
SCENARIOS = ("base", "optimistic", "pessimistic")
TRIAL_NAME = "analyst_upgrades_hold20"


def load_notes():
    calendar = pd.read_parquet(ROOT / "data" / "calendar.parquet")
    sessions = ms.session_table(calendar)
    columns = ["id", "available_at", "headline", "category", "n_stocks", "correction", "late_relay"]
    articles = pd.read_parquet(ROOT / "data" / "news" / "news_articles.parquet", columns=columns)
    assert articles.available_at.max() < pd.Timestamp("2025-01-01", tz="UTC"), "Période verrouillée"
    links = pd.read_parquet(ROOT / "data" / "news" / "news_links.parquet")
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet").set_index("security_id")
    notes = an.select_notes(articles, links, securities.security_type)
    funnel = {"analyst_articles": int((articles.category == "analyst").sum()), "selected_by_kind": notes.kind.value_counts().to_dict()}
    notes["available_ns"] = notes.available_at.dt.tz_convert("UTC").dt.as_unit("ns").astype("int64")
    notes["entry_idx"] = ms.entry_sessions(notes.available_ns.to_numpy(), sessions.open_ns.to_numpy())
    notes["decision_idx"] = an.decision_sessions(notes.available_ns.to_numpy(), sessions.close_ns.to_numpy())
    notes = notes[notes.entry_idx < len(sessions)].copy()
    entry = sessions.iloc[notes.entry_idx]
    # Contrôles anti-fuite : entrée au moins 5 minutes après la note, décision du moteur après la note.
    assert (entry.open_ns.to_numpy() >= notes.available_ns.to_numpy() + ms.LATENCY).all()
    ok = notes.decision_idx < len(sessions)
    assert (sessions.close_ns.to_numpy()[notes.decision_idx[ok]] > notes.available_ns[ok].to_numpy()).all()
    notes["entry_date"] = entry.date.to_numpy()
    notes["decision_date"] = sessions.date.reindex(notes.decision_idx).to_numpy()
    assert notes.entry_date.max() <= ms.LAST_DAY
    notes["cik"] = notes.security_id.map(securities.cik)

    events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["cik", "announced", "filed"])
    events["day"] = events.announced.fillna(events.filed)
    events = events.dropna(subset=["day", "cik"])
    events["pos"] = np.searchsorted(sessions.date.to_numpy(), events.day.to_numpy().astype(sessions.date.dtype))
    positions = {int(c): np.sort(g.pos.to_numpy()) for c, g in events.groupby("cik")}
    notes["near_earnings"] = an.near_earnings(notes.cik.to_numpy(), notes.entry_idx.to_numpy(), positions)
    notes["earnings_in_window"] = an.earnings_inside(notes.cik.to_numpy(), notes.entry_idx.to_numpy(), positions)

    ratings = an.collapse(notes, ("upgrade", "downgrade"))
    targets = an.collapse(notes, ("target_up", "target_down"))
    table = pd.concat([ratings.assign(family="rating"), targets.assign(family="target")], ignore_index=True)
    table["positive"] = table.kind.isin(["upgrade", "target_up"])
    table["quarter"] = table.entry_date.dt.to_period("Q")
    funnel["after_same_day_collapse"] = table.kind.value_counts().to_dict()
    funnel["near_earnings_share"] = table.groupby("kind").near_earnings.mean().round(3).to_dict()
    return table, sessions, securities, funnel


def attach_daily(table):
    market = load_universe(symbols=set(table.security_id.map(lambda s: s.split("#")[0])))
    dates, columns = market.data.close.index, market.data.close.columns
    rows = dates.get_indexer(table.entry_date)
    cols = columns.get_indexer(table.security_id)
    table["row"], table["col"] = rows, cols
    table["in_daily"] = (rows > 0) & (cols >= 0)
    ok = table.in_daily.to_numpy()
    r, c = rows[ok], cols[ok]
    for name, values, offset in (("tradable", market.data.tradable, -1), ("cost_bps", market.data.cost_bps, 0), ("liquidity", market.data.dollar_volume, -1)):
        table[name] = np.nan if name != "tradable" else False
        table.loc[ok, name] = values.to_numpy()[r + offset, c]
    table["tradable"] = table.tradable.astype(bool)
    table["liquid"] = table.liquidity >= ms.LIQUID
    # A3 : achat à l'ouverture qui suit la clôture de décision ; achetable connu à cette clôture.
    drow = dates.get_indexer(table.decision_date)
    table["decision_row"] = drow
    table["tradable_a3"] = False
    good = ok & (drow >= 0)
    table.loc[good, "tradable_a3"] = market.data.tradable.to_numpy()[drow[good], cols[good]]
    return market


def daily_returns(table, market):
    opens, closes = market.data.open.to_numpy(), market.data.close.to_numpy()
    last_rows = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
    spy_open = market.benchmarks.open["SPY"].to_numpy()
    spy_close = market.benchmarks.close["SPY"].ffill().to_numpy()
    ok = table.in_daily.to_numpy()

    def window(start, horizon, scenario):
        out = np.full(len(table), np.nan)
        valid = ok & (start >= 0)
        exits = market.exits[scenario].reindex(market.data.close.columns).to_numpy(dtype=float)
        value = ms.daily_window(opens, closes, start[valid], table.col.to_numpy()[valid], horizon, exits, last_rows)
        end = start[valid] + horizon - 1
        inside = end < closes.shape[0]
        spy = np.full(valid.sum(), np.nan)
        spy[inside] = spy_close[end[inside]] / spy_open[start[valid][inside]] - 1
        out[valid] = value - spy
        raw = np.full(len(table), np.nan)
        raw[valid] = value
        return out, raw

    rows = table.row.to_numpy()
    for horizon in HORIZONS:
        for scenario in SCENARIOS:
            table[f"ab_{horizon}_{scenario}"], raw = window(rows, horizon, scenario)
            if scenario == "base":
                table[f"raw_{horizon}"] = raw
    cost = table.cost_bps / 1e4
    spy20 = table.raw_20 - table.ab_20_base
    table["net_ab_20"] = (1 + table.raw_20) * (1 - cost) ** 2 - 1 - spy20
    table["net_ab_20_double"] = (1 + table.raw_20) * (1 - 2 * cost) ** 2 - 1 - spy20
    table["ab_placebo"], _ = window(rows - an.PLACEBO_SHIFT, 20, "base")
    table["ab_before"], _ = window(rows - 20, 20, "base")


def plain_test(series_summary):
    return series_summary["p_plain"]


def spread_test(frame, value):
    out = ms.summarize(ms.quarterly_spread(frame, value))
    return out | {"events_positive": int(frame[value].notna()[frame.positive].sum()), "events_negative": int(frame[value].notna()[~frame.positive].sum())}


def mean_test(frame, value):
    return ms.summarize(ms.quarterly_mean(frame, value)) | {"events": int(frame[value].notna().sum())}


def portfolio(table, market):
    """A3 : relèvements achetables, moteur quotidien, comparaison à SPY."""
    buys = table[(table.kind == "upgrade") & ~table.near_earnings & table.tradable_a3 & (table.decision_row >= 0)]
    weights = an.portfolio_weights(buys.decision_row.to_numpy(), buys.security_id.to_numpy(), market.data.close.index)
    result, benchmark, extra = run_variant(weights, market, lab.DEV_START, lab.DEV_END, n_random=20, seed=0)
    comparison = lab.compare(result.returns, benchmark.returns)
    bil_open = market.benchmarks.open["BIL"]
    cash = (bil_open.shift(-1) / bil_open - 1).fillna(0.0)
    with_cash = lab.backtest(weights, market.data, start=lab.DEV_START, end=lab.DEV_END, cost_bps=market.data.cost_bps, exits=market.exits["base"], cash_returns=cash)
    excess = lambda r: r - cash.reindex(r.index).fillna(0.0)
    sharpe = lambda r: float(excess(r).mean() / excess(r).std(ddof=1) * np.sqrt(lab.TRADING_DAYS))
    summary = lab.summarize(result)
    lab.record_trial("universe", TRIAL_NAME, "heuristic", {"hold": an.HOLD, "cap": an.CAP}, result, "SPY", benchmark.returns, extra)
    return {"buys": len(buys), "strategy": summary, "spy": lab.summarize(benchmark), "compare_vs_spy": comparison,
            "p_one_sided": comparison["excess_p_one_sided"], "extra": extra,
            "with_bil_cash_final": lab.summarize(with_cash)["final_capital"],
            "sharpe_over_bil": {"strategy": sharpe(result.returns), "spy": sharpe(benchmark.returns)}}


def describe(frame, value, by):
    out = {}
    for key, part in frame.groupby(by, observed=True):
        means = part.groupby("positive")[value].agg(["mean", "count"])
        if True in means.index and False in means.index:
            out[str(key)] = {"positive": float(means.loc[True, "mean"]), "negative": float(means.loc[False, "mean"]),
                             "n_positive": int(means.loc[True, "count"]), "n_negative": int(means.loc[False, "count"])}
    return out


def analyze(table, market):
    rating = table[(table.family == "rating") & table.tradable]
    main = rating[~rating.near_earnings]
    upgrades = main[main.positive]
    report = {}
    confirm = {"A1": spread_test(main, "ab_20_base"), "A2": mean_test(upgrades, "net_ab_20")}
    a3 = portfolio(table, market)
    confirm["A3"] = {"p": a3["p_one_sided"], "annual_log_excess_vs_spy": a3["compare_vs_spy"]["annual_log_excess"],
                     "final_capital": a3["strategy"]["final_capital"], "spy_final": a3["spy"]["final_capital"]}
    pvals = [confirm["A1"]["p_plain"], confirm["A2"]["p_plain"], confirm["A3"]["p"]]
    for name, p in zip(confirm, holm(pvals)):
        confirm[name]["p_holm"] = float(p)
    report["confirmatory"] = confirm
    report["portfolio_A3"] = a3

    liquid = main[main.liquid]
    targets = table[(table.family == "target") & table.tradable & ~table.near_earnings]
    secondary = {
        "S1_A1_5": spread_test(main, "ab_5_base"), "S2_A1_60": spread_test(main, "ab_60_base"), "S3_A1_entry_day": spread_test(main, "ab_1_base"),
        "S4_targets_20": spread_test(targets, "ab_20_base"), "S5_A1_near_earnings": spread_test(rating[rating.near_earnings], "ab_20_base"),
        "S6_A1_liquid": spread_test(liquid, "ab_20_base"), "S7_A2_liquid": mean_test(liquid[liquid.positive], "net_ab_20"),
    }
    for name, p in zip(secondary, holm([s["p_plain"] for s in secondary.values()])):
        secondary[name]["p_holm_secondary"] = float(p)
    report["secondary"] = secondary

    report["controls"] = {
        "placebo_60_sessions_earlier": spread_test(main, "ab_placebo"),
        "sign_placebo_p_A1": ms.sign_placebo_p(main, "ab_20_base"),
        "two_way_cluster_t": {"A1": ms.two_way_cluster(main.ab_20_base, main.positive, main.entry_date, main.cik.fillna(-1))[1],
                              "A2": ms.two_way_cluster(upgrades.net_ab_20, None, upgrades.entry_date, upgrades.cik.fillna(-1))[1]},
        "exit_scenarios_A1": {s: spread_test(main, f"ab_20_{s}")["mean"] for s in SCENARIOS},
        "A2_double_costs": mean_test(upgrades, "net_ab_20_double"),
    }
    report["per_event_means"] = {"ab_20": main.groupby("positive").ab_20_base.mean().rename(index=str).to_dict(),
                                 "net_ab_20_upgrades": float(upgrades.net_ab_20.mean())}
    tiers = pd.cut(main.liquidity, [0, 1e7, 1e8, np.inf], labels=["1-10M", "10-100M", ">=100M"])
    report["descriptive"] = {
        "before_20_sessions": main.groupby("positive").ab_before.mean().rename(index=str).to_dict(),
        "A1_by_year": describe(main, "ab_20_base", main.entry_date.dt.year), "A1_by_liquidity": describe(main, "ab_20_base", tiers),
        "A2_by_year": upgrades.groupby(upgrades.entry_date.dt.year).net_ab_20.mean().rename(index=str).to_dict(),
        "share_with_earnings_in_window": float(main.earnings_in_window.mean()),
    }
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    ms.check_hashes(EXPECTED, ROOT)
    print("Empreintes conformes au gel.", flush=True)
    table, sessions, securities, funnel = load_notes()
    market = attach_daily(table)
    rating = table[table.family == "rating"]
    funnel |= {
        "rating_in_daily": int(rating.in_daily.sum()), "rating_tradable": int(rating.tradable.sum()),
        "main_upgrades": int((rating.tradable & ~rating.near_earnings & rating.positive).sum()),
        "main_downgrades": int((rating.tradable & ~rating.near_earnings & ~rating.positive).sum()),
        "main_liquid": int((rating.tradable & ~rating.near_earnings & rating.liquid).sum()),
        "a3_upgrades_tradable_at_decision": int(((rating.kind == "upgrade") & ~rating.near_earnings & rating.tradable_a3).sum()),
        "targets_main": table[(table.family == "target") & table.tradable & ~table.near_earnings].kind.value_counts().to_dict(),
    }
    print(json.dumps(funnel, indent=1, default=int), flush=True)
    if args.dry_run:
        print("Essai à blanc : arrêt avant toute lecture de rendement.")
        return
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    daily_returns(table, market)
    extremes = table[(table.raw_20 > an.EXTREME_HIGH) | (table.raw_20 < an.EXTREME_LOW)][["id", "security_id", "entry_date", "kind", "raw_20", "tradable", "near_earnings"]]
    extremes.to_csv(OUT / "extreme_returns_20.csv", index=False)
    report = {"funnel": funnel, "extreme_returns_20": len(extremes), **analyze(table, market)}
    table.drop(columns=["quarter"]).to_parquet(OUT_DATA / "events.parquet", index=False)
    (OUT / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(report, indent=1, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
