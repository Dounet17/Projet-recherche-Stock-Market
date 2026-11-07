"""Tri des titres de news par règles fixes, et lecture de la surprise de résultats quand le titre la donne.

Aucun cours n'entre dans ce tri : les règles ne peuvent donc pas avoir été réglées sur les rendements.
La première catégorie reconnue l'emporte, dans cet ordre :

- `market_commentary` : décrit un mouvement de cours déjà fait. À exclure : c'est le cours qui cause l'article.
- `evergreen` : article de remplissage, sans fait nouveau (« If You Invested... », aperçus avant résultats).
- `earnings` : résultats publiés.
- `guidance` : prévisions de la société.
- `analyst` : recommandation ou objectif de cours d'un analyste.
- `company_news` : le reste, c'est-à-dire surtout des faits sur une société.

Vocabulaire : une surprise est ici l'écart entre le chiffre publié et l'estimation citée dans le même titre.
"""

import re

COMMENTARY = re.compile(
    r"\bstocks?\s+(?:that\s+are\s+)?moving\b|\bmoving\s+(?:higher|lower)\b|\bmovers?\b|\bwhale\s+alerts?\b|\bunusual\s+options?\b|\boptions?\s+(?:alert|activity|sweep)\b|\bsweep\b.*\bnear\s+the\s+(?:ask|bid)\b"
    r"|\bwhy\s+.*\b(?:shares?|stock|stocks)\b.*\b(?:today|trading|moving|up|down|higher|lower|rising|falling|soaring|plunging|tumbling|jumping|surging|sinking|sliding|flying|are|is)\b|\bwhat'?s\s+going\s+on\b"
    r"|\bshares?\s+(?:move[sd]?|wobbl\w+|slammed|tank(?:s|ed|ing)?|quiet|volatile|tick\s+(?:higher|lower))\b|^trading\s+halt:|\b(?:falls?|rises?|jumps?|slides?|drops?|sinks?|soars?|surges?|tumbles?|climbs?|plunges?)\s+(?:after|on|following|as)\b|\b(?:trade|trades|traded|react|reacts|reacted)\s+(?:higher|lower)\b|\bnear\s+(?:\w+\s+)?(?:highs?|lows?)\b|\b(?:crude\s+oil|gold|silver|nasdaq|s&p\s*500|dow)\s+(?:rises?|falls?|jumps?|gains?|drops?|slides?|moves?|surges?|dips?|up|down)\b|\bturns\s+(?:higher|lower)\b|\b(?:stock|index|equity)\s+futures\b|\bpeek\s+into\s+the\s+markets\b"
    r"|\b(?:shares?|stock|stocks)\s+(?:are\s+|is\s+|were\s+|was\s+)?(?:trading|moving|spike[sd]?|spiking|surg(?:e|es|ed|ing)|jump(?:s|ed|ing)?|f[ae]ll(?:s|ing)?|drop(?:s|ped|ping)?|dip(?:s|ped|ping)?|tumbl(?:e|es|ed|ing)|sink(?:s|ing)?|sank|soar(?:s|ed|ing)?|rall(?:y|ies|ied|ying)|slid(?:e|es|ing)?|plung(?:e|es|ed|ing)|gain(?:s|ed|ing)?|climb(?:s|ed|ing)?|rise[sn]?|rising|rose|down|up|higher|lower|halted|resume)\b"
    r"|\btrading\s+(?:higher|lower|up|down)\b|\bmarket\s+update\b|\bmid-?(?:day|morning|afternoon)\b|\b(?:top|biggest)\s+(?:gainers?|losers?)\b|\b(?:pre|after)-?market\b|\bin\s+\w+'?s?\s+session\b"
    r"|\b52-?week\b|\b(?:new|all-time)\s+highs?\b|\b(?:up|down)\s+(?:more\s+than|over|around|about)\s+[\d.]+%|\bwithin\s+(?:the\s+)?(?:last\s+)?24\s+hours\b|\bmarkets?\s+(?:mixed|higher|lower|open|close|wrap)\b|\bdow\s+(?:jumps|falls|surges|drops|tumbles|gains|dips|rises|settles)\b",
    re.IGNORECASE,
)
EVERGREEN = re.compile(
    r"\bif\s+you\s+(?:had\s+)?invested\b|\bhere'?s\s+how\s+much\b|\bwould\s+(?:be\s+worth|have)\b.*\btoday\b|\bthis\s+much\s+today\b|\binvested\s+in\s+this\b|\breturn\s+on\s+capital\b|\bshort\s+interest\b"
    r"|\b(?:analyst|expert)\s+ratings?\b|\bstands\s+with\s+analysts\b|\bwhat\s+analysts?\b|\banalysts?\s+have\s+this\b|\blatest\s+analyst\b|\bcheck\s+out\s+what\b|\bthis\s+is\s+what\b"
    r"|\bearnings\s+(?:outlook|preview|insights|scheduled|a\s+preview)\b|\ba\s+preview\s+of\b|\bpreview\s+of\b|\bq[1-4]\s+earnings\s+insights\b|\ba\s+look\s+(?:into|at|back)\b|\boverview\s+of\b|\bhow\s+is\s+the\s+market\b|\bprice\s+over\s+earnings\b|\bp/e\s+ratio\b"
    r"|\binsights\s+into\b|\bpower\s+hour\b|\b(?:earnings|ex-dividend)\b.*\bneed\s+to\s+know\b|\bglimpse\s+into\b|\bunderstanding\s+analyst\b|^preview:|\bweekend\s+stock\s+spotlight\b|\bmorning\s+memo\b|\bhow\s+to\s+trade\b|\bvalue\s+stocks\b|\bgrowth\s+stocks\b|\bcould\s+be\s+making\b"
    r"|\bearnings\s+(?:conference\s+)?call\s+(?:on|is\s+coming)\b|\bhow\s+to\s+attend\b|\b(?:to|likely\s+to)\s+report\b.*\b(?:q[1-4]|earnings|results)\b|\bkey\s+investor\s+questions\b|\bperformance\s+against\s+competitors\b"
    r"|\bstocks?\s+to\s+(?:watch|buy|consider)\b|\b(?:death|golden)\s+cross\b|\bsign\s+looms\b|\banalyst\s+(?:expectations|verdict)\b|\binsiders?\s+(?:buying|selling)\b|\bbetting\s+odds\b|\bhow\s+to\s+watch\b",
    re.IGNORECASE,
)
PERIOD = r"(?:\bQ[1-4]\b|\bFY\s?\d{2,4}\b|\bFY\b|\bfull[- ]year\b|\bquarter(?:ly)?\b|\bqtr\b)"
METRIC = r"(?:\bEPS\b|\bFFO\b|\bsales\b|\brevenues?\b|\bnet\s+(?:income|loss)\b|\bearnings\b)"
GUIDANCE = re.compile(rf"\b(?:sees|expects?|forecasts?|guides?|projects?|raises?|lowers?|cuts?|reaffirms?|affirms?|reiterates?|narrows?|boosts?|maintains?|updates?|withdraws?|suspends?)\b.*(?:{PERIOD}|{METRIC}|\bguidance\b|\boutlook\b)|\bguidance\b", re.IGNORECASE)
EARNINGS = re.compile(rf"{PERIOD}.*{METRIC}|{METRIC}.*\b(?:beats?|miss(?:es)?|estimate|est\.?)\b|\b(?:reports?|posts?)\b.*{METRIC}", re.IGNORECASE)
RATING = r"(?:buy|sell|hold|neutral|overweight|underweight|outperform|underperform|perform|equal-?weight|sector\s+weight|in-line|peer\s+perform|strong\s+buy|accumulate|reduce|positive|negative)"
ANALYST = re.compile(rf"\bprice\s+target\b|^(?:UPDATE:\s*)?[\w&.,' -]{{2,40}}\s(?:upgrades|downgrades)\b|^(?:UPDATE:\s*)?[\w&.,' -]{{2,40}}\s(?:maintains|initiates|reiterates|assumes|reinstates|resumes)\s+(?:coverage\b|{RATING}\b)", re.IGNORECASE)

