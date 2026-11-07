"""Tri des 1,4 million de news : catégorie, surprise lue dans le titre, lien vers les actions, surprise par publication.

Aucun rendement n'est lu. Corrigé après l'audit (`reports/lab_2026-11/news/AUDIT_TRI_NEWS.md`), avant toute étude.
Écrit dans `data/news/` :
- `news_articles.parquet` : une ligne par article ;
- `news_links.parquet` : une ligne par article et par titre boursier reconnu à la date de l'article ;
- `earnings_surprise.parquet` : une ligne par publication avec son écart à l'estimation citée ;
et le bilan dans `reports/lab_2026-11/news/filter_summary.json`.

Règles qui comptent pour éviter une fuite d'information :
- `available_at` = max(`created_at`, `updated_at`) : le fichier ne garde pas les versions d'un titre, on suppose donc
  le titre actuel disponible seulement après sa dernière modification. C'est une borne prudente, pas une preuve.
- Un alias de symbole peut venir d'un renommage postérieur à l'article (BBT, attribué à tort à Berkshire Hills) : il
  n'est accepté que si le titre cite le nom de la société. La liquidité moyenne n'arbitre plus rien : elle utilise le futur.
- L'estimation est celle citée par la dépêche. Sa source et sa date ne sont pas connues : ce n'est pas un consensus vérifié.

Depuis la racine : venv/bin/python reports/build_news_table.py
"""

import gzip
import json
import re
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from news_filter import CATEGORIES, LATE_RELAY, classify_headline, one_row_per_wire, parse_surprise

NEWS = ROOT / "data" / "news"
OUT = ROOT / "reports" / "lab_2026-11" / "news"
LAST_DAY = pd.Timestamp("2025-01-01", tz="UTC")
LAST_MONTH = "2024-12"
RECYCLED_AFTER_DAYS = 45
BEFORE_LISTING = pd.Timedelta(days=30)
AFTER_LAST_TRADE = pd.Timedelta(days=5)
# Fenêtre autour de l'acceptation SEC pour rattacher une dépêche à sa publication, appliquée avant tout choix.
EARNINGS_BEFORE = pd.Timedelta(hours=72)
EARNINGS_AFTER = pd.Timedelta(hours=24)
GENERIC = {"bear", "plus", "acquisition", "digital", "industrial", "york", "equity", "aqua", "the", "inc", "corp", "corporation", "co", "company", "companies", "ltd", "limited", "plc", "lp", "llc", "sa", "nv", "ag", "se", "group", "holdings", "holding", "hldgs", "trust", "international", "intl", "global", "american", "national", "first", "new", "united", "general", "financial", "bancorp", "bank", "common", "stock", "class", "shares", "ordinary", "technologies", "technology", "systems", "industries", "partners", "energy", "capital", "resources", "pharmaceuticals", "therapeutics", "of", "and", "de", "del"}


def read_articles():
    rows, symbols = [], []
    # Le nom du fichier est contrôlé avant de l'ouvrir : un fichier de 2025 ne doit même pas être lu.
    paths = [path for path in sorted(NEWS.glob("news_*.jsonl.gz")) if path.name[5:12] <= LAST_MONTH]
    for path in paths:
        with gzip.open(path, "rt") as file:
            for line in file:
                article = json.loads(line)
                rows.append((article["id"], article["created_at"], article["updated_at"], article["headline"] or "", bool(article["summary"])))
                symbols.append(article["symbols"] or [])
    table = pd.DataFrame(rows, columns=["id", "created_at", "updated_at", "headline", "has_summary"])
    table["created_at"] = pd.to_datetime(table.created_at, utc=True)
    table["updated_at"] = pd.to_datetime(table.updated_at, utc=True)
    assert table.created_at.max() < LAST_DAY and table.updated_at.max() < LAST_DAY, "Une news dépasse le 31/12/2024 : période verrouillée."
    table["available_at"] = table[["created_at", "updated_at"]].max(axis=1)
    table["n_symbols"] = [len(s) for s in symbols]
    return table, symbols


