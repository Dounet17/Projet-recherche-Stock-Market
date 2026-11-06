"""Premier modèle adaptatif : classer toutes les actions chaque mois selon leur mois à venir.

Le modèle ne prédit ni un cours ni la direction du marché, mais le rang du rendement d'une action parmi
les autres, sur le mois qui suit. Il n'utilise que les prix et la liquidité. Réentraîné chaque 1er janvier
(« walk-forward »), il n'apprend que sur des mois entièrement terminés avant cette date. Les paramètres
sont fixés d'avance et ne sont pas réglés.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import HistGradientBoostingRegressor

from experiment import month_starts, top_n
from price_lab import rsi

FIRST_TEST_YEAR = 2018
MODEL_PARAMS = {"learning_rate": 0.05, "max_iter": 200, "max_leaf_nodes": 15, "min_samples_leaf": 200, "l2_regularization": 1.0, "random_state": 0, "early_stopping": False}


def features(data):
    """Indicateurs connus à la clôture de chaque jour : uniquement des rapports entre cours, jamais un niveau."""
    close = data.close
    log_returns = np.log(close).diff()

    def rolling(frame, window):
        return frame.rolling(window, min_periods=int(window * 0.8))

    return {
        "return_21": close / close.shift(21) - 1,
        "return_63": close / close.shift(63) - 1,
        "return_126": close / close.shift(126) - 1,
        "return_252": close / close.shift(252) - 1,
        "return_252_skip_21": close.shift(21) / close.shift(252) - 1,
        "volatility_20": rolling(log_returns, 20).std(),
        "volatility_60": rolling(log_returns, 60).std(),
        "distance_average_50": close / rolling(close, 50).mean() - 1,
        "distance_average_200": close / rolling(close, 200).mean() - 1,
        "drawdown_252": close / rolling(close, 252).max() - 1,
        "rsi_14": rsi(close, 14),
        "log_dollar_volume": np.log(data.dollar_volume.where(data.dollar_volume > 0)),
        "liquidity_trend_60": data.dollar_volume / data.dollar_volume.shift(60),
    }


def percentile_ranks(values, mask):
    """Rang de 0 à 1 parmi les titres de `mask` d'une même date ; NaN conservé si l'indicateur manque."""
    result = np.full(values.shape, np.nan)
    known = mask & np.isfinite(values)
    if known.sum() > 1:
        result[known] = (pd.Series(values[known]).rank().to_numpy() - 1) / (known.sum() - 1)
    return result


def forward_multiples(data, exits, last_dates):
    """Rendement de chaque décision mensuelle : de l'ouverture du lendemain à celle qui suit la décision du mois suivant.

    Un titre disparu dans le mois rapporte son dernier cours et sa sortie : le modèle voit donc les faillites.
    `last_dates` et `exits` portent sur tout l'historique, mais ne servent que si la disparition précède la
    fin du mois visé, et seules les décisions dont ce mois est terminé entrent à l'entraînement.
    Renvoie (lignes de décision, date de fin du mois visé, matrice décisions x titres).
    """
    dates = data.dates
    rows = np.flatnonzero(month_starts(dates).to_numpy())
    opens = data.open.to_numpy()
    closes = data.close.to_numpy()
    marks = data.open.ffill().to_numpy()
    columns = data.close.columns
    exit_values = exits.reindex(columns).to_numpy(dtype=float)
    last = last_dates.reindex(columns)
    last_positions = dates.searchsorted(last.to_numpy())
    leaving = np.isfinite(exit_values) & last.notna().to_numpy()
    multiples = np.full((len(rows), opens.shape[1]), np.nan)
    ends = np.full(len(rows), np.datetime64("NaT", "ns"))
    for i, row in enumerate(rows):
        if i + 1 == len(rows) or rows[i + 1] + 1 >= len(dates) or row + 1 >= len(dates):
            continue
        entry, end = row + 1, rows[i + 1] + 1
        ends[i] = dates[end].to_datetime64()
        with np.errstate(divide="ignore", invalid="ignore"):
            held = marks[end] / opens[entry]
            gone = leaving & (last_positions < end) & (last_positions >= entry)
            cols = np.flatnonzero(gone)
            held[cols] = closes[last_positions[cols], cols] / opens[entry, cols] * (1 + exit_values[cols])
            # Disparu avant l'achat : rien à prédire.
            held[leaving & (last_positions < entry)] = np.nan
        multiples[i] = held
    return rows, ends, multiples


def yearly_training_rows(ends, year):
    """Décisions dont le mois visé est entièrement terminé avant le 1er janvier de `year`."""
    return np.flatnonzero(ends < np.datetime64(f"{year}-01-01"))


def make_strategy(exits, last_dates, model_params=None, first_test_year=FIRST_TEST_YEAR, keep=None):
    """Fabrique la stratégie. `keep`, s'il est donné, reçoit le dernier tableau des scores pour le diagnostic."""
    params = {**MODEL_PARAMS, **(model_params or {})}

    def strategy(data, top=50):
        indicators = features(data)
        names = list(indicators)
        rows, ends, multiples = forward_multiples(data, exits, last_dates)
        tradable = data.tradable.to_numpy()
        inputs = np.full((len(rows), tradable.shape[1], len(names)), np.nan, dtype=np.float32)
        targets = np.full(multiples.shape, np.nan, dtype=np.float32)
        for k, name in enumerate(names):
            matrix = indicators[name].to_numpy()
            for i, row in enumerate(rows):
                inputs[i, :, k] = percentile_ranks(matrix[row], tradable[row])
        for i, row in enumerate(rows):
            targets[i] = percentile_ranks(multiples[i], tradable[row])
        scores = pd.DataFrame(np.nan, index=data.dates, columns=data.close.columns)
        values = scores.to_numpy(copy=True)
        years = data.dates[rows].year
        for year in sorted(set(years[years >= first_test_year])):
            train = yearly_training_rows(ends, year)
            test = np.flatnonzero(years == year)
            X = inputs[train].reshape(-1, len(names))
            y = targets[train].reshape(-1)
            sample = np.isfinite(y)
            # Un indicateur sans aucune valeur sur la période d'entraînement ne peut rien apprendre.
            usable = np.isfinite(X[sample]).any(axis=0)
            model = HistGradientBoostingRegressor(**params).fit(X[sample][:, usable], y[sample])
            for i in test:
                eligible = tradable[rows[i]]
                if eligible.any():
                    values[rows[i], eligible] = model.predict(inputs[i][eligible][:, usable])
        scores = pd.DataFrame(values, index=data.dates, columns=data.close.columns)
        if keep is not None:
            keep["scores"] = scores
        return top_n(scores, n=top, tradable=data.tradable)

    return strategy


