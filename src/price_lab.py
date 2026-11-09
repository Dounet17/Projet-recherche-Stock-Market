"""Stratégies fondées uniquement sur les prix, à décision quotidienne ou mensuelle.

Paramètres standards de la littérature, fixés avant les essais. Chaque fonction renvoie
des poids décidés à la clôture : le moteur `lab.backtest` les applique le lendemain.

Vocabulaire :
- moyenne mobile (SMA) : moyenne des n derniers cours, elle indique la tendance ;
- momentum : un actif qui a monté récemment tend à continuer à monter ;
- retour à la moyenne : après une forte baisse, le cours tend à rebondir ;
- volatilité : ampleur des variations quotidiennes, une mesure du risque ;
- ciblage de volatilité : investir moins quand l'actif devient agité ;
- rotation : passer chaque mois sur les actifs les plus forts.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from lab import TRADING_DAYS

SECTORS = ("XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB")
MEGACAPS = ("TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META")


def first_trading_day_of_month(index):
    """Vrai au premier jour de bourse de chaque mois : ne dépend d'aucune date future."""
    months = index.to_period("M")
    flags = np.r_[True, months[1:] != months[:-1]]
    return pd.Series(flags, index=index)


def monthly_hold(frame):
    """Ne garde la décision qu'une fois par mois, puis la conserve jusqu'au mois suivant."""
    flags = first_trading_day_of_month(frame.index)
    return frame.where(flags).ffill()


def single_asset(panel, symbol, signal):
    """Poids sur un seul actif. Un signal NaN signifie « aucun ordre » ce jour-là."""
    target = signal.reindex(panel.dates).astype(float).clip(0, 1)
    weights = pd.DataFrame(0.0, index=panel.dates, columns=panel.close.columns)
    weights[symbol] = target
    weights[target.isna()] = np.nan
    return weights


def realized_vol(close, window=20):
    return np.log(close).diff().rolling(window, min_periods=window).std() * np.sqrt(TRADING_DAYS)


def rsi(close, window):
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    value = 100 - 100 / (1 + gain / loss.where(loss > 0))
    # Sans aucune perte : 100 si le cours monte, 50 par convention s'il reste plat.
    return value.mask((loss == 0) & (gain > 0), 100.0).mask((loss == 0) & (gain == 0), 50.0)


def _state_machine(enter, leave):
    """Position 1 après un signal d'entrée, jusqu'au signal de sortie."""
    state = pd.Series(np.nan, index=enter.index, dtype=float)
    state[leave.fillna(False)] = 0.0
    state[enter.fillna(False)] = 1.0
    return state.ffill().fillna(0.0)


def _with_band(raw, band=0.10, close=None, open_=None):
    """Renvoie un ordre seulement si la cible s'écarte de la bande, sinon NaN (aucun ordre).

    Avec `close` et `open_`, l'écart se mesure sur le poids détenu à la clôture : un ordre
    décidé hier s'exécute à l'ouverture d'aujourd'hui, puis seule la séance le fait dériver.
    Portefeuille fictif sans frais, lancé au début de l'historique : il sert de signal.
    Sans prix, l'écart se mesure sur le dernier ordre passé.
    """
    if (close is None) != (open_ is None):
        raise ValueError("close et open_ vont ensemble")
    values = raw.to_numpy(dtype=float)
    closes = None if close is None else close.reindex(raw.index).to_numpy(dtype=float)
    opens = None if open_ is None else open_.reindex(raw.index).to_numpy(dtype=float)
    out = np.full(len(values), np.nan)
    shares, cash, held, pending = 0.0, 1.0, 0.0, None
    for i, value in enumerate(values):
        if closes is not None:
            if pending is not None and np.isfinite(opens[i]):
                worth = shares * opens[i] + cash
                shares, cash = pending * worth / opens[i], (1 - pending) * worth
                pending = None
            if np.isfinite(closes[i]):
                worth = shares * closes[i] + cash
                held = shares * closes[i] / worth if worth > 0 else 0.0
        target = 0.0 if np.isnan(value) else value
        if abs(target - held) >= band or (target == 0.0 and held > 0.0):
            out[i] = target
            pending = target
            if closes is None:
                held = target
    return pd.Series(out, index=raw.index)


