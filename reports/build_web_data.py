"""Prépare les données de l'interface web dans `web/site_data.js`, à partir des résultats déjà calculés.

Aucun nouveau test de stratégie : le journal n'est pas touché. Le script s'arrête si une courbe ne retombe
pas sur le capital publié. Rien n'est lu après le 31/12/2024, sauf les quelques chiffres de la validation
2025-2026 déjà publiés dans `RAPPORT_VALIDATION.md`, recopiés ici à la main.

Depuis la racine : venv/bin/python reports/build_web_data.py
"""

import gzip
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
from per_stock import Simulator, equal_weight_returns
from universe_data import load_universe

LAB = ROOT / "reports" / "lab_2026-11"
OUT = ROOT / "web" / "site_data.js"
CAPITAL = 10_000
EIGHT_K_TOTAL = 81_304
NEWS_MONTHS = 84
START = pd.Timestamp("2018-01-02")

STRATEGIES = {
    "control_liquid_equal_weight__top=500": ("temoin", "500 actions liquides à parts égales", "reference", "Acheter à parts égales les 500 actions les plus échangées, puis réajuster chaque mois. Sert de témoin : aucune idée, juste de la diversification."),
    "test_a_momentum__lookback=252__top=50": ("momentum", "Momentum sur 12 mois", "heuristic", "Chaque mois, garder les 50 actions qui ont le plus monté sur un an. L'idée : ce qui monte continue de monter."),
    "test_b_low_pe__liquid=1000__min_pe=3.0__top=50": ("pe", "P/E bas", "heuristic", "Chaque mois, garder les 50 actions les moins chères par rapport à leur bénéfice, parmi les 1 000 plus liquides."),
    "step3_sma200_by_stock": ("sma200", "Moyenne mobile 200 séances", "heuristic", "Pour chaque action : rester investi si le cours dépasse sa moyenne des 200 dernières séances, sinon passer en liquidités."),
    "step4_bollinger_by_stock": ("bollinger", "Bandes de Bollinger", "heuristic", "Pour chaque action : acheter quand le cours tombe nettement sous sa moyenne récente, revendre quand il y revient."),
    "step4_rsi2_by_stock": ("rsi2", "RSI sur 2 séances", "heuristic", "Pour chaque action : acheter après une baisse très courte et très forte, revendre au premier rebond."),
    "step5_ml_rank__top=50": ("ml", "Classement par machine learning", "adaptive", "Chaque mois, un modèle classe toutes les actions à partir des prix et de la liquidité, puis on garde les 50 premières. Réentraîné chaque 1er janvier."),
}


def round_list(values, digits=4):
    return [None if value is None or not np.isfinite(value) else round(float(value), digits) for value in values]


def weekly_curve(returns):
    """Capital en fin de semaine, en partant de 10 000 USD à la veille de la première période."""
    capital = CAPITAL * (1 + returns.fillna(0.0)).cumprod()
    weekly = capital.groupby(capital.index.to_period("W")).tail(1)
    if weekly.index[-1] != capital.index[-1]:
        weekly = pd.concat([weekly, capital.iloc[[-1]]])
    return weekly


def describe_curve(returns):
    returns = returns.fillna(0.0)
    weekly = weekly_curve(returns)
    daily = (1 + returns).cumprod()
    drawdown = daily / daily.cummax() - 1
    weekly_drawdown = drawdown.groupby(drawdown.index.to_period("W")).min()
    return {
        "capital": round_list(weekly.to_numpy(), 1),
        "drawdown": round_list(weekly_drawdown.to_numpy(), 4),
        "years": {str(year): round(float((1 + group).prod() - 1), 4) for year, group in returns.groupby(returns.index.year)},
    }