CATEGORIES = ("market_commentary", "evergreen", "earnings", "guidance", "analyst", "company_news")
REPORTED = re.compile(r"\b(?:EPS|sales|revenues?)\b[^;,]*?\b(?:beats?|miss(?:es)?)\b", re.IGNORECASE)
FORWARD = re.compile(r"\b(?:sees|expects?|forecasts?|guides?|guidance|outlook|projects?|projected|on\s+track|reaffirms?|affirms|raises?|lowers?|cuts?|maintains?|narrows?|boosts?|updates?|withdraws?|reiterates?)\b", re.IGNORECASE)
# Forme stricte de la prévision en classement : « raises » seul peut aussi être un fait (capital, dividende).
GUIDE_WORD = re.compile(r"\b(?:sees|expects?|forecasts?|guides?|guidance|outlook|projects?|projected|on\s+track)\b", re.IGNORECASE)
LATE_RELAY = re.compile(r"\b(?:earlier|late\s+\w+|yesterday)\s+(?:reported|said|announced)\b", re.IGNORECASE)
ADJUSTED = re.compile(r"\b(?:adj(?:usted|\.)?|non-?gaap|core|comparable|operating)\b", re.IGNORECASE)
GAAP = re.compile(r"\bgaap\b", re.IGNORECASE)
QUARTER = re.compile(r"\bQ[1-4]\b|\b(?:first|second|third|fourth)\s+quarter\b|\bqtr\b", re.IGNORECASE)
ANNUAL = re.compile(r"\bFY\s?\d{0,4}\b|\bfull[- ]year\b|\bannual\b", re.IGNORECASE)
# Seuils de vraisemblance fixés avant toute lecture de rendement, repris de l'audit.
MAX_ABS_EPS, MAX_EPS_GAP, SALES_RATIO_MIN, SALES_RATIO_MAX = 100.0, 10.0, 0.1, 10.0
AMOUNT = r"\$?\s*(\(?-?\$?[\d,]*\.?\d+\)?)\s*([KMB]\b)?"
VERB = r"(beats?|miss(?:es)?|vs\.?|versus|compared\s+to|up\s+from|down\s+from)"
SCALE = {"K": 1e3, "M": 1e6, "B": 1e9, None: 1.0}


