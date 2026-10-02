# India Gummy Vitamin Market: Competitive Intelligence

A SQL + LLM pipeline that maps the Indian D2C gummy vitamin market: where brands price, what they claim, and where the gaps are.

## Questions it answers
1. How is the market tiered on price, and does sticker price match cost per gummy?
2. Which benefit lanes (hair, sleep, immunity, gut) are crowded and which are empty?
3. Which claims (sugar-free, vegan, Ayurvedic blend) are still under-owned?
4. What do customers praise or complain about, and does it differ by brand or platform?

## Structure
| File | What it is |
|---|---|
| `brands.csv` | 9 brands: positioning, USPs, price range, parsed min price, pack size, price per gummy |
| `reviews.csv` | 495 review rows linked to brands by `brand_id` |
| `analysis.sql` | Schema, data-quality audit, and 12 analysis queries (MySQL 8 / MariaDB 10.6+) |

The model has two tables (`brands`, `reviews`) so brand-level facts are counted once per brand, never once per review.

## Data notes (please read)
- **Brand-level data** (prices, positioning, USPs) drives the main findings.
- **Review data** is a 495-row sample containing **90 distinct review texts** (10 per brand, repeated with segment tags), and ratings only between 3 and 5 stars. Run `Q0` in `analysis.sql` to see this. Review-level queries (Q7 to Q12) are therefore a demonstration of the method, not market findings. The pipeline is designed to be re-run on a larger set of genuine reviews.
- Source and collection method for the dataset: Data available with the brand VITHUB and used Ai to sum up the data of other brands.
- Prices are as listed at the time of collection; Purna Gummies quotes a 30-60 count pack, so its price per gummy assumes the 30-count pack.

## Method
1. Parse price text into `min_price_inr`, `max_price_inr` and `pack_size_min`.
2. Brand-level SQL for tiers, per-gummy cost, claim coverage and lane crowding.
3. Review-level SQL for rating distribution, platform mix and complaint rates (normalised per 100 reviews).
4. **LLM layer (Claude API).** Each review is scored for sentiment and tagged with emotions (trust, price-pain, taste, results). An "AI Gap Finder" then combines the SQL outputs and the tagged sentiment and asks the model to propose positioning gaps. Tags have not yet been validated against human labels, so treat them as exploratory.

## Headline findings (brand level)
- Only 3 of 9 brands claim sugar-free; 1 of 9 is vegan; 2 of 9 blend Ayurvedic ingredients.
- 6 of 9 brands compete in hair/biotin. Sleep and gut health each have one brand.
- Sticker price misleads: What's Up Wellness ranks 4th on price but at about ₹18.7 per gummy; Carbamide Forte is the cheapest per gummy (₹7.5) despite a mid-market price tag.

## Limitations
- Nine brands is a small market sample.
- Keyword matching (`LIKE`/`REGEXP`) is a first pass and will miss paraphrases.
- Review-level conclusions need a larger, real review set before anyone acts on them.

## Next steps
- Collect 150-300 real reviews per brand in a platform-compliant way.
- Validate LLM sentiment tags against a hand-labelled subset and report agreement.
- Add a time dimension to track claim and price changes.
