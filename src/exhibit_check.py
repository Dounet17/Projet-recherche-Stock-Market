"""Le BPA d'une dépêche figure-t-il dans le communiqué officiel, et comme chiffre du trimestre en cours ?

Trois réponses possibles, sans aucun cours :
- `current` : le chiffre apparaît en position de trimestre courant, soit première valeur d'une ligne de tableau sur le
  résultat par action, soit dans une phrase sans mot de comparaison juste avant ;
- `historical_only` : il apparaît, mais seulement dans une autre colonne ou après « compared to » ;
- `absent` : il n'apparaît pas.

C'est une heuristique. Elle écarte les chiffres absents et une partie des chiffres d'une autre période, sans prouver
qu'un chiffre retenu est le bon. Un tableau qui place l'année passée en premier peut la tromper.
"""

import re
from decimal import Decimal

PER_SHARE = re.compile(r"per\s+(?:\w+\s+){0,3}share|\beps\b|per\s+(?:diluted|basic|common)|diluted|earnings\s+per", re.IGNORECASE)
COMPARISON = re.compile(r"compared|versus|\bvs\b|\bfrom\b|prior|last\s+year|year[- ]ago|year\s+ago|same\s+(?:period|quarter)|previous|preceding|\bor\s+\$[\d.]+\s+in\b", re.IGNORECASE)
ADJUSTED = re.compile(r"adjusted|non-?gaap|excluding|core\b|comparable|normalized|operating\s+earnings", re.IGNORECASE)
NUMBER = re.compile(r"\(?-?\$?\s*\(?\d[\d,]*\.\d+\)?|\(?-?\$?\s*\(?\.\d+\)?")
CONTEXT = 200
COMPARISON_REACH = 60


def figure_pattern(value):
    """Motif d'un montant par action : même valeur absolue, zéros finaux libres, jamais au milieu d'un autre nombre."""
    text = format(abs(Decimal(repr(float(value)))), "f")
    whole, _, decimals = text.partition(".")
    decimals = decimals.rstrip("0")
    if decimals:
        core = rf"(?:{whole})?\.{decimals}0*" if whole == "0" else rf"{whole}\.{decimals}0*"
    else:
        core = rf"{whole}\.0+"
    return re.compile(rf"(?<![\d.,]){core}(?!\d)")


def first_number_on_line(line):
    found = NUMBER.search(line)
    return found.span() if found else None


def locate_figure(text, value):
    """Renvoie (position, base vue autour du chiffre) : base `adjusted`, `plain` ou None si le chiffre manque."""
    pattern = figure_pattern(value)
    position = "absent"
    basis = None
    offset = 0
    for line in text.split("\n"):
        matches = list(pattern.finditer(line))
        if matches:
            position = "historical_only" if position == "absent" else position
            is_table = "|" in line
            for match in matches:
                around = text[max(0, offset + match.start() - CONTEXT):offset + match.end() + CONTEXT]
                current = False
                if is_table:
                    first = first_number_on_line(line)
                    current = bool(first and first[0] <= match.start() < first[1] and PER_SHARE.search(line))
                else:
                    before = line[max(0, match.start() - COMPARISON_REACH):match.start()]
                    current = bool(PER_SHARE.search(around)) and not COMPARISON.search(before)
                if current:
                    position = "current"
                    if basis != "adjusted":
                        basis = "adjusted" if ADJUSTED.search(around) else "plain"
        offset += len(line) + 1
    return position, basis