# Règles sur un seul actif : chaque fonction reçoit la clôture et renvoie l'exposition voulue.

def rule_sma(close, window=200, **_):
    sma = close.rolling(window, min_periods=window).mean()
    return (close > sma).where(sma.notna(), False).astype(float)


def rule_sma_monthly(close, window=200, **_):
    return monthly_hold(rule_sma(close, window).to_frame()).iloc[:, 0].fillna(0.0)


def rule_golden_cross(close, fast=50, slow=200, **_):
    a, b = close.rolling(fast, min_periods=fast).mean(), close.rolling(slow, min_periods=slow).mean()
    return (a > b).where(b.notna(), False).astype(float)


def rule_tsmom(close, lookback=252, **_):
    past = close.shift(lookback)
    return (close > past).where(past.notna(), False).astype(float)


def rule_donchian(close, entry=100, leave=50, **_):
    high = close.rolling(entry, min_periods=entry).max().shift(1)
    low = close.rolling(leave, min_periods=leave).min().shift(1)
    return _state_machine(close > high, close < low)


def rule_bollinger_reversion(close, window=20, width=2.0, **_):
    sma = close.rolling(window, min_periods=window).mean()
    std = close.rolling(window, min_periods=window).std()
    return _state_machine(close < sma - width * std, close > sma)


def rule_rsi2_reversion(close, **_):
    sma = close.rolling(200, min_periods=200).mean()
    return _state_machine((rsi(close, 2) < 10) & (close > sma), (rsi(close, 2) > 70) | (close < sma))


def rule_vol_target(close, target=0.30, open_=None, **_):
    return _with_band((target / realized_vol(close)).clip(upper=1.0), close=close, open_=open_)


def rule_trend_vol_target(close, target=0.30, open_=None, **_):
    return _with_band((target / realized_vol(close)).clip(upper=1.0) * rule_sma(close), close=close, open_=open_)


def rule_vol_regime(close, **_):
    """Rester investi sauf si la volatilité récente explose par rapport à sa norme sur un an."""
    short, long_ = realized_vol(close, 20), realized_vol(close, 252)
    return (short < 1.5 * long_).where(long_.notna(), False).astype(float)


def rule_drawdown_stop(close, stop=0.25, **_):
    peak = close.rolling(126, min_periods=126).max()
    high50 = close.rolling(50, min_periods=50).max()
    return _state_machine((close >= high50) & peak.notna(), close < peak * (1 - stop))


def rule_market_filter(close, market=None, **_):
    """Détenir l'actif seulement si le Nasdaq-100 est au-dessus de sa moyenne à 200 jours."""
    return rule_sma(market).reindex(close.index).fillna(0.0)


SINGLE_RULES = {
    "sma200": rule_sma,
    "sma200_monthly": rule_sma_monthly,
    "sma100": lambda c, **k: rule_sma(c, 100),
    "golden_cross": rule_golden_cross,
    "tsmom_252": rule_tsmom,
    "tsmom_126": lambda c, **k: rule_tsmom(c, 126),
    "donchian_100_50": rule_donchian,
    "bollinger_reversion": rule_bollinger_reversion,
    "rsi2_reversion": rule_rsi2_reversion,
    "vol_target_30": rule_vol_target,
    "trend_vol_target_30": rule_trend_vol_target,
    "vol_regime": rule_vol_regime,
    "drawdown_stop_25": rule_drawdown_stop,
    "market_filter_qqq": rule_market_filter,
}


def single_strategy(rule_name, symbol):
    rule = SINGLE_RULES[rule_name]

    def strategy(panel):
        return single_asset(panel, symbol, rule(panel.close[symbol], market=panel.close["QQQ"], open_=panel.open[symbol]))

    return strategy


# Rotations mensuelles entre plusieurs actifs.

