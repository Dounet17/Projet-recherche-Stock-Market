"""Signaux sociaux et événements, disponibles à la clôture de chaque séance.

Les chargements sont filtrés avant tout calcul. Aucun accès à une API payante,
aux secrets ou aux prix en dehors de lab.load_panel n'est nécessaire.
"""

import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

import lab

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOCIAL_DIR = lab.LAB_DIR / "social"
NEWS_CACHE = SOCIAL_DIR / "news_finbert.parquet"
TESLA_PATTERN = r"\b(?:tesla|tsla|cybertruck|autopilot|gigafactory|supercharg\w*|fsd|model\s*[syx3])\b"
OTHER_PATTERN = r"\b(?:twitter|tweet\w*|democrat\w*|republican\w*|politic\w*|election\w*|vote\w*|woke|biden|congress|immigra\w*)\b"

# Liste figée avant le calcul des rendements, sans balayage des paramètres.
TRIALS = {
    "earnings_positive_20": ("heuristic", "Après surprise positive : TSLA pendant 20 séances"),
    "earnings_negative_exit_10": ("heuristic", "Après surprise négative : liquidités pendant 10 séances"),
    "earnings_exit_3": ("heuristic", "Après tout résultat : liquidités pendant 3 séances"),
    "earnings_proxy_drift_10": ("heuristic", "Avant date estimée du trimestre : TSLA pendant 10 jours calendaires"),
    "earnings_proxy_exit_3": ("heuristic", "Date trimestrielle estimée : liquidités à plus ou moins 3 jours calendaires"),
    "musk_activity_exit_5": ("adaptive", "Activité Musk sur 5 séances au dessus du quantile passé à 90 % : liquidités"),
    "musk_other_exit_5": ("adaptive", "Pic Musk et plus de 75 % de sujets extérieurs à Tesla : liquidités"),
    "musk_finbert_exit_5": ("adaptive", "Sentiment FinBERT Musk négatif sur 5 séances : liquidités"),
    "musk_jev_exit_5": ("adaptive", "Impact Jev Musk négatif sur 5 séances : liquidités"),
    "news_activity_exit_5": ("adaptive", "Volume de news sur 5 séances au dessus du quantile passé à 90 % : liquidités"),
    "news_finbert_exit_5": ("adaptive", "Sentiment FinBERT des titres négatif sur 5 séances : liquidités"),
    "hybrid_musk_trend_200": ("hybrid", "Tendance 200 séances et absence de pic Musk hors Tesla"),
    "hybrid_news_trend_200": ("hybrid", "Tendance 200 séances et absence de sentiment news négatif"),
    "control_trend_200": ("control", "Contrôle : tendance 200 séances seule"),
    "control_half_tsla": ("control", "Contrôle : exposition TSLA constante à 50 %"),
}


def close_times(dates, data_dir=DATA_DIR):
    """Clôtures de New York, avec les séances écourtées du calendrier local."""
    dates = pd.DatetimeIndex(dates)
    local = pd.Series(dates + pd.Timedelta(hours=16), index=dates)
    path = Path(data_dir) / "calendar.parquet"
    if path.exists():
        calendar = pd.read_parquet(path, filters=[("date", "<=", dates[-1])])
        calendar = calendar.set_index("date")["close"].reindex(dates)
        local = calendar.combine_first(local)
    return pd.DatetimeIndex(local).tz_localize("America/New_York").tz_convert("UTC")


