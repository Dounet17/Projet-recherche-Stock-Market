"""Tri des 1,4 million de news : catégorie, surprise lue dans le titre, lien vers les actions.

Aucun rendement n'est lu : le tri ne peut donc pas être réglé sur les résultats. Écrit dans `data/news/` :
- `news_articles.parquet` : une ligne par article ;
- `news_links.parquet` : une ligne par article et par titre boursier reconnu à la date de l'article ;
et le bilan dans `reports/lab_2026-11/news/filter_summary.json`.

Depuis la racine : venv/bin/python reports/build_news_table.py
"""

import gzip
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from news_filter import CATEGORIES, classify_headline, parse_surprise

NEWS = ROOT / "data" / "news"
OUT = ROOT / "reports" / "lab_2026-11" / "news"
BEFORE_LISTING = pd.Timedelta(days=30)
AFTER_LAST_TRADE = pd.Timedelta(days=5)
# Fenêtre autour de l'heure d'acceptation SEC pour rattacher une dépêche de résultats à sa publication.
EARNINGS_BEFORE = pd.Timedelta(days=3)
EARNINGS_AFTER = pd.Timedelta(days=1)


def read_articles():
    rows, symbols = [], []
    for path in sorted(NEWS.glob("news_*.jsonl.gz")):
        with gzip.open(path, "rt") as file:
            for line in file:
                article = json.loads(line)
                rows.append((article["id"], article["created_at"], article["updated_at"], article["headline"] or "", bool(article["summary"])))
                symbols.append(article["symbols"] or [])
    table = pd.DataFrame(rows, columns=["id", "created_at", "updated_at", "headline", "has_summary"])
    table["created_at"] = pd.to_datetime(table.created_at, utc=True)
    table["updated_at"] = pd.to_datetime(table.updated_at, utc=True)
    table["n_symbols"] = [len(s) for s in symbols]
    return table, symbols


def analyze(headline):
    found = parse_surprise(headline)
    return classify_headline(headline), found["eps"], found["eps_estimate"], found["sales"], found["sales_estimate"], found["verb_conflict"]


def security_lookup():
    """Symbole vers titres possibles, avec leurs dates : un même symbole peut changer de société."""
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["security_id", "symbol", "alias_symbols", "first_trade", "last_trade", "mean_dollar_volume", "security_type"])
    lookup = {}
    for row in securities.itertuples():
        first, last = pd.Timestamp(row.first_trade), pd.Timestamp(row.last_trade)
        first = first.tz_localize("UTC") if first.tzinfo is None else first
        last = last.tz_localize("UTC") if last.tzinfo is None else last
        aliases = row.alias_symbols
        if isinstance(aliases, str):
            aliases = [a for a in aliases.replace(",", " ").replace("|", " ").split() if a]
        elif aliases is None or (isinstance(aliases, float) and np.isnan(aliases)):
            aliases = []
        for symbol in {row.symbol, *aliases}:
            lookup.setdefault(symbol, []).append((first - BEFORE_LISTING, last + AFTER_LAST_TRADE, row.mean_dollar_volume if np.isfinite(row.mean_dollar_volume) else 0.0, row.security_id))
    return lookup, securities.set_index("security_id").security_type


def link_articles(table, symbols, lookup):
    """Un symbole cité devient le titre actif à cette date ; s'il y en a plusieurs, le plus liquide."""
    ids, securities, ambiguous = [], [], 0
    unknown, outside, cited = 0, 0, 0
    for article, created, names in zip(table.id.to_numpy(), table.created_at, symbols):
        for name in names:
            cited += 1
            candidates = lookup.get(name)
            if not candidates:
                unknown += 1
                continue
            active = [c for c in candidates if c[0] <= created <= c[1]]
            if not active:
                outside += 1
                continue
            ambiguous += len(active) > 1
            ids.append(article)
            securities.append(max(active, key=lambda c: c[2])[3])
    links = pd.DataFrame({"id": ids, "security_id": securities}).drop_duplicates()
    return links, {"citations": cited, "unknown_symbol": unknown, "outside_listing_dates": outside, "linked": cited - unknown - outside, "ambiguous_resolved_by_liquidity": int(ambiguous)}