def _empty(panel):
    return pd.DataFrame(0.0, index=panel.dates, columns=panel.close.columns)


def _finish(raw, panel):
    """Un ordre au premier jour de bourse du mois, aucun ordre les autres jours."""
    orders = raw.reindex(columns=panel.close.columns).fillna(0.0)
    orders[~first_trading_day_of_month(panel.dates)] = np.nan
    return orders


def equal_weight(symbols):
    def strategy(panel):
        raw = _empty(panel)
        raw[list(symbols)] = 1 / len(symbols)
        return _finish(raw, panel)

    return strategy


def dual_momentum(panel):
    """Antonacci : le meilleur de SPY et EFA sur 12 mois, sinon obligations si le marché est sous le cash."""
    mom = panel.close / panel.close.shift(252) - 1
    raw = _empty(panel)
    valid = mom["SPY"].notna() & mom["EFA"].notna() & mom["BIL"].notna()
    risk_on = mom["SPY"] > mom["BIL"]
    pick_spy = mom["SPY"] >= mom["EFA"]
    raw["SPY"] = (valid & risk_on & pick_spy).astype(float)
    raw["EFA"] = (valid & risk_on & ~pick_spy).astype(float)
    raw["IEF"] = (valid & ~risk_on).astype(float)
    return _finish(raw, panel)


def trend_portfolio(symbols, window=200):
    """Faber : une part égale par actif, conservée seulement si l'actif est au-dessus de sa moyenne."""

    def strategy(panel):
        raw = _empty(panel)
        for symbol in symbols:
            raw[symbol] = rule_sma(panel.close[symbol], window) / len(symbols)
        return _finish(raw, panel)

    return strategy


def momentum_top(symbols, top=3, lookback=126, trend_filter=True, vol_adjust=False):
    """Chaque mois, les `top` actifs les plus forts, en part égale. Cash si tendance baissière."""

    def strategy(panel):
        close = panel.close[list(symbols)]
        score = close / close.shift(lookback) - 1
        if vol_adjust:
            score = score / close.pipe(np.log).diff().rolling(lookback, min_periods=lookback).std()
        ranks = score.rank(axis=1, ascending=False, method="first")
        chosen = (ranks <= top) & score.notna() & (score > 0)
        if trend_filter:
            chosen = chosen & (close > close.rolling(200, min_periods=200).mean())
        raw = _empty(panel)
        raw[list(symbols)] = chosen.astype(float) / top
        return _finish(raw, panel)

    return strategy


def inverse_vol(symbols, window=60):
    """Parité de risque simple : plus de poids aux actifs calmes."""

    def strategy(panel):
        close = panel.close[list(symbols)]
        vol = np.log(close).diff().rolling(window, min_periods=window).std()
        inverse = 1 / vol
        raw = _empty(panel)
        raw[list(symbols)] = inverse.div(inverse.sum(axis=1), axis=0).fillna(0.0)
        return _finish(raw, panel)

    return strategy


def trend_or_safe(risky="QQQ", safe="IEF", window=200):
    """Actif risqué en tendance haussière, sinon actif refuge."""

    def strategy(panel):
        signal = rule_sma(panel.close[risky], window)
        raw = _empty(panel)
        raw[risky] = signal
        raw[safe] = (1 - signal) * panel.close[risky].rolling(window, min_periods=window).mean().notna()
        return _finish(raw, panel)

    return strategy


