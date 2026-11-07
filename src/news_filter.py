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
    r"|\bwhy\s+.*\b(?:shares?|stock|stocks)\b|\bwhat'?s\s+going\s+on\b|\bhere'?s\s+why\b"
    r"|\b(?:shares?|stock|stocks)\s+(?:are\s+|is\s+|were\s+|was\s+)?(?:trading|moving|spike[sd]?|spiking|surg(?:e|es|ed|ing)|jump(?:s|ed|ing)?|f[ae]ll(?:s|ing)?|drop(?:s|ped|ping)?|dip(?:s|ped|ping)?|tumbl(?:e|es|ed|ing)|sink(?:s|ing)?|sank|soar(?:s|ed|ing)?|rall(?:y|ies|ied|ying)|slid(?:e|es|ing)?|plung(?:e|es|ed|ing)|gain(?:s|ed|ing)?|climb(?:s|ed|ing)?|rise[sn]?|rising|rose|down|up|higher|lower|halted|resume)\b"
    r"|\btrading\s+(?:higher|lower|up|down)\b|\bmarket\s+update\b|\bmid-?(?:day|morning|afternoon)\b|\b(?:top|biggest)\s+(?:gainers?|losers?)\b|\b(?:pre|after)-?market\b|\bin\s+\w+'?s?\s+session\b"
    r"|\b52-?week\b|\b(?:new|all-time)\s+highs?\b|\b(?:up|down)\s+(?:more\s+than|over|around|about)\s+[\d.]+%|\bwithin\s+(?:the\s+)?(?:last\s+)?24\s+hours\b|\bmarkets?\s+(?:mixed|higher|lower|open|close|wrap)\b|\bdow\s+(?:jumps|falls|surges|drops|tumbles|gains|dips|rises|settles)\b",
    re.IGNORECASE,
)
EVERGREEN = re.compile(
    r"\bif\s+you\s+(?:had\s+)?invested\b|\bhere'?s\s+how\s+much\b|\bwould\s+(?:be\s+worth|have)\b.*\btoday\b|\bthis\s+much\s+today\b|\binvested\s+in\s+this\b|\breturn\s+on\s+capital\b|\bshort\s+interest\b"
    r"|\b(?:analyst|expert)\s+ratings?\b|\bstands\s+with\s+analysts\b|\bwhat\s+analysts?\b|\banalysts?\s+have\s+this\b|\blatest\s+analyst\b|\bcheck\s+out\s+what\b|\bthis\s+is\s+what\b"
    r"|\bearnings\s+(?:outlook|preview|insights|scheduled|a\s+preview)\b|\ba\s+preview\s+of\b|\bpreview\s+of\b|\bq[1-4]\s+earnings\s+insights\b|\ba\s+look\s+(?:into|at|back)\b|\boverview\s+of\b|\bhow\s+is\s+the\s+market\b|\bprice\s+over\s+earnings\b|\bp/e\s+ratio\b"
    r"|\binsights\s+into\b|\bpower\s+hour\b|\bneed\s+to\s+know\b|\bvalue\s+stocks\b|\bgrowth\s+stocks\b|\bcould\s+be\s+making\b"
    r"|\bearnings\s+(?:conference\s+)?call\s+(?:on|is\s+coming)\b|\bhow\s+to\s+attend\b|\b(?:to|likely\s+to)\s+report\b.*\b(?:q[1-4]|earnings|results)\b|\bkey\s+investor\s+questions\b|\bperformance\s+against\s+competitors\b"
    r"|\bstocks?\s+to\s+(?:watch|buy|consider)\b|\b(?:death|golden)\s+cross\b|\bsign\s+looms\b|\banalyst\s+(?:expectations|verdict)\b|\binsiders?\s+(?:buying|selling)\b|\bbetting\s+odds\b|\bhow\s+to\s+watch\b",
    re.IGNORECASE,
)
PERIOD = r"(?:\bQ[1-4]\b|\bFY\s?\d{2,4}\b|\bFY\b|\bfull[- ]year\b|\bquarter(?:ly)?\b|\bqtr\b)"
METRIC = r"(?:\bEPS\b|\bFFO\b|\bsales\b|\brevenues?\b|\bnet\s+(?:income|loss)\b|\bearnings\b)"
GUIDANCE = re.compile(rf"\b(?:sees|expects?|forecasts?|guides?|projects?|raises?|lowers?|cuts?|reaffirms?|affirms?|reiterates?|narrows?|boosts?|maintains?|updates?|withdraws?|suspends?)\b.*(?:{PERIOD}|{METRIC}|\bguidance\b|\boutlook\b)|\bguidance\b", re.IGNORECASE)
EARNINGS = re.compile(rf"{PERIOD}.*{METRIC}|{METRIC}.*\b(?:beats?|miss(?:es)?|estimate|est\.?)\b|\b(?:reports?|posts?)\b.*{METRIC}", re.IGNORECASE)
ANALYST = re.compile(r"\bprice\s+target\b|\b(?:maintains|upgrades|downgrades|initiates|reiterates|assumes|reinstates|resumes|initiated|upgraded|downgraded)\b.*\b(?:buy|sell|hold|neutral|overweight|underweight|outperform|underperform|perform|equal-?weight|sector\s+weight|in-line|peer|strong|accumulate|reduce|market)\b|\bcoverage\b.*\b(?:initiates|assumes|resumes)\b", re.IGNORECASE)

