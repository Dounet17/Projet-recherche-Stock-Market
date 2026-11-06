"""Socle commun du laboratoire de stratégies quotidiennes (protocole du 06/11/2026).

Convention de temps : `weights.loc[t]` est décidé avec l'information connue à la
clôture de t, et appliqué à l'ouverture de t+1. La période t+1 rapporte donc
open(t+2) / open(t+1) - 1. Le moteur applique ce décalage : une stratégie ne doit
jamais décaler elle-même ses poids.

Une ligne de poids entièrement vide (NaN) signifie « aucun ordre » : les positions
restent en place et leurs poids dérivent avec les prix, sans frais. Une ligne remplie
est une cible à rétablir à l'ouverture suivante.

Vocabulaire :
- rendement annualisé (CAGR) : gain moyen composé par an ;
- Sharpe : rendement moyen / volatilité, le gain obtenu par unité de risque ;
- drawdown : pire chute depuis un sommet ;
- alpha : gain qui reste une fois retiré ce qui vient de la simple exposition au marché ;
- point de base (pb) : 0,01 %.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "lab_daily_adjusted.parquet"
LAB_DIR = ROOT / "reports" / "lab_2026-11"

WARMUP_START = "2016-01-04"
DEV_START = "2018-01-02"
DEV_END = "2024-12-31"
HOLDOUT_START = "2025-01-02"
HOLDOUT_END = "2026-10-30"

INITIAL_CAPITAL = 10_000.0
DEFAULT_COST_BPS = 5.0
TRADING_DAYS = 252

# Univers figé avant tout essai. On publie tous les résultats, pas seulement les réussites.
TARGETS = ("TSLA", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "SPY", "QQQ", "IWM")
ROTATION = ("SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ",
            "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB")
CASH_PROXY = "BIL"
UNIVERSE = tuple(dict.fromkeys(TARGETS + ROTATION + (CASH_PROXY,)))


@dataclass(frozen=True)
class Panel:
    """Prix ajustés (splits et dividendes), une colonne par symbole, index = jour de bourse."""

    open: pd.DataFrame
    high: pd.DataFrame
    low: pd.DataFrame
    close: pd.DataFrame
    volume: pd.DataFrame

    @property
    def dates(self):
        return self.close.index

    def truncate(self, last_date):
        """Vue du panel telle qu'elle était connue à la clôture de `last_date`."""
        last_date = pd.Timestamp(last_date)
        return Panel(*(getattr(self, f).loc[:last_date] for f in ("open", "high", "low", "close", "volume")))


def load_panel(symbols=None, end=DEV_END, allow_holdout=False, path=DATA_FILE):
    """Charge le panel. La période de validation reste inaccessible sans demande explicite."""
    end = pd.Timestamp(end)
    if end > pd.Timestamp(DEV_END) and not allow_holdout:
        raise PermissionError("Période de validation 2025-2026 verrouillée : voir le protocole")
    frame = pd.read_parquet(path)
    frame = frame[frame.date <= end]
    if symbols is not None:
        frame = frame[frame.symbol.isin(symbols)]
    wide = {f: frame.pivot(index="date", columns="symbol", values=f).sort_index() for f in ("open", "high", "low", "close", "volume")}
    return Panel(**wide)


@dataclass(frozen=True)
class Result:
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series


def _exit_rows(exits, panel, window):
    """Pour chaque colonne, ligne de `window` où le titre sort, et rendement de sa dernière période.

    Renvoie (positions, rendements). Position : len(window) si le titre ne sort pas dans la
    fenêtre, -1 s'il est déjà sorti avant. Rendement : NaN si le titre ne sort pas.
    """
    values = exits.reindex(panel.close.columns).to_numpy(dtype=float)
    close = panel.close.to_numpy()
    valid = np.isfinite(close)
    last = close.shape[0] - 1 - valid[::-1].argmax(axis=0)
    columns = np.arange(close.shape[1])
    mark = panel.open.ffill().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        final = close[last, columns] / mark[last, columns] * (1 + values) - 1
    leaving = np.isfinite(values) & valid.any(axis=0) & np.isfinite(final)
    last_dates = panel.dates[last]
    positions = np.full(close.shape[1], len(window))
    inside = window.get_indexer(last_dates)
    positions[leaving & (inside >= 0)] = inside[leaving & (inside >= 0)]
    positions[leaving & (last_dates < window[0])] = -1
    return positions, np.where(leaving, final, np.nan)