@dataclass(frozen=True)
class Diagnostics:
    monthly: pd.DataFrame     # corrélation de rang et écarts par mois
    deciles: pd.Series        # rendement mensuel moyen brut par décile de score, 1 = le moins bien classé


def diagnose(scores, data, exits, last_dates):
    """Le classement contient-il de l'information ? Avant frais et sans passer par un portefeuille."""
    rows, _, multiples = forward_multiples(data, exits, last_dates)
    records, buckets = [], []
    for i, row in enumerate(rows):
        predicted = scores.to_numpy()[row]
        known = np.isfinite(predicted) & np.isfinite(multiples[i])
        if known.sum() < 100:
            continue
        p, m = predicted[known], multiples[i][known] - 1
        order = pd.Series(p).rank(method="first").to_numpy()
        decile = np.ceil(order / len(p) * 10).astype(int)
        by_decile = pd.Series(m).groupby(decile).mean()
        # Les 50 premiers sont choisis avant de connaître leur rendement, comme dans le portefeuille :
        # un titre choisi puis sans rendement mesurable est écarté de la moyenne, jamais remplacé.
        scored = np.flatnonzero(np.isfinite(predicted))
        chosen = scored[np.argsort(-predicted[scored], kind="stable")[:50]]
        top50 = multiples[i][chosen]
        top50 = top50[np.isfinite(top50)] - 1
        records.append({"date": data.dates[row], "stocks": int(known.sum()), "rank_correlation": spearmanr(p, m).statistic, "top_minus_bottom": by_decile.loc[10] - by_decile.loc[1], "universe_mean": m.mean(), "top50_mean": top50.mean(), "top50_share_lost": float((top50 < 0).mean())})
        buckets.append(by_decile)
    return Diagnostics(pd.DataFrame(records).set_index("date"), pd.concat(buckets, axis=1).mean(axis=1))
