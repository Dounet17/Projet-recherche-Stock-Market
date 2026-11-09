"""Panels quotidiens du grand univers nettoyé, sans métadonnées futures de signal.

Les niveaux ajustés proviennent du fichier nettoyé : les filtres de prix et de
liquidité utilisent exclusivement les cours et volumes bruts. Ce module ne lit
que les deux fichiers de développement, même si le verrou est explicitement levé.
"""

from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import pandas as pd

from lab import DEV_END, Panel


COST_BUCKETS = ((100_000_000.0, 5), (10_000_000.0, 15), (1_000_000.0, 40))
DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "universe_clean"
PRICE_FIELDS = ("open", "high", "low", "close", "volume")
TTM_GAP_DAYS = (70, 110)      # écart entre deux fins de trimestre consécutives
TTM_MAX_AGE_DAYS = 200        # au-delà, le dernier BPA connu est trop ancien


@dataclass(frozen=True)
class Universe(Panel):
    """Matrices accessibles à une stratégie, indexées par date et security_id."""

    raw_close: pd.DataFrame
    dollar_volume: pd.DataFrame
    traded: pd.DataFrame
    tradable: pd.DataFrame
    cost_bps: pd.DataFrame
    eps_ttm: pd.DataFrame = None    # seulement avec load_universe(fundamentals=True)

    def truncate(self, last_date):
        """Coupe chaque matrice en conservant même les titres encore sans cours."""
        last_date = pd.Timestamp(last_date)
        cut = {field.name: getattr(self, field.name) for field in fields(self)}
        return Universe(**{name: None if values is None else values.loc[:last_date]
                           for name, values in cut.items()})


@dataclass(frozen=True)
class Market:
    """Données de signal, sorties et métadonnées restent dans des objets séparés."""

    data: Universe
    exits: pd.DataFrame
    benchmarks: Panel
    securities: pd.DataFrame


def _neutralize(prices, suspect):
    """Annule cumulativement les gains franchissant au moins un cours suspect."""
    close = prices["close"]
    for column in np.flatnonzero(suspect.any(axis=0)):
        valid = np.flatnonzero(np.isfinite(close[:, column]))
        after = np.searchsorted(valid, np.flatnonzero(suspect[:, column]), side="right")
        after = np.unique(after[(after > 0) & (after < len(valid))])
        if not len(after):
            continue
        previous, resumed = valid[after - 1], valid[after]
        ratios = np.minimum(1.0, close[previous, column] / close[resumed, column])
        scale = np.ones(close.shape[0])
        scale[resumed] = ratios
        np.cumprod(scale, out=scale)
        for name in ("open", "high", "low", "close"):
            prices[name][:, column] *= scale


def ttm_eps_column(quarters, dates, factor):
    """BPA sur 12 mois d'un titre, par séance, dans l'échelle d'actions de cette séance.

    `quarters` : period_end, filed et eps triés par period_end. `factor` : cours ajusté / cours brut
    par séance, recopié sur les trous. Un BPA est exprimé dans l'échelle de sa publication : le
    multiplier par le facteur de ce jour, puis diviser par celui de la séance, suit les fractionnements.
    Les dividendes font bouger ce facteur d'environ 2 % par an : erreur faible, jamais une fuite, car
    seul le rapport entre deux dates passées est utilisé.

    Il faut quatre trimestres consécutifs. Le chiffre n'est utilisable qu'après la date `filed` du
    plus récent : un dépôt peut arriver après la clôture. Il expire TTM_MAX_AGE_DAYS après la fin de période.
    """
    out = np.full(len(dates), np.nan)
    ends, filed = quarters.period_end.to_numpy(), quarters.filed.to_numpy()
    if len(ends) < 4:
        return out
    scaled = quarters.eps.to_numpy() * factor[np.minimum(np.searchsorted(dates, filed), len(dates) - 1)]
    gaps = (ends[1:] - ends[:-1]) / np.timedelta64(1, "D")
    for k in range(3, len(ends)):
        if not ((gaps[k - 3:k] >= TTM_GAP_DAYS[0]) & (gaps[k - 3:k] <= TTM_GAP_DAYS[1])).all():
            continue
        begin = np.searchsorted(dates, filed[k - 3:k + 1].max(), side="right")
        stop = np.searchsorted(dates, ends[k] + np.timedelta64(TTM_MAX_AGE_DAYS, "D"), side="right")
        out[begin:stop] = scaled[k - 3:k + 1].sum() / factor[begin:stop]
    return out


