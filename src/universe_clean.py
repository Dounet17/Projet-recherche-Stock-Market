"""Règles de nettoyage du grand dataset quotidien (fonctions pures, sans lecture de fichier).

Une « série » correspond à un symbole tel que renvoyé par Alpaca. Elle peut contenir plusieurs
sociétés (symbole réutilisé) ou répéter une autre série (changement de nom). Le nettoyage produit
des « titres » (security_id) : une seule société, sans cours fantôme ni doublon.

Vocabulaire : un cours « ajusté » est corrigé des fractionnements et dividendes pour que les
rendements soient comparables dans le temps. Le cours « brut » est celui réellement affiché ce
jour-là : c'est le seul valable pour un filtre de prix ou de liquidité.
"""

import re
from collections import Counter

import numpy as np
import pandas as pd

# Sans échange ce nombre de séances, la série n'est plus considérée comme la même société...
REUSE_ALWAYS_SESSIONS = 252
# ... ou à partir de ces durées, si le prix ajusté change trop à la reprise.
REUSE_RULES = ((60, 0.25), (20, 1.0))
ALIVE_TOLERANCE_SESSIONS = 20
SHORT_SECURITY_DAYS = 20
ALIAS_MIN_SHARE = 0.80
ALIAS_MIN_MATCHES = 5
ALIAS_MAX_GROUP = 30
# Au-delà, le chiffre vient presque toujours d'une erreur de balisage XBRL (montant total, autre devise).
EPS_SUSPECT_ABS = 500

# Symboles techniques des bourses américaines : ce ne sont pas des sociétés.
TEST_SYMBOLS = {"ZVZZT", "ZWZZT", "ZXZZT", "ZAZZT", "ZBZZT", "ZCZZT", "ZJZZT", "ZVV", "ZTST", "NTEST", "ATEST", "PTEST", "CTEST", "ZTEST", "IGZ", "CBO", "CBX", "IBO", "IBKA", "TEST"}
# Banques déposant auprès de la FDIC et non de la SEC : aucun 8-K ne signale leur faillite.
FAILED_BANKS = {"SBNY": "2023-03-12", "FRC": "2023-05-01", "FRCB": "2023-05-01"}

FUND_NAME = re.compile(r"\b(ETF|ETN|ETFs|ETNs|iShares|ProShares|SPDR|Vanguard|Direxion|WisdomTree|VanEck|Global X|First Trust|Exchange[- ]Traded|Funds?|Index|Portfolio|Grayscale|Invesco|Tidal|Roundhill|Innovator|AdvisorShares|Amplify|PIMCO|BlackRock|Nuveen|Eaton Vance|ClearBridge|Income Trust|Commodity|Bitcoin Trust|Ether Trust|Gold Trust|Silver Trust|Oil Trust|MicroSectors|Leverage Shares|GraniteShares|T-Rex|YieldMax|Defiance)\b", re.IGNORECASE)
OPERATING_OVERRIDE = re.compile(r"\b(Inc|Corp|Corporation|Ltd|Limited|PLC|Holdings?|N\.V\.|S\.A\.)\b\.?(?!.*\b(ETF|ETN|Fund|iShares)\b)", re.IGNORECASE)
PREFERRED_NAME = re.compile(r"\b(Preferred|Pref|Depositary (Shares|Share) .*(Series|%)|Series [A-Z]\b.*(Shares|Stock)|Notes?|Debentures?|Senior|Subordinated|Bonds?)\b|\d+(\.\d+)?\s?%", re.IGNORECASE)
DERIVATIVE_NAME = re.compile(r"\b(warrants?|rights?|units?|contra|escrow|CVR)\b", re.IGNORECASE)
ADR_NAME = re.compile(r"\b(American Depositary|ADS|ADR|Sponsored)\b", re.IGNORECASE)
SPAC_NAME = re.compile(r"\b(Acquisition|Merger|Blank Check|SPAC)\b", re.IGNORECASE)
FUND_SIC = {"6221", "6722", "6726"}
FUND_FORMS = ("N-CEN", "N-CSR", "NPORT-P")


