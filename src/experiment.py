"""Enchaîne une expérience sur le grand univers : une nouvelle idée tient en une fonction de poids.

    from experiment import run_experiment, top_n
    from universe_data import load_universe

    def momentum(data, lookback=252, top=50):
        score = data.close.pct_change(lookback, fill_method=None)
        return top_n(score, n=top, tradable=data.tradable)

    market = load_universe()
    table = run_experiment(momentum, market, name="momentum", family="heuristic", lookback=[126, 252])

Une stratégie reçoit `market.data` à la clôture de chaque jour et renvoie un DataFrame de poids
(dates x titres). Une ligne vide signifie « aucun ordre ». Elle ne décale jamais ses poids : le moteur
exécute à l'ouverture suivante. Elle ne reçoit ni les sorties ni les métadonnées, qui révèlent l'avenir.

Chaque variante passe le contrôle anti-fuite, puis le moteur sous les trois hypothèses de sortie, et
est inscrite au journal, réussie ou non. Toutes les variantes sont comparées à SPY et à un portefeuille
tiré au hasard. Vocabulaire : voir `lab.py`.
"""

import itertools
from functools import partial

import numpy as np
import pandas as pd

import lab

EXIT_SCENARIOS = ("base", "optimistic", "pessimistic")
REFERENCE = "SPY"


def month_starts(index):
    """Vrai au premier jour de bourse de chaque mois : ne dépend d'aucune date future."""
    months = index.to_period("M")
    return pd.Series(np.r_[True, months[1:] != months[:-1]], index=index)


def top_n(score, n, tradable, rebalance=month_starts):
    """Poids égaux sur les `n` meilleurs scores parmi les titres achetables.

    `rebalance(index)` donne les jours de décision, les autres lignes restent vides (aucun ordre).
    Un jour sans aucun candidat donne une ligne de zéros : tout est vendu.
    """
    chosen = score.where(tradable).rank(axis=1, ascending=False, method="first") <= n
    weights = chosen.astype(float).div(chosen.sum(axis=1).clip(lower=1), axis=0)
    return weights.where(rebalance(score.index), axis=0)


def random_like(weights, tradable, seed):
    """Même calendrier d'ordres et mêmes poids que `weights`, sur des titres achetables tirés au hasard."""
    rng = np.random.default_rng(seed)
    matrix = weights.reindex(index=tradable.index, columns=tradable.columns).to_numpy()
    allowed = tradable.to_numpy()
    out = np.full(matrix.shape, np.nan)
    for i in np.flatnonzero(~np.isnan(matrix).all(axis=1)):
        row = np.nan_to_num(matrix[i])
        held = row[row != 0]
        candidates = np.flatnonzero(allowed[i])
        out[i] = 0.0
        size = min(len(held), len(candidates))
        out[i, rng.choice(candidates, size, replace=False)] = rng.permutation(held)[:size]
    return pd.DataFrame(out, index=tradable.index, columns=tradable.columns)


def untradable_share(weights, tradable):
    """Part du poids visé sur des titres non achetables : doit être nulle sauf choix délibéré."""
    aligned = weights.reindex(index=tradable.index, columns=tradable.columns).fillna(0.0)
    total = aligned.abs().to_numpy().sum()
    return float(aligned.where(~tradable, 0.0).abs().to_numpy().sum() / total) if total else 0.0


def expand_grid(grid):
    """{"a": [1, 2], "b": 3} donne [{"a": 1, "b": 3}, {"a": 2, "b": 3}]."""
    lists = {k: v if isinstance(v, (list, tuple)) else [v] for k, v in grid.items()}
    return [dict(zip(lists, values)) for values in itertools.product(*lists.values())]


def variant_name(name, params):
    return "__".join([name, *(f"{k}={v}" for k, v in sorted(params.items()))])


def run_variant(weights, market, start, end, n_random=20, seed=0):
    """Mesures d'une variante déjà calculée. Renvoie le résultat central, la référence et les extras."""
    data = market.data
    run = partial(lab.backtest, panel=data, start=start, end=end)
    results = {s: run(weights, cost_bps=data.cost_bps, exits=market.exits[s]) for s in EXIT_SCENARIOS}
    # Même fenêtre que la stratégie : une série de sorties vide suffit à activer ce mode.
    benchmark = lab.backtest(lab.buy_hold_weights(market.benchmarks, REFERENCE), market.benchmarks, start=start, end=end, exits=pd.Series(dtype=float))
    random_final = [lab.summarize(run(random_like(weights, data.tradable, seed + k), cost_bps=data.cost_bps, exits=market.exits["base"]))["final_capital"] for k in range(n_random)]
    final = {s: lab.summarize(results[s])["final_capital"] for s in EXIT_SCENARIOS}
    doubled = lab.summarize(run(weights, cost_bps=data.cost_bps * 2, exits=market.exits["base"]))["final_capital"]
    bench = lab.summarize(benchmark)
    extra = {
        "final_capital_optimistic": final["optimistic"],
        "final_capital_pessimistic": final["pessimistic"],
        "final_capital_cost_x2": doubled,
        "benchmark_final": bench["final_capital"],
        "benchmark_sharpe": bench["sharpe"],
        "benchmark_max_drawdown": bench["max_drawdown"],
        "random_final_median": float(np.median(random_final)) if random_final else float("nan"),
        "random_share_beaten": float((np.array(random_final) < final["base"]).mean()) if random_final else float("nan"),
        "n_random": n_random,
        "untradable_share": untradable_share(weights, data.tradable),
        "start": str(pd.Timestamp(start).date()),
        "end": str(pd.Timestamp(end).date()),
    }
    return results["base"], benchmark, extra


def adjusted_p_values(owner, benchmark_returns):
    """p de Romano-Wolf contre la référence, sur TOUS les essais du journal de `owner`."""
    folder = lab.LAB_DIR / "trials" / owner
    excess = {}
    for path in sorted(folder.glob("*.parquet")):
        returns = pd.read_parquet(path)["return"]
        excess[path.stem] = lab.log_return(returns) - lab.log_return(benchmark_returns.reindex(returns.index))
    return lab.romano_wolf(pd.DataFrame(excess))


def run_experiment(strategy, market, name, family, owner="universe", start=lab.DEV_START, end=lab.DEV_END, n_random=20, seed=0, lookahead_check=True, **grid):
    """Évalue toutes les combinaisons de paramètres de `grid` et les inscrit au journal.

    Chaque liste de `grid` est un paramètre à balayer. Renvoie un tableau par variante. Le fichier
    `reports/lab_2026-11/experiments/<name>.csv` garde ce tableau, avec la p corrigée sur tout le journal.
    """
    if pd.Timestamp(end) > pd.Timestamp(lab.DEV_END):
        raise PermissionError("Période de validation 2025-2026 verrouillée : voir le protocole")
    rows, benchmark = [], None
    for params in expand_grid(grid):
        trial = variant_name(name, params)
        fn = partial(strategy, **params)
        if lookahead_check:
            lab.check_no_lookahead(fn, market.data)
        result, benchmark, extra = run_variant(fn(market.data), market, start, end, n_random, seed)
        rows.append(lab.record_trial(owner, trial, family, params, result, REFERENCE, benchmark.returns, extra=extra))
    table = pd.DataFrame(rows).set_index("name")
    table["romano_wolf_p"] = adjusted_p_values(owner, benchmark.returns).reindex(table.index)
    folder = lab.LAB_DIR / "experiments"
    folder.mkdir(exist_ok=True)
    table.to_csv(folder / f"{name}.csv")
    return table