CATEGORIES = ("market_commentary", "evergreen", "earnings", "guidance", "analyst", "company_news")
REPORTED = re.compile(r"\b(?:EPS|sales|revenues?)\b[^;,]*?\b(?:beats?|miss(?:es)?)\b", re.IGNORECASE)
FORWARD = re.compile(r"\b(?:sees|expects?|forecasts?|guides?|guidance|outlook|projects?)\b", re.IGNORECASE)
AMOUNT = r"\$?\s*(\(?-?\$?[\d,]*\.?\d+\)?)\s*([KMB]\b)?"
VERB = r"(beats?|miss(?:es)?|vs\.?|versus|compared\s+to|up\s+from|down\s+from)"
SCALE = {"K": 1e3, "M": 1e6, "B": 1e9, None: 1.0}


def classify_headline(text):
    """Catégorie d'un titre. Le sens du marché n'est jamais regardé."""
    if not text or not text.strip():
        return "company_news"
    if COMMENTARY.search(text):
        return "market_commentary"
    if EVERGREEN.search(text):
        return "evergreen"
    # Une recommandation peut citer un résultat ; un objectif de cours reste une note d'analyste.
    if re.search(r"\bprice\s+target\b", text, re.IGNORECASE) or re.match(r"^(?:UPDATE:\s*)?[\w&.,' -]{2,40}\s(?:maintains|upgrades|downgrades|initiates|reiterates|assumes|reinstates|resumes)\b", text, re.IGNORECASE):
        return "analyst"
    # « Q1 EPS Beats... ; Reaffirms Guidance » est d'abord un résultat publié, sauf si la prévision vient avant.
    reported = REPORTED.search(text)
    if reported and not FORWARD.search(text[:reported.start()]):
        return "earnings"
    forward = FORWARD.search(text)
    if forward and GUIDANCE.search(text):
        return "guidance"
    # Un dividende relevé est un fait sur la société, pas une prévision de résultats.
    if re.search(r"\bdividend\b", text, re.IGNORECASE):
        return "company_news"
    if EARNINGS.search(text):
        return "earnings"
    if GUIDANCE.search(text):
        return "guidance"
    if ANALYST.search(text):
        return "analyst"
    return "company_news"


def _number(raw, scale):
    negative = raw.startswith("(") or raw.startswith("-") or raw.startswith("$-") or raw.startswith("$(")
    value = float(re.sub(r"[^\d.]", "", raw))
    return (-value if negative else value) * SCALE[scale.upper() if scale else None]


def _pair(text, metric):
    """Chiffre publié et estimation pour une mesure : « EPS $1.46 Beats $1.38 Estimate » ou « Sales $8M vs $9M Est. »."""
    pattern = re.compile(rf"\b{metric}\b\s*(?:of\s+)?{AMOUNT}\s*[,;]?\s*{VERB}\s*(?:the\s+)?{AMOUNT}\s*(?:analyst\s+|consensus\s+)?(est(?:imate)?s?\b\.?|consensus)", re.IGNORECASE)
    match = pattern.search(text)
    # Une prévision placée avant le chiffre (« Sees Q4 Sales $70M vs $71M Est. ») n'est pas un résultat publié.
    if not match or FORWARD.search(text[:match.start()]):
        return None
    try:
        return _number(match[1], match[2]), match[3].lower(), _number(match[4], match[5])
    except ValueError:
        return None


def parse_surprise(text):
    """Surprise lue dans un titre de résultats, ou rien. Le signe vient des chiffres, le verbe n'est qu'un contrôle.

    Renvoie un dictionnaire : `eps`, `eps_estimate`, `sales`, `sales_estimate`, `verb_conflict` si le verbe contredit
    les chiffres. Un chiffre annoncé après une prévision (« Sees ») n'est pas un résultat publié : il ne donne rien.
    """
    result = {"eps": None, "eps_estimate": None, "sales": None, "sales_estimate": None, "verb_conflict": False}
    if not text:
        return result
    for name, metric in (("eps", r"EPS"), ("sales", r"(?:sales|revenues?)")):
        pair = _pair(text, metric)
        if pair is None:
            continue
        actual, verb, estimate = pair
        result[name], result[f"{name}_estimate"] = actual, estimate
        if (verb.startswith("beat") and actual < estimate) or (verb.startswith("miss") and actual > estimate):
            result["verb_conflict"] = True
    return result