def available_days(timestamps, dates, closes):
    """Premier jour dont la clôture suit l'information, sans perdre les fuseaux."""
    timestamps = pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True))
    slots = closes.searchsorted(timestamps, side="left")
    values = np.full(len(slots), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    valid = (slots < len(dates)) & timestamps.notna()
    values[valid] = pd.DatetimeIndex(dates).as_unit("ns").to_numpy()[slots[valid]]
    return pd.DatetimeIndex(values)


def headline_hash(text):
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def load_external(cutoff, data_dir=DATA_DIR, allow_holdout=False):
    """Filtre dans Parquet, y compris les caches dont les dates viennent des IDs."""
    cutoff = pd.Timestamp(cutoff).tz_convert("UTC")
    if cutoff.tz_convert("America/New_York").date() > pd.Timestamp(lab.DEV_END).date() and not allow_holdout:
        raise PermissionError("Données sociales de validation verrouillées")
    data_dir = Path(data_dir)
    posts = pd.read_parquet(data_dir / "musk_posts.parquet", filters=[("ts_utc", "<=", cutoff)])
    posts = posts.loc[posts.ts_utc <= cutoff].copy()
    # L'horodatage fait autorité, jamais les compteurs de réactions futurs.
    inferred = pd.to_datetime(np.right_shift(posts.id.to_numpy(dtype="int64"), 22) + 1288834974657,
                              unit="ms", utc=True)
    if not np.array_equal(pd.DatetimeIndex(posts.ts_utc).as_unit("ms").asi8, inferred.as_unit("ms").asi8):
        raise ValueError("Horodatage Musk incohérent avec son identifiant")
    posts = posts.loc[posts.kind != "retweet", ["id", "ts_utc", "text"]].copy()
    max_id = ((cutoff.value // 1_000_000 - 1288834974657) << 22) + (1 << 22) - 1
    fb = pd.read_parquet(data_dir / "finbert_musk_tesla.parquet", filters=[("id", "<=", max_id)])
    jev = pd.read_parquet(data_dir / "jev_musk_tesla.parquet", filters=[("id", "<=", max_id)])
    posts = posts.merge(fb[["id", "p_positive", "p_negative"]], on="id", how="left", validate="one_to_one")
    posts = posts.merge(jev[["id", "impact_p_up", "impact_p_down"]], on="id", how="left", validate="one_to_one")
    earnings = pd.read_parquet(data_dir / "tsla_earnings.parquet", filters=[("ts", "<=", cutoff)])
    earnings = earnings.loc[earnings.ts <= cutoff].sort_values("ts").copy()
    news = pd.read_parquet(data_dir / "tsla_news.parquet",
                           filters=[("created_at", "<=", cutoff), ("updated_at", "<=", cutoff)])
    news = news.loc[(news.created_at <= cutoff) & (news.updated_at <= cutoff)].copy()
    news["available_at"] = news[["created_at", "updated_at"]].max(axis=1)
    return posts, earnings, news


def _daily_sum(frame, value, dates):
    return frame.groupby("day")[value].sum(min_count=1).reindex(dates).fillna(0.0)


@lru_cache(maxsize=12)
def _features(date_values, data_dir, cache_path, allow_holdout):
    dates = pd.DatetimeIndex(date_values)
    closes = close_times(dates, data_dir)
    posts, earnings, news = load_external(closes[-1], data_dir, allow_holdout)
    frame = pd.DataFrame(index=dates)
    posts["day"] = available_days(posts.ts_utc, dates, closes)
    posts["count"] = 1.0
    posts["other"] = (posts.text.str.contains(OTHER_PATTERN, case=False, regex=True, na=False)
                      & ~posts.text.str.contains(TESLA_PATTERN, case=False, regex=True, na=False)).astype(float)
    for prefix, pos, neg in (("fb", "p_positive", "p_negative"), ("jev", "impact_p_up", "impact_p_down")):
        posts[prefix + "_score"] = posts[pos] - posts[neg]
        posts[prefix + "_count"] = posts[prefix + "_score"].notna().astype(float)
        sums = _daily_sum(posts, prefix + "_score", dates).rolling(5, min_periods=1).sum()
        counts = _daily_sum(posts, prefix + "_count", dates).rolling(5, min_periods=1).sum()
        frame[prefix + "_score5"] = sums / counts.replace(0, np.nan)
        frame[prefix + "_count5"] = counts
    counts = _daily_sum(posts, "count", dates)
    frame["posts5"] = counts.rolling(5, min_periods=1).sum()
    frame["posts_threshold"] = frame.posts5.shift(1).rolling(252, min_periods=126).quantile(0.90)
    frame["other_share5"] = (_daily_sum(posts, "other", dates).rolling(5, min_periods=1).sum()
                              / frame.posts5.replace(0, np.nan))
    news["day"] = available_days(news.available_at, dates, closes)
    news["count"] = 1.0
    frame["news5"] = _daily_sum(news, "count", dates).rolling(5, min_periods=1).sum()
    observed_news = frame.news5.where(dates >= news.day.min())
    frame["news_threshold"] = observed_news.shift(1).rolling(252, min_periods=126).quantile(0.90)
    frame["news_score5"] = np.nan
    frame["news_score_count5"] = 0.0
    if Path(cache_path).exists():
        cache = pd.read_parquet(cache_path, filters=[("available_at", "<=", closes[-1])])
        news["headline_hash"] = news.headline.map(headline_hash)
        news = news.merge(cache[["id", "headline_hash", "p_positive", "p_negative"]],
                          on=["id", "headline_hash"], how="left", validate="one_to_one")
        news["score"] = news.p_positive - news.p_negative
        news["score_count"] = news.score.notna().astype(float)
        n = _daily_sum(news, "score_count", dates).rolling(5, min_periods=1).sum()
        frame["news_score5"] = _daily_sum(news, "score", dates).rolling(5, min_periods=1).sum() / n.replace(0, np.nan)
        frame["news_score_count5"] = n
    frame["earnings_positive20"] = False
    frame["earnings_negative10"] = False
    frame["earnings_after3"] = False
    frame["last_earnings_day"] = pd.NaT
    for event in earnings.itertuples():
        publication_day = event.ts.tz_convert("America/New_York").tz_localize(None).normalize()
        if publication_day < dates[0]:
            frame.iloc[0, frame.columns.get_loc("last_earnings_day")] = publication_day
            continue
        first = dates.searchsorted(publication_day, side="right")
        if first >= len(dates):
            continue
        # Même une heure de source aberrante ne permet pas d'utiliser la surprise le jour même.
        frame.iloc[first:first + 3, frame.columns.get_loc("earnings_after3")] = True
        valid_eps = np.isfinite(event.eps_estimate) and np.isfinite(event.eps_reported)
        if valid_eps and event.eps_reported > event.eps_estimate:
            frame.iloc[first:first + 20, frame.columns.get_loc("earnings_positive20")] = True
        if valid_eps and event.eps_reported < event.eps_estimate:
            frame.iloc[first:first + 10, frame.columns.get_loc("earnings_negative10")] = True
        frame.iloc[first, frame.columns.get_loc("last_earnings_day")] = publication_day
    last = frame.last_earnings_day.ffill()
    frame["calendar_to_proxy"] = ((last + pd.Timedelta(days=91)) - dates.to_series(index=dates)).dt.days
    return frame


def features(panel, data_dir=DATA_DIR, cache_path=NEWS_CACHE, allow_holdout=False):
    return _features(tuple(panel.dates), str(data_dir), str(cache_path), allow_holdout).copy()


def strategy_weights(panel, variant, data_dir=DATA_DIR, cache_path=NEWS_CACHE, allow_holdout=False):
    """Fonction commune figée : poids de TSLA décidés à la clôture, sans décalage."""
    if variant not in TRIALS:
        raise ValueError("Variante inconnue")
    frame = features(panel, data_dir, cache_path, allow_holdout)
    spike = frame.posts5 > frame.posts_threshold
    other_risk = spike & (frame.other_share5 > 0.75)
    news_negative = (frame.news_score5 < -0.10) & (frame.news_score_count5 >= 3)
    trend = panel.close.TSLA > panel.close.TSLA.rolling(200, min_periods=200).mean()
    rules = {
        "earnings_positive_20": frame.earnings_positive20,
        "earnings_negative_exit_10": ~frame.earnings_negative10,
        "earnings_exit_3": ~frame.earnings_after3,
        "earnings_proxy_drift_10": frame.calendar_to_proxy.between(1, 10),
        "earnings_proxy_exit_3": ~frame.calendar_to_proxy.between(-3, 3),
        "musk_activity_exit_5": ~spike,
        "musk_other_exit_5": ~other_risk,
        "musk_finbert_exit_5": ~((frame.fb_score5 < -0.10) & (frame.fb_count5 >= 1)),
        "musk_jev_exit_5": ~((frame.jev_score5 < -0.10) & (frame.jev_count5 >= 1)),
        "news_activity_exit_5": ~(frame.news5 > frame.news_threshold),
        "news_finbert_exit_5": ~news_negative,
        "hybrid_musk_trend_200": trend & ~other_risk,
        "hybrid_news_trend_200": trend & ~news_negative,
        "control_trend_200": trend,
        "control_half_tsla": pd.Series(0.5, index=panel.dates),
    }
    if variant in ("news_finbert_exit_5", "hybrid_news_trend_200"):
        incomplete = frame.news_score_count5 < frame.news5
        if incomplete.any() or frame.news_score_count5.sum() == 0:
            raise ValueError("Cache FinBERT des news incomplet : préparer tous les titres avant les essais")
    weights = pd.DataFrame(0.0, index=panel.dates, columns=panel.open.columns)
    weights["TSLA"] = rules[variant].astype(float)
    return weights


def prepare_news_cache(panel, cache_path=NEWS_CACHE, batch_size=32):
    """Inférence CPU locale seulement, cache dans le périmètre de fichiers autorisé."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    closes = close_times(panel.dates)
    _, _, news = load_external(closes[-1])
    news["headline_hash"] = news.headline.map(headline_hash)
    cache_path = Path(cache_path)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = pd.read_parquet(cache_path, filters=[("available_at", "<=", closes[-1])]) if cache_path.exists() else pd.DataFrame()
    if len(cache):
        keys = pd.MultiIndex.from_frame(cache[["id", "headline_hash"]])
        news = news.loc[~pd.MultiIndex.from_frame(news[["id", "headline_hash"]]).isin(keys)]
    if not len(news):
        return
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert", local_files_only=True)
    model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert", local_files_only=True).to("cpu").eval()
    labels = {label.lower(): int(i) for i, label in model.config.id2label.items()}
    pending = []
    for first in range(0, len(news), batch_size):
        batch = news.iloc[first:first + batch_size]
        encoded = tokenizer(batch.headline.fillna("").tolist(), padding=True, truncation=True,
                            max_length=128, return_tensors="pt")
        with torch.inference_mode():
            probabilities = model(**encoded).logits.softmax(dim=-1).numpy()
        rows = batch[["id", "headline_hash", "available_at"]].copy()
        rows["p_positive"] = probabilities[:, labels["positive"]]
        rows["p_negative"] = probabilities[:, labels["negative"]]
        rows["p_neutral"] = probabilities[:, labels["neutral"]]
        pending.append(rows)
        if (first // batch_size + 1) % 16 == 0 or first + batch_size >= len(news):
            cache = pd.concat([cache, *pending], ignore_index=True)
            cache.to_parquet(cache_path, index=False)
            pending = []
            print(f"FinBERT CPU : {min(first + batch_size, len(news))}/{len(news)} titres supplémentaires", flush=True)
    _features.cache_clear()
