"""Construit le dataset quotidien propre, sur 2016-2024 uniquement, à partir de data/universe/.

Produit dans data/universe_clean/ :
- prices_dev.parquet : une ligne par titre et par séance, sans cours fantôme ni doublon ;
- securities_dev.parquet : une ligne par titre (type, société SEC, cause et rendement de sortie) ;
- aliases_dev.parquet : symboles retirés comme doublons, et le titre conservé ;
- cuts_dev.parquet : coupures de symboles réutilisés ;
- fundamentals_quarterly_dev.parquet : BPA trimestriel avec 4e trimestre et date de publication.
Et reports/lab_2026-11/qc_clean.json pour les chiffres du rapport.
Les dossiers *holdout_* ne sont jamais lus.
Depuis la racine : venv/bin/python -I reports/clean_universe.py
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
from universe_clean import ALIVE_TOLERANCE_SESSIONS, FAILED_BANKS, SHORT_SECURITY_DAYS, add_adjusted_returns, classify_security, exit_returns, find_aliases, flag_suspect_prints, group_aliases, normalize_name, reconstruct_quarterly_eps, split_segments

U = ROOT / "data" / "universe"
SEC = ROOT / "data" / "sec"
OUT = ROOT / "data" / "universe_clean"
OUT.mkdir(exist_ok=True)
COLUMNS = ["symbol", "ts_utc", "open", "high", "low", "close", "volume", "vwap"]
report = {}


def read(folders):
    frames = []
    for folder in folders:
        assert "holdout" not in folder
        for path in sorted(glob.glob(str(U / folder / "*.parquet"))):
            frame = pd.read_parquet(path, columns=COLUMNS)
            if len(frame):
                frames.append(frame.astype({c: "float64" for c in COLUMNS if c not in ("symbol", "ts_utc", "volume")} | {"volume": "int64", "symbol": "string"}))
    return pd.concat(frames, ignore_index=True).drop_duplicates(["symbol", "ts_utc"])


def load_panel():
    adjusted = read(["dev_all", "extra_dev_all", "gap_dev_all", "gap_sec_dev_all"] if (U / "gap_dev_all").exists() else ["dev_all", "extra_dev_all"])
    raw = read(["dev_raw", "extra_dev_raw", "gap_dev_raw", "gap_sec_dev_raw"] if (U / "gap_dev_raw").exists() else ["dev_raw", "extra_dev_raw"])
    for name in ("raw_default", "raw_noasof"):
        path = U / "fix_dev" / f"{name}.parquet"
        if path.exists():
            extra = pd.read_parquet(path, columns=COLUMNS)
            if len(extra):
                extra = extra[~extra.symbol.isin(raw.symbol.unique())].astype({"symbol": "string"})
                raw = pd.concat([raw, extra], ignore_index=True)
    report["rows_adjusted"] = len(adjusted)
    report["symbols_adjusted"] = int(adjusted.symbol.nunique())
    panel = raw.merge(adjusted[["symbol", "ts_utc", "close"]].rename(columns={"close": "adj_close"}), on=["symbol", "ts_utc"], how="outer", indicator=True)
    report["rows_without_raw"] = int((panel._merge == "right_only").sum())
    report["symbols_without_raw"] = sorted(panel.loc[panel._merge == "right_only", "symbol"].unique().tolist())[:30]
    report["rows_without_adjusted"] = int((panel._merge == "left_only").sum())
    panel = panel[panel._merge == "both"].drop(columns="_merge")
    # Ajustement "all" invalide (nul ou négatif) : repli sur le seul ajustement des fractionnements.
    invalid = panel.loc[panel.adj_close <= 0, "symbol"].unique().tolist()
    report["symbols_invalid_adjustment"] = sorted(invalid)
    path = U / "fix_dev" / "split_invalid.parquet"
    if invalid and path.exists():
        split = pd.read_parquet(path, columns=["symbol", "ts_utc", "close"]).rename(columns={"close": "split_close"}).astype({"symbol": "string"})
        panel = panel.merge(split, on=["symbol", "ts_utc"], how="left")
        mask = panel.symbol.isin(invalid)
        panel.loc[mask, "adj_close"] = panel.loc[mask, "split_close"]
        panel = panel.drop(columns="split_close")
    panel["adjustment_fallback"] = panel.symbol.isin(invalid)
    panel = panel[panel.adj_close > 0]
    return panel.sort_values(["symbol", "ts_utc"], ignore_index=True)


panel = load_panel()
report["rows_before"] = len(panel)
report["symbols_before"] = int(panel.symbol.nunique())
report["zero_raw_volume_rows_before"] = int((panel.volume == 0).sum())
print("Panel", len(panel), panel.symbol.nunique(), flush=True)

# 1. Cours fantômes et symboles réutilisés.
clean, cuts = split_segments(panel)
report["rows_ghost_removed"] = len(panel) - len(clean)
report["reused_symbol_cuts"] = len(cuts)
report["zero_raw_volume_rows_kept_thin"] = int((clean.volume == 0).sum())
del panel
clean["security_id"] = clean.symbol.astype(str) + "#" + clean.segment.astype(str)
traded_days = clean[clean.traded].groupby("security_id").size()
clean = clean[clean.security_id.isin(traded_days.index)].reset_index(drop=True)
print("Après fantômes", len(clean), clean.security_id.nunique(), flush=True)

# 2. Doublons de renommage.
pairs = find_aliases(clean)
aliases = group_aliases(pairs, traded_days.to_dict())
report["alias_pairs"] = len(pairs)
report["alias_securities_dropped"] = len(aliases)
print("Doublons", len(aliases), flush=True)
dropped = clean[clean.security_id.isin(aliases.dropped)]
kept_keys = clean[clean.security_id.isin(aliases.kept)][["security_id", "ts_utc"]]
own = dropped.merge(aliases, left_on="security_id", right_on="dropped").merge(kept_keys, left_on=["kept", "ts_utc"], right_on=["security_id", "ts_utc"], how="left", indicator=True, suffixes=("", "_kept"))
report["alias_rows_not_in_kept_security"] = int((own._merge == "left_only").sum())
clean = clean[~clean.security_id.isin(aliases.dropped)].reset_index(drop=True)

# 3. Rendements ajustés et cours aberrants.
clean = add_adjusted_returns(clean)
clean["suspect_print"] = flag_suspect_prints(clean)
actions_all = pd.read_parquet(U / "corporate_actions_dev.parquet")
known_days = {}
for kind_column in ("symbol", "old_symbol", "new_symbol", "acquiree_symbol", "source_symbol"):
    if kind_column in actions_all:
        subset = actions_all[actions_all.kind != "name_changes"] if kind_column in ("old_symbol", "new_symbol") else actions_all
        for symbol, date in zip(subset[kind_column], pd.to_datetime(subset.ex_date.fillna(subset.process_date), errors="coerce")):
            if isinstance(symbol, str) and pd.notna(date):
                known_days.setdefault(symbol, []).append(date.tz_localize("UTC"))
traded_rows = clean[clean.traded]
raw_return = traded_rows.groupby("security_id", sort=False).close.pct_change()
mismatch = traded_rows[(raw_return - traded_rows.ret_adj).abs() > 0.5]
# Un écart entre brut et ajusté doit correspondre à une opération connue, sinon le facteur est douteux.
unexplained = [i for i, symbol, day in zip(mismatch.index, mismatch.symbol, mismatch.ts_utc) if not any(abs((day - known).days) <= 7 for known in known_days.get(symbol, []))]
report["raw_vs_adjusted_mismatches"] = len(mismatch)
report["raw_vs_adjusted_unexplained"] = len(unexplained)
clean.loc[unexplained, "suspect_print"] = True
report["daily_moves_above_100pct_after"] = int((clean.ret_adj.abs() > 1).sum())
report["suspect_prints"] = int(clean.suspect_print.sum())

# 4. Fiche de chaque titre.
last_session = clean.ts_utc.max()
sessions = np.sort(clean.ts_utc.unique())
traded = clean[clean.traded]
securities = traded.groupby("security_id", sort=False).agg(symbol=("symbol", "first"), segment=("segment", "first"), first_trade=("ts_utc", "min"), last_trade=("ts_utc", "max"), traded_days=("ts_utc", "size"), last_raw=("close", "last"), max_raw_year=("close", lambda s: s.tail(252).max()), mean_dollar_volume=("volume", lambda s: 0.0), adjustment_fallback=("adjustment_fallback", "first")).reset_index()
dollars = (traded.close * traded.volume).groupby(traded.security_id).mean()
securities["mean_dollar_volume"] = securities.security_id.map(dollars)
position = np.searchsorted(sessions, securities.last_trade.to_numpy())
securities["alive_at_end"] = (len(sessions) - 1 - position) <= ALIVE_TOLERANCE_SESSIONS
last_segment = securities.groupby("symbol").segment.transform("max") == securities.segment
members = aliases.assign(symbol=aliases.dropped.str.rsplit("#", n=1).str[0]).groupby("kept").symbol.agg(lambda s: sorted(set(s)))
securities["alias_symbols"] = securities.security_id.map(members).apply(lambda v: v if isinstance(v, list) else [])

assets = pd.read_parquet(U / "assets_all.parquet") if (U / "assets_all.parquet").exists() else pd.read_parquet(U / "assets.parquet")
asset_name = assets.set_index("symbol").name.to_dict()
asset_status = assets.set_index("symbol").status.to_dict()
asset_exchange = assets.set_index("symbol").exchange.to_dict()
# Le nom Alpaca est celui du détenteur actuel : valable pour le dernier titre du symbole seulement.
active_elsewhere = securities.symbol.map(asset_status).eq("active") & ~securities.alive_at_end
securities["name_alpaca"] = securities.symbol.map(asset_name).replace("", np.nan)
securities["name_trusted"] = last_segment & ~active_elsewhere & securities.name_alpaca.notna()
report["securities_with_trusted_name"] = int(securities.name_trusted.sum())

# 5. Rattachement à la SEC.
entities = pd.read_parquet(SEC / "dev_entities.parquet")
prefixes = pd.read_parquet(SEC / "dev_doc_prefixes.parquet")
entity = entities.set_index("cik")
first_filing, last_filing = pd.to_datetime(entity.first_filing, errors="coerce"), pd.to_datetime(entity.last_filing, errors="coerce")
prefix_index = {}
instances = pd.read_parquet(SEC / "dev_instances.parquet", columns=["cik", "prefix", "filed"]).dropna(subset=["prefix"])
instance_prefixes = instances.groupby(["cik", "prefix"]).filed.agg(first_filing="min", last_filing="max", filings="size").reset_index()
report["sec_instance_prefixes"] = len(instance_prefixes)
# Un nom de document est moins sûr qu'un fichier XBRL : au moins 3 lettres et 4 dépôts (CA donnait Novo Nordisk).
prefixes = pd.concat([instance_prefixes, prefixes[(prefixes.prefix.str.len() >= 3) & (prefixes.filings >= 4)]], ignore_index=True)
for row in prefixes.itertuples():
    prefix_index.setdefault(row.prefix, []).append((row.cik, pd.Timestamp(row.first_filing), pd.Timestamp(row.last_filing), row.filings))
predecessors = {}
renames = pd.read_parquet(U / "corporate_actions_dev.parquet", columns=["kind", "old_symbol", "new_symbol"])
for old, new in zip(renames.old_symbol, renames.new_symbol):
    if isinstance(old, str) and isinstance(new, str):
        predecessors.setdefault(new, set()).add(old)
ticker_index = {}
for cik, tickers in entity.tickers.dropna().items():
    for ticker in tickers.split(","):
        ticker_index.setdefault(ticker.upper().replace("-", "."), []).append(cik)
name_index = {}
for cik, row in entity[["name", "former"]].iterrows():
    names = [row["name"]] + [f.get("name") for f in json.loads(row["former"] or "[]")]
    for label in names:
        normalized = normalize_name(label)
        if len(normalized) >= 4:
            name_index.setdefault(normalized, set()).add(cik)


def overlaps(cik, begin, end, slack_days=200):
    if cik not in entity.index or pd.isna(first_filing.get(cik)):
        return False
    first_seen, last_seen = first_filing[cik], last_filing[cik]
    return first_seen.tz_localize("UTC") <= end + pd.Timedelta(days=slack_days) and last_seen.tz_localize("UTC") >= begin - pd.Timedelta(days=slack_days)


def symbol_history(row):
    """Le symbole, ses doublons, ses anciens noms et sa version sans suffixe de faillite."""
    seen, stack = set(), [row.symbol] + row.alias_symbols
    while stack:
        symbol = stack.pop()
        if symbol not in seen:
            seen.add(symbol)
            stack.extend(predecessors.get(symbol, ()))
            if len(symbol) == 5 and symbol.endswith("Q"):
                stack.append(symbol[:-1])
    return seen


def link(row):
    begin, end = row.first_trade.tz_localize(None), row.last_trade.tz_localize(None)
    listed = max((end - begin).days, 1)
    found = {}
    best = None
    for symbol in symbol_history(row):
        for cik, first_seen, last_seen, count in prefix_index.get(symbol, []):
            # Les dépôts doivent couvrir au moins la moitié de la cotation, à quatre mois près.
            shared = (min(end, last_seen + pd.Timedelta(days=120)) - max(begin, first_seen - pd.Timedelta(days=120))).days
            if count >= 2 and shared >= 0.5 * listed and (best is None or count > best[1]):
                best = (cik, count, first_seen, last_seen)
        for cik in ticker_index.get(symbol, []):
            if overlaps(cik, row.first_trade, row.last_trade):
                found.setdefault("ticker", cik)
    if best:
        found["filing_prefix"] = best[0]
        # Preuve forte qu'une société cotée occupait le symbole jusqu'à la fin de la cotation.
        span = (min(end, best[3]) - max(begin, best[2])).days
        found["strict_prefix"] = best[1] >= 8 and best[3] + pd.Timedelta(days=200) >= end and span >= 0.8 * listed - 200
    if row.name_trusted:
        for cik in sorted(name_index.get(normalize_name(row.name_alpaca), [])):
            if overlaps(cik, row.first_trade, row.last_trade):
                found.setdefault("name", cik)
                break
    return found


links = securities.apply(link, axis=1)
# Le symbole actuel n'est sûr que pour le dernier titre du symbole : sinon le préfixe d'époque passe avant.
def choose(found, is_last):
    order = ("ticker", "filing_prefix", "name") if is_last else ("filing_prefix", "name", "ticker")
    for method in order:
        if method in found:
            return found[method], method
    return (np.nan, "none")


chosen = [choose(found, is_last) for found, is_last in zip(links, last_segment)]
securities["cik"] = [c[0] for c in chosen]
securities["sec_link"] = [c[1] for c in chosen]
securities["strict_prefix"] = [bool(found.get("strict_prefix")) for found in links]
agree = [(f["ticker"] == f["filing_prefix"]) for f in links if "ticker" in f and "filing_prefix" in f]
report["sec_link_agreement_ticker_vs_prefix"] = {"pairs": len(agree), "same_company": round(float(np.mean(agree)), 4) if agree else None}
agree = [(f["name"] == f["filing_prefix"]) for f in links if "name" in f and "filing_prefix" in f]
report["sec_link_agreement_name_vs_prefix"] = {"pairs": len(agree), "same_company": round(float(np.mean(agree)), 4) if agree else None}
print("Rattachés", securities.cik.notna().sum(), "/", len(securities), flush=True)

manual_path = ROOT / "reports" / "lab_2026-11" / "known_securities.csv"
manual = pd.read_csv(manual_path, comment="#", dtype=str).fillna("")
manual_cik = {r.symbol: int(r.cik) for r in manual.itertuples() if r.cik}
fill_cik = securities.cik.isna() & securities.symbol.isin(manual_cik)
securities.loc[fill_cik, "cik"] = securities.loc[fill_cik, "symbol"].map(manual_cik)
securities.loc[fill_cik, "sec_link"] = "manual"

# 6. Type de titre.
records = entity.to_dict("index")
securities["security_type"] = [classify_security(s, n, t, records.get(c) if pd.notna(c) else None, "filing_prefix" if strict and m == "filing_prefix" else None) for s, n, t, c, m, strict in zip(securities.symbol, securities.name_alpaca, securities.name_trusted, securities.cik, securities.sec_link, securities.strict_prefix)]
# Table écrite à la main pour les titres les plus échangés que rien d'automatique ne qualifie.
report["manual_security_rows"] = len(manual)
manual_type = manual.set_index("symbol").security_type.to_dict()
unresolved = securities.security_type.eq("unknown") & securities.symbol.isin(manual_type)
securities.loc[unresolved, "security_type"] = securities.loc[unresolved, "symbol"].map(manual_type)
securities["type_source"] = np.where(unresolved, "manual", "auto")
# Pas d'option comment="#" ici : les identifiants contiennent ce caractère (LAZR#0).
overrides = pd.read_csv(ROOT / "reports" / "lab_2026-11" / "security_overrides.csv", skiprows=2, dtype=str).fillna("")
for row in overrides.itertuples():
    mask = securities.security_id == row.security_id
    assert mask.sum() == 1, f"Correction sans titre : {row.security_id}"
    securities.loc[mask, "security_type"] = row.security_type
    securities.loc[mask, "type_source"] = "override"
    if row.clear_cik == "yes":
        securities.loc[mask, "cik"] = np.nan
        securities.loc[mask, "sec_link"] = "none"
report["security_overrides"] = len(overrides)
securities["is_spac_name"] = securities.name_alpaca.fillna("").str.contains(r"\bAcquisition\b", case=False) & securities.name_trusted

# 7. Cause de disparition.
actions = pd.read_parquet(U / "corporate_actions_dev.parquet") if (U / "corporate_actions_dev.parquet").exists() else pd.DataFrame(columns=["kind"])
actions["date"] = pd.to_datetime(actions.get("effective_date"), errors="coerce").fillna(pd.to_datetime(actions.get("process_date"), errors="coerce"))
by_symbol = {}
for row in actions[actions.kind.isin(["cash_mergers", "stock_mergers", "stock_and_cash_mergers", "worthless_removals", "redemptions", "name_changes"])].itertuples():
    symbol = row.acquiree_symbol if row.kind.endswith("mergers") else (row.old_symbol if row.kind == "name_changes" else row.symbol)
    if isinstance(symbol, str):
        by_symbol.setdefault(symbol, []).append(row)
filings = pd.read_parquet(SEC / "dev_filings.parquet", columns=["cik", "form", "filing_date", "items"])
filings = filings[filings.form.isin(["8-K", "8-K/A"]) & filings["items"].fillna("").str.contains(r"1\.03|2\.01|5\.01")]
filings["filing_date"] = pd.to_datetime(filings.filing_date, utc=True)
items_by_cik = {cik: group for cik, group in filings.groupby("cik")}
raw_close = clean[clean.traded].set_index(["symbol", "ts_utc"]).close.sort_index()


def price_on_or_before(symbol, date):
    """Dernier cours brut de l'acquéreur à la date de la fusion, pour valoriser l'échange d'actions."""
    if not isinstance(symbol, str) or symbol not in raw_close.index.get_level_values(0):
        return np.nan
    series = raw_close.loc[symbol]
    series = series[series.index <= date.tz_localize("UTC")]
    return series.iloc[-1] if len(series) else np.nan