def _after_first_word(text):
    """Le premier mot est presque toujours le nom de la société : il ne peut pas être un verbe de prévision."""
    return re.sub(r"^\s*\S+", lambda m: " " * len(m[0]), text, count=1)


def classify_headline(text):
    """Catégorie d'un titre. Le sens du marché n'est jamais regardé."""
    if not text or not text.strip():
        return "company_news"
    if COMMENTARY.search(text):
        return "market_commentary"
    if EVERGREEN.search(text):
        return "evergreen"
    # Une recommandation peut citer un résultat ; un objectif de cours reste une note d'analyste.
    if ANALYST.search(text):
        return "analyst"
    # « Q1 EPS Beats... ; Reaffirms Guidance » est d'abord un résultat publié, sauf si la prévision vient avant.
    reported = REPORTED.search(text)
    if reported and not FORWARD.search(_after_first_word(text)[:reported.start()]):
        return "earnings"
    # Un dividende relevé est un fait sur la société, pas une prévision de résultats.
    body = _after_first_word(text)
    if re.search(r"\bdividend\b", text, re.IGNORECASE) and not GUIDE_WORD.search(body):
        return "company_news"
    # « Reaffirms FY19 EPS $10.03 vs $10.09 Estimate » est une prévision, comme « Sees ».
    if (GUIDE_WORD.search(body) or re.search(r"\b(?:reaffirms?|affirms|raises?|lowers?|cuts?|narrows?|boosts?|withdraws?)\b.*" + METRIC, body, re.IGNORECASE)) and GUIDANCE.search(body):
        return "guidance"
    if EARNINGS.search(text):
        return "earnings"
    return "company_news"


def _number(raw, scale):
    """Montant du titre. « 4,35 » est une virgule décimale, « 1,234 » un séparateur de milliers ; le reste est refusé."""
    negative = raw.startswith(("(", "-", "$-", "$("))
    digits = re.sub(r"[^\d.,]", "", raw)
    if re.fullmatch(r"\d+,\d{1,2}", digits):
        digits = digits.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", digits):
        digits = digits.replace(",", "")
    elif "," in digits:
        raise ValueError(raw)
    value = float(digits)
    return (-value if negative else value) * SCALE[scale.upper() if scale else None]


