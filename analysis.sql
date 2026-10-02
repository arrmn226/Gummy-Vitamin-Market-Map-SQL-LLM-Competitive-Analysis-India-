-- =====================================================================
-- India Gummy Vitamin Market: Competitive Intelligence (MySQL 8+)
-- Two tables: brands (1 row per brand) and reviews (1 row per review).
-- Brand-level facts live in `brands`, so counting brands never counts
-- reviews by mistake.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS vithub_analytics;
USE vithub_analytics;

DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS brands;

CREATE TABLE brands (
    brand_id              INT PRIMARY KEY,
    brand_name            VARCHAR(50) NOT NULL,
    target_market         VARCHAR(20),
    positioning_statement TEXT,
    pricing_inr           VARCHAR(40),
    usps_key_features     TEXT,
    min_price_inr         INT,            -- parsed from pricing_inr
    max_price_inr         INT,
    pack_size_min         INT,            -- smallest pack count quoted
    price_per_gummy_inr   DECIMAL(6,2)    -- min_price / pack_size_min
);

CREATE TABLE reviews (
    review_id       VARCHAR(12) PRIMARY KEY,
    brand_id        INT NOT NULL,
    review_text     TEXT,
    star_rating     INT,
    review_platform VARCHAR(30),
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

-- Load (adjust paths; needs local_infile enabled, or use your client's import wizard)
-- LOAD DATA LOCAL INFILE 'brands.csv'  INTO TABLE brands
--   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;
-- LOAD DATA LOCAL INFILE 'reviews.csv' INTO TABLE reviews
--   FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' IGNORE 1 LINES;

-- Note: Purna Gummies quotes "30-60 count"; pack_size_min uses 30, so its
-- price per gummy (13.33) is an upper-bound assumption.

-- ---------------------------------------------------------------------
-- Q0. DATA QUALITY AUDIT (run this first)
-- ---------------------------------------------------------------------
SELECT
    COUNT(*)                                                     AS total_reviews,
    COUNT(DISTINCT TRIM(SUBSTRING_INDEX(review_text, ' [Verified', 1))) AS distinct_review_texts,
    MIN(star_rating)                                             AS min_rating,
    MAX(star_rating)                                             AS max_rating
FROM reviews;

-- =====================================================================
-- PART A: BRAND-LEVEL ANALYSIS (reliable; does not depend on review text)
-- =====================================================================

-- Q1. Pricing tiers
SELECT
    CASE
        WHEN min_price_inr < 400 THEN '1 Value (under 400)'
        WHEN min_price_inr BETWEEN 400 AND 749 THEN '2 Mid-market (400-749)'
        ELSE '3 Premium (750+)'
    END AS pricing_tier,
    COUNT(*) AS total_brands,
    ROUND(AVG(min_price_inr), 2) AS avg_starting_price_inr,
    GROUP_CONCAT(brand_name ORDER BY min_price_inr SEPARATOR ', ') AS brands_in_tier
FROM brands
GROUP BY pricing_tier
ORDER BY pricing_tier;

-- Q2. Sticker price vs real cost per gummy (rank changes!)
SELECT
    brand_name,
    min_price_inr,
    pack_size_min,
    price_per_gummy_inr,
    RANK() OVER (ORDER BY min_price_inr DESC)        AS sticker_price_rank,
    RANK() OVER (ORDER BY price_per_gummy_inr DESC)  AS per_gummy_rank
FROM brands
ORDER BY per_gummy_rank;

-- Q3. Sugar-free claims (brand count, not review count)
SELECT
    COUNT(*) AS total_brands,
    SUM(CASE WHEN LOWER(CONCAT(usps_key_features, ' ', positioning_statement))
             LIKE '%sugar%' THEN 1 ELSE 0 END) AS brands_claiming_sugar_free,
    ROUND(100.0 * SUM(CASE WHEN LOWER(CONCAT(usps_key_features, ' ', positioning_statement))
             LIKE '%sugar%' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_of_brands
FROM brands;
-- Caution: "No added sugar" and "zero added sugar" both match; Tata 1mg etc.
-- do not mention sugar at all, which is different from "contains sugar".

-- Q4. Vegan / vegetarian claims
SELECT
    COUNT(*) AS total_brands,
    SUM(CASE WHEN LOWER(usps_key_features) LIKE '%vegan%'
               OR LOWER(usps_key_features) LIKE '%vegetarian%' THEN 1 ELSE 0 END) AS brands_claiming_vegan,
    GROUP_CONCAT(CASE WHEN LOWER(usps_key_features) LIKE '%vegan%'
               OR LOWER(usps_key_features) LIKE '%vegetarian%' THEN brand_name END
               SEPARATOR ', ') AS which_brands
FROM brands;

-- Q5. Ayurvedic-Western hybrid vs purely Western (checks positioning too)
SELECT
    brand_name,
    CASE WHEN LOWER(CONCAT(usps_key_features, ' ', positioning_statement))
              REGEXP 'amla|aloe|ayurved'
         THEN 'Ayurvedic-Western hybrid' ELSE 'Western actives only' END AS composition_type
FROM brands
ORDER BY composition_type, brand_name;

-- Q6. Benefit-lane crowding: how many BRANDS compete in each lane
SELECT
    SUM(LOWER(CONCAT(usps_key_features, ' ', positioning_statement)) REGEXP 'biotin|hair')       AS hair_skin_brands,
    SUM(LOWER(CONCAT(usps_key_features, ' ', positioning_statement)) REGEXP 'sleep|melatonin')   AS sleep_brands,
    SUM(LOWER(CONCAT(usps_key_features, ' ', positioning_statement)) REGEXP 'immunity|zinc')     AS immunity_brands,
    SUM(LOWER(CONCAT(usps_key_features, ' ', positioning_statement)) REGEXP 'acv|gut|digest')    AS gut_brands
FROM brands;

-- =====================================================================
-- PART B: REVIEW-LEVEL ANALYSIS
-- These run correctly, but the sample has very few distinct review
-- texts (see Q0), so treat results as a demonstration of the method,
-- not as market findings. Re-run on real scraped reviews.
-- =====================================================================

-- Q7. Rating distribution per brand (counts AND share)
SELECT
    b.brand_name,
    COUNT(*) AS n_reviews,
    ROUND(AVG(r.star_rating), 2) AS avg_rating,
    ROUND(100.0 * SUM(r.star_rating >= 4) / COUNT(*), 1) AS pct_4_5_star,
    ROUND(100.0 * SUM(r.star_rating <= 3) / COUNT(*), 1) AS pct_3_star_or_less
FROM reviews r JOIN brands b USING (brand_id)
GROUP BY b.brand_name
ORDER BY avg_rating DESC;

-- Q8. Platform comparison with sample sizes
SELECT review_platform,
       COUNT(*) AS n_reviews,
       ROUND(AVG(star_rating), 2) AS avg_rating
FROM reviews
GROUP BY review_platform
ORDER BY avg_rating DESC;

-- Q9. Dominant platform per brand (the original MAX() returned the
--     alphabetically last platform, not the most frequent one)
WITH counts AS (
    SELECT brand_id, review_platform, COUNT(*) AS n,
           ROW_NUMBER() OVER (PARTITION BY brand_id ORDER BY COUNT(*) DESC) AS rn
    FROM reviews
    GROUP BY brand_id, review_platform
)
SELECT b.brand_name, c.review_platform AS dominant_platform, c.n AS reviews_on_platform
FROM counts c JOIN brands b USING (brand_id)
WHERE c.rn = 1;

-- Q10. Heat-damage complaints per 100 reviews (normalised by review volume)
SELECT
    b.brand_name,
    SUM(LOWER(r.review_text) REGEXP 'melt|sticky|stuck together|clump') AS heat_complaints,
    ROUND(100.0 * SUM(LOWER(r.review_text) REGEXP 'melt|sticky|stuck together|clump') / COUNT(*), 1) AS per_100_reviews
FROM reviews r JOIN brands b USING (brand_id)
GROUP BY b.brand_name
ORDER BY per_100_reviews DESC;

-- Q11. Price complaints per 100 reviews
SELECT
    b.brand_name,
    SUM(LOWER(r.review_text) REGEXP 'expensive|overpriced|costly|pricey|premium side') AS price_complaints,
    ROUND(100.0 * SUM(LOWER(r.review_text) REGEXP 'expensive|overpriced|costly|pricey|premium side') / COUNT(*), 1) AS per_100_reviews
FROM reviews r JOIN brands b USING (brand_id)
GROUP BY b.brand_name
ORDER BY per_100_reviews DESC;

-- Q12. Does price buy satisfaction? (brand-level join)
SELECT
    b.brand_name,
    b.min_price_inr,
    b.price_per_gummy_inr,
    COUNT(r.review_id) AS n_reviews,
    ROUND(AVG(r.star_rating), 2) AS avg_rating
FROM brands b JOIN reviews r USING (brand_id)
GROUP BY b.brand_id, b.brand_name, b.min_price_inr, b.price_per_gummy_inr
ORDER BY b.price_per_gummy_inr;
