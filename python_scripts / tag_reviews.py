"""
Claude review tagging: sentiment score + emotion tags.

Usage (run from the repo root):
    python src/tag_reviews.py tag               # tag all reviews (cached)
    python src/tag_reviews.py sample 40         # write 40 reviews to hand-label
    python src/tag_reviews.py validate          # compare your labels with Claude's

Design notes
- The review file repeats the same text many times with a "[Verified Review
  Segment N]" suffix. We strip the suffix and tag each DISTINCT text once,
  which is cheaper and keeps tags consistent. Results are cached on disk so
  re-runs cost nothing.
- Emotions allowed: trust, price_pain, taste, results, none.
"""
import json
import re
import sys
from pathlib import Path

import pandas as pd

from llm import ask_json

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)
CACHE = OUT / "tags_cache.json"
EMOTIONS = ["trust", "price_pain", "taste", "results", "none"]

SYSTEM = f"""You label customer reviews of gummy vitamins sold in India.
Return ONLY a JSON object, with no preamble and no markdown, in this exact shape:
{{"sentiment_score": <number from -1.0 (very negative) to 1.0 (very positive)>,
  "sentiment_label": "positive" | "neutral" | "negative",
  "emotions": [<zero or more of {EMOTIONS}>],
  "evidence": "<a short phrase copied from the review that justifies the emotions>"}}
Definitions: trust = brand credibility, safety, authenticity; price_pain = cost or
value-for-money complaints; taste = flavour or texture; results = perceived
effectiveness. Use ["none"] if no emotion applies. Judge only what the review says."""


def clean(text: str) -> str:
    return re.sub(r"\s*\[Verified Review Segment \d+\]", "", str(text)).strip()


def load_cache() -> dict:
    return json.loads(CACHE.read_text()) if CACHE.exists() else {}


def tag_one(text: str) -> dict:
    result = ask_json(SYSTEM, f"Review:\n{text}", max_tokens=300)
    result["emotions"] = [e for e in result.get("emotions", []) if e in EMOTIONS] or ["none"]
    result["sentiment_score"] = max(-1.0, min(1.0, float(result["sentiment_score"])))
    return result


def cmd_tag():
    reviews = pd.read_csv(ROOT / "reviews.csv")
    brands = pd.read_csv(ROOT / "brands.csv")[["brand_id", "brand_name"]]
    reviews["clean_text"] = reviews["review_text"].map(clean)
    cache = load_cache()
    todo = [t for t in reviews["clean_text"].unique() if t not in cache]
    print(f"{len(reviews)} reviews, {reviews['clean_text'].nunique()} distinct texts, {len(todo)} to tag")
    for i, text in enumerate(todo, 1):
        try:
            cache[text] = tag_one(text)
        except Exception as e:  # keep going; failed texts are retried next run
            print(f"  skipped one text: {e}")
        if i % 10 == 0:
            CACHE.write_text(json.dumps(cache, indent=1))
            print(f"  tagged {i}/{len(todo)}")
    CACHE.write_text(json.dumps(cache, indent=1))

    tags = reviews["clean_text"].map(cache)
    reviews["sentiment_score"] = tags.map(lambda t: t["sentiment_score"] if t else None)
    reviews["sentiment_label"] = tags.map(lambda t: t["sentiment_label"] if t else None)
    reviews["emotions"] = tags.map(lambda t: "|".join(t["emotions"]) if t else None)
    out = reviews.drop(columns=["clean_text"]).merge(brands, on="brand_id")
    out.to_csv(OUT / "review_tags.csv", index=False)

    summary = out.groupby("brand_name").agg(
        n_reviews=("review_id", "count"),
        avg_sentiment=("sentiment_score", "mean"),
        avg_star_rating=("star_rating", "mean"),
    ).round(2)
    for emo in EMOTIONS[:-1]:
        summary[f"pct_{emo}"] = out.groupby("brand_name")["emotions"].apply(
            lambda s: round(100 * s.fillna("").str.contains(emo).mean(), 1)
        )
    summary.to_csv(OUT / "brand_sentiment_summary.csv")
    print(summary.to_string())


def cmd_sample(n: int):
    """Pick n distinct texts for hand-labelling. Fill in my_label with positive/neutral/negative."""
    reviews = pd.read_csv(ROOT / "reviews.csv")
    texts = pd.Series(reviews["review_text"].map(clean).unique())
    sample = texts.sample(min(n, len(texts)), random_state=42).reset_index(drop=True)
    pd.DataFrame({"review_text": sample, "my_label": ""}).to_csv(OUT / "hand_labels.csv", index=False)
    print(f"Wrote {OUT / 'hand_labels.csv'}. Fill the my_label column, then run: python src/tag_reviews.py validate")


def cmd_validate():
    labels = pd.read_csv(OUT / "hand_labels.csv")
    labels = labels[labels["my_label"].fillna("").str.strip() != ""]
    cache = load_cache()
    labels["claude_label"] = labels["review_text"].map(lambda t: cache.get(t, {}).get("sentiment_label"))
    labels = labels.dropna(subset=["claude_label"])
    agree = (labels["my_label"].str.lower().str.strip() == labels["claude_label"]).mean()
    print(f"Agreement with your hand labels: {agree:.0%} on {len(labels)} reviews")
    print(pd.crosstab(labels["my_label"], labels["claude_label"]))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tag"
    if cmd == "tag":
        cmd_tag()
    elif cmd == "sample":
        cmd_sample(int(sys.argv[2]) if len(sys.argv) > 2 else 40)
    elif cmd == "validate":
        cmd_validate()
    else:
        sys.exit("Use: tag | sample [n] | validate")
