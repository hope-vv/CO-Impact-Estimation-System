import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

schema_sql = """
-- 1. Create the analytics schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS analytics;

-- 2. Ingredient Analytics View
CREATE OR REPLACE VIEW analytics.ingredients_co2 AS
SELECT
    i.id                  AS ingredient_id,
    i.inci_name,
    COALESCE(e.estimated_impact, 'unknown') AS estimated_impact,
    COALESCE(e.confidence_score, 0)          AS confidence_score,
    CASE e.estimated_impact
        WHEN 'low'    THEN 1
        WHEN 'medium' THEN 2
        WHEN 'high'   THEN 3
        ELSE 0 
    END AS impact_score,
    CASE 
        WHEN e.confidence_score > 0.9 THEN 'High Trust'
        WHEN e.confidence_score > 0.7 THEN 'Medium Trust'
        WHEN e.confidence_score > 0   THEN 'Low Trust'
        ELSE 'Unverified'
    END AS trust_level,
    COALESCE(e.method, 'none') AS method,
    e.created_at AS recorded_at  -- FIXED: Changed updated_at to created_at
FROM open_beauty.ingredients i
LEFT JOIN open_beauty.ingredient_emissions e
    ON i.id = e.ingredient_id;

-- 3. Product CO2 Fact View
CREATE OR REPLACE VIEW analytics.products_co2 AS
SELECT
    p.id              AS product_id,
    p.product_name,
    p.brands,
    p.categories,
    p.countries,
    p.total_quantity,
    p.unit,
    COALESCE(c.estimated_impact, 'unknown') AS estimated_impact,
    CASE c.estimated_impact
        WHEN 'low'    THEN 1
        WHEN 'medium' THEN 2
        WHEN 'high'   THEN 3
        ELSE 0
    END AS impact_score,
    COALESCE(c.method, 'none') AS method,
    c.updated_at AS recorded_at -- This table uses updated_at
FROM open_beauty.products p
LEFT JOIN open_beauty.co2_metrics c
    ON p.id = c.product_id;

-- 4. Product-Ingredient Bridge View
CREATE OR REPLACE VIEW analytics.product_ingredients AS
SELECT
    pi.product_id,
    pi.ingredient_id,
    pi.percentage_estimated,
    pi.rank
FROM open_beauty.product_ingredients pi;

-- 5. Impact Dimension (Optimized for Power BI Sorting)
CREATE OR REPLACE VIEW analytics.dim_impact AS
SELECT 'low' AS impact_label, 1 AS impact_score, 3 AS sort_order, 'Low environmental impact' AS description
UNION ALL
SELECT 'medium', 2, 2, 'Medium environmental impact'
UNION ALL
SELECT 'high', 3, 1, 'High environmental impact'
UNION ALL
SELECT 'unknown', 0, 4, 'Not yet classified';
"""

def run_schema():
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL missing. Please check your .env file.")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            print("Analytics views created successfully!")
        conn.close()
    except Exception as e:
        print(f"Error creating schema: {e}")


if __name__ == "__main__":
    run_schema()