def backtest(weights, panel, start=DEV_START, end=DEV_END, cost_bps=DEFAULT_COST_BPS, cash_returns=None, allow_short=False, max_gross=1.0, exits=None):
    """Simule un portefeuille pondéré, de l'ouverture du premier jour à la dernière ouverture.

    Le coût par côté s'applique à chaque montant échangé, y compris l'entrée initiale et
    la liquidation finale. Entre deux décisions, les poids dérivent avec les prix.
    La dernière période n'existe que si l'ouverture du lendemain est connue.

    `cost_bps` : un nombre, ou un DataFrame dates x colonnes donnant le coût d'une exécution
    à l'ouverture de chaque date.

    `exits` (Series colonne -> rendement de sortie, NaN si le titre ne sort pas) active le
    mode « cycle de vie », pour un univers dont des titres disparaissent. `panel` doit alors
    être complet : limiter la période avec `end`, pas avec `truncate`, car la sortie d'un titre
    se déduit de son dernier cours connu. Tout est vendu à la dernière ouverture <= `end`.
    - À travers un trou de cotation, la position garde sa dernière ouverture connue.
    - À la dernière séance L du titre, la période rapporte close(L) / ouverture * (1 + sortie) - 1,
      sans frais ; le produit reste ensuite en liquidités.
    - Sans ouverture valide à la date d'exécution, ni achat ni vente : la position reste telle
      quelle, et les autres cibles sont réduites si la somme dépasse le maximum autorisé.
    """
    raw = weights.reindex(panel.dates)
    no_order = raw.isna().all(axis=1)
    weights = raw.reindex(columns=panel.open.columns).fillna(0.0)
    if not np.isfinite(weights.to_numpy()).all():
        raise ValueError("Poids non finis")
    if not allow_short and (weights.to_numpy() < -1e-12).any():
        raise ValueError("Vente à découvert non autorisée")
    if (weights.abs().sum(axis=1) > max_gross + 1e-9).any():
        raise ValueError("Levier non autorisé")
    per_asset_cost = isinstance(cost_bps, pd.DataFrame)
    if not per_asset_cost and not 0 <= cost_bps < 10_000:
        raise ValueError("Coût invalide")
    lifecycle = exits is not None
    if lifecycle and allow_short:
        raise ValueError("Vente à découvert non gérée en mode cycle de vie")

    # Sans cycle de vie, un prix manquant reste manquant : le contrôle plus bas le refuse.
    mark = panel.open.ffill() if lifecycle else panel.open
    period_return = mark.shift(-1) / mark - 1
    applied = weights.shift(1).fillna(0.0)
    hold = no_order.shift(1, fill_value=True)
    # Une entrée au milieu d'un cycle reprend la dernière décision connue au départ.
    last_order = weights.where(~no_order).ffill().fillna(0.0).shift(1).fillna(0.0)
    window = panel.dates[(panel.dates >= pd.Timestamp(start)) & (panel.dates <= pd.Timestamp(end))]
    # La dernière ouverture de la fenêtre sert à vendre : aucun prix postérieur à `end` n'est lu.
    if lifecycle:
        window = window[:-1]
    # Seule la fin de série peut manquer d'ouverture suivante. Un trou interne reste visible :
    # le contrôle ci-dessous refuse alors toute position impossible à valoriser.
    priced = period_return.index[period_return.notna().any(axis=1)]
    window = window[window <= priced.max()] if len(priced) else window[:0]
    if len(window) == 0:
        raise ValueError("Fenêtre vide")

    r = period_return.loc[window].to_numpy()
    w = applied.loc[window].to_numpy().copy()
    hold_flags = hold.loc[window].to_numpy()
    w[0] = last_order.loc[window[0]].to_numpy()
    priced_flags = np.isfinite(r)
    r = np.nan_to_num(r)
    cash = np.zeros(len(window)) if cash_returns is None else cash_returns.reindex(window).fillna(0.0).to_numpy()
    if per_asset_cost:
        c = cost_bps.reindex(index=window, columns=weights.columns).to_numpy() / 10_000
        if not ((c >= 0) & (c < 1)).all():
            raise ValueError("Coût invalide")
    else:
        c = cost_bps / 10_000
    if lifecycle:
        executable = np.isfinite(panel.open.loc[window].to_numpy())
        exit_rows, exit_final = _exit_rows(exits, panel, window)
        leaving = np.flatnonzero(exit_rows < len(window))
        leaving = leaving[exit_rows[leaving] >= 0]
        r[exit_rows[leaving], leaving] = exit_final[leaving]

    out, turns = np.zeros(len(window)), np.zeros(len(window))
    drifted = np.zeros(w.shape[1])
    for i in range(len(window)):
        if i > 0 and hold_flags[i]:
            w[i] = drifted
        elif lifecycle:
            w[i] = _executable_target(w[i], drifted, executable[i], i > exit_rows, max_gross)
        if not lifecycle and (~priced_flags[i] & (np.abs(w[i]) > 1e-12)).any():
            raise ValueError("Position sur un actif sans prix d'exécution")
        traded_amount = np.abs(w[i] - drifted)
        turn = traded_amount.sum()
        fee = (c[i] * traded_amount).sum() if per_asset_cost else c * turn
        gross = (w[i] * r[i]).sum() + (1 - w[i].sum()) * cash[i]
        growth = 1 + gross
        out[i] = (1 - fee) * growth - 1
        turns[i] = turn
        drifted = w[i] * (1 + r[i]) / growth if growth > 0 else np.zeros(w.shape[1])
        if lifecycle:
            drifted[exit_rows == i] = 0.0
    final_turn = np.abs(drifted).sum()
    if per_asset_cost:
        # La liquidation s'exécute à l'ouverture qui suit la dernière ligne : c'est son coût qui s'applique.
        last_open = panel.dates[panel.dates.get_loc(window[-1]) + 1]
        final_cost = cost_bps.loc[last_open].reindex(weights.columns).to_numpy() / 10_000
        if not ((final_cost >= 0) & (final_cost < 1)).all():
            raise ValueError("Coût invalide")
        final_fee = (final_cost * np.abs(drifted)).sum()
    else:
        final_fee = c * final_turn
    out[-1] = (1 + out[-1]) * (1 - final_fee) - 1
    turns[-1] += final_turn
    index = pd.DatetimeIndex(window, name="date")
    return Result(pd.Series(out, index=index, name="return"), pd.DataFrame(w, index=index, columns=weights.columns), pd.Series(turns, index=index, name="turnover"))


