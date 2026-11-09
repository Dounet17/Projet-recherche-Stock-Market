"""Audit exploratoire des caches existants, sans téléchargement ni appel de classification.

Lancement depuis la racine : venv/bin/python reports/audit_cached_results.py
Les variantes après publication sont des sensibilités, pas un backtest exécutable.
Les p-values supposent l'indépendance des événements, non garantie ici.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import cohen_kappa_score

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / 'src'))
from collect import mentions_tesla
from timeutils import session_of, tweet_time_utc

data = root / 'data'
posts = pd.read_parquet(data / 'musk_posts.parquet')
posts = posts[posts.ts_utc.dt.year.between(2018, 2024) & posts.kind.isin(['original', 'quote', 'reply'])]
posts = posts[mentions_tesla(posts.text)].copy()
posts['clean_text'] = posts.text.str.replace(r'https?://\S+', '', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip()
posts = posts[posts.clean_text.str.len() > 0].reset_index(drop=True)
fb = pd.read_parquet(data / 'finbert_musk_tesla.parquet')
jev = pd.read_parquet(data / 'jev_musk_tesla.parquet')
df = posts.merge(fb.add_prefix('fb_').rename(columns={'fb_id': 'id'}), on='id').merge(jev.add_prefix('jev_').rename(columns={'jev_id': 'id'}), on='id')
df['fb_score'] = df.fb_p_positive - df.fb_p_negative
df['jev_sent_score'] = df.jev_sent_p_positive - df.jev_sent_p_negative
df['jev_impact_score'] = df.jev_impact_p_up - df.jev_impact_p_down
cal = pd.read_parquet(data / 'calendar.parquet')
df['session'] = session_of(df.ts_utc, cal)
ny = df.ts_utc.dt.tz_convert('America/New_York').dt.tz_localize(None)
opening = ny.dt.normalize().map(cal.set_index('date').open)
closing = ny.dt.normalize().map(cal.set_index('date').close)
ev = df[(df.session == 'regular') & ((ny - opening).dt.total_seconds() >= 60) & ((closing - ny).dt.total_seconds() >= 61 * 60)].copy()
t0 = ev.ts_utc.dt.floor('min')
bars = {s: pd.read_parquet(data / f'{s}_1min.parquet').set_index('ts_utc').sort_index() for s in ['tsla', 'qqq']}
horizons = [1, 5, 15, 60]
scores = {'FinBERT': 'fb_score', 'Jev sentiment': 'jev_sent_score', 'Jev impact': 'jev_impact_score'}
rows = []
returns = {}
for mode in ['notebook_total_reaction', 'after_post_minute_close', 'next_minute_open_proxy']:
    ars = {}
    for h in horizons:
        rets = {}
        for s, b in bars.items():
            if mode == 'notebook_total_reaction':
                ref = b.close.reindex(t0 - pd.Timedelta(minutes=1), method='ffill').to_numpy()
            elif mode == 'after_post_minute_close':
                ref = b.close.reindex(t0).to_numpy()
            else:
                ref = b.open.reindex(t0 + pd.Timedelta(minutes=1)).to_numpy()
            end = b.close.reindex(t0 + pd.Timedelta(minutes=h), method='ffill' if mode == 'notebook_total_reaction' else None).to_numpy()
            rets[s] = end / ref - 1
        ar = rets['tsla'] - rets['qqq']
        ars[h] = ar
        for label, col in scores.items():
            valid = np.isfinite(ev[col].to_numpy()) & np.isfinite(ar)
            rho, p = stats.spearmanr(ev[col].to_numpy()[valid], ar[valid])
            sign = ev.jev_impact_label.map({'up': 1, 'down': -1}).to_numpy() if label == 'Jev impact' else np.full(len(ev), np.nan)
            active = valid & np.isfinite(sign)
            rows.append({'mode': mode, 'model': label, 'horizon_label_min': h, 'n': int(valid.sum()), 'rho': float(rho), 'p_naive': float(p), 'p_bonferroni_12': float(min(1, p * 12)), 'signed_mean_bp_jev_impact': float(np.mean((sign * ar)[active]) * 1e4) if active.any() else None, 'n_directional_jev_impact': int(active.sum()) if active.any() else None})
    returns[mode] = ars

times = ev.ts_utc.sort_values()
missing = {}
for s,b in bars.items():
    missing[s] = {'duplicate_timestamps': int(b.index.duplicated().sum()), 'missing_reference_bars': int((~(t0 - pd.Timedelta(minutes=1)).isin(b.index)).sum()), 'missing_end_bars': {str(h): int((~(t0 + pd.Timedelta(minutes=h)).isin(b.index)).sum()) for h in horizons}, 'missing_next_open_bars': int((~(t0 + pd.Timedelta(minutes=1)).isin(b.index)).sum())}
news = pd.read_parquet(data / 'tsla_news.parquet')
earn = pd.read_parquet(data / 'tsla_earnings.parquet')
out = {'date': '2026-10-25', 'posts': len(df), 'kinds': df.kind.value_counts().to_dict(), 'sessions': df.session.value_counts().to_dict(), 'events': len(ev), 'event_days': ev.ts_utc.dt.tz_convert('America/New_York').dt.date.nunique(), 'events_by_year': ev.ts_utc.dt.year.value_counts().sort_index().to_dict(), 'posts_with_previous_event_within_60min': int((times.diff() <= pd.Timedelta(minutes=60)).sum()), 'timestamp_mismatches': int((tweet_time_utc(df.id) != df.ts_utc).sum()), 'agreement': float((df.fb_label == df.jev_sent_label).mean()), 'kappa': float(cohen_kappa_score(df.fb_label,df.jev_sent_label)), 'finbert_neutral_fraction': float(df.fb_label.eq('neutral').mean()), 'jev_versions': df.jev_model.value_counts().to_dict(), 'bar_checks': missing, 'news_updated_later_than_created': int((news.updated_at > news.created_at).sum()), 'earnings_in_period': int(earn.ts.dt.year.between(2018,2024).sum()), 'correlations': rows}
print(f'{len(df)} posts classes ; {len(ev)} evenements sur {out["event_days"]} jours')
for row in rows:
    if row['model'] == 'Jev impact' and row['horizon_label_min'] == 1:
        print(f"{row['mode']}: rho={row['rho']:.4f}, p={row['p_naive']:.4g}, p_Bonferroni12={row['p_bonferroni_12']:.4g}")
(root / 'reports' / 'audit_metrics_2026-10-25.json').write_text(json.dumps(out, indent=2) + '\n')
