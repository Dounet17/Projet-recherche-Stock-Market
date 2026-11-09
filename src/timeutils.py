"""Outils d'horodatage : heure exacte depuis les identifiants, heure de New York, séances de bourse."""

import numpy as np
import pandas as pd

# Époque des identifiants Twitter (snowflake), en millisecondes
TWITTER_EPOCH_MS = 1288834974657
NY_TZ = "America/New_York"


def _as_int64(ids: pd.Series) -> np.ndarray:
    # Les identifiants doivent arriver en texte ou en int64 : un float a déjà perdu les derniers chiffres
    if pd.api.types.is_float_dtype(ids):
        raise TypeError("Identifiants en float : relire le fichier avec dtype={'id': 'string'}")
    return ids.astype("int64").to_numpy()


def tweet_time_utc(ids: pd.Series) -> pd.Series:
    """Heure de création d'un tweet, déduite de son identifiant (précision à la milliseconde)."""
    ms = (_as_int64(ids) >> 22) + TWITTER_EPOCH_MS
    return pd.Series(pd.to_datetime(ms, unit="ms", utc=True), index=ids.index)


def truth_time_utc(ids: pd.Series) -> pd.Series:
    """Heure de création d'un post Truth Social (identifiant de type Mastodon)."""
    ms = _as_int64(ids) >> 16
    return pd.Series(pd.to_datetime(ms, unit="ms", utc=True), index=ids.index)


def session_of(ts_utc: pd.Series, calendar: pd.DataFrame) -> pd.Series:
    """Classe chaque instant en 'regular', 'pre', 'post' ou 'closed'.

    `calendar` vient de `collect.alpaca_calendar` : une ligne par jour de bourse avec
    l'heure d'ouverture et de fermeture (les séances écourtées sont donc gérées).
    Pré-séance : 4 h - ouverture ; post-séance : fermeture - 20 h (heure de New York).
    """
    ny = ts_utc.dt.tz_convert(NY_TZ)
    day = ny.dt.tz_localize(None).dt.normalize()
    cal = calendar.set_index("date")
    open_ = day.map(cal["open"])
    close = day.map(cal["close"])
    minutes = ny.dt.hour * 60 + ny.dt.minute + ny.dt.second / 60
    open_min = open_.dt.hour * 60 + open_.dt.minute
    close_min = close.dt.hour * 60 + close.dt.minute

    result = pd.Series("closed", index=ts_utc.index)
    trading_day = open_.notna()
    result[trading_day & (minutes >= 4 * 60) & (minutes < open_min)] = "pre"
    result[trading_day & (minutes >= open_min) & (minutes < close_min)] = "regular"
    result[trading_day & (minutes >= close_min) & (minutes < 20 * 60)] = "post"
    return result