def analyze(headline):
    found = parse_surprise(headline)
    return classify_headline(headline), found["eps"], found["eps_estimate"], found["sales"], found["sales_estimate"], found["verb_conflict"], found["eps_conflict"], found["eps_ok"], found["sales_ok"], found["basis"], found["period"], found["quarter"]


def has_word(token, lowered):
    return re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered) is not None


def name_tokens(names):
    """Premier mot distinctif de chaque nom d'une société : assez pour la reconnaître dans un titre."""
    tokens = set()
    for name in names:
        for word in re.findall(r"[a-z0-9&]+", name.lower()):
            if len(word) >= 4 and word not in GENERIC:
                tokens.add(word)
                break
    return tokens


def security_lookup():
    """Symbole direct et alias séparés : seul le symbole direct suffit à relier un article, dans ses dates d'activité."""
    securities = pd.read_parquet(ROOT / "data" / "universe_clean" / "securities_dev.parquet", columns=["security_id", "symbol", "alias_symbols", "first_trade", "last_trade", "name_alpaca", "cik", "security_type", "alive_at_end"])
    companies = pd.read_parquet(ROOT / "data" / "sec" / "dev_companies.parquet", columns=["cik", "name", "former_names"])
    wanted = set(securities.cik.dropna().astype(int))
    sec_names = {}
    for cik, name, former in companies[companies.cik.isin(wanted)].itertuples(index=False):
        names = [name] if isinstance(name, str) and name else []
        names += [part for part in former.split("|") if part] if isinstance(former, str) else []
        sec_names.setdefault(cik, []).extend(names)
    direct, alias, tokens = {}, {}, {}
    for row in securities.itertuples():
        window = (row.first_trade - BEFORE_LISTING, row.last_trade + AFTER_LAST_TRADE)
        cik = None if pd.isna(row.cik) else int(row.cik)
        direct.setdefault(row.symbol, []).append((*window, cik, row.security_id))
        for name in row.alias_symbols:
            alias.setdefault(name, []).append((*window, cik, row.security_id))
        known = [row.name_alpaca] if isinstance(row.name_alpaca, str) else []
        tokens[row.security_id] = name_tokens(known + sec_names.get(cik, []))
    return direct, alias, tokens, securities.set_index("security_id")


def link_articles(table, symbols, direct, alias, tokens):
    """Un symbole cité devient le titre actif à cette date. Sociétés différentes possibles : on n'en choisit aucune."""
    ids, securities, kinds, conflicts = [], [], [], []
    counts = dict.fromkeys(["citations", "unknown_symbol", "outside_listing_dates", "linked_direct", "linked_alias_with_name", "alias_refused_no_name", "ambiguous_companies_dropped", "same_company_classes_resolved", "direct_conflicts_with_alias"], 0)
    for article, created, headline, names in zip(table.id.to_numpy(), table.created_at, table.headline, symbols):
        lowered = None
        for name in names:
            counts["citations"] += 1
            active = [c for c in direct.get(name, ()) if c[0] <= created <= c[1]]
            kind = "direct"
            if not active:
                candidates = alias.get(name)
                if not candidates and name not in direct:
                    counts["unknown_symbol"] += 1
                    continue
                active = [c for c in (candidates or ()) if c[0] <= created <= c[1]]
                if not active:
                    counts["outside_listing_dates"] += 1
                    continue
                lowered = headline.lower() if lowered is None else lowered
                active = [c for c in active if any(has_word(t, lowered) for t in tokens.get(c[3], ()))]
                if not active:
                    counts["alias_refused_no_name"] += 1
                    continue
                kind = "alias"
            if len(active) > 1 and (None in {c[2] for c in active} or len({c[2] for c in active}) > 1):
                counts["ambiguous_companies_dropped"] += 1
                continue
            # Un symbole direct peut être contredit par un alias d'une autre société : à écarter du périmètre principal.
            conflict = kind == "direct" and any(c[2] != active[0][2] and c[0] <= created <= c[1] for c in alias.get(name, ()))
            counts["direct_conflicts_with_alias"] += conflict
            if len(active) > 1:
                counts["same_company_classes_resolved"] += 1
            counts["linked_direct" if kind == "direct" else "linked_alias_with_name"] += 1
            ids.append(article)
            securities.append(min(c[3] for c in active))
            kinds.append(kind)
            conflicts.append(conflict)
    links = pd.DataFrame({"id": ids, "security_id": securities, "link": kinds, "conflict": conflicts}).drop_duplicates(["id", "security_id"])
    return links, counts


