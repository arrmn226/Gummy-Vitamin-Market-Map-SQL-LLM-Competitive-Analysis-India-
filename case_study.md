# Case Study: Finding White Space in India's Gummy Vitamin Market

**Role:** Solo project | **Stack:** MySQL, Python, Pandas, Claude API | **Context:** Built while working on growth at VITHUB, a D2C gummy brand

## The problem
A new gummy brand has to decide where to compete: price, benefit, or claim. Most of that information sits scattered across brand sites and marketplace listings. I wanted one structured view of the market.

## What I built
- A two-table database (`brands`, `reviews`) covering 9 competitors, with prices parsed into min price, pack size and cost per gummy.
- 12 SQL queries for pricing tiers, claim coverage, benefit-lane crowding and review patterns.
- An LLM layer using Claude to tag review sentiment and emotions (trust, price-pain, taste, results), plus a Gap Finder that turns the SQL outputs into positioning hypotheses. **[EDIT: add one line on how you validated the tags]**

## What I found

**1. Sticker price hides the real price.**
Per gummy, What's Up Wellness is the most expensive brand (about ₹18.7) even though it ranks only 4th on sticker price. Power Gummies has the highest sticker price (₹900) but sits mid-table per gummy (₹15). Carbamide Forte is the cheapest per gummy (₹7.5) while looking mid-market.
*Action:* compare on cost per gummy in ads and listings, and position value against the brands that look cheap but aren't.

**2. Hair and biotin is crowded; other lanes are nearly empty.**
6 of 9 brands compete on hair/biotin. Sleep is owned by one brand (Carbamide Forte) and gut health by one (Purna, via ACV).
*Action:* test a sleep or gut-focused hero SKU before adding another hair product.

**3. Claims are under-owned.**
Only 3 of 9 brands claim sugar-free, 1 of 9 is vegan, and 2 of 9 blend Ayurvedic ingredients (What's Up Wellness, Nyumi).
*Action:* a sugar-free + vegan + Ayurvedic-hybrid combination has no direct competitor in this set. Validate demand with a small ad test on those claims.

## Data limitations (and what I'd do next)
- The review-level sample has only 90 distinct review texts and no ratings below 3 stars, so I treat review-based results as a demonstration of the method and do not base conclusions on them.
- Keyword matching is a first pass, and the LLM tags need validating against a hand-labelled subset.
- Next: collect 150-300 real reviews per brand, re-run the pipeline, and measure agreement between LLM tags and human labels.

## What I learned
Counting the wrong unit is easy: my first version counted reviews where I meant brands, which produced a "1833% market penetration". Splitting the data into `brands` and `reviews` tables fixed the whole class of error, and I added a data-quality query so I audit the data before analysing it.

**Links:** GitHub repo | Gap Finder screenshot **[ADD]**