def _executable_target(target, drifted, executable, gone, max_gross):
    """Cible réellement atteignable à l'ouverture, en mode cycle de vie."""
    result = target.copy()
    result[gone] = 0.0
    blocked = ~executable & ~gone
    result[blocked] = drifted[blocked]
    room = max_gross - drifted[blocked].sum()
    wanted = result[~blocked].sum()
    if wanted > room:
        result[~blocked] *= max(room, 0.0) / wanted
    return result


def window_final_capital(weights, panel, start, end, cost_bps=DEFAULT_COST_BPS, capital=INITIAL_CAPITAL):
    """Capital d'un nouvel investissement sur [start, end], vendu au plus tard à la dernière
    ouverture de la fenêtre : aucun prix postérieur à `end` n'est utilisé.

    Le portefeuille démarre sur le dernier ordre connu au départ. Pour les règles à bande,
    le signal continue de suivre son portefeuille fictif lancé au début de l'historique.
    """
    returns = backtest(weights, panel.truncate(end), start=start, end=end, cost_bps=cost_bps).returns
    return capital * float((1 + returns).prod())


def buy_hold_weights(panel, symbol):
    return pd.DataFrame({symbol: 1.0}, index=panel.dates).reindex(columns=panel.open.columns).fillna(0.0)


def summarize(result, capital=INITIAL_CAPITAL):
    r = result.returns
    equity = capital * (1 + r).cumprod()
    peak = np.maximum.accumulate(np.r_[capital, equity.to_numpy()])
    years = len(r) / TRADING_DAYS
    cagr = (equity.iloc[-1] / capital) ** (1 / years) - 1
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    downside = np.sqrt((np.minimum(r, 0) ** 2).mean()) * np.sqrt(TRADING_DAYS)
    max_dd = (np.r_[capital, equity.to_numpy()] / peak - 1).min()
    return {
        "final_capital": float(equity.iloc[-1]),
        "total_return": float(equity.iloc[-1] / capital - 1),
        "cagr": float(cagr),
        "volatility": float(vol),
        "sharpe": float(r.mean() * TRADING_DAYS / vol) if vol > 0 else 0.0,
        "sortino": float(r.mean() * TRADING_DAYS / downside) if downside > 0 else 0.0,
        "max_drawdown": float(max_dd),
        "calmar": float(cagr / -max_dd) if max_dd < 0 else 0.0,
        "exposure": float(result.weights.sum(axis=1).mean()),
        "turnover_per_year": float(result.turnover.sum() / years),
    }