def _pair(text, metric):
    """Chiffre publié et estimation : « EPS $1.46 Beats $1.38 Estimate » ou « Sales $8M vs $9M Est. ».

    Un chiffre placé après un verbe de prévision (« Sees », « Reaffirms ») n'est pas un résultat publié.
    Renvoie aussi les suffixes d'unité, nécessaires aux contrôles de vraisemblance.
    """
    pattern = re.compile(rf"\b{metric}\b\s*(?:of\s+)?{AMOUNT}\s*[,;]?\s*{VERB}\s*(?:the\s+)?{AMOUNT}\s*(?:analyst\s+|consensus\s+)?(est(?:imate)?s?\b\.?|consensus)", re.IGNORECASE)
    match = pattern.search(text)
    if not match or FORWARD.search(_after_first_word(text)[:match.start()]):
        return None
    try:
        return _number(match[1], match[2]), match[3].lower(), _number(match[4], match[5]), match[2], match[5], match.start()
    except ValueError:
        return None


def _basis(text, start, quarter):
    """Base du couple retenu : les mots juste avant lui, dans sa clause, sans le nom de la société ni un FFO précédent."""
    clause_start = max(text.rfind(",", 0, start), text.rfind(";", 0, start)) + 1
    if quarter and quarter.end() <= start:
        clause_start = max(clause_start, quarter.end())
    before = text[clause_start:start]
    if not quarter or quarter.end() > start:
        before = _after_first_word(before)
    if re.search(r"\bFFO\b", before, re.IGNORECASE):
        return "other"
    return "gaap" if GAAP.search(before) and not re.search(r"non-?gaap", before, re.IGNORECASE) else "adjusted" if ADJUSTED.search(before) else "unlabeled"


def parse_surprise(text):
    """Surprise lue dans un titre de résultats, avec ce qu'il faut pour la qualifier.

    Le signe vient des chiffres, le verbe n'est qu'un contrôle. `eps_ok` et `sales_ok` disent si le chiffre passe les
    contrôles fixés d'avance. Un chiffre refusé n'est jamais corrigé en silence. `basis` vaut `adjusted`, `gaap` ou
    `unlabeled` : un BPA sans étiquette n'est pas forcément comptable. `period` vaut `quarter`, `annual` ou `unknown`.
    """
    result = {"eps": None, "eps_estimate": None, "sales": None, "sales_estimate": None, "verb_conflict": False, "eps_conflict": False, "eps_ok": False, "sales_ok": False, "basis": None, "period": None, "quarter": None}
    if not text:
        return result
    annual, quarter = ANNUAL.search(text), QUARTER.search(text)
    if quarter and (not annual or quarter.start() < annual.start()):
        result["period"] = "quarter"
        number = re.search(r"\bQ([1-4])\b", text[quarter.start():quarter.end()])
        result["quarter"] = int(number[1]) if number else None
    else:
        result["period"] = "annual" if annual else "unknown"
    for name, metric in (("eps", r"EPS"), ("sales", r"(?:sales|revenues?)")):
        pair = _pair(text, metric)
        if pair is None:
            continue
        actual, verb, estimate, unit_actual, unit_estimate, start = pair
        result[name], result[f"{name}_estimate"] = actual, estimate
        if (verb.startswith("beat") and actual < estimate) or (verb.startswith("miss") and actual > estimate):
            result["verb_conflict"] = True
            result["eps_conflict"] = result["eps_conflict"] or name == "eps"
        if name == "eps":
            # Un BPA ne peut pas porter de suffixe de milliers, de millions ou de milliards.
            result["eps_ok"] = not unit_actual and not unit_estimate and abs(actual) <= MAX_ABS_EPS and abs(actual - estimate) <= MAX_EPS_GAP
            result["basis"] = _basis(text, start, quarter)
        else:
            result["sales_ok"] = actual > 0 and estimate > 0 and SALES_RATIO_MIN <= actual / estimate <= SALES_RATIO_MAX
    return result


def one_row_per_wire(wires, stocks):
    """Une ligne par dépêche et par société, sur le titre cité : une action de `stocks` plutôt qu'une autre ligne de la cote.

    `wires` porte `id`, `cik` et `security_id`. Le choix ne regarde ni les dates ni la liquidité, connue seulement après coup.
    """
    other = ~wires.security_id.isin(stocks)
    return wires.assign(_other=other).sort_values(["id", "_other", "security_id"]).drop_duplicates(["id", "cik"]).drop(columns="_other")
