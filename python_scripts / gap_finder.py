"""
AI Gap Finder: turns brand-level market facts (and tagged review sentiment, if
available) into positioning hypotheses.

Usage (run from the repo root, after tag_reviews.py tag):
    python src/gap_finder.py

Why the facts are computed in code and not by the model: the numbers (brand
counts, price per gummy, lane crowding) are calculated with pandas, mirroring
analysis.sql, and the model only interprets them. That keeps figures auditable.
"""
import json
import re
from pathlib import Path

import pandas as pd

from llm import ask_json

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

CLAIMS = {
    "sugar_free": r"sugar",
    "vegan_or_vegetarian": r"vegan|vegetarian",
    "ayurvedic_blend": r"amla|aloe|ayurved",
    "hair_skin_biotin": r"biotin|hair",
    "sleep": r"sleep|melatonin",
    "immunity": r"immunity|zinc",
    "gut_acv": r"acv|gut|digest",
}

SYSTEM = """You are a market analyst for a new Indian D2C gummy vitamin brand.
Use ONLY the JSON facts provided; do not invent numbers, brands or trends.
Return ONLY valid JSON (no markdown) shaped as:
{"gaps": [{"title": str, "evidence": str (cite specific figures from the facts),
           "who_it_serves": str, "confidence": "low"|"medium"|"high",
           "why_this_confidence": str, "test_to_validate": str}],
 "data_caveats": [str]}
Give 3 to 5 gaps. If review data has limited distinct texts or a narrow rating
range, say so in data_caveats and lower your confidence accordingly."""


def build_facts() -> dict:
    brands = pd.read_csv(ROOT / "brands.csv")
    reviews = pd.read_csv(ROOT / "reviews.csv")
    text = (brands["usps_key_features"].fillna("") + " " + brands["positioning_statement"].fillna("")).str.lower()

    coverage = {}
    for claim, pattern in CLAIMS.items():
        mask = text.str.contains(pattern, regex=True)
        coverage[claim] = {"brands": int(mask.sum()), "of": len(brands), "which": sorted(brands.loc[mask, "brand_name"])}

    price = brands[["brand_name", "min_price_inr", "pack_size_min", "price_per_gummy_inr"]].copy()
    price["sticker_rank"] = price["min_price_inr"].rank(ascending=False, method="min").astype(int)
    price["per_gummy_rank"] = price["price_per_gummy_inr"].rank(ascending=False, method="min").astype(int)

    clean = reviews["review_text"].str.replace(r"\s*\[Verified Review Segment \d+\]", "", regex=True)
    facts = {
        "market_size": f"{len(brands)} brands",
        "claim_coverage": coverage,
        "pricing": price.to_dict("records"),
        "review_data_quality": {
            "rows": len(reviews),
            "distinct_texts": int(clean.nunique()),
            "min_rating": int(reviews["star_rating"].min()),
            "max_rating": int(reviews["star_rating"].max()),
        },
    }
    summary = OUT / "brand_sentiment_summary.csv"
    if summary.exists():
        facts["claude_review_tags_per_brand"] = pd.read_csv(summary).to_dict("records")
    return facts


def main():
    facts = build_facts()
    result = ask_json(SYSTEM, "Facts:\n" + json.dumps(facts, indent=1, default=str), max_tokens=2500)
    (OUT / "gap_report.json").write_text(json.dumps(result, indent=2))

    lines = ["# Gap Finder report", ""]
    for i, g in enumerate(result["gaps"], 1):
        lines += [f"## {i}. {g['title']}", f"**Evidence:** {g['evidence']}", f"**Serves:** {g['who_it_serves']}",
                  f"**Confidence:** {g['confidence']} ({g['why_this_confidence']})", f"**Test:** {g['test_to_validate']}", ""]
    lines += ["## Data caveats"] + [f"- {c}" for c in result.get("data_caveats", [])]
    (OUT / "gap_report.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
