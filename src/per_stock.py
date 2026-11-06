"""Applique une règle à chaque action et la compare au buy and hold de cette même action.

Une règle reçoit `data` et renvoie, par date et par titre, 1 pour être investi, 0 pour être en
liquidités, NaN pour ne rien changer. Chaque action forme son propre petit portefeuille, sans argent
partagé, selon les règles de `lab.backtest` : décision à la clôture, exécution à l'ouverture suivante
si elle est possible, frais selon la liquidité, sortie à la disparition du titre.

La moyenne des capitaux finaux est le résultat d'un portefeuille qui répartit l'argent à parts égales
au départ, sans jamais le déplacer d'une action à l'autre.
"""

import numpy as np
import pandas as pd

import lab
from reference import month_start_rows


class Simulator:
    """Calculs communs à toutes les dates d'achat d'une même règle."""

    def __init__(self, signal, market, cost_multiplier=1.0, cash_returns=None):
        data = market.data
        self.columns = data.close.columns
        self.dates = data.dates
        self.signal = signal.reindex(index=self.dates, columns=self.columns).to_numpy(dtype=float)
        opens, closes = data.open.to_numpy(), data.close.to_numpy()
        marks = data.open.ffill().to_numpy()
        self.valid_open = np.isfinite(opens)
        self.marks, self.closes = marks, closes
        self.costs = data.cost_bps.to_numpy() / 10_000 * cost_multiplier
        self.last_row = closes.shape[0] - 1 - np.isfinite(closes)[::-1].argmax(axis=0)
        self.exits = market.exits.reindex(self.columns)
        # Position pendant la période t : l'ordre de la veille s'il est exécutable, sinon celle d'avant.
        wanted = np.full(self.signal.shape, np.nan)
        wanted[1:] = np.where(self.valid_open[1:], self.signal[:-1], np.nan)
        self.position = pd.DataFrame(wanted).ffill().fillna(0.0).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            growth = marks[1:] / marks[:-1]
        self.growth = np.where(np.isfinite(growth), growth, 1.0)
        # Rendement des liquidités sur la période t. Par défaut 0 %, comme dans le protocole.
        cash = np.zeros(len(self.dates)) if cash_returns is None else cash_returns.reindex(self.dates).fillna(0.0).to_numpy()
        self.cash = cash[:-1][:, None]

    def eligible(self, start):
        """Peut-on comparer la règle et le buy and hold pour cet achat ? Signal connu et ouverture valide."""
        return np.isfinite(self.signal[start - 1]) & self.valid_open[start]

    def paths(self, start, end, cols, scenario="base", always_invested=False):
        """Capital de chaque titre après chaque période de [start, end[ ; lignes = périodes, base 1.

        La dernière ligne inclut la vente finale à l'ouverture de `end`.
        """
        rows = np.arange(start, end)
        held = np.ones((len(rows), len(cols))) if always_invested else self.position[start:end][:, cols].copy()
        previous = np.vstack([np.zeros(len(cols)), held[:-1]])
        costs = self.costs[start:end][:, cols]
        cash = self.cash[start:end]
        factors = (held * self.growth[start:end][:, cols] + (1 - held) * (1 + cash)) * (1 - costs * np.abs(held - previous))
        exit_values = self.exits[scenario].to_numpy()[cols]
        last = self.last_row[cols]
        leaves = np.isfinite(exit_values) & (last < end)
        for j in np.flatnonzero(leaves):
            row = last[j] - start
            column = cols[j]
            final = self.closes[last[j], column] / self.marks[last[j], column] * (1 + exit_values[j])
            factors[row, j] = (final if held[row, j] else 1 + cash[row, 0]) * (1 - costs[row, j] * abs(held[row, j] - previous[row, j]))
            factors[row + 1:, j] = 1 + cash[row + 1:, 0]
            held[row + 1:, j] = 0.0   # après la sortie, l'argent est en liquidités
        wealth = np.cumprod(factors, axis=0)
        wealth[-1] *= np.where(leaves, 1.0, 1 - self.costs[end, cols] * held[-1])
        return wealth, leaves, held


def rule_table(simulator, starts, horizons):
    """Multiple de la règle par titre, date d'achat et horizon, sous les trois hypothèses de sortie."""
    months = month_start_rows(simulator.dates)
    periods = simulator.dates.to_period("M")
    frames = []
    for start in starts:
        cols = np.flatnonzero(simulator.eligible(start))
        if not len(cols):
            continue
        for horizon in horizons:
            if horizon == -1:
                end = len(simulator.dates) - 1
            else:
                later = months[periods[months] == periods[start] + horizon]
                if not len(later):
                    continue
                end = later[0]
            wealth, _, held = simulator.paths(start, end, cols)
            frame = {"start": simulator.dates[start], "horizon": horizon, "security_id": np.asarray(simulator.columns)[cols], "rule_base": wealth[-1], "invested_share": held.mean(axis=0), "switches": np.abs(np.diff(held, axis=0)).sum(axis=0)}
            for scenario in ("optimistic", "pessimistic"):
                frame[f"rule_{scenario}"] = simulator.paths(start, end, cols, scenario)[0][-1]
            frames.append(pd.DataFrame(frame))
    return pd.concat(frames, ignore_index=True)


def risk_by_stock(wealth):
    """Sharpe et pire chute de chaque titre, à partir de ses chemins de capital."""
    full = np.vstack([np.ones(wealth.shape[1]), wealth])
    with np.errstate(divide="ignore", invalid="ignore"):
        returns = full[1:] / full[:-1] - 1
        returns = np.where(np.isfinite(returns), returns, 0.0)
        std = returns.std(axis=0, ddof=1)
        sharpe = np.where(std > 1e-12, returns.mean(axis=0) / std * np.sqrt(lab.TRADING_DAYS), 0.0)
    drawdown = (full / np.maximum.accumulate(full, axis=0) - 1).min(axis=0)
    return sharpe, drawdown


def equal_weight_result(wealth, held, leaves, dates):
    """Résultat du portefeuille à parts égales, exposition et rotation pondérées en dollars.

    Une sortie n'est pas une vente : elle ne compte pas dans la rotation. Après la période finale, ce
    qui est encore en position est vendu à la dernière ouverture.
    """
    before = np.vstack([np.ones(wealth.shape[1]), wealth[:-1]])
    total = before.sum(axis=1)
    exposure = (before * held).sum(axis=1) / total
    previous = np.vstack([np.zeros(held.shape[1]), held[:-1]])
    # La ligne qui suit une sortie remet held à 0 sans transaction.
    gone = (held == 0) & (previous == 1) & (np.cumsum(held[::-1], axis=0)[::-1] == 0) & leaves[None, :]
    turnover = (before * np.abs(held - previous) * ~gone).sum(axis=1) / total
    turnover[-1] += (wealth[-1] * held[-1] * ~leaves).sum() / wealth[-1].sum()
    return lab.Result(equal_weight_returns(wealth, dates), pd.DataFrame({"exposure": exposure}, index=dates), pd.Series(turnover, index=dates, name="turnover"))


def equal_weight_returns(wealth, dates):
    """Rendement quotidien du portefeuille à parts égales au départ, jamais rééquilibré."""
    level = np.r_[1.0, wealth.mean(axis=1)]
    return pd.Series(level[1:] / level[:-1] - 1, index=dates, name="return")