def _runs_of_zero_volume(panel):
    """Une ligne par suite de séances sans échange, avec sa position dans la série."""
    zero = panel.volume.to_numpy() == 0
    symbols = panel.symbol.to_numpy()
    new_symbol = np.r_[True, symbols[1:] != symbols[:-1]]
    change = new_symbol | np.r_[True, zero[1:] != zero[:-1]]
    run = np.cumsum(change) - 1
    frame = pd.DataFrame({"run": run[zero], "position": np.flatnonzero(zero)})
    runs = frame.groupby("run").position.agg(first_position="min", last_position="max")
    runs["sessions"] = runs.last_position - runs.first_position + 1
    return runs.reset_index(drop=True)


def split_segments(panel):
    """Retire les cours fantômes et découpe les symboles réutilisés.

    `panel` est trié par symbole et date, avec les colonnes symbol, ts_utc, adj_close, volume
    (brut). Une séance à volume brut nul est un cours recopié par Alpaca. Une suite courte, encadrée
    d'échanges, est conservée (titre peu échangé) ; le début et la fin d'une série sans échange sont
    retirés ; une longue suite coupe la série en deux titres.
    Renvoie le panel réduit avec `segment`, et la liste des coupures.
    """
    panel = panel.reset_index(drop=True)
    symbols = panel.symbol.to_numpy()
    positions = np.arange(len(panel))
    first_of_symbol = pd.Series(positions).groupby(symbols, sort=False).transform("min").to_numpy()
    last_of_symbol = pd.Series(positions).groupby(symbols, sort=False).transform("max").to_numpy()
    adjusted = panel.adj_close.to_numpy()
    runs = _runs_of_zero_volume(panel)
    if runs.empty:
        panel["segment"] = 0
        panel["traded"] = True
        return panel, pd.DataFrame(columns=["symbol", "last_before", "first_after", "sessions", "adj_jump", "reason"])
    start, stop = runs.first_position.to_numpy(), runs.last_position.to_numpy()
    leading = start == first_of_symbol[start]
    trailing = stop == last_of_symbol[stop]
    interior = ~leading & ~trailing
    # Le saut est calculé sur le cours ajusté : un fractionnement pendant le trou n'est pas un saut.
    before, after = adjusted[np.maximum(start - 1, 0)], adjusted[np.minimum(stop + 1, len(panel) - 1)]
    with np.errstate(divide="ignore", invalid="ignore"):
        jump = np.abs(np.log(after / before))
    sessions = runs.sessions.to_numpy()
    cut = sessions >= REUSE_ALWAYS_SESSIONS
    for minimum, threshold in REUSE_RULES:
        cut |= (sessions >= minimum) & ~(jump <= np.log1p(threshold))
    cut &= interior
    keep = np.ones(len(panel), dtype=bool)
    new_segment = np.zeros(len(panel), dtype=bool)
    for begin, end in zip(start[leading | trailing | cut], stop[leading | trailing | cut]):
        keep[begin:end + 1] = False
    new_segment[stop[cut] + 1] = True
    cuts = pd.DataFrame({"symbol": symbols[start[cut]], "last_before": panel.ts_utc.to_numpy()[start[cut] - 1], "first_after": panel.ts_utc.to_numpy()[stop[cut] + 1], "sessions": sessions[cut], "adj_jump": np.exp(jump[cut]) - 1})
    panel["segment"] = pd.Series(new_segment.astype(int)).groupby(symbols, sort=False).cumsum().to_numpy()
    panel["traded"] = panel.volume.to_numpy() > 0
    panel["removed_ghost"] = ~keep
    return panel[keep].drop(columns="removed_ghost").reset_index(drop=True), cuts