def build_surprises(table, links, securities):
    """Une ligne par publication : la première dépêche admissible qui donne le BPA et l'estimation citée.

    Tous les candidats de la fenêtre sont construits avant le choix, qui suit `available_at` puis `id` : jamais la
    proximité avec le dépôt SEC, ni la complétude future. Chaque exclusion est comptée.
    """
    events = pd.read_parquet(ROOT / "data" / "events" / "earnings_events.parquet", columns=["security_id", "cik", "period_end", "accepted_time", "days_to_filing"]).dropna(subset=["accepted_time"])
    events = events[(events.days_to_filing <= 150) & (events.accepted_time >= "2018-01-01") & (events.accepted_time < "2025-01-01")].copy()
    events["accepted_utc"] = events.accepted_time.dt.tz_localize("America/New_York", ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    events = events.dropna(subset=["accepted_utc"]).sort_values(["cik", "accepted_utc", "period_end", "security_id"]).drop_duplicates(["cik", "accepted_utc"], keep="last")
    # Périmètre principal : liens directs sans conflit. Les alias restent une heuristique (Wyndham Hotels sur Travel + Leisure).
    trusted_links = links[links.link.eq("direct") & ~links.conflict]
    earlier = table.sort_values("available_at").groupby("headline").available_at.transform("first")
    recycled = (table.available_at - earlier) >= pd.Timedelta(days=RECYCLED_AFTER_DAYS)
    wires = table[table.category == "earnings"].assign(recycled=recycled).merge(trusted_links, on="id")
    wires["cik"] = wires.security_id.map(securities.cik)
    stocks = securities.index[securities.security_type.isin(["common", "adr"])]
    # Le titre de l'événement est celui que cite la dépêche : une société (CIK) peut avoir plusieurs symboles au fil du temps.
    wires = one_row_per_wire(wires.dropna(subset=["cik"]), stocks).rename(columns={"security_id": "event_security"})
    wires["cik"] = wires.cik.astype(int)
    events["cik"] = events.cik.astype(int)
    columns = ["id", "cik", "available_at", "created_at", "updated_at", "headline", "eps", "eps_estimate", "sales", "sales_estimate", "eps_ok", "sales_ok", "basis", "period", "quarter", "eps_conflict", "recycled", "correction", "update_prefix", "late_relay", "n_stocks", "event_security"]
    candidates = events[["cik", "accepted_utc", "period_end"]].merge(wires[columns], on="cik")
    candidates["accepted_utc"] = candidates.accepted_utc.astype("datetime64[ns, UTC]")
    candidates["available_at"] = candidates.available_at.astype("datetime64[ns, UTC]")
    lag = candidates.available_at - candidates.accepted_utc
    candidates = candidates[(lag >= -EARNINGS_BEFORE) & (lag <= EARNINGS_AFTER)]

    funnel = {"publications": len(events), "with_any_earnings_wire": candidates.groupby(["cik", "accepted_utc"]).ngroups}
    steps = [
        ("with_eps_and_estimate", candidates.eps.notna()),
        ("eps_passes_checks", candidates.eps_ok),
        ("quarterly_marker", candidates.period.eq("quarter")),
        ("not_a_correction", ~candidates.correction),
        ("not_a_late_relay", ~candidates.late_relay),
        ("verb_agrees", ~candidates.eps_conflict),
        ("headline_not_recycled", ~candidates.recycled),
        ("one_stock_only", candidates.n_stocks.eq(1)),
    ]
    mask = pd.Series(True, index=candidates.index)
    for name, condition in steps:
        mask &= condition
        funnel[name] = candidates[mask].groupby(["cik", "accepted_utc"]).ngroups
    kept = candidates[mask]
    # Une dépêche ne sert qu'à une publication, la plus proche dans le temps : sinon deux trimestres partageraient un chiffre.
    kept = kept.assign(_gap=(kept.available_at - kept.accepted_utc).abs()).sort_values(["id", "_gap", "accepted_utc"]).drop_duplicates("id").drop(columns="_gap")
    first = kept.sort_values(["cik", "accepted_utc", "available_at", "id"]).drop_duplicates(["cik", "accepted_utc"])
    first = first.assign(surprise=first.eps - first.eps_estimate, wire_minus_sec_hours=(first.available_at - first.accepted_utc).dt.total_seconds() / 3600)
    # Numéro de trimestre du titre contre le numéro habituel de ce mois de clôture, pour cette société : alerte, pas correction.
    month = first.period_end.dt.month
    usual = first.groupby(["cik", month]).quarter.transform(lambda q: q.mode().iloc[0] if q.notna().any() else np.nan)
    first = first.assign(quarter_mismatch=first.quarter.notna() & usual.notna() & (first.quarter != usual))
    funnel["quarter_matches_issuer_calendar"] = int((~first.quarter_mismatch).sum())
    first = first[~first.quarter_mismatch]
    first = first.assign(principal_basis=first.basis.isin(["adjusted", "gaap"]))
    funnel["basis_stated_adjusted_or_gaap"] = int(first.principal_basis.sum())
    funnel["final_one_wire_per_publication"] = len(first)
    cited = first.event_security.map(securities.cik)
    assert cited.eq(first.cik).all() and first.event_security.isin(stocks).all(), "Le titre cité doit être une action de la société publiante."
    # Un titre qui ne cote pas ce jour-là n'a pas de prix à la minute : signalé, jamais remplacé par un autre.
    day = first.available_at.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    listed = first.event_security.map(securities.first_trade).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    last = first.event_security.map(securities.last_trade).dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
    first = first.assign(security_active=(listed <= day) & (day <= last))
    funnel["security_active_on_wire_day"] = int(first.security_active.sum())
    first.to_parquet(NEWS / "earnings_surprise.parquet", index=False)

    # La survie sert ici à décrire la sélection, jamais à la définir.
    # Au niveau de la société : `events` porte un titre arbitraire par CIK. Vivante si l'un de ses titres cote encore.
    company_alive = securities.dropna(subset=["cik"]).assign(cik=lambda f: f.cik.astype(int)).groupby("cik").alive_at_end.any()
    event_alive = events.cik.map(company_alive)
    first_alive = first.cik.map(company_alive)
    year = first.accepted_utc.dt.year
    all_year = events.accepted_utc.dt.year
    hours = first.wire_minus_sec_hours
    return {
        "funnel": funnel,
        "share_of_publications": len(first) / len(events),
        "by_year": {str(y): {"publications": int((all_year == y).sum()), "kept": int((year == y).sum()), "share": round(float((year == y).sum() / (all_year == y).sum()), 3)} for y in sorted(all_year.unique())},
        "by_survival": {"alive": round(float(first_alive.eq(True).sum() / event_alive.eq(True).sum()), 3), "gone": round(float(first_alive.eq(False).sum() / event_alive.eq(False).sum()), 3)},
        "basis": first.basis.value_counts().to_dict(),
        "sign": {"above": int((first.surprise > 0).sum()), "below": int((first.surprise < 0).sum()), "equal": int((first.surprise == 0).sum())},
        "late_relay": int(first.late_relay.sum()), "update_prefix": int(first.update_prefix.sum()),
        "wire_minus_sec_hours": {"median": float(hours.median()), "p10": float(hours.quantile(.1)), "p90": float(hours.quantile(.9))}, "wire_before_sec": float((hours < 0).mean()),
    }


def main():
    table, symbols = read_articles()
    print(f"{len(table):,} articles lus", flush=True)
    headlines = table.headline.drop_duplicates().tolist()
    with Pool(8) as pool:
        analyzed = pool.map(analyze, headlines, chunksize=5000)
    frame = pd.DataFrame(analyzed, columns=["category", "eps", "eps_estimate", "sales", "sales_estimate", "verb_conflict", "eps_conflict", "eps_ok", "sales_ok", "basis", "period", "quarter"], index=headlines)
    table = table.join(frame, on="headline")
    # Seul un titre classé en résultats compte comme surprise publiée.
    outside = table.category != "earnings"
    table.loc[outside, ["eps", "eps_estimate", "sales", "sales_estimate"]] = np.nan
    table.loc[outside, ["verb_conflict", "eps_conflict", "eps_ok", "sales_ok"]] = False
    for column in ("verb_conflict", "eps_conflict", "eps_ok", "sales_ok"):
        table[column] = table[column].astype(bool)
    table["correction"] = table.headline.str.contains(r"(?i)^\s*correct(?:ion|ed)\b")
    table["update_prefix"] = table.headline.str.contains(r"(?i)^\s*update\b")
    table["late_relay"] = table.headline.map(lambda text: bool(LATE_RELAY.search(text)))

    direct, alias, tokens, securities = security_lookup()
    links, link_stats = link_articles(table, symbols, direct, alias, tokens)
    links["security_type"] = links.security_id.map(securities.security_type)
    linked = links.groupby("id").size()
    stocks = links[links.security_type.isin(["common", "adr"])].groupby("id").size()
    table["n_securities"] = table.id.map(linked).fillna(0).astype(int)
    table["n_stocks"] = table.id.map(stocks).fillna(0).astype(int)
    table.to_parquet(NEWS / "news_articles.parquet", index=False)
    links.drop(columns=["security_type"]).to_parquet(NEWS / "news_links.parquet", index=False)

    year = table.created_at.dt.year
    categories = table.category.value_counts().reindex(CATEGORIES)
    usable = ~table.category.isin(["market_commentary", "evergreen"]) & (table.n_stocks >= 1) & table.headline.str.strip().ne("")
    earnings = table[table.category == "earnings"]
    late = (table.updated_at - table.created_at).dt.total_seconds()
    summary = {
        "articles": len(table), "unique_headlines": len(headlines),
        "categories": {k: int(v) for k, v in categories.items()},
        "categories_by_year": {str(y): {k: round(float(v), 3) for k, v in part.category.value_counts(normalize=True).reindex(CATEGORIES).fillna(0).items()} for y, part in table.groupby(year)},
        "links": link_stats, "with_stock": float((table.n_stocks >= 1).mean()), "one_stock": float((table.n_stocks == 1).mean()),
        "usable": int(usable.sum()), "usable_one_stock": int((usable & (table.n_stocks == 1)).sum()), "usable_unique_headlines": int(table[usable].headline.nunique()),
        "updated": {"over_1h": float((late > 3600).mean()), "over_1d": float((late > 86400).mean())},
        "earnings": {
            "articles": len(earnings), "with_eps_estimate": int(earnings.eps.notna().sum()), "with_sales_estimate": int(earnings.sales.notna().sum()), "eps_ok": int(earnings.eps_ok.sum()), "sales_ok": int(earnings.sales_ok.sum()),
            "verb_conflicts": int(earnings.verb_conflict.sum()), "corrections": int(earnings.correction.sum()), "late_relays": int(earnings.late_relay.sum()), "periods": earnings[earnings.eps.notna()].period.value_counts().to_dict(),
            "readable_share_by_year": {str(y): round(float(part.eps.notna().mean()), 3) for y, part in earnings.groupby(earnings.created_at.dt.year)},
        },
        "earnings_surprise": build_surprises(table, links, securities),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "filter_summary.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False))
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