def build_curves():
    """Courbes de SPY, QQQ, du buy and hold moyen et des 7 essais, après contrôle des capitaux finaux."""
    market = load_universe()
    print("univers chargé", flush=True)
    dates = market.data.dates
    start = int(dates.get_loc(START))
    end = len(dates) - 1
    window = dates[start:end]
    ledger = pd.read_csv(LAB / "ledger_universe.csv").set_index("name")
    curves = {}
    weeks = None
    for key, symbol, label in (("spy", "SPY", "SPY"), ("qqq", "QQQ", "QQQ")):
        result = lab.backtest(lab.buy_hold_weights(market.benchmarks, symbol), market.benchmarks, start=window[0], exits=pd.Series(dtype=float))
        curves[key] = {"label": label, **describe_curve(result.returns)}
        weeks = weekly_curve(result.returns).index
    assert abs(curves["spy"]["capital"][-1] - ledger.benchmark_final.iloc[0]) < 1, curves["spy"]["capital"][-1]

    cohorts = pd.read_parquet(ROOT / "data" / "reference" / "buy_hold_by_cohort.parquet")
    first = cohorts[(cohorts.start == START) & (cohorts.horizon == -1)].set_index("security_id")
    simulator = Simulator(pd.DataFrame(1.0, index=dates, columns=market.data.close.columns), market)
    position = {column: i for i, column in enumerate(simulator.columns)}
    columns = np.array([position[security] for security in first.index])
    wealth, _, _ = simulator.paths(start, end, columns, always_invested=True)
    np.testing.assert_allclose(wealth[-1], first.base.to_numpy(), atol=1e-9)
    curves["buyhold"] = {"label": "Buy and hold moyen", **describe_curve(equal_weight_returns(wealth, window))}

    for name, (key, label, _, _) in STRATEGIES.items():
        returns = pd.read_parquet(LAB / "trials" / "universe" / f"{name}.parquet")["return"]
        curves[key] = {"label": label, **describe_curve(returns)}
        assert abs(curves[key]["capital"][-1] - ledger.final_capital[name]) < 1, name
    assert all(len(curve["capital"]) == len(weeks) for curve in curves.values()), {k: len(v["capital"]) for k, v in curves.items()}
    assert weeks.max() <= pd.Timestamp("2024-12-31")
    print("courbes contrôlées :", {k: v["capital"][-1] for k, v in curves.items()}, flush=True)
    return {"weeks": [d.strftime("%Y-%m-%d") for d in weeks], "series": curves}, first


def exit_sensitivity(name, row):
    """Hypothèses de sortie et frais doublés : au journal, ou dans le bilan pour les règles action par action."""
    path = LAB / "per_stock" / f"{name}_january2018.json"
    if path.exists():
        part = json.loads(path.read_text())["all"]
        return {"optimistic": round(part["mean_rule_optimistic"] * CAPITAL), "pessimistic": round(part["mean_rule_pessimistic"] * CAPITAL), "costDouble": round(part["mean_rule_cost_x2"] * CAPITAL)}
    return {"optimistic": round(row.final_capital_optimistic), "pessimistic": round(row.final_capital_pessimistic), "costDouble": round(row.final_capital_cost_x2)}


def build_strategies():
    ledger = pd.read_csv(LAB / "ledger_universe.csv").set_index("name")
    rows = []
    adjusted = {}
    for path in (LAB / "experiments").glob("*.csv"):
        table = pd.read_csv(path)
        if "romano_wolf_p" in table:
            adjusted.update(table.set_index("name").romano_wolf_p.dropna().to_dict())
    adjusted.update(pd.read_csv(LAB / "per_stock" / "adjusted_p_all_trials.csv", index_col=0).romano_wolf_p.to_dict())
    for name, (key, label, family, explain) in STRATEGIES.items():
        row = ledger.loc[name]
        rows.append({
            "id": key, "label": label, "family": family, "explain": explain,
            "final": round(row.final_capital), "cagr": round(row.cagr, 4), "volatility": round(row.volatility, 4), "sharpe": round(row.sharpe, 2),
            "maxDrawdown": round(row.max_drawdown, 4), "exposure": round(row.exposure, 3), "turnover": round(row.turnover_per_year, 1),
            "beta": round(row.beta, 2), "alpha": round(row.annual_alpha, 4), "pValue": round(row.excess_p_one_sided, 3),
            "pAdjusted": round(float(adjusted[name]), 3) if name in adjusted else None,
            **exit_sensitivity(name, row),
            "ownBuyHold": round(row.own_buy_hold_final) if np.isfinite(row.own_buy_hold_final) else None,
            "shareWins": round(row.share_rule_wins, 3) if np.isfinite(row.share_rule_wins) else None,
        })
    return rows, ledger.benchmark_final.iloc[0], ledger.benchmark_sharpe.iloc[0], ledger.benchmark_max_drawdown.iloc[0]