def explain_exit(row):
    """Cause, valeur de sortie, successeur. Fenêtre courte autour de la dernière séance échangée."""
    end = row.last_trade
    symbols = [row.symbol] + row.alias_symbols
    candidates = []
    for symbol in symbols:
        for action in by_symbol.get(symbol, []):
            if pd.notna(action.date) and -10 <= (action.date.tz_localize("UTC") - end).days <= 45:
                candidates.append(action)
    candidates.sort(key=lambda a: {"worthless_removals": 0, "cash_mergers": 1, "stock_and_cash_mergers": 1, "stock_mergers": 1, "redemptions": 2, "name_changes": 3}[a.kind])
    for action in candidates:
        if action.kind == "worthless_removals":
            return "worthless", None, None
        if action.kind == "cash_mergers" and pd.notna(action.rate):
            value = action.rate / row.last_raw - 1
            return ("cash_merger", value if -0.8 <= value <= 2 else None, None)
        if action.kind == "stock_and_cash_mergers":
            value = ((action.cash_rate or 0) + (action.acquirer_rate or 0) * price_on_or_before(action.acquirer_symbol, action.date)) / row.last_raw - 1
            return ("stock_and_cash_merger", value if -0.8 <= value <= 2 else None, action.acquirer_symbol)
        if action.kind == "stock_mergers":
            value = (action.acquirer_rate or 0) * price_on_or_before(action.acquirer_symbol, action.date) / row.last_raw - 1
            return ("stock_merger", value if -0.8 <= value <= 2 else None, action.acquirer_symbol)
        if action.kind == "redemptions" and pd.notna(action.rate) and action.rate > 0:
            value = action.rate / row.last_raw - 1
            return ("redemption", value if -0.8 <= value <= 2 else None, None)
        if action.kind == "name_changes":
            new = action.new_symbol
            # Le suffixe Q signale une société en faillite passée hors cote (BBBY devient BBBYQ).
            if isinstance(new, str) and len(new) == 5 and new.endswith("Q"):
                return "bankruptcy", None, new
            return "renamed", None, new
    for symbol in symbols:
        if symbol in FAILED_BANKS and abs((pd.Timestamp(FAILED_BANKS[symbol], tz="UTC") - end).days) <= 45:
            return "failed_bank", None, None
    if any(len(s) == 5 and s.endswith("Q") for s in symbols):
        return "bankruptcy", None, None
    if pd.notna(row.cik) and row.cik in items_by_cik:
        group = items_by_cik[row.cik]
        recent = group[(group.filing_date >= end - pd.Timedelta(days=365)) & (group.filing_date <= end + pd.Timedelta(days=180))]
        if recent["items"].str.contains(r"1\.03").any():
            return "bankruptcy", None, None
        close = group[(group.filing_date >= end - pd.Timedelta(days=45)) & (group.filing_date <= end + pd.Timedelta(days=60))]
        if close["items"].str.contains(r"2\.01|5\.01").any():
            return "merger_terms_unknown", None, None
    if row.last_raw < 5 or row.last_raw < 0.3 * row.max_raw_year:
        return "unknown_distress", None, None
    return "unknown", None, None