def earnings_coverage(table, links):
    """Combien de publications ont une dépêche donnant la surprise, et avec quel délai sur l'acceptation SEC."""
    events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["security_id", "cik", "period_end", "accepted_time", "days_to_filing"]).dropna(subset=["accepted_time"])
    events = events[(events.days_to_filing <= 150) & (events.accepted_time >= "2018-01-01")]
    events["accepted_utc"] = events.accepted_time.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    events = events.dropna(subset=["accepted_utc"]).drop_duplicates(["cik", "accepted_utc"])
    wires = table[table.category.eq("earnings") & (table.eps.notna() | table.sales.notna())][["id", "created_at", "eps", "eps_estimate", "sales", "sales_estimate"]].merge(links, on="id")
    wires["created_at"] = wires.created_at.astype("datetime64[ns, UTC]")
    events["accepted_utc"] = events.accepted_utc.astype("datetime64[ns, UTC]")
    wires = wires.sort_values("created_at")
    events = events.sort_values("accepted_utc")
    matched = pd.merge_asof(events, wires, left_on="accepted_utc", right_on="created_at", by="security_id", direction="nearest", tolerance=EARNINGS_BEFORE)
    lag = matched.created_at - matched.accepted_utc
    near = matched.created_at.notna() & (lag >= -EARNINGS_BEFORE) & (lag <= EARNINGS_AFTER)
    hours = lag[near].dt.total_seconds() / 3600
    by_year = near.groupby(matched.accepted_utc.dt.year).mean().round(3).to_dict()
    has_eps = matched.eps.notna() & near
    return {
        "events": int(len(matched)), "with_wire": float(near.mean()), "with_eps_estimate": float(has_eps.mean()), "by_year": {str(k): v for k, v in by_year.items()},
        "wire_minus_sec_hours": {"median": float(hours.median()), "p10": float(hours.quantile(.1)), "p90": float(hours.quantile(.9))},
        "wire_before_sec": float((hours < 0).mean()),
    }


def main():
    table, symbols = read_articles()
    print(f"{len(table):,} articles lus", flush=True)
    headlines = table.headline.drop_duplicates().tolist()
    with Pool(8) as pool:
        analyzed = pool.map(analyze, headlines, chunksize=5000)
    frame = pd.DataFrame(analyzed, columns=["category", "eps", "eps_estimate", "sales", "sales_estimate", "verb_conflict"], index=headlines)
    table = table.join(frame, on="headline")
    # Seul un titre classé en résultats compte comme surprise publiée.
    outside = table.category != "earnings"
    table.loc[outside, ["eps", "eps_estimate", "sales", "sales_estimate"]] = np.nan
    table.loc[outside, "verb_conflict"] = False
    table["verb_conflict"] = table.verb_conflict.astype(bool)

    lookup, types = security_lookup()
    links, link_stats = link_articles(table, symbols, lookup)
    links["security_type"] = links.security_id.map(types)
    linked = links.groupby("id").size()
    stocks = links[links.security_type.isin(["common", "adr"])].groupby("id").size()
    table["n_securities"] = table.id.map(linked).fillna(0).astype(int)
    table["n_stocks"] = table.id.map(stocks).fillna(0).astype(int)
    table.drop(columns=["updated_at"]).to_parquet(NEWS / "news_articles.parquet", index=False)
    links.drop(columns=["security_type"]).to_parquet(NEWS / "news_links.parquet", index=False)

    year = table.created_at.dt.year
    categories = table.category.value_counts().reindex(CATEGORIES)
    usable = ~table.category.isin(["market_commentary", "evergreen"]) & (table.n_stocks >= 1)
    earnings = table[table.category == "earnings"]
    parsed_eps, parsed_sales = earnings.eps.notna(), earnings.sales.notna()
    summary = {
        "articles": len(table), "unique_headlines": len(headlines),
        "categories": {k: int(v) for k, v in categories.items()},
        "categories_by_year": {str(y): {k: round(float(v), 3) for k, v in part.category.value_counts(normalize=True).reindex(CATEGORIES).fillna(0).items()} for y, part in table.groupby(year)},
        "links": link_stats, "with_stock": float((table.n_stocks >= 1).mean()), "one_stock": float((table.n_stocks == 1).mean()),
        "usable": int(usable.sum()), "usable_one_stock": int((usable & (table.n_stocks == 1)).sum()), "usable_unique_headlines": int(table[usable].headline.nunique()),
        "earnings": {"articles": len(earnings), "with_eps_estimate": int(parsed_eps.sum()), "with_sales_estimate": int(parsed_sales.sum()), "verb_conflicts": int(earnings.verb_conflict.sum()), "eps_beats": int((earnings.eps > earnings.eps_estimate).sum()), "eps_misses": int((earnings.eps < earnings.eps_estimate).sum()), "eps_equal": int((earnings.eps == earnings.eps_estimate).sum())},
        "earnings_coverage": earnings_coverage(table, links),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "filter_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    # Tirage figé, distinct de celui qui a servi à écrire les règles : il mesure l'erreur sans se la cacher.
    sample = table.groupby("category", group_keys=False).sample(n=60, random_state=20261108)[["category", "headline", "n_stocks"]].sort_values("category")
    sample.to_csv(OUT / "filter_sample_to_review.csv", index=False)


if __name__ == "__main__":
    main()