def build_rules():
    """Comparaison de chaque règle au buy and hold de la même action."""
    names = {"sma200": "step3_sma200_by_stock", "bollinger": "step4_bollinger_by_stock", "rsi2": "step4_rsi2_by_stock"}
    result = {}
    for key, name in names.items():
        cohorts = pd.read_csv(LAB / "per_stock" / f"{name}_cohorts.csv")
        by_date = cohorts[(cohorts.tier == "all") & (cohorts.horizon == 12)].sort_values("start")
        summary = pd.read_csv(LAB / "per_stock" / f"{name}_summary.csv")
        summary = summary[summary.tier == "all"]
        sectors = pd.read_csv(LAB / "per_stock" / f"{name}_sectors.csv").sort_values("share_rule_wins", ascending=False)
        report = json.loads((LAB / "per_stock" / f"{name}_january2018.json").read_text())
        tiers = []
        for tier, label in (("top500", "500 plus liquides"), ("top1000", "1 000 plus liquides"), ("all", "Toutes achetables")):
            part = report[tier]
            tiers.append({"label": label, "stocks": part["stocks"], "rule": round(part["rule"]["final_capital"]), "buyHold": round(part["buy_hold"]["final_capital"]), "shareWins": round(part["share_rule_wins"], 3)})
        everything = report["all"]
        result[key] = {
            "byDate": {"dates": by_date.start.str[:7].tolist(), "share": round_list(by_date.share_rule_wins, 3)},
            "horizons": [{"months": int(row.horizon), "cohorts": int(row.cohorts), "rule": round(row.mean_rule_annual, 4), "buyHold": round(row.mean_bh_annual, 4), "ruleMedian": round(row.median_rule_annual, 4), "buyHoldMedian": round(row.median_bh_annual, 4), "share": round(row.share_rule_wins, 3)} for row in summary.itertuples()],
            "sectors": [{"sector": row.sector12, "share": round(row.share_rule_wins, 3), "lines": int(row.lines)} for row in sectors.itertuples()],
            "tiers": tiers,
            "risk": {"sharpeRule": round(everything["rule"]["sharpe"], 2), "sharpeBuyHold": round(everything["buy_hold"]["sharpe"], 2), "drawdownRule": round(everything["rule"]["max_drawdown"], 3), "drawdownBuyHold": round(everything["buy_hold"]["max_drawdown"], 3), "exposureRule": round(everything["rule"]["exposure"], 3), "volatilityRule": round(everything["rule"]["volatility"], 3), "volatilityBuyHold": round(everything["buy_hold"]["volatility"], 3), "turnoverRule": round(everything["rule"]["turnover_per_year"], 1)},
        }
    return result


def build_stocks(first):
    """Une ligne par action achetée le 02/01/2018 et gardée jusqu'à fin 2024 (ou sa disparition)."""
    frames = []
    for key, name in (("sma", "step3_sma200_by_stock"), ("bol", "step4_bollinger_by_stock"), ("rsi", "step4_rsi2_by_stock")):
        table = pd.read_parquet(ROOT / "data" / "per_stock" / f"{name}.parquet", columns=["start", "horizon", "security_id", "rule_base"], filters=[("horizon", "==", -1)])
        table = table[table.start == START].set_index("security_id").rule_base.rename(key)
        frames.append(table)
    joined = pd.concat(frames, axis=1, join="inner").join(first[["base", "liquidity_rank", "exited"]], how="inner")
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["security_id", "symbol", "name_trusted", "name_alpaca"]).set_index("security_id")
    sectors = pd.read_parquet(ROOT / "data" / "reference" / "sectors.parquet")[["sector12"]]
    joined = joined.join(securities).join(sectors)
    rows = []
    for row in joined.sort_values("liquidity_rank").itertuples():
        name = row.name_trusted if isinstance(row.name_trusted, str) else row.name_alpaca
        rows.append([row.symbol, name.title() if isinstance(name, str) else "", row.sector12 if isinstance(row.sector12, str) else "Other", round(row.base, 3), round(row.sma, 3), round(row.bol, 3), round(row.rsi, 3), int(bool(row.exited))])
    print("actions pour l'explorateur :", len(rows), flush=True)
    return rows