ROTATIONS = {
    "dual_momentum": dual_momentum,
    "gtaa5_trend": trend_portfolio(("SPY", "EFA", "IEF", "DBC", "VNQ")),
    "gtaa9_trend": trend_portfolio(("SPY", "QQQ", "IWM", "EFA", "EEM", "IEF", "TLT", "GLD", "DBC")),
    "sector_top3_mom": momentum_top(SECTORS),
    "sector_top3_mom_nofilter": momentum_top(SECTORS, trend_filter=False),
    "assets_top3_mom": momentum_top(("SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ")),
    "inverse_vol_4": inverse_vol(("SPY", "TLT", "GLD", "DBC")),
    "qqq_trend_ief": trend_or_safe("QQQ", "IEF"),
    "qqq_trend_gld": trend_or_safe("QQQ", "GLD"),
    "spy_trend_ief": trend_or_safe("SPY", "IEF"),
    # Biais de survie : gagnantes connues de 2016-2024, résultat non généralisable.
    "megacap_equal": equal_weight(MEGACAPS),
    "megacap_top3_mom": momentum_top(MEGACAPS),
    "megacap_top3_mom_nofilter": momentum_top(MEGACAPS, trend_filter=False),
    "megacap_top1_mom": momentum_top(MEGACAPS, top=1),
    "megacap_top3_voladj": momentum_top(MEGACAPS, vol_adjust=True),
}


# Apprentissage automatique : réentraînement annuel, jamais de mélange temporel.

ML_HORIZON = 5


def ml_features(panel, symbol):
    close = panel.close[symbol]
    log = np.log(close)
    frame = pd.DataFrame(index=panel.dates)
    for lag in (1, 5, 21, 63, 126, 252):
        frame[f"ret_{lag}"] = log.diff(lag)
    frame["vol_20"], frame["vol_60"] = realized_vol(close, 20), realized_vol(close, 60)
    frame["vol_ratio"] = frame.vol_20 / frame.vol_60
    frame["dist_sma50"] = close / close.rolling(50, min_periods=50).mean() - 1
    frame["dist_sma200"] = close / close.rolling(200, min_periods=200).mean() - 1
    frame["rsi_14"] = rsi(close, 14)
    frame["range_20"] = ((panel.high[symbol] - panel.low[symbol]) / close).rolling(20, min_periods=20).mean()
    volume = np.log(panel.volume[symbol].replace(0, np.nan))
    frame["volume_z"] = (volume - volume.rolling(60, min_periods=60).mean()) / volume.rolling(60, min_periods=60).std()
    market = np.log(panel.close["SPY"])
    frame["market_21"], frame["market_63"] = market.diff(21), market.diff(63)
    frame["market_dist_sma200"] = panel.close["SPY"] / panel.close["SPY"].rolling(200, min_periods=200).mean() - 1
    return frame


def make_model(kind):
    if kind == "logistic":
        return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(C=0.1, max_iter=1000))
    if kind == "boosting":
        return HistGradientBoostingClassifier(max_depth=3, learning_rate=0.03, max_iter=150, min_samples_leaf=40, l2_regularization=1.0, early_stopping=False, random_state=0)
    raise ValueError(kind)


def ml_strategy(symbol, kind, first_test_year=2018):
    """Prédit si l'actif montera sur 5 jours, réentraîné chaque janvier sur tout le passé.

    Le dernier exemple d'apprentissage est purgé : son résultat est connu avant la décision.
    Investi si la probabilité dépasse la fréquence de hausse observée à l'entraînement.
    """

    def strategy(panel):
        features = ml_features(panel, symbol)
        future = panel.open[symbol].shift(-(ML_HORIZON + 1)) / panel.open[symbol].shift(-1) - 1
        signal = pd.Series(np.nan, index=panel.dates, dtype=float)
        years = sorted({d.year for d in panel.dates if d.year >= first_test_year})
        for year in years:
            test_mask = panel.dates.year == year
            boundary = panel.dates[test_mask][0]
            position = panel.dates.get_loc(boundary)
            # Exemple t utilisable si open(t+6) est connu à la clôture précédant la décision.
            last_train = position - (ML_HORIZON + 2)
            if last_train < 300:
                continue
            train_index = panel.dates[260:last_train + 1]
            x, y = features.loc[train_index], (future.loc[train_index] > 0).astype(int)
            model = make_model(kind).fit(x, y)
            signal[test_mask] = (model.predict_proba(features.loc[test_mask])[:, 1] > y.mean()).astype(float)
        return single_asset(panel, symbol, signal.fillna(0.0))

    return strategy
