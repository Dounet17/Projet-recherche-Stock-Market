"""Lancement unique de l'étude figée dans `reports/lab_2026-11/PROTOCOLE_NOTES_ANALYSTES.md`.

Vérifie d'abord les empreintes des données du gel. Avec `--dry-run`, s'arrête après les effectifs et les exclusions :
aucun rendement n'est lu (seuls les filtres de prix et de liquidité, comme ailleurs dans le projet).

Deux échantillons distincts (relecture de Codex, `analyst_study/AUDIT_CODE_CODEX.md`) :
- A1, A2 : étude d'événements, notes regroupées par séance d'entrée, exclusion symétrique et rétrospective des notes
  proches d'une publication de résultats ;
- A3 : portefeuille achetable, notes regroupées par séance de décision avec les seules notes déjà connues, exclusion
  des seules publications déjà faites.

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
    "data/reference/buy_hold_by_cohort.parquet": "df7456f7ccd3ad18e432e8281c54400e14b7d090fd06aa127fcd63f07dbb500d",
}
OUT = ROOT / "reports" / "lab_2026-11" / "analyst_study"
OUT_DATA = ROOT / "data" / "events" / "analyst_study"
HORIZONS = (1, 5, 20, 60)
SCENARIOS = ("base", "optimistic", "pessimistic")
TRIAL_NAME = "analyst_upgrades_hold20"
QUARTERS = 28
REFERENCE_START = pd.Timestamp("2018-01-02")


def load_notes():
    """Notes admissibles, avant tout regroupement, avec leurs deux horloges et leurs drapeaux de résultats."""
    calendar = pd.read_parquet(ROOT / "data" / "calendar.parquet")
    sessions = ms.session_table(calendar)
    columns = ["id", "available_at", "headline", "category", "n_stocks", "correction", "late_relay"]
    articles = pd.read_parquet(ROOT / "data" / "news" / "news_articles.parquet", columns=columns)
    assert articles.available_at.max() < pd.Timestamp("2025-01-01", tz="UTC"), "Période verrouillée"
    links = pd.read_parquet(ROOT / "data" / "news" / "news_links.parquet")
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet").set_index("security_id")
    analyst = articles[articles.category == "analyst"]
    funnel = {"analyst_articles": len(analyst), "credit_agency_titles_refused": int(analyst.headline.str.contains(an.CREDIT_AGENCY).sum())}
    notes = an.select_notes(articles, links, securities.security_type)
    funnel["selected_by_kind"] = notes.kind.value_counts().to_dict()
    notes["available_ns"] = notes.available_at.dt.tz_convert("UTC").dt.as_unit("ns").astype("int64")
    notes["entry_idx"] = ms.entry_sessions(notes.available_ns.to_numpy(), sessions.open_ns.to_numpy())
    notes["decision_idx"] = an.decision_sessions(notes.available_ns.to_numpy(), sessions.close_ns.to_numpy())
    notes["before_idx"] = ms.placebo_sessions(notes.available_ns.to_numpy(), sessions.close_ns.to_numpy())
    notes = notes[notes.entry_idx < len(sessions)].copy()
    # Contrôles anti-fuite : entrée et décision au moins 5 minutes après la note ; fenêtre « avant » terminée avant elle.
    assert (sessions.open_ns.to_numpy()[notes.entry_idx] >= notes.available_ns.to_numpy() + ms.LATENCY).all()
    ok = notes.decision_idx < len(sessions)
    assert (sessions.close_ns.to_numpy()[notes.decision_idx[ok]] >= notes.available_ns[ok].to_numpy() + ms.LATENCY).all()
    known = notes.before_idx >= 0
    assert (sessions.close_ns.to_numpy()[notes.before_idx[known]] <= notes.available_ns[known].to_numpy()).all()
    notes["entry_date"] = sessions.date.to_numpy()[notes.entry_idx]
    notes["decision_date"] = sessions.date.reindex(notes.decision_idx).to_numpy()
    notes["before_date"] = sessions.date.reindex(notes.before_idx).to_numpy()
    assert notes.entry_date.max() <= ms.LAST_DAY
    notes["cik"] = notes.security_id.map(securities.cik)

    events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["cik", "announced", "filed"])
    events["day"] = events.announced.fillna(events.filed)
    events = events.dropna(subset=["day", "cik"])
    events["pos"] = np.searchsorted(sessions.date.to_numpy(), events.day.to_numpy().astype(sessions.date.dtype))
    positions = {int(c): np.sort(g.pos.to_numpy()) for c, g in events.groupby("cik")}
    notes["near_earnings"] = an.near_earnings(notes.cik.to_numpy(), notes.entry_idx.to_numpy(), positions)
    notes["past_earnings"] = an.past_earnings(notes.cik.to_numpy(), notes.decision_idx.to_numpy(), positions)
    notes["calendar_covered"] = an.calendar_covered(notes.cik.to_numpy(), positions)
    notes["earnings_in_window"] = an.earnings_inside(notes.cik.to_numpy(), notes.entry_idx.to_numpy(), positions)
    return notes, sessions, funnel


def event_table(notes):
    """A1, A2 et secondaires : regroupement par séance d'entrée, chaque famille à part."""
    ratings = an.collapse(notes, ("upgrade", "downgrade"))
    targets = an.collapse(notes, ("target_up", "target_down"))
    table = pd.concat([ratings.assign(family="rating"), targets.assign(family="target")], ignore_index=True)
    table["positive"] = table.kind.isin(["upgrade", "target_up"])
    table["quarter"] = table.entry_date.dt.to_period("Q")
    return table


