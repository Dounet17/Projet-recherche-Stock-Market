"""Règles appliquées action par action : 1 investi, 0 en liquidités, NaN pour ne rien changer.

Toutes exigent la même histoire (au moins 180 clôtures valides sur 200 séances) : elles se comparent
ainsi sur les mêmes actions et les mêmes dates. Bollinger et RSI reprennent les définitions de
`price_lab`, figées avant de voir le moindre résultat sur le grand univers.
"""

import numpy as np
import pandas as pd

from price_lab import rsi

HISTORY_WINDOW = 200
HISTORY_MIN_VALID = 180


def _average_200(close):
    return close.rolling(HISTORY_WINDOW, min_periods=HISTORY_MIN_VALID).mean()


def state_machine(enter, leave):
    """Position 1 après un signal d'entrée, jusqu'au signal de sortie ; une entrée l'emporte le même jour."""
    values = np.where(enter.fillna(False).to_numpy(dtype=bool), 1.0, np.where(leave.fillna(False).to_numpy(dtype=bool), 0.0, np.nan))
    return pd.DataFrame(values, index=enter.index, columns=enter.columns).ffill().fillna(0.0)


def _only_with_history(state, close):
    """Pas d'ordre sans clôture du jour, ni sans histoire suffisante."""
    return state.where(_average_200(close).notna() & close.notna())


def sma200(data, window=HISTORY_WINDOW, min_valid=HISTORY_MIN_VALID):
    """Suivi de tendance : investi tant que la clôture dépasse sa moyenne sur 200 séances."""
    average = data.close.rolling(window, min_periods=min_valid).mean()
    return (data.close > average).astype(float).where(average.notna() & data.close.notna())


def bollinger_reversion(data, window=20, width=2.0):
    """Retour à la moyenne : achat sous la bande basse, vente au-dessus de la moyenne sur 20 séances."""
    close = data.close
    average = close.rolling(window, min_periods=window).mean()
    deviation = close.rolling(window, min_periods=window).std()
    return _only_with_history(state_machine(close < average - width * deviation, close > average), close)


def rsi2_reversion(data, enter_below=10, leave_above=70):
    """Retour à la moyenne dans une hausse : achat après une courte baisse, si le cours reste au-dessus de sa moyenne sur 200 séances.

    Le RSI mesure de 0 à 100 la force des dernières variations. Sur 2 séances, il réagit très vite.
    """
    close = data.close
    average = _average_200(close)
    value = rsi(close, 2)
    return _only_with_history(state_machine((value < enter_below) & (close > average), (value > leave_above) | (close < average)), close)