def find_aliases(panel, close="close"):
    """Trouve les titres qui sont la même cotation sous deux symboles.

    Le cours ajusté diffère d'un symbole à l'autre (FB et META), mais le brut et le volume brut
    d'une même séance sont identiques. Deux sociétés distinctes n'ont pas le même couple (cours,
    volume) jour après jour. Renvoie les paires retenues avec leur taux de concordance.
    """
    traded = panel[panel.traded]
    codes, labels = pd.factorize(traded.security_id, sort=False)
    day = pd.factorize(traded.ts_utc, sort=False)[0]
    price = np.round(traded[close].to_numpy() * 10000).astype(np.int64)
    volume = traded.volume.to_numpy().astype(np.int64)
    order = np.lexsort((codes, volume, price, day))
    key = np.c_[day[order], price[order], volume[order]]
    boundary = np.r_[True, np.any(key[1:] != key[:-1], axis=1), True]
    edges = np.flatnonzero(boundary)
    sizes = np.diff(edges)
    sorted_codes = codes[order]
    pairs = Counter()
    for begin, size in zip(edges[:-1][(sizes >= 2) & (sizes <= ALIAS_MAX_GROUP)], sizes[(sizes >= 2) & (sizes <= ALIAS_MAX_GROUP)]):
        members = sorted_codes[begin:begin + size]
        for i in range(size):
            for j in range(i + 1, size):
                pairs[(members[i], members[j])] += 1
    candidates = [(a, b, n) for (a, b), n in pairs.items() if n >= ALIAS_MIN_MATCHES]
    days_of = {}
    needed = {c for a, b, _ in candidates for c in (a, b)}
    frame = pd.DataFrame({"code": codes, "day": day})
    for code, group in frame[frame.code.isin(needed)].groupby("code").day:
        days_of[code] = set(group.to_numpy().tolist())
    rows = []
    for a, b, matches in candidates:
        common = len(days_of[a] & days_of[b])
        share = matches / common if common else 0.0
        if share >= ALIAS_MIN_SHARE:
            rows.append((labels[a], labels[b], matches, common, share))
    return pd.DataFrame(rows, columns=["security_a", "security_b", "matches", "common_days", "share"])


def group_aliases(pairs, rank):
    """Regroupe les paires et désigne le titre conservé : le plus de séances échangées d'abord.

    `rank` associe à chaque titre un score (plus grand = préféré).
    """
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in zip(pairs.security_a, pairs.security_b):
        parent[find(a)] = find(b)
    groups = {}
    for member in list(parent):
        groups.setdefault(find(member), []).append(member)
    rows = []
    for members in groups.values():
        keeper = max(members, key=lambda m: (rank.get(m, 0), m))
        rows.extend((member, keeper) for member in members if member != keeper)
    return pd.DataFrame(rows, columns=["dropped", "kept"])


def add_adjusted_returns(prices):
    """Replace le cours ajusté sur le cours brut de fin de titre et calcule le rendement quotidien.

    Le facteur d'ajustement d'Alpaca intègre les opérations postérieures à la période (WHLR affiche
    1e12 en 2016 à cause de regroupements de 2025) et celles d'une autre société dans un symbole
    réutilisé. Seuls les rapports entre deux dates d'un même titre ont du sens : le niveau est donc
    renormalisé, ce qui efface l'information future sans changer les rendements.
    """
    prices = prices.copy()
    grouped = prices.groupby("security_id", sort=False)
    prices["adj_close"] = prices.adj_close * (grouped.close.transform("last") / grouped.adj_close.transform("last"))
    # Les rendements sont calculés entre séances réellement échangées uniquement.
    prices["ret_adj"] = np.nan
    traded = prices[prices.traded]
    returns = traded.groupby("security_id", sort=False).adj_close.pct_change()
    prices.loc[traded.index, "ret_adj"] = returns
    return prices


