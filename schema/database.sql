-- CO₂ Impact Estimation System - Database Schema

CREATE DATABASE co2_db;

\c co2_db

CREATE SCHEMA IF NOT EXISTS open_beauty;
CREATE SCHEMA IF NOT EXISTS analytics;


-- Raw product data
CREATE TABLE open_beauty.raw_products (
    id SERIAL PRIMARY KEY,
    source TEXT NOT NULL,
    product_code TEXT UNIQUE,
    raw_json JSONB NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Parsed products
CREATE TABLE open_beauty.products (
    id SERIAL PRIMARY KEY,
    raw_product_id INT REFERENCES open_beauty.raw_products(id),
    product_name TEXT NOT NULL,
    code TEXT NOT NULL,
    brands TEXT,
    categories TEXT,
    countries TEXT,
    quantity_text TEXT,
    source TEXT,
    total_quantity FLOAT,
    unit TEXT CHECK (unit IS NULL OR unit IN ('g','ml', 'l', 'kg')),
    has_ingredients BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source, code)
);

-- Ingredients table
CREATE TABLE open_beauty.ingredients (
    id SERIAL PRIMARY KEY,
    inci_name TEXT UNIQUE NOT NULL,
    function TEXT,
    normalized_name TEXT,
    co2_impact TEXT CHECK (co2_impact IN ('low','medium','high')),
    is_good BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product-Ingredient relationship table
CREATE TABLE open_beauty.product_ingredients (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES open_beauty.products(id) ON DELETE CASCADE,
    ingredient_id INT REFERENCES open_beauty.ingredients(id) ON DELETE CASCADE,
    percentage_estimated FLOAT CHECK (percentage_estimated >= 0 AND percentage_estimated <= 100),
    rank INT,
    UNIQUE (product_id, ingredient_id)
);


-- Store classification for each unique ingredient
CREATE TABLE IF NOT EXISTS open_beauty.ingredient_emissions (
    ingredient_id INT PRIMARY KEY REFERENCES open_beauty.ingredients(id) ON DELETE CASCADE,
    estimated_impact TEXT CHECK (estimated_impact IN ('low', 'medium', 'high')),
    confidence_score FLOAT,
    method TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Store final product-level CO2 ratings
CREATE TABLE IF NOT EXISTS open_beauty.co2_metrics (
    product_id INT PRIMARY KEY REFERENCES open_beauty.products(id) ON DELETE CASCADE,
    estimated_impact TEXT CHECK (estimated_impact IN ('low', 'medium', 'high')),
    method TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Product indexes
CREATE INDEX idx_products_brand ON open_beauty.products(brands);
CREATE INDEX idx_products_category ON open_beauty.products(categories);
CREATE INDEX idx_products_raw_product ON open_beauty.products(raw_product_id);

-- Ingredient indexes
CREATE INDEX idx_ingredients_inci_name ON open_beauty.ingredients(inci_name);

-- Product-Ingredient relationship indexes
CREATE INDEX idx_product_ingredients_product ON open_beauty.product_ingredients(product_id);
CREATE INDEX idx_product_ingredients_ingredient ON open_beauty.product_ingredients(ingredient_id);

-- Emission indexes
CREATE INDEX idx_ingredient_emissions_ingredient ON open_beauty.ingredient_emissions(ingredient_id);
CREATE INDEX idx_co2_metrics_product ON open_beauty.co2_metrics(product_id);


-- COMMENTS
COMMENT ON SCHEMA open_beauty IS 'Main application schema for cosmetic products and CO₂ data';
COMMENT ON SCHEMA analytics IS 'Analytics and PowerBI views';

COMMENT ON TABLE open_beauty.raw_products IS 'Raw JSON data from Open Beauty Facts';
COMMENT ON TABLE open_beauty.products IS 'Parsed and structured product data';
COMMENT ON TABLE open_beauty.ingredients IS 'Master list of cosmetic ingredients (INCI names)';
COMMENT ON TABLE open_beauty.product_ingredients IS 'Many-to-many relationship between products and ingredients';
COMMENT ON TABLE open_beauty.ingredient_emissions IS 'CO₂ impact estimates for individual ingredients';
COMMENT ON TABLE open_beauty.co2_metrics IS 'Aggregated CO₂ metrics at product level';