gone = securities[~securities.alive_at_end]
explained = gone.apply(explain_exit, axis=1, result_type="expand")
explained.columns = ["exit_reason", "exit_value", "successor"]
securities = securities.join(explained)
# Même société avant et après le trou : passage hors cote puis retour (DXLG), pas une disparition.
# Aucun gain n'est crédité : le cours n'est pas observé hors cote et l'écart à la reprise n'est pas fiable.
ordered = securities.sort_values(["symbol", "segment"])
next_cik = ordered.groupby("symbol").cik.shift(-1)
same_company = ordered.index[(ordered.cik == next_cik) & ordered.exit_reason.isin(["unknown", "unknown_distress", "merger_terms_unknown"])]
securities.loc[same_company, "exit_reason"] = "relisted"
report["relisted_same_company"] = len(same_company)
returns = [exit_returns(r, v if pd.notna(v) else None) if isinstance(r, str) else (np.nan,) * 3 for r, v in zip(securities.exit_reason, securities.exit_value)]
securities[["exit_return_base", "exit_return_optimistic", "exit_return_pessimistic"]] = returns
securities["too_short"] = securities.traded_days < SHORT_SECURITY_DAYS
securities["exchange_now"] = securities.symbol.map(asset_exchange)

# 8. BPA trimestriel.
facts = pd.read_parquet(SEC / "dev_facts.parquet")
eps = facts[(facts.concept == "eps_diluted") & facts.unit.str.lower().str.contains("usd") & facts.start.notna()]
basic = facts[(facts.concept == "eps_basic") & facts.unit.str.lower().str.contains("usd") & facts.start.notna()]
# Le BPA de base ne sert que pour les sociétés qui ne publient pas le dilué.
eps = pd.concat([eps, basic[~basic.cik.isin(eps.cik.unique())]], ignore_index=True)
split_rows = actions_all[actions_all.kind.isin(["forward_splits", "reverse_splits", "unit_splits"])].copy()
split_rows["date"] = pd.to_datetime(split_rows.ex_date.fillna(split_rows.process_date), errors="coerce")
split_rows["factor"] = split_rows.old_rate.astype(float) / split_rows.new_rate.astype(float)
linked_symbols = securities.dropna(subset=["cik"]).assign(all_symbols=lambda f: f.apply(lambda r: sorted(symbol_history(r)), axis=1)).explode("all_symbols")[["cik", "all_symbols", "first_trade", "last_trade"]]
splits = split_rows.merge(linked_symbols, left_on="symbol", right_on="all_symbols")
splits = splits[(splits.date.dt.tz_localize("UTC") >= splits.first_trade) & (splits.date.dt.tz_localize("UTC") <= splits.last_trade + pd.Timedelta(days=30))]
splits = splits[(splits.factor > 0) & (splits.factor != 1)].drop_duplicates(["cik", "date"])[["cik", "date", "factor"]].astype({"cik": "int64"})
report["splits_linked_to_companies"] = len(splits)
quarterly = reconstruct_quarterly_eps(eps, splits)
report["eps_suspect_quarters"] = int(quarterly.eps_suspect.sum())
quarterly.to_parquet(OUT / "fundamentals_quarterly_dev.parquet", index=False)
report["eps_quarters"] = len(quarterly)
report["eps_q4_derived"] = int((quarterly.source == "q4_derived").sum())
report["eps_companies"] = int(quarterly.cik.nunique())
with_eps = set(quarterly[~quarterly.eps_suspect].cik)
securities["has_eps"] = securities.cik.isin(with_eps)