def portfolio_table(notes):
    """A3 : relèvements regroupés par séance de décision, à partir des notes brutes, contradictions comprises."""
    a3 = an.collapse(notes, ("upgrade", "downgrade"), key="decision_idx")
    return a3[(a3.kind == "upgrade") & a3.decision_date.notna()].copy()


def load_market(table, a3):
    symbols = set(table.security_id.str.split("#").str[0]) | set(a3.security_id.str.split("#").str[0])
    return load_universe(symbols=symbols)


def attach_daily(table, a3, market):
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
    table["before_row"] = dates.get_indexer(table.before_date)

    # A3 : achat à l'ouverture qui suit la clôture de décision ; achetable connu à cette clôture.
    drow = dates.get_indexer(a3.decision_date)
    acol = columns.get_indexer(a3.security_id)
    a3["decision_row"], a3["col"] = drow, acol
    a3["tradable_a3"] = False
    good = (drow >= 0) & (acol >= 0)
    a3.loc[good, "tradable_a3"] = market.data.tradable.to_numpy()[drow[good], acol[good]]


def daily_returns(table, market):
    opens, closes = market.data.open.to_numpy(), market.data.close.to_numpy()
    last_rows = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
    spy_open = market.benchmarks.open["SPY"].to_numpy()
    spy_close = market.benchmarks.close["SPY"].ffill().to_numpy()
    ok = table.in_daily.to_numpy()

    def window(start, horizon, scenario):
        """Rendement anormal et rendement brut de l'ouverture `start` à la clôture de `start + horizon - 1`."""
        abnormal, raw = np.full(len(table), np.nan), np.full(len(table), np.nan)
        valid = ok & (start >= 0)
        exits = market.exits[scenario].reindex(market.data.close.columns).to_numpy(dtype=float)
        value = ms.daily_window(opens, closes, start[valid], table.col.to_numpy()[valid], horizon, exits, last_rows)
        end = start[valid] + horizon - 1
        inside = end < closes.shape[0]
        spy = np.full(valid.sum(), np.nan)
        spy[inside] = spy_close[end[inside]] / spy_open[start[valid][inside]] - 1
        abnormal[valid], raw[valid] = value - spy, value
        return abnormal, raw

    rows = table.row.to_numpy()
    cost = table.cost_bps / 1e4
    for horizon in HORIZONS:
        for scenario in SCENARIOS:
            table[f"ab_{horizon}_{scenario}"], table[f"raw_{horizon}_{scenario}"] = window(rows, horizon, scenario)
    for scenario in SCENARIOS:
        spy20 = table[f"raw_20_{scenario}"] - table[f"ab_20_{scenario}"]
        table[f"net_ab_20_{scenario}"] = (1 + table[f"raw_20_{scenario}"]) * (1 - cost) ** 2 - 1 - spy20
    spy20 = table.raw_20_base - table.ab_20_base
    table["net_ab_20_double"] = (1 + table.raw_20_base) * (1 - 2 * cost) ** 2 - 1 - spy20
    for scenario in SCENARIOS:
        table[f"ab_placebo_{scenario}"], _ = window(rows - an.PLACEBO_SHIFT, 20, scenario)
        # Les 20 séances terminées avant la note : fin à la clôture de la dernière séance finie avant elle (relecture D3).
        before = table.before_row.to_numpy()
        table[f"ab_before_{scenario}"], _ = window(np.where(before >= 0, before - 19, -1), 20, scenario)


