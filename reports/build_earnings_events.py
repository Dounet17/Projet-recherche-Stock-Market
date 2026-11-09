"""Table des publications de résultats et étude de la réaction des cours, 2018-2024.

Aucune stratégie n'est testée et le journal n'est pas touché. Conception révisée après l'audit
(`reports/lab_2026-11/events/AUDIT_ETUDE_RESULTATS.md`), donc après avoir vu une première version des résultats.

- Dates : `filing_date` et entrée à l'ouverture de la séance suivante, sauf pour les deux cas `after_8k_time_*`.
- Deux cas ajoutés le 07/11/2026, règle figée avant tout calcul mais après avoir vu les autres cas : heure lue dans
  l'en-tête SEC, entrée à l'ouverture du jour si le dépôt est accepté au plus tard à 9 h 25, sinon à la suivante.
- Trois cas : `after_8k_retrospective`, après le 8-K avec le BPA issu d'un dépôt ultérieur, qui décrit le marché
  mais ne se négocie pas ; `after_8k_available`, le même, si le BPA est déjà dans nos données ; `after_filing`, après
  le dépôt des comptes. Dans les deux derniers, tous les termes de la SUE sont publiés avant la décision.
- Trimestres déposés plus de 150 jours après leur fin : écartés (ce sont surtout d'anciennes périodes reprises).
- Rendement anormal contre SPY. Écart groupe 5 moins groupe 1 par trimestre, Holm sur tous les tests.

Depuis la racine : venv/bin/python reports/build_earnings_events.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import lab
from events import RECENT_MAX_DAYS, block_bootstrap_p, day_positions, forward_multiple, holm, match_announcements, newey_west_t, positions_after_time, prior_quarter_groups, quarterly_spread, standardized_surprise, two_sided_p
from universe_data import load_universe

DATA = ROOT / "data" / "events"
OUT = lab.LAB_DIR / "events"
HORIZONS = (1, 5, 20, 60)
TIERS = {"top1000": 1000, "all": None}
CASES = {"after_8k_retrospective": ("announcement", "sue_retrospective"), "after_8k_available": ("announcement", "sue_available"), "after_filing": ("filing", "sue_filing"), "after_8k_time_retrospective": ("timed", "sue_time_retrospective"), "after_8k_time_available": ("timed", "sue_time_available")}
START, END = pd.Timestamp("2018-01-01"), pd.Timestamp("2024-12-31")
PLACEBO_SHIFTS = (41, 63, 83)

for folder in (DATA, OUT):
    folder.mkdir(parents=True, exist_ok=True)
pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 200)

market = load_universe(types=("common",))
data = market.data
dates, columns = data.dates, data.close.columns
position = {c: j for j, c in enumerate(columns)}
opens, closes = data.open.to_numpy(), data.close.to_numpy()
marks = data.open.ffill().to_numpy()
tradable = data.tradable.to_numpy()
liquidity = data.dollar_volume.to_numpy()
ranks = data.dollar_volume.where(data.tradable).rank(axis=1, ascending=False).to_numpy()
costs = data.cost_bps.to_numpy() / 10_000
last_rows = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
exit_values = {s: market.exits[s].reindex(columns).to_numpy() for s in ("base", "optimistic", "pessimistic")}
spy_open = market.benchmarks.open["SPY"].ffill().to_numpy()

# Facteur d'échelle des actions, avant neutralisation : cours ajusté / cours brut.
raw = pd.read_parquet(ROOT / "data" / "universe_clean" / "prices_dev.parquet", columns=["security_id", "ts_utc", "close", "adj_close", "suspect_print"])
raw = raw[raw.security_id.isin(columns) & ~raw.suspect_print]
raw["date"] = raw.ts_utc.dt.tz_convert("America/New_York").dt.tz_localize(None).dt.normalize()
factor_values = np.full((len(dates), len(columns)), np.nan)
factor_values[dates.get_indexer(raw.date), columns.get_indexer(raw.security_id)] = (raw.adj_close / raw.close).to_numpy()
factor = pd.DataFrame(factor_values).ffill().bfill().to_numpy()
del raw

filings = pd.read_parquet(ROOT / "data" / "sec" / "dev_filings.parquet", columns=["cik", "form", "filing_date", "items", "accession"])
eight_k = filings[(filings.form == "8-K") & filings["items"].fillna("").str.contains(r"\b2\.02\b")].copy()
eight_k["date"] = pd.to_datetime(eight_k.filing_date)
del filings
# Heure réelle du 8-K, lue dans l'en-tête SEC. Plusieurs 8-K le même jour : le dernier, ce qui ne peut que retarder l'entrée.
times = pd.concat([pd.read_parquet(path) for path in sorted((DATA / "eight_k_times").glob("batch_*.parquet"))])
times = times[times.status == "ok"].merge(eight_k[["accession", "cik", "date"]], on="accession")
times["accepted_time"] = pd.to_datetime(times.accepted_new_york, format="%Y%m%d%H%M%S").astype("datetime64[ns]")
times = times.groupby(["cik", "date"], as_index=False).accepted_time.max().rename(columns={"date": "announced"})
quarters = pd.read_parquet(ROOT / "data" / "universe_clean" / "fundamentals_quarterly_dev.parquet")
quarters = quarters[~quarters.eps_suspect].sort_values(["cik", "period_end"]).reset_index(drop=True)
quarters = match_announcements(quarters, eight_k)
quarters = quarters.merge(times, on=["cik", "announced"], how="left")
by_cik = dict(tuple(quarters.groupby("cik", sort=False)))

rows = []
for security, cik in market.securities.cik.items():
    if pd.isna(cik) or int(cik) not in by_cik:
        continue
    group = by_cik[int(cik)].sort_values("period_end")
    j = position[security]
    ends = group.period_end.to_numpy().astype("datetime64[ns]")
    filed = group.filed.to_numpy().astype("datetime64[ns]")
    announced = group.announced.to_numpy().astype("datetime64[ns]")
    base = group.eps.to_numpy() * factor[np.minimum(dates.searchsorted(filed), len(dates) - 1), j]
    pre_filing, entry_filing = day_positions(filed, dates)
    pre_8k, entry_8k = day_positions(pd.DatetimeIndex(announced).fillna(pd.Timestamp("1900-01-01")), dates)
    accepted_time = group.accepted_time.to_numpy().astype("datetime64[ns]")
    pre_timed, entry_timed = positions_after_time(pd.DatetimeIndex(accepted_time).fillna(pd.Timestamp("1900-01-01")), dates)
    calendar = np.r_[dates.to_numpy().astype("datetime64[ns]"), np.datetime64("2099-01-01", "ns")]
    decision_8k = calendar[np.minimum(entry_8k, len(dates))]
    decision_filing = calendar[np.minimum(entry_filing, len(dates))]
    decision_timed = calendar[np.minimum(entry_timed, len(dates))]
    rows.append(pd.DataFrame({
        "security_id": security, "cik": int(cik), "period_end": ends, "filed": filed, "announced": announced, "accepted_time": accepted_time, "eps": group.eps.to_numpy(), "source": group.source.to_numpy(), "column": j,
        "pre_announcement": pre_8k, "entry_announcement": entry_8k, "pre_filing": pre_filing, "entry_filing": entry_filing, "pre_timed": pre_timed, "entry_timed": entry_timed,
        "sue_retrospective": standardized_surprise(ends, base, filed, decision_8k, current_known=True),
        "sue_available": standardized_surprise(ends, base, filed, decision_8k),
        "sue_filing": standardized_surprise(ends, base, filed, decision_filing),
        "sue_time_retrospective": standardized_surprise(ends, base, filed, decision_timed, current_known=True),
        "sue_time_available": standardized_surprise(ends, base, filed, decision_timed),
    }))
events = pd.concat(rows, ignore_index=True)
events["has_8k"] = events.announced.notna()
events["days_to_filing"] = (events.filed - events.period_end).dt.days
events.to_parquet(DATA / "earnings_events.parquet", index=False)
print(f"{len(events):,} publications, {events.cik.nunique():,} sociétés, avec 8-K : {events.has_8k.mean():.1%}, déposées à plus de {RECENT_MAX_DAYS} jours : {(events.days_to_filing > RECENT_MAX_DAYS).mean():.1%}", flush=True)


def anomalies(frame, entry, shift=0, horizons=HORIZONS, scenario="base"):
    """Rendement anormal contre SPY, pour chaque horizon."""
    start = entry + shift
    cols = frame["column"].to_numpy()
    usable = (start >= 0) & (start < len(dates))
    result = {}
    tradable_open = np.zeros(len(start), dtype=bool)
    tradable_open[usable] = np.isfinite(opens[start[usable], cols[usable]])
    for horizon in horizons:
        out = np.full(len(start), np.nan)
        keep = tradable_open & (start + horizon < len(dates))
        multiple = forward_multiple(marks, opens, closes, start[keep], cols[keep], horizon, exit_values[scenario], last_rows)
        out[keep] = multiple - spy_open[start[keep] + horizon] / spy_open[start[keep]]
        result[horizon] = out
    return result


def build_case(events, kind, score):
    mask = (events.days_to_filing <= RECENT_MAX_DAYS)
    if kind == "announcement":
        mask &= events.has_8k
    elif kind == "timed":
        mask &= events.accepted_time.notna()
    frame = events[mask].copy()
    entry = frame[f"entry_{kind}"].to_numpy()
    pre = frame[f"pre_{kind}"].to_numpy()
    valid = (pre >= 0) & (entry < len(dates))
    frame, entry, pre = frame[valid].copy(), entry[valid], pre[valid]
    cols = frame["column"].to_numpy()
    frame["entry_row"], frame["pre_row"] = entry, pre
    frame["entry_date"] = dates[entry]
    if kind == "timed":
        # Contrôle anti-fuite : l'achat suit l'acceptation d'au moins 5 minutes, et la clôture de départ la précède.
        assert (frame.entry_date + pd.Timedelta(hours=9, minutes=30) >= frame.accepted_time + pd.Timedelta(minutes=5)).all()
        assert (pd.DatetimeIndex(dates[pre]) + pd.Timedelta(hours=16) <= frame.accepted_time).all()
    keep = tradable[pre, cols] & np.isfinite(opens[entry, cols]) & (frame.entry_date >= START).to_numpy() & (frame.entry_date <= END).to_numpy()
    frame = frame[keep].copy()
    cols = frame["column"].to_numpy()
    frame["liquidity"] = liquidity[frame.pre_row.to_numpy(), cols]
    frame["liquidity_rank"] = ranks[frame.pre_row.to_numpy(), cols]
    # Une ligne par société et par publication : le titre le plus liquide ; un dépôt qui reprend plusieurs périodes n'en compte qu'une, la plus récente.
    frame = frame.sort_values("liquidity", ascending=False).drop_duplicates(["cik", "period_end"])
    frame = frame.sort_values("period_end", ascending=False).drop_duplicates(["cik", "entry_date"]).sort_values(["entry_date", "security_id"]).reset_index(drop=True)
    frame["sue"] = frame[score]
    frame["group"] = prior_quarter_groups(frame)
    frame["gap"] = opens[frame.entry_row.to_numpy(), frame["column"].to_numpy()] / closes[frame.pre_row.to_numpy(), frame["column"].to_numpy()] - 1
    for horizon, values in anomalies(frame, frame.entry_row.to_numpy()).items():
        frame[f"abnormal_{horizon}"] = values
    return frame


def net_of_costs(frame, horizon):
    """Achat du groupe 5 seul : rendement net de frais, et écart à SPY sur les mêmes fenêtres. Moyenne par événement."""
    chosen = frame[frame.group == 5]
    entry, cols = chosen.entry_row.to_numpy(), chosen["column"].to_numpy()
    keep = entry + horizon < len(dates)
    entry, cols = entry[keep], cols[keep]
    multiple = forward_multiple(marks, opens, closes, entry, cols, horizon, exit_values["base"], last_rows)
    end = entry + horizon
    left = np.isfinite(exit_values["base"][cols]) & (last_rows[cols] < end)
    net = multiple * (1 - costs[entry, cols]) * np.where(left, 1.0, 1 - costs[end, cols])
    spy = spy_open[end] / spy_open[entry] * (1 - 5e-4) ** 2
    return {"events": len(net), "gross": float(np.nanmean(multiple - 1)), "cost_round_trip": float(np.nanmean(costs[entry, cols] + costs[end, cols])), "net": float(np.nanmean(net - 1)), "net_minus_spy": float(np.nanmean(net - spy))}


results, nets, placebos, reactions = [], [], [], {}
details = {}
for name, (kind, score) in CASES.items():
    frame = build_case(events, kind, score)
    details[name] = frame
    frame.to_parquet(DATA / f"earnings_study_{name}.parquet", index=False)
    print(f"\n{name} : {len(frame):,} publications, score connu {frame.sue.notna().mean():.1%}, groupe connu {frame.group.notna().mean():.1%}, trimestres {frame.entry_date.dt.to_period('Q').nunique()}", flush=True)
    reactions[name] = frame.groupby("group").gap.agg(["mean", "median", "count"])
    for tier, limit in TIERS.items():
        subset = frame if limit is None else frame[frame.liquidity_rank <= limit]
        for horizon in HORIZONS:
            column = f"abnormal_{horizon}"
            spread = quarterly_spread(subset, column)
            t_value = newey_west_t(spread)
            means = subset.groupby("group")[column].mean()
            results.append({"case": name, "tier": tier, "horizon": horizon, "events": int(subset[[column, "group"]].dropna().shape[0]), "quarters": len(spread), "spread": spread.mean(), "t_newey_west": t_value, "p_newey_west": two_sided_p(t_value, len(spread)), "p_block_bootstrap": block_bootstrap_p(spread), "share_quarters_positive": (spread > 0).mean(), **{f"group_{g}": means.get(g, np.nan) for g in range(1, 6)}})
            nets.append({"case": name, "tier": tier, "horizon": horizon, **net_of_costs(subset, horizon)})
    for shift in PLACEBO_SHIFTS:
        shifted = frame.assign(**{f"abnormal_{h}": v for h, v in anomalies(frame, frame.entry_row.to_numpy(), shift=shift).items()})
        placebos.append({"case": name, "shift": shift, **{f"spread_{h}": quarterly_spread(shifted, f"abnormal_{h}").mean() for h in HORIZONS}})

table = pd.DataFrame(results)
table["holm_newey_west"] = holm(table.p_newey_west).to_numpy()
table["holm_block_bootstrap"] = holm(table.p_block_bootstrap).to_numpy()
table.to_csv(OUT / "earnings_study_results.csv", index=False)
net_table = pd.DataFrame(nets)
net_table.to_csv(OUT / "earnings_study_net_of_costs.csv", index=False)
placebo_table = pd.DataFrame(placebos)
placebo_table.to_csv(OUT / "earnings_study_date_placebo.csv", index=False)
pd.concat([reaction.assign(case=name).reset_index() for name, reaction in reactions.items()]).to_csv(OUT / "earnings_study_reaction.csv", index=False)

# Descriptif, hors correction : selon l'heure du dépôt, sur les cas à heure réelle.
slots = []
for name in ("after_8k_time_retrospective", "after_8k_time_available"):
    frame = details[name]
    seconds = frame.accepted_time.dt.hour * 3600 + frame.accepted_time.dt.minute * 60 + frame.accepted_time.dt.second
    labels = np.select([seconds <= (9 * 60 + 25) * 60, seconds < 16 * 3600], ["jusqu'à 9 h 25", "9 h 25 à 16 h"], "après 16 h")
    for label in ("jusqu'à 9 h 25", "9 h 25 à 16 h", "après 16 h"):
        part = frame[labels == label]
        # Une tranche peut manquer d'un groupe extrême : pas d'écart à calculer dans ce cas.
        one = quarterly_spread(part, "abnormal_1") if {1, 5} <= set(part.group.dropna()) else pd.Series(dtype=float)
        means = part.groupby("group").gap.mean()
        slots.append({"case": name, "slot": label, "events": int(part.group.notna().sum()), "reaction_spread": means.get(5, np.nan) - means.get(1, np.nan), "quarters": len(one), "spread_1": one.mean(), "t_1": newey_west_t(one)})
pd.DataFrame(slots).to_csv(OUT / "earnings_study_by_time_slot.csv", index=False)
old, new = details["after_8k_retrospective"], details["after_8k_time_retrospective"]
same = old.merge(new, on=["cik", "period_end"], suffixes=("_old", "_new"))
moved = {"events_compared": len(same), "same_entry": float((same.entry_row_old == same.entry_row_new).mean()), "one_session_earlier": float((same.entry_row_new == same.entry_row_old - 1).mean()), "other": float(((same.entry_row_new != same.entry_row_old) & (same.entry_row_new != same.entry_row_old - 1)).mean())}
(OUT / "earnings_study_entry_changes.json").write_text(json.dumps(moved, indent=1))
print("\nEntrées changées :", moved, flush=True)
print(pd.DataFrame(slots).round(4).to_string(), flush=True)

sensitivity = []
for name in CASES:
    for scenario in ("base", "optimistic", "pessimistic"):
        frame = details[name]
        values = anomalies(frame, frame.entry_row.to_numpy(), horizons=(60,), scenario=scenario)[60]
        sensitivity.append({"case": name, "scenario": scenario, "spread_60": quarterly_spread(frame.assign(x=values), "x").mean()})
pd.DataFrame(sensitivity).to_csv(OUT / "earnings_study_exit_sensitivity.csv", index=False)

securities = market.securities
alive = securities.alive_at_end
coverage = []
for name, frame in details.items():
    grouped = frame[frame.group.notna()]
    held = set(grouped.security_id)
    coverage.append({"case": name, "share_alive_covered": float(securities.index[alive].isin(held).mean()), "share_gone_covered": float(securities.index[~alive].isin(held).mean()), "share_of_events_from_gone": float(grouped.security_id.isin(securities.index[~alive]).mean())})
pd.DataFrame(coverage).to_csv(OUT / "earnings_study_coverage.csv", index=False)

print("\n", table.drop(columns=["share_quarters_positive"]).round(4).to_string())
print("\nFrais, achat du groupe 5 :\n", net_table.round(5).to_string())
print("\nPlacebo en date (mêmes groupes, dates décalées vers l'avant) :\n", placebo_table.round(4).to_string())
print("\nRéaction brute, de la dernière clôture avant le jour J à l'ouverture d'entrée :")
for name, reaction in reactions.items():
    print(name, "\n", reaction.round(4).to_string())
print(pd.DataFrame(sensitivity).round(4).to_string())
print(pd.DataFrame(coverage).round(3).to_string())
spread = quarterly_spread(details["after_filing"], "abnormal_20")
print("écart 20 séances après dépôt, par année", spread.groupby(spread.index.year).mean().round(4).to_dict())
spread = quarterly_spread(details["after_8k_retrospective"], "abnormal_1")
print("écart 1 séance après 8-K, par année", spread.groupby(spread.index.year).mean().round(4).to_dict())