def flag_suspect_prints(prices, spike=1.0, reversal=-0.5, extreme_rise=3.0, extreme_fall=-0.9):
    """Signale les rendements à ne pas croire sans vérification.

    Hausse d'au moins 100 % effacée à la séance suivante (ou l'inverse), hausse d'au moins 300 % ou
    baisse d'au moins 90 % en une séance. Une sortie de faillite (BCEI +7 600 %) annule les anciennes
    actions et en crée de nouvelles sous le même symbole : ce n'est pas un gain pour l'actionnaire.
    La règle écarte aussi quelques vraies envolées (TPST), ce qui va dans le sens prudent.
    """
    returns = prices.ret_adj
    following = prices.groupby("security_id", sort=False).ret_adj.shift(-1)
    reverted = ((returns >= spike) & (following <= reversal)) | ((returns <= reversal) & (following >= spike))
    return reverted | (returns >= extreme_rise) | (returns <= extreme_fall)


def classify_security(symbol, name, name_trusted, sec_row=None, link_method=None):
    """Type du titre : common, adr, spac, fund, preferred, derivative, test ou unknown.

    Le nom d'Alpaca est celui du détenteur actuel du symbole : `name_trusted` est faux pour une
    ancienne société (l'actuel FB est un fonds ProShares, pas Facebook). Il date aussi de 2026 : LAZR
    est devenu un fonds après 2024. Des dépôts de comptes faits sous ce symbole pendant la cotation
    (`link_method` = "filing_prefix") l'emportent donc sur un nom de fonds.
    """
    if symbol in TEST_SYMBOLS:
        return "test"
    filings = sec_row is not None and (sec_row.get("10-K") or 0) + (sec_row.get("10-Q") or 0) > 0
    if link_method == "filing_prefix" and filings and str(sec_row.get("sic") or "") not in FUND_SIC:
        name_trusted = False
    if name_trusted and isinstance(name, str) and name:
        if DERIVATIVE_NAME.search(name):
            return "derivative"
        if FUND_NAME.search(name) and not (OPERATING_OVERRIDE.search(name) and not re.search(r"\b(ETF|ETN|Fund|iShares|ProShares|Trust)\b", name, re.IGNORECASE)):
            return "fund"
        if PREFERRED_NAME.search(name):
            return "preferred"
    if ".PR" in symbol or ".W" in symbol or ".U" in symbol or ".R" in symbol:
        return "preferred" if ".PR" in symbol else "derivative"
    if sec_row is not None:
        sic = str(sec_row.get("sic") or "")
        if sic in FUND_SIC or any((sec_row.get(form) or 0) > 0 for form in FUND_FORMS):
            return "fund"
        if sic == "6770":
            return "spac"
        if (sec_row.get("20-F") or 0) > 0 or (sec_row.get("40-F") or 0) > 0:
            return "adr"
        if (sec_row.get("10-K") or 0) + (sec_row.get("10-Q") or 0) > 0:
            return "common"
    if name_trusted and isinstance(name, str) and name:
        if SPAC_NAME.search(name):
            return "spac"
        if ADR_NAME.search(name):
            return "adr"
        return "common"
    return "unknown"


def exit_returns(reason, value=None):
    """Rendement de sortie (central, optimiste, pessimiste) selon la cause de disparition.

    Sans cause connue, le titre en difficulté reçoit les pertes moyennes mesurées par Shumway (1997,
    -30 %) et Shumway et Warther (1999, -55 % sur le Nasdaq) ; les trois valeurs servent à mesurer la
    sensibilité d'un résultat à cette hypothèse.
    """
    if reason in {"cash_merger", "stock_merger", "stock_and_cash_merger", "redemption"} and value is not None and np.isfinite(value):
        return value, value, value
    return {
        "worthless": (-1.0, -1.0, -1.0),
        "failed_bank": (-1.0, -1.0, -1.0),
        "bankruptcy": (-1.0, -0.5, -1.0),
        "renamed": (0.0, 0.0, 0.0),
        "relisted": (0.0, 0.0, -0.3),
        "merger_terms_unknown": (0.0, 0.0, -0.3),
        "cash_merger": (0.0, 0.0, -0.3),
        "stock_merger": (0.0, 0.0, -0.3),
        "stock_and_cash_merger": (0.0, 0.0, -0.3),
        "redemption": (0.0, 0.0, -0.3),
        "unknown_distress": (-0.55, -0.3, -1.0),
        "unknown": (0.0, 0.0, -0.3),
    }[reason]