def headline(stats):
    """Résultat principal : t ordinaire sur les trimestres ; Newey-West à part, en sensibilité (relecture D5)."""
    return {"quarters": stats["quarters"], "mean": stats["mean"], "t": stats["t_plain"], "p": stats["p_plain"],
            "ci_low": stats["ci_low_plain"], "ci_high": stats["ci_high_plain"],
            "newey_west": {"t": stats["t"], "p": stats["p"], "ci_low": stats["ci_low"], "ci_high": stats["ci_high"]}}


def spread_test(frame, value, require=False):
    out = headline(ms.summarize(ms.quarterly_spread(frame, value)))
    if require and out["quarters"] != QUARTERS:
        raise RuntimeError(f"{value} : {out['quarters']} trimestres au lieu de {QUARTERS}")
    return out | {"events_positive": int(frame[value].notna()[frame.positive].sum()), "events_negative": int(frame[value].notna()[~frame.positive].sum())}


def mean_test(frame, value, require=False):
    out = headline(ms.summarize(ms.quarterly_mean(frame, value)))
    if require and out["quarters"] != QUARTERS:
        raise RuntimeError(f"{value} : {out['quarters']} trimestres au lieu de {QUARTERS}")
    return out | {"events": int(frame[value].notna().sum())}


def reference_buy_and_hold():
    """Buy and hold à poids égaux de toutes les actions achetables le 02/01/2018, gardées jusqu'à fin 2024."""
    table = pd.read_parquet(ROOT / "data" / "reference" / "buy_hold_by_cohort.parquet")
    part = table[(table.start == REFERENCE_START) & (table.horizon == -1)]
    return {"securities": len(part), **{s: float(10_000 * part[s].mean()) for s in SCENARIOS}}


def portfolio(a3, market):
    """A3 : relèvements achetables à la décision, moteur quotidien, comparaison à SPY."""
    buys = a3[a3.tradable_a3 & ~a3.past_earnings & (a3.decision_row >= 0)]
    closes = market.data.close.to_numpy()
    last = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
    gone = market.exits["base"].reindex(market.data.close.columns).notna().to_numpy()
    last_rows = {s: int(last[i]) for i, s in enumerate(market.data.close.columns) if gone[i]}
    weights = an.portfolio_weights(buys.decision_row.to_numpy(), buys.security_id.to_numpy(), market.data.close.index, last_rows=last_rows)
    result, benchmark, extra = run_variant(weights, market, lab.DEV_START, lab.DEV_END, n_random=20, seed=0)
    comparison = lab.compare(result.returns, benchmark.returns)
    bil_open = market.benchmarks.open["BIL"]
    cash = (bil_open.shift(-1) / bil_open - 1).fillna(0.0)
    with_cash = lab.backtest(weights, market.data, start=lab.DEV_START, end=lab.DEV_END, cost_bps=market.data.cost_bps, exits=market.exits["base"], cash_returns=cash)
    excess = lambda r: r - cash.reindex(r.index).fillna(0.0)
    sharpe = lambda r: float(excess(r).mean() / excess(r).std(ddof=1) * np.sqrt(lab.TRADING_DAYS))
    lab.record_trial("universe", TRIAL_NAME, "heuristic", {"hold": an.HOLD, "cap": an.CAP}, result, "SPY", benchmark.returns, extra)
    return {"buys": len(buys), "excluded_past_earnings": int((a3.tradable_a3 & a3.past_earnings).sum()),
            "strategy": lab.summarize(result), "spy": lab.summarize(benchmark), "compare_vs_spy": comparison,
            "p_one_sided": comparison["excess_p_one_sided"], "extra": extra, "with_bil_cash_final": lab.summarize(with_cash)["final_capital"],
            "sharpe_over_bil": {"strategy": sharpe(result.returns), "spy": sharpe(benchmark.returns)},
            "reference_buy_and_hold_tradable_2018": reference_buy_and_hold(),
            "note": "Écart annuel en log-rendements quotidiens, bootstrap stationnaire de lab.compare, p unilatérale."}