def build_market(first):
    """Référence du buy and hold : ce que vaut en moyenne « acheter et garder »."""
    cohorts = pd.read_parquet(ROOT / "data" / "reference" / "buy_hold_by_cohort.parquet", columns=["start", "horizon", "liquidity_rank", "base"])
    cohorts = cohorts[(cohorts.start == START) & (cohorts.horizon == -1)]
    listed = pd.read_parquet(ROOT / "data" / "reference" / "buy_hold_all_listed.parquet", columns=["start", "horizon", "base"])
    listed = listed[(listed.start == START) & (listed.horizon == -1)]
    tiers = []
    for label, values in (("500 plus liquides", cohorts[cohorts.liquidity_rank <= 500].base), ("1 000 plus liquides", cohorts[cohorts.liquidity_rank <= 1000].base), ("Toutes achetables", cohorts.base), ("Toutes cotées", listed.base)):
        tiers.append({"label": label, "stocks": int(len(values)), "mean": round(values.mean() * CAPITAL), "median": round(values.median() * CAPITAL), "shareLoss": round(float((values < 1).mean()), 3)})
    # Une borne tombe sur SPY, pour que chaque barre soit entièrement au-dessus ou en dessous.
    spy_multiple = pd.read_csv(LAB / "ledger_universe.csv").benchmark_final.iloc[0] / CAPITAL
    edges = [0, 0.1, 0.25, 0.5, 0.75, 1, 1.5, 2, spy_multiple, 3.5, 5, 10, np.inf]
    counts, _ = np.histogram(first.base.clip(lower=0), bins=edges)
    histogram = [{"from": round(edges[i] * CAPITAL), "to": None if not np.isfinite(edges[i + 1]) else round(edges[i + 1] * CAPITAL), "count": int(counts[i])} for i in range(len(counts))]
    table = pd.read_csv(LAB / "reference" / "summary_by_sector.csv")
    print("classifications :", table.classification.unique().tolist(), flush=True)
    sectors = table[(table.classification == "french12") & (table.tier == "all") & (table.horizon == 60)].sort_values("mean_annual", ascending=False)
    defense = table[(table.classification != "french12") & (table.classification != "french49") & (table.tier == "all") & (table.horizon == 60)]
    horizons = pd.read_csv(LAB / "reference" / "summary_by_horizon.csv")
    long_term = pd.read_csv(LAB / "reference" / "long_term_market.csv")
    return {
        "tiers": tiers, "histogram": histogram, "shareBeatsSpy": round(float((first.base > spy_multiple).mean()), 3), "stocks": int(len(first)),
        "sectors": [{"sector": row.sector, "mean": round(row.mean_annual, 4), "median": round(row.median_annual, 4), "shareLoss": round(row.share_loss, 3), "titles": round(row.avg_titles)} for row in sectors.itertuples()],
        "themes": [{"sector": row.sector, "mean": round(row.mean_annual, 4), "median": round(row.median_annual, 4), "shareLoss": round(row.share_loss, 3), "titles": round(row.avg_titles)} for row in defense.itertuples()],
        "horizons": [{"tier": row.tier, "months": int(row.horizon), "mean": round(row.mean_annual, 4), "median": round(row.median_annual, 4), "spy": round(row.spy_annual, 4), "shareLoss": round(row.share_loss, 3), "shareBeats": round(row.share_beats_spy, 3)} for row in horizons.itertuples()],
        "longTerm": [{"window": row.window, "annual": round(row.annual, 4), "percentile": round(row.percentile_since_1926, 3)} for row in long_term.itertuples()],
    }


def build_ml():
    deciles = pd.read_csv(LAB / "ml" / "step5_ml_rank_deciles.csv", index_col=0).mean_monthly_return
    monthly = pd.read_csv(LAB / "ml" / "step5_ml_rank_monthly.csv", parse_dates=["date"])
    years = monthly.groupby(monthly.date.dt.year).rank_correlation.mean()
    return {"deciles": round_list(deciles, 5), "correlationByYear": {str(k): round(v, 4) for k, v in years.items()}, "correlationMean": round(monthly.rank_correlation.mean(), 4), "topMinusUniverse": {str(k): round(v, 4) for k, v in monthly.assign(gap=monthly.top50_mean - monthly.universe_mean).groupby(monthly.date.dt.year).gap.mean().items()}, "noCosts": 12110}


