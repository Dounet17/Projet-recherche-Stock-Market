"""Buy and hold de chaque action, pour chaque date d'achat : la référence à dépasser.

Le buy and hold d'une date d'achat suit les mêmes règles que `lab.backtest` : décision à la clôture
de la veille, achat à l'ouverture, frais selon la liquidité, vente à la dernière ouverture de
l'horizon. Un titre qui disparaît avant rapporte son dernier cours et son rendement de sortie, sans
frais, puis reste en liquidités à 0 %. La moyenne des multiples d'une date d'achat est exactement le
résultat d'un portefeuille à poids égaux jamais rééquilibré.

Les secteurs reprennent les définitions de Fama et French à partir du code d'activité SIC. Ce code
est celui d'aujourd'hui : il décrit le marché, et ne doit jamais servir de signal à une stratégie.
"""

import re

import numpy as np
import pandas as pd

SCENARIOS = ("base", "optimistic", "pessimistic")
HORIZONS = (None, 12, 36, 60)   # en mois ; None : jusqu'à la fin des données
TIERS = {"top500": 500, "top1000": 1000, "top3000": 3000, "all": None}


def month_start_rows(dates):
    """Position du premier jour de bourse de chaque mois, sauf la toute première ligne (pas de veille)."""
    months = dates.to_period("M")
    return np.flatnonzero(np.r_[False, months[1:] != months[:-1]])


def buy_hold_table(market, starts=None, horizons=HORIZONS):
    """Une ligne par titre achetable, date d'achat et horizon. Multiples en net de frais, sauf `gross_base`."""
    data = market.data
    dates = data.dates
    opens, closes = data.open.to_numpy(), data.close.to_numpy()
    marks = data.open.ffill().to_numpy()
    costs = data.cost_bps.to_numpy() / 10_000
    tradable = data.tradable.to_numpy()
    liquidity = data.dollar_volume.where(data.tradable).rank(axis=1, ascending=False, method="first").to_numpy()
    last_row = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
    exits = market.exits.reindex(data.close.columns)
    securities = np.asarray(data.close.columns)
    rows = month_start_rows(dates) if starts is None else starts
    frames = []
    for start in rows:
        entry_ok = tradable[start - 1] & np.isfinite(opens[start])
        if not entry_ok.any():
            continue
        for horizon in horizons:
            if horizon is None:
                end = len(dates) - 1
            else:
                target = month_start_rows(dates)
                later = target[dates.to_period("M")[target] == dates.to_period("M")[start] + horizon]
                if not len(later):
                    continue
                end = later[0]
            leaves = np.isfinite(exits["base"].to_numpy()) & (last_row < end)
            cols = np.flatnonzero(entry_ok)
            entry = opens[start, cols]
            stop = np.where(leaves[cols], last_row[cols], end)
            frame = {"start": dates[start], "horizon": -1 if horizon is None else horizon, "security_id": securities[cols],
                     "liquidity_rank": liquidity[start - 1, cols], "exited": leaves[cols], "years": (dates[stop] - dates[start]).days / 365.25,
                     "nominal_years": (dates[end] - dates[start]).days / 365.25}
            fee_in, fee_out = 1 - costs[start, cols], np.where(leaves[cols], 1.0, 1 - costs[end, cols])
            held = marks[end, cols] / entry
            gone = closes[last_row[cols], cols] / entry
            for scenario in SCENARIOS:
                gross = np.where(leaves[cols], gone * (1 + exits[scenario].to_numpy()[cols]), held)
                frame[scenario] = gross * fee_in * fee_out
                if scenario == "base":
                    frame["gross_base"] = gross
            frames.append(pd.DataFrame(frame))
    return pd.concat(frames, ignore_index=True)


def benchmark_multiple(panel, symbol, cost_bps=5.0, starts=None, horizons=HORIZONS):
    """Multiple net de frais d'une référence achetable, par date d'achat et horizon."""
    dates = panel.dates
    opens = panel.open[symbol].ffill().to_numpy()
    cost = 1 - cost_bps / 10_000
    target = month_start_rows(dates)
    periods = dates.to_period("M")
    rows = []
    for start in target if starts is None else starts:
        for horizon in horizons:
            if horizon is None:
                end = len(dates) - 1
            else:
                later = target[periods[target] == periods[start] + horizon]
                if not len(later):
                    continue
                end = later[0]
            rows.append((dates[start], -1 if horizon is None else horizon, opens[end] / opens[start] * cost ** 2))
    return pd.DataFrame(rows, columns=["start", "horizon", symbol])


