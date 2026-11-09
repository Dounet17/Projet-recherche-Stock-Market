"""Backtest exploratoire intraday, chronologique et sans appel réseau.

Prix à la minute corrigés des splits ; achats TSLA ou liquidités, sans levier.
Les timestamps de barres désignent le début de la minute.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
INITIAL_CAPITAL = 10_000.0
HOLD_MINUTES = 15
DELAY_SECONDS = 60
TEST_YEARS = (2022, 2023, 2024)


def load_posts(data_dir):
    posts = pd.read_parquet(data_dir / "musk_posts.parquet")
    fb = pd.read_parquet(data_dir / "finbert_musk_tesla.parquet")
    jev = pd.read_parquet(data_dir / "jev_musk_tesla.parquet")
    # Les caches identifient précisément les textes du notebook 02, sans reclassification.
    posts = posts.merge(fb.add_prefix("fb_").rename(columns={"fb_id": "id"}), on="id", validate="one_to_one")
    posts = posts.merge(jev.add_prefix("jev_").rename(columns={"jev_id": "id"}), on="id", validate="one_to_one")
    posts["fb_score"] = posts.fb_p_positive - posts.fb_p_negative
    posts["jev_sent_score"] = posts.jev_sent_p_positive - posts.jev_sent_p_negative
    posts["jev_impact_score"] = posts.jev_impact_p_up - posts.jev_impact_p_down
    return posts.sort_values("ts_utc").reset_index(drop=True)


def social_features(entries, posts, delay_seconds=DELAY_SECONDS):
    """Agrège uniquement les posts des 60 minutes précédant la disponibilité du signal."""
    entries = pd.DatetimeIndex(entries)
    cutoff = entries - pd.Timedelta(seconds=delay_seconds)
    times = pd.DatetimeIndex(posts.ts_utc)
    right = times.searchsorted(cutoff, side="right")
    left = times.searchsorted(cutoff - pd.Timedelta(minutes=60), side="right")
    recent_left = times.searchsorted(cutoff - pd.Timedelta(minutes=15), side="right")
    result = {"social_count_60": right - left, "social_count_15": right - recent_left}
    for col in ("fb_score", "jev_sent_score", "jev_impact_score", "jev_relevant_p"):
        values = posts[col].to_numpy(dtype=float)
        prefix = np.r_[0.0, np.cumsum(values)]
        count = right - left
        result[f"social_{col}_mean"] = np.divide(prefix[right] - prefix[left], count, out=np.zeros(len(count), dtype=float), where=count > 0)
        last = np.zeros(len(count))
        valid = count > 0
        last[valid] = values[right[valid] - 1]
        result[f"social_{col}_last"] = last
    return pd.DataFrame(result, index=entries)


def build_grid(calendar, bars, posts):
    rows = []
    for day in calendar.itertuples():
        opening = pd.Timestamp(day.open).tz_localize("America/New_York").tz_convert("UTC")
        closing = pd.Timestamp(day.close).tz_localize("America/New_York").tz_convert("UTC")
        # Ne pas utiliser une barre commençant à 16 h comme prix de clôture de séance.
        entries = pd.date_range(opening + pd.Timedelta(minutes=15), closing - pd.Timedelta(minutes=30), freq="15min")
        rows.extend({"entry_ts": t, "exit_ts": t + pd.Timedelta(minutes=HOLD_MINUTES), "day": day.date} for t in entries)
    grid = pd.DataFrame(rows)
    entries = pd.DatetimeIndex(grid.entry_ts)
    # À t, la barre t-2 est terminée à t-1 : marge de 60 s pour recevoir et traiter.
    ref = entries - pd.Timedelta(minutes=2)
    price_cols = []
    for symbol, frame in bars.items():
        close = frame.close
        base = close.reindex(ref).to_numpy()
        for lag in (1, 5, 15, 60):
            name = f"price_{symbol}_return_{lag}"
            older = close.reindex(ref - pd.Timedelta(minutes=lag)).to_numpy()
            grid[name] = np.log(base / older)
            price_cols.append(name)
        # Grille complète : une absence de barre reste NaN, sans propagation de cours.
        minute = close.reindex(pd.date_range(close.index.min(), close.index.max(), freq="1min"))
        vol = np.log(minute / minute.shift()).rolling(15, min_periods=10).std()
        name = f"price_{symbol}_volatility_15"
        grid[name] = vol.reindex(ref).to_numpy()
        price_cols.append(name)
    ny = entries.tz_convert("America/New_York")
    phase = 2 * np.pi * (ny.hour * 60 + ny.minute) / (24 * 60)
    grid["clock_sin"], grid["clock_cos"] = np.sin(phase), np.cos(phase)
    price_cols += ["clock_sin", "clock_cos"]
    grid["entry_price"] = bars["tsla"].open.reindex(entries).to_numpy()
    grid["exit_price"] = bars["tsla"].open.reindex(pd.DatetimeIndex(grid.exit_ts)).to_numpy()
    grid["asset_return"] = grid.exit_price / grid.entry_price - 1
    social = social_features(entries, posts)
    for col in social:
        grid[col] = social[col].to_numpy()
    valid = grid.entry_price.gt(0) & grid.exit_price.gt(0)
    stats = {"scheduled_intervals": len(grid), "missing_execution_intervals": int((~valid).sum()), "feature_missing_fraction": grid[price_cols].isna().mean().to_dict()}
    grid = grid[valid].reset_index(drop=True)
    grid["target_up"] = (grid.asset_return > 0).astype(int)
    return grid, price_cols, stats


def walk_forward(grid, price_cols):
    activity = ["social_count_60", "social_count_15"]
    fb_cols = [c for c in grid if c.startswith("social_fb_")]
    jev_cols = [c for c in grid if c.startswith("social_jev_")]
    feature_sets = {
        "prices": price_cols,
        "prices_activity": price_cols + activity,
        "prices_finbert": price_cols + activity + fb_cols,
        "prices_jev": price_cols + activity + jev_cols,
    }
    predictions, folds, coefficients = [], [], []
    for year in TEST_YEARS:
        boundary = pd.Timestamp(f"{year}-01-01", tz="UTC")
        # Purge explicite : chaque label d'apprentissage est terminé avant l'année testée.
        train = grid[grid.exit_ts < boundary]
        test = grid[grid.entry_ts.dt.year == year].copy()
        for name, columns in feature_sets.items():
            model = make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler(), LogisticRegression(C=1.0, max_iter=2000, random_state=0))
            model.fit(train[columns], train.target_up)
            test[f"prob_{name}"] = model.predict_proba(test[columns])[:, 1]
            test[f"position_{name}"] = (test[f"prob_{name}"] > 0.5).astype(int)
            folds.append({"test_year": year, "model": name, "train_rows": len(train), "test_rows": len(test), "last_train_exit": str(train.exit_ts.max()), "first_test_entry": str(test.entry_ts.min()), "accuracy": float(((test[f"prob_{name}"] > 0.5) == test.target_up).mean()), "social_intervals": int(test.social_count_60.gt(0).sum())})
            fitted_names = model[0].get_feature_names_out(columns)
            coefficients.extend({"test_year": year, "model": name, "feature": col, "standardized_coefficient": float(value)} for col, value in zip(fitted_names, model[-1].coef_[0]))
        predictions.append(test)
    return pd.concat(predictions, ignore_index=True), pd.DataFrame(folds), pd.DataFrame(coefficients)


def simulate(intervals, positions, cost_bps=5.0, capital=INITIAL_CAPITAL):
    """Compte cash/actions ; conserve les actions entre deux intervalles contigus achetés.

    Le coût par côté est une hypothèse globale (spread, slippage et commissions).
    Aucun levier : tout le capital disponible est investi, en fractions d'action.
    Les actions sont liquidées à chaque trou de calendrier et en fin de journée.
    """
    frame = intervals.reset_index(drop=True)
    position = np.asarray(positions, dtype=int)
    if len(position) != len(frame) or not np.isin(position, [0, 1]).all():
        raise ValueError("Positions attendues : une valeur 0 ou 1 par intervalle")
    if len(frame) and (frame.exit_ts <= frame.entry_ts).any():
        raise ValueError("Chaque sortie doit suivre son entrée")
    if len(frame) > 1 and (frame.entry_ts.iloc[1:].to_numpy() < frame.exit_ts.iloc[:-1].to_numpy()).any():
        raise ValueError("Intervalles non triés ou positions superposées")
    c = cost_bps / 10_000
    if not 0 <= c < 1:
        raise ValueError("Coût invalide")
    contiguous = np.zeros(len(frame), dtype=bool)
    if len(frame) > 1:
        contiguous[1:] = frame.entry_ts.iloc[1:].to_numpy() == frame.exit_ts.iloc[:-1].to_numpy()
    previous = np.r_[0, position[:-1]]
    following = np.r_[position[1:], 0]
    starts = (position == 1) & ~((previous == 1) & contiguous)
    next_contiguous = np.r_[contiguous[1:], False]
    stops = (position == 1) & ~((following == 1) & next_contiguous)
    if len(frame) > 1:
        joins = contiguous & (previous == 1) & (position == 1)
        if not np.allclose(frame.entry_price.to_numpy()[joins], np.r_[np.nan, frame.exit_price.to_numpy()[:-1]][joins]):
            raise ValueError("Prix incohérents à la jonction de deux positions")
    factor = np.where(position == 1, frame.exit_price / frame.entry_price, 1.0)
    factor = factor * np.where(starts, 1 / (1 + c), 1.0) * np.where(stops, 1 - c, 1.0)
    out = frame[["entry_ts", "exit_ts", "day"]].copy()
    out["position"], out["buy"], out["sell"] = position, starts, stops
    out["factor"] = factor
    out["equity"] = capital * np.cumprod(factor)
    return out


def summarize(curve, trading_days, capital=INITIAL_CAPITAL):
    daily_factor = curve.groupby("day").factor.prod().reindex(pd.DatetimeIndex(trading_days), fill_value=1.0)
    daily_return = daily_factor - 1
    full_equity = np.r_[capital, curve.equity.to_numpy()]
    drawdown = full_equity / np.maximum.accumulate(full_equity) - 1
    final = float(full_equity[-1])
    sd = daily_return.std(ddof=1)
    return {"final_capital": final, "total_return": final / capital - 1, "annualized_return": (final / capital) ** (252 / len(daily_factor)) - 1, "max_drawdown_grid": float(drawdown.min()), "sharpe_daily_rf0": float(np.sqrt(252) * daily_return.mean() / sd) if sd > 0 else None, "round_trips": int(curve.buy.sum()), "invested_interval_fraction": float(curve.position.mean()), "daily_returns": daily_return}


def event_rule(posts, bars, calendar, horizon=1, delay_seconds=DELAY_SECONDS):
    """Contrôle descriptif : acheter après un signal Jev « up », sans modèle appris."""
    cal = calendar.set_index("date")
    rows, busy_until, ignored_busy, missing = [], None, 0, 0
    for p in posts.itertuples():
        if p.ts_utc.year not in TEST_YEARS or p.jev_impact_label != "up":
            continue
        entry = (p.ts_utc + pd.Timedelta(seconds=delay_seconds)).ceil("min")
        exit_ = entry + pd.Timedelta(minutes=horizon)
        ny = entry.tz_convert("America/New_York")
        day = ny.tz_localize(None).normalize()
        if day not in cal.index:
            continue
        opening, closing = cal.loc[day, ["open", "close"]]
        if ny.tz_localize(None) < opening or exit_.tz_convert("America/New_York").tz_localize(None) >= closing:
            continue
        if busy_until is not None and entry < busy_until:
            ignored_busy += 1
            continue
        if entry not in bars.index or exit_ not in bars.index:
            missing += 1
            continue
        rows.append({"entry_ts": entry, "exit_ts": exit_, "day": day, "entry_price": bars.at[entry, "open"], "exit_price": bars.at[exit_, "open"], "post_id": int(p.id), "post_ts": p.ts_utc})
        busy_until = exit_
    return pd.DataFrame(rows), {"ignored_overlaps": ignored_busy, "missing_execution_pairs": missing}