def build_events():
    results = pd.read_csv(LAB / "events" / "earnings_study_results.csv")
    net = pd.read_csv(LAB / "events" / "earnings_study_net_of_costs.csv")
    placebo = pd.read_csv(LAB / "events" / "earnings_study_date_placebo.csv")
    print("placebo", placebo.columns.tolist(), flush=True)
    reaction = pd.read_csv(LAB / "events" / "earnings_study_reaction.csv")
    results = results[results.tier == "all"]
    top1000 = net[net.tier == "top1000"]
    net = net[net.tier == "all"]
    return {
        "changes": json.loads((LAB / "events" / "earnings_study_entry_changes.json").read_text()),
        "slots": pd.read_csv(LAB / "events" / "earnings_study_by_time_slot.csv").round(7).replace({np.nan: None}).to_dict("records"),
        "top1000": [{"case": row.case, "horizon": int(row.horizon), "events": int(row.events), "vsSpy": round(row.net_minus_spy, 7)} for row in top1000.itertuples()],
        "spread": [{"case": row.case, "horizon": int(row.horizon), "spread": round(row.spread, 7), "t": round(row.t_newey_west, 2), "holm": round(row.holm_block_bootstrap, 3), "events": int(row.events), "groups": round_list([row.group_1, row.group_2, row.group_3, row.group_4, row.group_5], 5)} for row in results.itertuples()],
        "net": [{"case": row.case, "horizon": int(row.horizon), "gross": round(row.gross, 7), "net": round(row.net, 7), "vsSpy": round(row.net_minus_spy, 7)} for row in net.itertuples()],
        # Réaction jusqu'à la première ouverture où l'on peut acheter.
        "before": {case: round_list(part.sort_values("group")["mean"], 5) for case, part in reaction.groupby("case")},
        "events": 206569, "companies": 5784,
    }


def build_data_quality():
    quality = json.loads((LAB / "qc_clean.json").read_text())
    summary = json.loads((LAB / "news" / "coverage_summary.json").read_text())
    strata = pd.read_csv(LAB / "news" / "coverage_by_stratum.csv")
    week = pd.DataFrame(summary["weekly_volume"])
    month = week.assign(month=week.week.str[:7]).groupby("month").articles.sum()
    return {
        "funnel": {"symbolsBefore": quality["symbols_before"], "securitiesAfter": quality["securities_after"], "rowsBefore": quality["rows_before"], "rowsAfter": quality["rows_after"], "ghostRows": quality["rows_ghost_removed"], "aliasPairs": quality["alias_pairs"], "suspectPrints": quality["suspect_prints"], "eps": quality["eps_quarters"], "epsCompanies": quality["eps_companies"], "aliveAtEnd": quality["alive_at_end"]},
        "stocks": {"total": 8119, "gone": 2845},
        "exits": {"base": -0.18, "optimistic": -0.094, "pessimistic": -0.373},
        "news": {"strata": [{"tier": row.tier, "alive": bool(row.alive_at_end), "covered": round(row.covered, 3), "regular": round(row.regular, 3), "perYear": round(row.median_per_year)} for row in strata.itertuples()], "covered": round(summary["estimates"]["covered"], 3), "regular": round(summary["estimates"]["regular"], 3), "oneSymbol": round(summary["quality"]["share_one_symbol"], 3), "withSummary": round(summary["quality"]["share_with_summary"], 3), "inSession": round(summary["quality"]["share_in_session"], 3), "preMarket": round(summary["quality"]["share_pre_market"], 3), "afterClose": round(summary["quality"]["share_after_close"], 3), "byMonth": {"months": month.index.tolist(), "articles": month.tolist()}},
    }


def build_news_totals():
    """Compte sur tous les articles téléchargés. Les heures et les titres servent, jamais un rendement."""
    rows = []
    for path in sorted((ROOT / "data" / "news").glob("news_*.jsonl.gz")):
        with gzip.open(path, "rt") as file:
            for line in file:
                article = json.loads(line)
                rows.append((article["created_at"], len(article["symbols"] or []), bool(article["summary"])))
    table = pd.DataFrame(rows, columns=["created", "symbols", "summary"])
    created = pd.to_datetime(table.created, utc=True).dt.tz_convert("America/New_York")
    assert created.max().year <= 2024
    minutes = created.dt.hour * 60 + created.dt.minute
    weekday = created.dt.dayofweek < 5
    years = table.groupby(created.dt.year.to_numpy())
    return {
        "total": len(table), "oneSymbol": round(float((table.symbols == 1).mean()), 3), "withSummary": round(float(table.summary.mean()), 3),
        "preMarket": round(float((weekday & (minutes < 570)).mean()), 3), "inSession": round(float((weekday & (minutes >= 570) & (minutes < 960)).mean()), 3), "afterClose": round(float((weekday & (minutes >= 960)).mean()), 3), "weekend": round(float((~weekday).mean()), 3),
        "byYear": [{"year": int(year), "articles": len(part), "summary": round(float(part.summary.mean()), 3)} for year, part in years],
    }