def _ttm_eps(path, columns, ciks, dates, factor):
    """Matrice du BPA sur 12 mois, à partir du fichier trimestriel."""
    quarters = pd.read_parquet(path / "fundamentals_quarterly_dev.parquet", columns=["cik", "period_end", "filed", "eps", "eps_suspect"])
    quarters = quarters[~quarters.eps_suspect].sort_values(["cik", "period_end"])
    by_cik = dict(tuple(quarters.groupby("cik", sort=False)))
    filled = pd.DataFrame(factor).ffill().to_numpy()
    out = np.full(factor.shape, np.nan)
    day_values = dates.to_numpy()
    for j, column in enumerate(columns):
        cik = ciks.get(column)
        if pd.notna(cik) and int(cik) in by_cik:
            out[:, j] = ttm_eps_column(by_cik[int(cik)], day_values, filled[:, j])
    return out


def load_universe(end=DEV_END, allow_holdout=False, types=("common", "adr"),
                  symbols=None, min_price=5.0, min_dollar_volume=1_000_000.0,
                  benchmarks=("SPY", "QQQ", "BIL"), path=DATA_PATH, fundamentals=False):
    """Charge les prix jusqu'à `end`, sans pivot et sans ouvrir la validation.

    `dollar_volume` est connu à la clôture ; `cost_bps` est décalé d'une séance
    et correspond à l'ouverture. Les lignes non échangées restent présentes dans
    la médiane de liquidité avec un montant nul. La normalisation déjà appliquée
    à `adj_close` ne garantit pas des niveaux ajustés historiquement disponibles.
    """
    end = pd.Timestamp(end)
    if end.tzinfo is not None:
        end = end.tz_convert("America/New_York").tz_localize(None)
    if end > pd.Timestamp(DEV_END) and not allow_holdout:
        raise PermissionError("Période de validation 2025-2026 verrouillée : voir le protocole")
    path = Path(path)
    securities = pd.read_parquet(path / "securities_dev.parquet")
    selected = securities.security_type.isin(types) & ~securities.too_short
    if symbols is not None:
        selected &= securities.symbol.isin(symbols)
    retained = securities.loc[selected].copy().set_index("security_id", drop=False)

    benchmark_ids = []
    for symbol in benchmarks:
        candidates = securities.loc[(securities.symbol == symbol)
                                    & (securities.security_type == "fund")
                                    & securities.alive_at_end, "security_id"]
        if len(candidates) != 1:
            raise ValueError(f"Référence {symbol!r} : attendu un fonds vivant fin 2024, trouvé {len(candidates)}")
        benchmark_ids.append(candidates.iloc[0])
    columns = pd.Index(list(dict.fromkeys([*retained.index, *benchmark_ids])), name="security_id")
    source = pd.read_parquet(
        path / "prices_dev.parquet",
        columns=["security_id", "ts_utc", "open", "high", "low", "close",
                 "volume", "adj_close", "traded", "suspect_print"],
        filters=[("ts_utc", "<=", end.normalize().tz_localize("America/New_York").tz_convert("UTC"))],
    )
    # Factoriser le calendrier complet avant le filtre conserve aussi les séances
    # où aucun des titres demandés ne possède de ligne.
    date_codes, timestamps = pd.factorize(source.ts_utc, sort=True)
    dates = pd.DatetimeIndex(timestamps).tz_convert("America/New_York").tz_localize(None).normalize()
    dates.name = "date"
    column_codes = columns.get_indexer(source.security_id)
    keep = column_codes >= 0
    rows, cols = date_codes[keep], column_codes[keep]
    source = source.loc[keep]
    shape = (len(dates), len(columns))
    traded = np.zeros(shape, dtype=bool)
    suspect = np.zeros(shape, dtype=bool)
    traded[rows, cols] = source.traded.to_numpy(dtype=bool)
    suspect[rows, cols] = source.suspect_print.to_numpy(dtype=bool)
    raw_close = np.full(shape, np.nan)
    raw_close[rows, cols] = source.close.to_numpy()
    raw_volume = np.full(shape, np.nan)
    raw_volume[rows, cols] = source.volume.to_numpy(dtype=float, na_value=np.nan)
    prices = {}
    factor = source.adj_close.to_numpy() / source.close.to_numpy()
    share_factor = np.full(shape, np.nan)
    share_factor[rows, cols] = factor
    share_factor[suspect] = np.nan
    for name in ("open", "high", "low"):
        values = np.full(shape, np.nan)
        values[rows, cols] = source[name].to_numpy() * factor
        prices[name] = values
    closing = np.full(shape, np.nan)
    closing[rows, cols] = source.adj_close.to_numpy()
    prices["close"] = closing
    valid = traded & ~suspect
    for values in prices.values():
        values[~valid] = np.nan
    # Un cours d'ouverture aberrant ne doit pas devenir un prix d'exécution.
    ratio = source.open.to_numpy() / source.close.to_numpy()
    bad_open = (ratio < 1 / 3) | (ratio > 3)
    prices["open"][rows[bad_open], cols[bad_open]] = np.nan
    del source, date_codes, column_codes, keep, factor, ratio, bad_open, rows, cols
    _neutralize(prices, suspect)

    dollar_volume = raw_close * raw_volume
    dollar_volume[~traded & np.isfinite(raw_close)] = 0.0
    dollar_volume[suspect] = np.nan
    raw_close[suspect] = np.nan
    prices["volume"] = raw_volume
    raw_volume[~valid] = np.nan

    def frame(values):
        return pd.DataFrame(values, index=dates, columns=columns, copy=False)

    liquidity = frame(dollar_volume).rolling(20, min_periods=10).median()
    tradable = valid & (raw_close >= min_price) & (liquidity.to_numpy() >= min_dollar_volume)
    costs = np.full(shape, 100, dtype=np.int16)
    yesterday = liquidity.to_numpy()[:-1]
    for threshold, cost in reversed(COST_BUCKETS):
        costs[1:][yesterday >= threshold] = cost
    matrices = {name: frame(values) for name, values in prices.items()}
    stock_columns = retained.index
    data = Universe(**{name: values.reindex(columns=stock_columns)
                       for name, values in matrices.items()},
                    raw_close=frame(raw_close).reindex(columns=stock_columns),
                    dollar_volume=liquidity.reindex(columns=stock_columns),
                    traded=frame(traded).reindex(columns=stock_columns),
                    tradable=frame(tradable).reindex(columns=stock_columns),
                    cost_bps=frame(costs).reindex(columns=stock_columns),
                    eps_ttm=frame(_ttm_eps(path, columns, retained.cik, dates, share_factor)).reindex(columns=stock_columns) if fundamentals else None)
    benchmark_panel = Panel(**{name: values.reindex(columns=benchmark_ids)
                              .set_axis(pd.Index(benchmarks, name="symbol"), axis=1)
                              for name, values in matrices.items()})
    exits = retained[["exit_return_base", "exit_return_optimistic", "exit_return_pessimistic"]].copy()
    exits.columns = ["base", "optimistic", "pessimistic"]
    exits.loc[retained.alive_at_end] = np.nan
    return Market(data=data, exits=exits, benchmarks=benchmark_panel, securities=retained)
