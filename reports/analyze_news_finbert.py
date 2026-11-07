"""FinBERT lit-il correctement les titres ? Contrôle sur les titres dont le verdict est écrit, sans aucun cours.

Trois comparaisons : bénéfice au-dessus ou en dessous de l'estimation, relèvement ou abaissement par un analyste, prévision
relevée ou abaissée. L'aire sous la courbe (AUC) vaut 0,5 pour un classement au hasard et 1 pour un classement parfait.
Écrit `data/news/news_scored.parquet` et `reports/lab_2026-11/news/finbert_check.json`.

Depuis la racine : venv/bin/python reports/analyze_news_finbert.py
"""

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "data" / "news"
OUT = ROOT / "reports" / "lab_2026-11" / "news" / "finbert_check.json"
LABELS = ["p_positive", "p_negative", "p_neutral"]


def check(frame, good, bad):
    """Compare le score sur deux groupes de verdict opposé ; `good` et `bad` sont des masques."""
    part = frame[good | bad]
    high, low = part[good.loc[part.index]], part[bad.loc[part.index]]
    return {
        "good": len(high), "bad": len(low), "auc": float(roc_auc_score(good.loc[part.index], part.score)),
        "good_read_positive": float((high.label == "p_positive").mean()), "good_read_negative": float((high.label == "p_negative").mean()),
        "bad_read_positive": float((low.label == "p_positive").mean()), "bad_read_negative": float((low.label == "p_negative").mean()),
    }


def main():
    scores = pd.concat([pd.read_parquet(path) for path in sorted((NEWS / "finbert").glob("part_*.parquet"))], ignore_index=True)
    assert not scores.headline.duplicated().any()
    articles = pd.read_parquet(NEWS / "news_articles.parquet")
    # Le même titre peut revenir sur un article écarté : on filtre les articles avant de joindre.
    usable = ~articles.category.isin(["market_commentary", "evergreen"]) & (articles.n_stocks >= 1) & articles.headline.str.strip().ne("")
    table = articles[usable].merge(scores, on="headline", how="inner")
    assert len(table) == int(usable.sum()), (len(table), int(usable.sum()))
    table["score"] = table.p_positive - table.p_negative
    table["label"] = table[LABELS].idxmax(axis=1)
    table.to_parquet(NEWS / "news_scored.parquet", index=False)

    text = table.headline
    beat, miss = table.eps > table.eps_estimate, table.eps < table.eps_estimate
    upgrade = table.category.eq("analyst") & text.str.contains(r"(?i)\bupgrades?\b") & ~text.str.contains(r"(?i)\bdowngrades?\b")
    downgrade = table.category.eq("analyst") & text.str.contains(r"(?i)\bdowngrades?\b") & ~text.str.contains(r"(?i)\bupgrades?\b")
    raises = table.category.eq("guidance") & text.str.contains(r"(?i)\b(?:raises|boosts)\b.*\b(?:guidance|outlook)\b") & ~text.str.contains(r"(?i)\b(?:cuts|lowers)\b")
    cuts = table.category.eq("guidance") & text.str.contains(r"(?i)\b(?:cuts|lowers)\b.*\b(?:guidance|outlook)\b") & ~text.str.contains(r"(?i)\b(?:raises|boosts)\b")
    result = {
        "revision": "4556d13015211d73dccd3fdd39d39232506f3e43", "articles_scored": len(table), "unique_headlines": len(scores),
        "labels_by_category": {name: part.label.value_counts(normalize=True).round(3).to_dict() for name, part in table.groupby("category")},
        "labels_by_year": {str(year): part.label.value_counts(normalize=True).round(3).to_dict() for year, part in table.groupby(table.created_at.dt.year)},
        "checks": {"eps_beat_vs_miss": check(table, beat, miss), "upgrade_vs_downgrade": check(table, upgrade, downgrade), "guidance_raise_vs_cut": check(table, raises, cuts)},
    }
    OUT.write_text(json.dumps(result, indent=1, ensure_ascii=False))
    print(json.dumps(result, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