def _stationary_indices(n, n_boot, mean_block, rng):
    """Indices du bootstrap stationnaire (blocs de longueur aléatoire, pour garder l'autocorrélation)."""
    idx = np.empty((n_boot, n), dtype=np.int64)
    idx[:, 0] = rng.integers(0, n, n_boot)
    restart = rng.random((n_boot, n)) < 1 / mean_block
    fresh = rng.integers(0, n, (n_boot, n))
    for t in range(1, n):
        idx[:, t] = np.where(restart[:, t], fresh[:, t], (idx[:, t - 1] + 1) % n)
    return idx


def _fit_alpha(sample_s, sample_b):
    """Intercept annualisé et pente de la régression, réestimés sur chaque échantillon."""
    ds = sample_s - sample_s.mean(axis=-1, keepdims=True)
    db = sample_b - sample_b.mean(axis=-1, keepdims=True)
    var = (db * db).sum(axis=-1)
    slope = np.divide((ds * db).sum(axis=-1), var, out=np.zeros_like(var, dtype=float), where=var > 1e-15)
    return (sample_s.mean(axis=-1) - slope * sample_b.mean(axis=-1)) * TRADING_DAYS, slope


def log_return(returns):
    """Log-rendement, borné : une perte de 100 % donnerait -inf et rendrait toute statistique indéfinie."""
    return np.log1p(np.maximum(returns, -1 + 1e-9))


def compare(strategy, benchmark, n_boot=4000, mean_block=21, seed=0):
    """Compare deux séries appariées : écart de rendement, écart de Sharpe et alpha.

    L'écart absolu est annualisé en log-rendement. La p-value est unilatérale, pour
    l'hypothèse « la stratégie n'apporte rien ».
    """
    pair = pd.concat([strategy, benchmark], axis=1, join="inner").dropna().to_numpy()
    s, b = pair[:, 0], pair[:, 1]
    diff = log_return(s) - log_return(b)
    rng = np.random.default_rng(seed)
    idx = _stationary_indices(len(diff), n_boot, mean_block, rng)
    draws = diff[idx].mean(axis=1) * TRADING_DAYS

    def sharpe(x, axis=None):
        # Rendements constants : Sharpe nul par convention, comme dans `summarize`.
        mean, std = x.mean(axis=axis), x.std(axis=axis, ddof=1)
        return np.divide(mean, std, out=np.zeros_like(mean, dtype=float), where=std > 1e-15) * np.sqrt(TRADING_DAYS)

    sharpe_draws = sharpe(s[idx], axis=1) - sharpe(b[idx], axis=1)
    alpha_point, beta = _fit_alpha(s, b)
    alpha_draws, _ = _fit_alpha(s[idx], b[idx])
    excess = diff.mean() * TRADING_DAYS
    return {
        "annual_log_excess": float(excess),
        "excess_ci95": np.quantile(draws, [0.025, 0.975]).tolist(),
        "excess_p_one_sided": float(((draws - excess) >= excess).mean()),
        "sharpe_difference": float(sharpe(s) - sharpe(b)),
        "sharpe_diff_ci95": np.quantile(sharpe_draws, [0.025, 0.975]).tolist(),
        "sharpe_diff_p_one_sided": float(((sharpe_draws - (sharpe(s) - sharpe(b))) >= sharpe(s) - sharpe(b)).mean()),
        "beta": float(beta),
        "annual_alpha": float(alpha_point),
        "alpha_ci95": np.quantile(alpha_draws, [0.025, 0.975]).tolist(),
        "alpha_p_one_sided": float(((alpha_draws - alpha_point) >= alpha_point).mean()),
    }


def romano_wolf(excess, n_boot=4000, mean_block=21, seed=0):
    """p-values ajustées pour les comparaisons multiples (Romano-Wolf, pas à pas).

    Corrige le biais « on a essayé beaucoup de stratégies et on garde la meilleure ».
    `excess` : DataFrame jours × essais des écarts de log-rendement au benchmark.
    """
    frame = excess.dropna()
    values = frame.to_numpy()
    n = len(values)
    mean = values.mean(axis=0)
    std = values.std(axis=0, ddof=1)
    # Écart constant : aucune incertitude. Statistique infinie de son signe, nulle sous l'hypothèse nulle.
    constant = std <= 1e-15
    safe_std = np.where(constant, 1.0, std)
    stat = np.where(constant, np.where(mean > 1e-15, np.inf, np.where(mean < -1e-15, -np.inf, 0.0)), mean / safe_std * np.sqrt(n))
    rng = np.random.default_rng(seed)
    idx = _stationary_indices(n, n_boot, mean_block, rng)
    null = np.stack([np.where(constant, 0.0, (values[idx[b]].mean(axis=0) - mean) / safe_std * np.sqrt(n)) for b in range(n_boot)])
    return pd.Series(_step_down(stat, null), index=frame.columns, name="romano_wolf_p")