# 9. Écriture et chiffres de contrôle.
columns = ["security_id", "symbol", "ts_utc", "open", "high", "low", "close", "volume", "vwap", "adj_close", "ret_adj", "traded", "suspect_print"]
clean[columns].to_parquet(OUT / "prices_dev.parquet", index=False)
securities.to_parquet(OUT / "securities_dev.parquet", index=False)
aliases.to_parquet(OUT / "aliases_dev.parquet", index=False)
pairs.to_parquet(OUT / "alias_pairs_dev.parquet", index=False)
cuts.to_parquet(OUT / "cuts_dev.parquet", index=False)

report["rows_after"] = len(clean)
report["securities_after"] = len(securities)
report["last_date"] = str(clean.ts_utc.max())
report["security_types"] = securities.security_type.value_counts().to_dict()
report["alive_at_end"] = int(securities.alive_at_end.sum())
report["exit_reasons_all"] = securities.exit_reason.value_counts().to_dict()
equity = securities[securities.security_type.isin(["common", "adr", "unknown", "spac"]) & ~securities.too_short]
report["exit_reasons_equities"] = equity.exit_reason.value_counts().to_dict()


def coverage(frame):
    return {"n": len(frame), "linked": round(float(frame.cik.notna().mean()), 4) if len(frame) else None, "with_eps": round(float(frame.has_eps.mean()), 4) if len(frame) else None}