def describe(frame, value, by):
    out = {}
    for key, part in frame.groupby(by, observed=True):
        means = part.groupby("positive")[value].agg(["mean", "count"])
        if True in means.index and False in means.index:
            out[str(key)] = {"positive": float(means.loc[True, "mean"]), "negative": float(means.loc[False, "mean"]),
                             "n_positive": int(means.loc[True, "count"]), "n_negative": int(means.loc[False, "count"])}
    return out


def analyze(table, a3, market):
    rating = table[(table.family == "rating") & table.tradable]
    main = rating[~rating.near_earnings]
    upgrades = main[main.positive]
    report = {}
    confirm = {"A1": spread_test(main, "ab_20_base", require=True), "A2": mean_test(upgrades, "net_ab_20_base", require=True)}
    a3_out = portfolio(a3, market)
    confirm["A3"] = {"p": a3_out["p_one_sided"], "annual_log_excess_vs_spy": a3_out["compare_vs_spy"]["annual_log_excess"],
                     "final_capital": a3_out["strategy"]["final_capital"], "spy_final": a3_out["spy"]["final_capital"]}
    for name, p in zip(confirm, holm([confirm["A1"]["p"], confirm["A2"]["p"], confirm["A3"]["p"]])):
        confirm[name]["p_holm"] = float(p)
    report["confirmatory"] = confirm
    report["portfolio_A3"] = a3_out

    liquid = main[main.liquid]
    targets = table[(table.family == "target") & table.tradable & ~table.near_earnings]
    secondary = {
        "S1_A1_5": spread_test(main, "ab_5_base"), "S2_A1_60": spread_test(main, "ab_60_base"), "S3_A1_entry_day": spread_test(main, "ab_1_base"),
        "S4_targets_20": spread_test(targets, "ab_20_base"), "S5_A1_near_earnings": spread_test(rating[rating.near_earnings], "ab_20_base"),
        "S6_A1_liquid": spread_test(liquid, "ab_20_base"), "S7_A2_liquid": mean_test(liquid[liquid.positive], "net_ab_20_base"),
    }
    for name, p in zip(secondary, holm([s["p"] for s in secondary.values()])):
        secondary[name]["p_holm_secondary"] = float(p)
    report["secondary"] = secondary

    report["controls"] = {
        "placebo_60_sessions_earlier": {s: spread_test(main, f"ab_placebo_{s}") for s in SCENARIOS},
        "sign_placebo_p_A1": ms.sign_placebo_p(main, "ab_20_base"),
        "sign_placebo_note": "Permutation des signes au sein du trimestre : A1 seulement, A2 n'ayant qu'un groupe.",
        "two_way_cluster": {
            "note": "Régression pondérée par événement : estime une moyenne par événement, pas la moyenne des trimestres.",
            "A1": dict(zip(("per_event_difference", "t"), ms.two_way_cluster(main.ab_20_base, main.positive, main.entry_date, main.cik.fillna(-1)))),
            "A2": dict(zip(("per_event_mean", "t"), ms.two_way_cluster(upgrades.net_ab_20_base, None, upgrades.entry_date, upgrades.cik.fillna(-1)))),
        },
        "exit_scenarios": {"A1": {s: spread_test(main, f"ab_20_{s}")["mean"] for s in SCENARIOS},
                           "A2": {s: mean_test(upgrades, f"net_ab_20_{s}") for s in SCENARIOS}},
        "A2_double_costs": mean_test(upgrades, "net_ab_20_double"),
        "calendar_not_covered": {f"{kind} {year}": int(n) for (kind, year), n in main[~main.calendar_covered].groupby([main.kind, main.entry_date.dt.year]).size().items()},
        "missing_entry_open": int(main.ab_20_base.isna().sum()),
    }
    report["per_event_means"] = {"ab_20": main.groupby("positive").ab_20_base.mean().rename(index=str).to_dict(),
                                 "net_ab_20_upgrades": float(upgrades.net_ab_20_base.mean())}
    tiers = pd.cut(main.liquidity, [0, 1e7, 1e8, np.inf], labels=["1-10M", "10-100M", ">=100M"])
    report["descriptive"] = {
        "before_20_sessions": {s: main.groupby("positive")[f"ab_before_{s}"].mean().rename(index=str).to_dict() for s in SCENARIOS},
        "A1_by_year": describe(main, "ab_20_base", main.entry_date.dt.year), "A1_by_liquidity": describe(main, "ab_20_base", tiers),
        "A2_by_year": upgrades.groupby(upgrades.entry_date.dt.year).net_ab_20_base.mean().rename(index=str).to_dict(),
        "A2_by_liquidity": upgrades.groupby(tiers[upgrades.index], observed=True).net_ab_20_base.mean().rename(index=str).to_dict(),
        "share_with_earnings_in_window": float(main.earnings_in_window.mean()),
    }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    ms.check_hashes(EXPECTED, ROOT)
    print("Empreintes conformes au gel.", flush=True)
    notes, sessions, funnel = load_notes()
    table, a3 = event_table(notes), portfolio_table(notes)
    market = load_market(table, a3)
    attach_daily(table, a3, market)
    rating = table[table.family == "rating"]
    main_mask = rating.tradable & ~rating.near_earnings
    funnel |= {
        "after_same_entry_collapse": table.kind.value_counts().to_dict(),
        "near_earnings_share": table.groupby("kind").near_earnings.mean().round(3).to_dict(),
        "rating_in_daily": int(rating.in_daily.sum()), "rating_tradable": int(rating.tradable.sum()),
        "main_upgrades": int((main_mask & rating.positive).sum()), "main_downgrades": int((main_mask & ~rating.positive).sum()),
        "main_liquid": int((main_mask & rating.liquid).sum()),
        "main_calendar_not_covered": int((main_mask & ~rating.calendar_covered).sum()),
        "a3_upgrades_after_decision_collapse": len(a3),
        "a3_tradable_at_decision": int(a3.tradable_a3.sum()),
        "a3_excluded_past_earnings": int((a3.tradable_a3 & a3.past_earnings).sum()),
        "a3_buys": int((a3.tradable_a3 & ~a3.past_earnings).sum()),
        "targets_main": table[(table.family == "target") & table.tradable & ~table.near_earnings].kind.value_counts().to_dict(),
    }
    print(json.dumps(funnel, indent=1, default=int), flush=True)
    if args.dry_run:
        print("Essai à blanc : arrêt avant toute lecture de rendement.")
        return funnel
    OUT.mkdir(parents=True, exist_ok=True)
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    daily_returns(table, market)
    extremes = table[(table.raw_20_base > an.EXTREME_HIGH) | (table.raw_20_base < an.EXTREME_LOW)][["id", "security_id", "entry_date", "kind", "raw_20_base", "tradable", "near_earnings"]]
    extremes.to_csv(OUT / "extreme_returns_20.csv", index=False)
    report = {"funnel": funnel, "extreme_returns_20": len(extremes), **analyze(table, a3, market)}
    table.drop(columns=["quarter"]).to_parquet(OUT_DATA / "events.parquet", index=False)
    a3.to_parquet(OUT_DATA / "portfolio_signals.parquet", index=False)
    (OUT / "summary.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(report, indent=1, ensure_ascii=False, default=float))
    return report


if __name__ == "__main__":
    main()