def _step_down(stat, null):
    """Étape commune de Romano-Wolf : du résultat le plus fort au plus faible."""
    order = np.argsort(-stat)
    adjusted = np.zeros(len(stat))
    running = 0.0
    for rank, col in enumerate(order):
        remaining = order[rank:]
        p = float((null[:, remaining].max(axis=1) >= stat[col]).mean())
        running = max(running, p)
        adjusted[col] = running
    return adjusted


def romano_wolf_alpha(strategies, benchmarks, n_boot=4000, mean_block=21, seed=0):
    """p-values de l'alpha ajustées pour les essais multiples, beta réestimé à chaque tirage.

    Tous les essais partagent les mêmes blocs de jours. Les deux tableaux ont les mêmes
    colonnes ; chaque essai a sa propre référence.
    """
    columns = list(strategies.columns)
    both = pd.concat([strategies[columns], benchmarks[columns].add_suffix("__ref")], axis=1).dropna()
    n = len(both)
    rng = np.random.default_rng(seed)
    idx = _stationary_indices(n, n_boot, mean_block, rng)
    stat, null = np.zeros(len(columns)), np.zeros((n_boot, len(columns)))
    for j, column in enumerate(columns):
        s, b = both[column].to_numpy(), both[f"{column}__ref"].to_numpy()
        point, _ = _fit_alpha(s, b)
        draws, _ = _fit_alpha(s[idx], b[idx])
        scale = draws.std(ddof=1)
        if scale > 1e-12:
            stat[j], null[:, j] = point / scale, (draws - point) / scale
        else:
            # Alpha sans incertitude : statistique infinie de son signe, comme dans romano_wolf.
            stat[j] = np.inf if point > 1e-15 else (-np.inf if point < -1e-15 else 0.0)
    return pd.Series(_step_down(stat, null), index=columns, name="romano_wolf_alpha_p")


def check_no_lookahead(strategy_fn, panel, cutoffs=None, tolerance=1e-10):
    """Vérifie qu'une décision passée ne change pas quand on retire les données futures."""
    full = strategy_fn(panel)
    if cutoffs is None:
        positions = np.linspace(0.4, 0.95, 5) * len(panel.dates)
        cutoffs = [panel.dates[int(p)] for p in positions]
    for cutoff in cutoffs:
        partial = strategy_fn(panel.truncate(cutoff))
        past = full.loc[:cutoff]
        if not past.index.equals(partial.index):
            raise AssertionError(f"Dates de décision différentes à la date {cutoff.date()}")
        if not past.isna().all(axis=1).equals(partial.isna().all(axis=1)):
            raise AssertionError(f"Jours d'ordre différents à la date {cutoff.date()}")
        # Une colonne présente d'un seul côté compte comme un poids nul de l'autre.
        columns = past.columns.union(partial.columns)
        left = past.reindex(columns=columns).fillna(0.0).to_numpy()
        right = partial.reindex(columns=columns).fillna(0.0).to_numpy()
        if np.abs(left - right).max() > tolerance:
            raise AssertionError(f"Fuite d'information détectée à la date {cutoff.date()}")
    return True


def record_trial(owner, name, family, params, result, benchmark_symbol, benchmark_returns, extra=None):
    """Inscrit chaque essai au journal, réussi ou non : le nombre d'essais doit rester connu."""
    folder = LAB_DIR / "trials" / owner
    folder.mkdir(parents=True, exist_ok=True)
    result.returns.to_frame().to_parquet(folder / f"{name}.parquet")
    row = {"owner": owner, "name": name, "family": family, "params": json.dumps(params, sort_keys=True), "benchmark": benchmark_symbol, **summarize(result), **{k: v for k, v in compare(result.returns, benchmark_returns, n_boot=1000).items() if not k.endswith("ci95")}, **(extra or {})}
    ledger = LAB_DIR / f"ledger_{owner}.csv"
    frame = pd.DataFrame([row])
    if ledger.exists():
        old = pd.read_csv(ledger)
        frame = pd.concat([old[old.name != name], frame], ignore_index=True)
    frame.to_csv(ledger, index=False)
    return row