operating = securities[securities.security_type.isin(["common", "adr", "unknown"]) & ~securities.too_short].sort_values("mean_dollar_volume", ascending=False)
report["sec_coverage"] = {"all_operating": coverage(operating), "alive": coverage(operating[operating.alive_at_end]), "disappeared": coverage(operating[~operating.alive_at_end])}
for size in (500, 1000, 3000):
    top = operating.head(size)
    report["sec_coverage"][f"top_{size}"] = coverage(top)
    report["sec_coverage"][f"top_{size}_disappeared"] = coverage(top[~top.alive_at_end])
report["sec_link_methods"] = securities.sec_link.value_counts().to_dict()
fund_like = securities[securities.security_type.isin(["common", "adr"]) & securities.name_trusted & securities.name_alpaca.fillna("").str.contains(r"\bETF\b|\bETN\b|iShares|ProShares|SPDR")]
report["equities_with_fund_name_now"] = sorted(fund_like.symbol.tolist())
watch = {}
for symbol in ("SBNY", "FB", "META", "ANTM", "ELV", "LB", "CA", "MON", "TWTR", "SIVB", "BBBYQ", "FRCB", "TQQQ", "WHLR", "TSLA"):
    for row in securities[(securities.symbol == symbol) | securities.alias_symbols.apply(lambda v: symbol in v)].itertuples():
        watch.setdefault(symbol, []).append({"id": row.security_id, "first": str(row.first_trade)[:10], "last": str(row.last_trade)[:10], "type": row.security_type, "cik": None if pd.isna(row.cik) else int(row.cik), "link": row.sec_link, "exit": row.exit_reason, "exit_base": None if pd.isna(row.exit_return_base) else round(float(row.exit_return_base), 4), "aliases": row.alias_symbols})
report["watch"] = watch
report["alias_contains"] = {"FB-META": any(a.startswith("FB#") and k.startswith("META#") for a, k in zip(aliases.dropped, aliases.kept)), "ANTM-ELV": any(a.startswith("ANTM#") and k.startswith("ELV#") for a, k in zip(aliases.dropped, aliases.kept))}
(ROOT / "reports" / "lab_2026-11" / "qc_clean.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(json.dumps(report, indent=1, ensure_ascii=False, default=str))