def build_journal():
    """Les 244 essais du premier laboratoire, sur TSLA et de grandes valeurs choisies, 2018-2024."""
    table = pd.concat([pd.read_csv(LAB / "ledger_claude.csv"), pd.read_csv(LAB / "ledger_codex.csv")])
    assert len(table) == 244
    edges = np.arange(-0.5, 0.51, 0.05)
    counts, _ = np.histogram(table.annual_log_excess.clip(-0.4999, 0.4999), bins=edges)
    return {"histogram": [{"from": round(edges[i], 2), "to": round(edges[i + 1], 2), "count": int(counts[i])} for i in range(len(counts))], "total": len(table), "shareBeats": round(float((table.annual_log_excess > 0).mean()), 3), "significant": int((table.excess_p_one_sided < 0.05).sum())}


def download_status():
    """Téléchargements encore incomplets au moment de la construction, d'après les fichiers présents."""
    status = {"builtAt": pd.Timestamp.now().strftime("%d/%m/%Y à %H:%M")}
    done = sum(pd.read_parquet(path, columns=["status"]).status.eq("ok").sum() for path in (ROOT / "data" / "events" / "eight_k_times").glob("batch_*.parquet"))
    if done < EIGHT_K_TOTAL:
        status["sec"] = {"done": int(done), "total": EIGHT_K_TOTAL}
    months = sorted(path.name[5:12] for path in (ROOT / "data" / "news").glob("news_*.jsonl.gz"))
    if len(months) < NEWS_MONTHS:
        status["news"] = {"month": months[-1] if months else "2018-01", "articles": None}
    return status


def main():
    curves, first = build_curves()
    strategies, spy_final, spy_sharpe, spy_drawdown = build_strategies()
    data = {
        "capital": CAPITAL, "curves": curves, "strategies": strategies,
        "spy": {"final": round(spy_final), "sharpe": round(spy_sharpe, 2), "maxDrawdown": round(spy_drawdown, 4)},
        "rules": build_rules(), "stocks": build_stocks(first), "market": build_market(first), "ml": build_ml(),
        "events": build_events(), "data": {**build_data_quality(), "newsTotals": build_news_totals()}, "journal": build_journal(), "status": download_status(),
        # Publié dans RAPPORT_VALIDATION.md et CLAUDE.md : aucune lecture des données de 2025-2026 ici.
        "validation": [
            {"label": "Rotation top 3 sur 7 grandes valeurs", "final": 10050, "reference": 13274, "referenceLabel": "panier égal"},
            {"label": "Filtre QQQ sur TSLA", "final": 8527, "reference": 10070, "referenceLabel": "TSLA conservée"},
            {"label": "Ciblage de volatilité sur TSLA", "final": 10178, "reference": 10070, "referenceLabel": "TSLA conservée"},
            {"label": "Sortie sur news sur TSLA", "final": 8090, "reference": 10070, "referenceLabel": "TSLA conservée"},
        ],
        # Publié dans reports/Backtest_Musk_Tesla_2026-10-25.md et CLAUDE.md, 2022-2024, grille de 15 minutes.
        "intraday": [
            {"label": "Prix seuls", "gross": -0.2110, "net": -0.8245},
            {"label": "Prix et Jev", "gross": -0.1854, "net": -0.8190},
            {"label": "Prix et FinBERT", "gross": -0.2428, "net": -0.8344},
        ],
        "intradayPassive": 0.054,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("window.SITE_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + ";\n")
    print(f"{OUT.relative_to(ROOT)} : {OUT.stat().st_size / 1024:.0f} Ko", flush=True)


if __name__ == "__main__":
    main()