def cohort_statistics(table, by=(), scenario="base"):
    """Résumé par date d'achat et horizon : la moyenne, mais aussi ce que vit l'action typique."""
    keys = ["start", "horizon", *by]
    grouped = table.groupby(keys, observed=True)[scenario]
    result = grouped.agg(count="count", mean="mean", median="median", p10=lambda x: x.quantile(0.10), p90=lambda x: x.quantile(0.90), share_loss=lambda x: (x < 1).mean(), share_wiped_90=lambda x: (x < 0.1).mean())
    result["share_exited"] = table.groupby(keys, observed=True).exited.mean()
    result["nominal_years"] = table.groupby(keys, observed=True).nominal_years.first()
    result["mean_annual"] = result["mean"] ** (1 / result.nominal_years) - 1
    result["median_annual"] = result["median"] ** (1 / result.nominal_years) - 1
    return result.reset_index()


def tier_mask(table, tier):
    limit = TIERS[tier]
    return np.ones(len(table), dtype=bool) if limit is None else (table.liquidity_rank <= limit).to_numpy()


def parse_sic_definitions(text):
    """Lit un fichier Siccodes de French : [(nom court, début, fin)] et l'ordre des secteurs."""
    ranges, names, current = [], [], None
    for line in text.splitlines():
        head = re.match(r"^\s*\d+\s+([A-Za-z]+)\s+\S", line)
        span = re.match(r"^\s+(\d{4})-(\d{4})", line)
        if span and current:
            ranges.append((current, int(span.group(1)), int(span.group(2))))
        elif head:
            current = head.group(1)
            names.append(current)
    return ranges, names


def sector_of(sic, ranges, fallback="Other"):
    """Secteur de chaque code SIC. Un code connu hors de toute plage va dans `fallback`, comme chez French."""
    codes = pd.to_numeric(pd.Series(sic), errors="coerce").to_numpy()
    out = np.full(len(codes), fallback, dtype=object)
    out[~np.isfinite(codes)] = "unknown"
    # Certaines plages se recouvrent : la première définie dans le fichier l'emporte.
    done = ~np.isfinite(codes)
    for name, begin, end in ranges:
        hit = ~done & (codes >= begin) & (codes <= end)
        out[hit] = name
        done |= hit
    return out


def parse_french_csv(text, last_date=20241231):
    """Sections d'un fichier de French, en décimal. Rien après `last_date` n'est conservé : c'est le verrou."""
    sections, title, columns, rows, previous = {}, "data", None, [], ""

    def close():
        if columns and rows:
            frame = pd.DataFrame(rows, columns=["date", *columns]).set_index("date")
            frame.index = pd.to_datetime(frame.index.astype(str), format="%Y%m%d")
            sections[title] = frame.where(frame > -99).div(100)

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(","):
            close()
            title = "equal" if "Equal" in previous else ("value" if "Value" in previous else "data")
            columns, rows = [c.strip() for c in stripped.split(",")[1:]], []
        elif re.match(r"^\d{8},", stripped) and columns:
            parts = stripped.split(",")
            if int(parts[0]) <= last_date:
                rows.append([int(parts[0]), *map(float, parts[1:])])
        elif stripped:
            previous = stripped
    close()
    return sections


def annualized(returns):
    """Rendement annuel composé d'une série quotidienne, sur sa durée réelle.

    Compter 252 jours par an serait faux avant 1952 : la bourse ouvrait aussi le samedi.
    """
    clean = returns.dropna()
    if len(clean) < 2:
        return float("nan")
    years = (clean.index[-1] - clean.index[0]).days / 365.25
    return float((1 + clean).prod() ** (1 / years) - 1)


def rolling_annual(returns, years):
    """Rendement annuel sur chaque fenêtre de `years` années civiles entières qui finit à cette date."""
    clean = returns.dropna()
    wealth = np.log1p(clean).cumsum()
    begin = clean.index - pd.DateOffset(years=years)
    positions = clean.index.searchsorted(begin, side="right") - 1
    complete = positions >= 0
    values = np.expm1((wealth.to_numpy()[complete] - wealth.to_numpy()[positions[complete]]) / years)
    return pd.Series(values, index=clean.index[complete])