def normalize_name(name):
    """Nom de société comparable entre Alpaca et la SEC."""
    if not isinstance(name, str):
        return ""
    text = re.sub(r"[^a-z0-9 ]", " ", name.lower().replace("&", " and "))
    text = re.sub(r"\b(class|cl|common|stock|shares?|ordinary|american depositary|ads|adr|sponsored|new|the|series [a-z])\b", " ", text)
    text = re.sub(r"\b(incorporated|inc|corporation|corp|company|co|limited|ltd|plc|llc|lp|l p|holdings?|group|n v|nv|s a|sa|de|del|md|ny)\b", " ", text)
    return " ".join(text.split())


def _split_factor(splits, begin, end):
    """Facteur à appliquer à un BPA publié à `begin` pour l'exprimer dans les actions de `end`."""
    if splits is None or len(splits) == 0:
        return 1.0
    inside = splits[(splits.date > begin) & (splits.date <= end)]
    return float(inside.factor.prod()) if len(inside) else 1.0


def reconstruct_quarterly_eps(facts, splits=None):
    """Bénéfice par action trimestriel, 4e trimestre inclus, à partir des faits SEC.

    Les sociétés ne déposent pas de formulaire pour le 4e trimestre : seul l'exercice complet figure
    dans le 10-K. Il est déduit par T4 = exercice - 9 mois, sinon exercice - (T1 + T2 + T3). Le cumul
    sur 9 mois passe d'abord : publié plus tard, il a moins de chances de précéder un fractionnement.
    Tout chiffre publié avant un fractionnement survenu dans l'exercice est remis à l'échelle du 10-K
    (`splits` : cik, date, factor). Cela évite le faux -2,14 de TSLA au T4 2022 (vrai : 1,07).
    La différence reste approximative car le nombre d'actions varie dans l'année. `filed` est la date
    qui rend le chiffre public : aucune décision ne doit l'utiliser avant.
    """
    facts = facts.copy()
    facts["start"] = pd.to_datetime(facts.start)
    facts["end"] = pd.to_datetime(facts.end)
    facts["filed"] = pd.to_datetime(facts.filed)
    facts["days"] = (facts.end - facts.start).dt.days
    facts = facts[facts.value.notna() & facts.days.notna()]
    by_cik = {cik: group for cik, group in splits.groupby("cik")} if splits is not None and len(splits) else {}
    rows = []
    for cik, group in facts.groupby("cik", sort=False):
        own_splits = by_cik.get(cik)
        quarters = group[group.days.between(80, 100)]
        rows.extend((cik, q.start, q.end, q.value, q.filed, "reported") for q in quarters.itertuples())
        for year in group[group.days.between(350, 380)].itertuples():
            inside = quarters[(quarters.start >= year.start) & (quarters.end <= year.end)].sort_values("end")
            if inside.end.isin([year.end]).any():
                continue
            nine = group[(group.start == year.start) & group.days.between(255, 290) & (group.end < year.end)]
            if len(nine):
                base = nine.iloc[0]
                value = year.value - base.value * _split_factor(own_splits, base.filed, year.filed)
                begin = base.end + pd.Timedelta(days=1)
            elif len(inside) == 3:
                value = year.value - sum(q.value * _split_factor(own_splits, q.filed, year.filed) for q in inside.itertuples())
                begin = inside.end.max() + pd.Timedelta(days=1)
            else:
                continue
            rows.append((cik, begin, year.end, round(value, 4), year.filed, "q4_derived"))
    frame = pd.DataFrame(rows, columns=["cik", "period_start", "period_end", "eps", "filed", "source"])
    frame["eps_suspect"] = frame.eps.abs() > EPS_SUSPECT_ABS
    return frame.sort_values(["cik", "period_end", "filed"]).drop_duplicates(["cik", "period_end"], keep="first").reset_index(drop=True)
