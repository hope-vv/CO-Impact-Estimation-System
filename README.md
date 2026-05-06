# CO₂ Impact Estimation System
### Environmental Impact Analysis for Cosmetic & Beauty Products

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Quick Start](#2-quick-start)
3. [System Architecture](#3-system-architecture)
4. [Configuration](#4-configuration)
5. [Classification Methodology](#5-classification-methodology)
6. [Product-Level Aggregation](#6-product-level-aggregation)
7. [Database Schema](#7-database-schema)
8. [Analytics & Reporting](#8-analytics--reporting)
9. [Validation & Limitations](#9-validation--limitations)
10. [Deployment](#10-deployment)
11. [References](#11-references)

---

## 1. Executive Summary

A comprehensive environmental impact analysis platform for cosmetic and beauty products. This system processes multi-source product data through an intelligent pipeline to classify ingredients by carbon footprint, enabling data-driven sustainability insights for stakeholders and decision-makers.

### Key Capabilities

- Zero-shot ML classification for ingredient environmental impact assessment
- Multi-stage data quality validation and enrichment
- Constellation schema for dimensional analysis
- Scalable batch processing architecture
- Executive dashboards with drill-through analytics

### Impact Levels at a Glance

| Level | Score | Criteria | Examples |
|-------|-------|----------|----------|
| **Low** | 1.0 | Naturally derived, biodegradable, minimal extraction footprint | Water, glycerin, plant extracts, common minerals |
| **Medium** | 2.0 | Synthesized or moderate processing; recyclable or renewable | Emulsifiers, preservatives, common surfactants |
| **High** | 3.0 | Petroleum-derived, energy-intensive synthesis, poor biodegradability | Synthetic fragrances, persistent polymers |
| **Unclassified** | 1.5 | Proprietary blends, obsolete names, or insufficient data | Trade secrets, deprecated INCI names |

---

## 2. Quick Start

### Installation

```bash
# Clone and setup
git clone <repository>
cd folder

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
python start_db
```

### Running the Pipeline

```bash
# Ingest and process product data
python main.py ingest data/file.jsonl.gz

# Inspect data quality
python main.py inspect

# View classification results
python main.py classify
```

---

## 3. System Architecture

### High-Level Pipeline

```
Raw Product Data (JSON/CSV)
         ↓
   [INGESTION]      — Load & Store raw product data
         ↓
   [PARSING]        — Extract & Normalize ingredient lists
         ↓
   [INSPECTION]     — Validate data quality
         ↓
   [CLASSIFICATION] — ML-based environmental impact assessment
         ↓
   [ANALYTICS]      — Dashboard generation & stakeholder reporting
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Data Pipeline** | Python | ETL orchestration and processing |
| **ML Classification** | DistilBART (Zero-shot) | Ingredient environmental scoring |
| **Database** | PostgreSQL | Dimensional data warehouse |
| **Analytics** | Power BI / SQL | Executive insights and drill-through |

### Project Structure

```
.
├── main.py                      # CLI entry point
├── init/                        # Configuration & initialization
│   ├── config.py               # Environment config management
│   └── __init__.py
├── inspecting/                  # Data ingestion & validation
│   ├── ingestion.py            # Raw data loader
│   ├── parser.py               # Data parsing & normalization
│   ├── inspector.py            # Quality validation
│   ├── raw_loader.py           # File handling
│   └── __init__.py
├── co2_impact/                  # ML classification module
│   ├── pipeline.py             # Pipeline orchestration
│   └── __init__.py
├── db/                          # Database management
│   ├── analytics_db.py         # Analytics queries
│   ├── start_db.py             # DB initialization
│   └── __init__.py
├── shared/                      # Shared utilities
│   ├── database.py             # Database abstraction
│   └── __init__.py
├── schema/                      # Database schema
│   └── database.sql            # PostgreSQL DDL
└── data/                        # Data directory
```

---

## 4. Configuration

Set these environment variables in `.env`:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/co2_db
DB_HOST=localhost
DB_PORT=5432
DB_USER=user_name
DB_PASSWORD=your_password
DB_NAME=co2_db

# Processing Configuration
DATA_BATCH_SIZE=1000

# ML Model Configuration
MODEL_NAME=facebook/bart-large-mnli
CONFIDENCE_THRESHOLD=0.5
```

---

## 5. Classification Methodology

### Zero-Shot Learning Approach

The system uses **zero-shot classification** via Hugging Face's distilBART-MNLI model, requiring no labeled training data.

**Why Zero-Shot?**
- ✅ No expensive labeling of 60K+ ingredients required
- ✅ Generalizable across new ingredients not seen at training time
- ✅ Interpretable: template-based prompts are fully transparent
- ✅ Scalable: incremental classification of new ingredients as needed

### Classification Pipeline

| Step | Stage | Description |
|------|-------|-------------|
| 1 | **Prompt Template** | Input ingredient mapped to: `"The environmental CO₂ impact of this ingredient is {label}"` |
| 2 | **Model Scoring** | DistilBART computes entailment probability for labels: `low`, `medium`, `high` |
| 3 | **Confidence Filtering** | Default threshold 0.6 — results below threshold marked as `unclassified` |
| 4 | **Batch Processing** | 1,000 ingredients/chunk, batched in groups of 32 for GPU efficiency |
| 5 | **Storage** | Results written to `ingredient_emissions` table with confidence scores |
| 6 | **Aggregation** | Weighted product-level impact computed from ingredient classifications |

### Model Characteristics

| Parameter | Value |
|-----------|-------|
| **Model** | distilbart-12-1-MNLI |
| **Task** | Natural Language Inference (NLI) |
| **Framework** | Hugging Face Transformers |
| **Parameters** | 82 million |
| **Inference Speed (GPU)** | ~3–5ms per ingredient |
| **Inference Speed (CPU)** | ~20–50ms per ingredient |
| **Batch Size** | 32 (tuned for V100 GPU) |
| **Device** | Auto-detect CUDA, fallback to CPU |

### Pipeline Configuration Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `use_threshold` | bool | `True` | Enable/disable confidence filtering |
| `confidence_threshold` | float | `0.6` | Minimum confidence score when filtering enabled |
| `chunk_size` | int | `1000` | Number of ingredients to process per batch |

### Usage Examples

```python
# Default: with confidence threshold
pipeline = CO2Pipeline(use_threshold=True)
pipeline.run_pipeline(chunk_size=1000)

# Research mode: include all results regardless of confidence
pipeline = CO2Pipeline(use_threshold=False)
pipeline.run_pipeline(chunk_size=5000)

# Memory-constrained: smaller chunk sizes
pipeline = CO2Pipeline()
pipeline.run_pipeline(chunk_size=500)
```

```bash
# CLI: default
python main.py classify

# CLI: custom parameters
python main.py classify --use-threshold false --chunk-size 5000
```

### Limitations & Uncertainties

- **Model Bias** — Zero-shot model trained on general text may not capture domain-specific chemical knowledge; rare or proprietary ingredients may receive uncertain scores.
- **Prompt Sensitivity** — Template phrasing affects outcomes; no ensemble weighting of multiple templates is currently implemented.
- **Ingredient Ambiguity** — Some INCI names map to multiple compounds; trade names and proprietary blends are not individually classified.

---

## 6. Product-Level Aggregation

### Aggregation Formula

Once ingredients are classified, product-level impact is computed as a **weighted mean**:

$$\text{Product Impact Score} = \frac{\sum_{i=1}^{n} (\text{Impact Score}_i \times \text{Percentage}_i)}{\sum_{i=1}^{n} \text{Percentage}_i}$$

**Numeric encoding:** `low = 1`, `medium = 2`, `high = 3`, `unclassified = 1.5` (neutral)

### Score-to-Category Mapping

| Score Range | Category | Interpretation |
|-------------|----------|----------------|
| 1.0 – 1.49 | **Low** | Predominantly natural or biodegradable formulation |
| 1.50 – 2.49 | **Medium** | Mixed formulation with some synthetic ingredients |
| 2.50 – 3.0 | **High** | Significant synthetic or petroleum-derived content |

### Special Cases

- **Missing Percentages** — If not disclosed, assumes equal distribution (1/n); all ingredients treated equally.
- **No Ingredients Listed** — Product marked `has_ingredients = FALSE` and excluded from analysis.
- **All Unclassified** — Product receives `unclassified` label to prevent false confidence.

---

## 7. Database Schema

### Constellation Schema Overview

| Table Type | Table Name | Description |
|------------|------------|-------------|
| **Fact** | `fact_products` | Product-level metrics and aggregated impact scores |
| **Fact** | `fact_ingredients` | Ingredient-level emission data and confidence scores |
| **Dimension** | `dim_impact` | Standardized impact categories (Low/Medium/High/Unclassified) |
| **Dimension** | `dim_brand` | Brand metadata and identifiers |
| **Dimension** | `dim_category` | Product category taxonomy |
| **Bridge** | `product_ingredients` | Many-to-many product–ingredient relationships with percentages |
| **Raw** | `raw_products` | Source tracking and original ingested records |

See [`schema/database.sql`](schema/database.sql) for complete DDL.

### Analytics Views for Power BI

#### `analytics.ingredients_co2` — Fact Table

Ingredient usage frequency and confidence distributions with trust level classification.


#### `analytics.products_co2` — Fact Table

Aggregates product-level CO₂ metrics with brand, category, and country dimensions.

**Measures:** product count, average impact score, % High/Medium/Low  
**Dimensions:** Brand, Category, Country, Impact Level

#### `analytics.product_ingredients` — Bridge Table

Enables drill-through from product level to individual ingredient composition.

#### `analytics.dim_impact` — Dimension Table

Optimized for Power BI sorting via an explicit `sort_order` column.

---

## 8. Analytics & Reporting

### Executive Overview KPIs

1. **Total Products Analyzed** — Count of products with at least one ingredient listed
2. **Average Product Impact Score** — Mean of all product-level weighted scores
3. **High-Impact Exposure** — Percentage of products classified as High impact

### Dashboard Visualizations

| Visual | Type | Insight |
|--------|------|---------|
| Impact Distribution | Donut Chart | Breakdown by category — highlights data gaps vs. real low-impact trends |
| Impact by Brand | Bar Chart | Top 10 brands by avg. impact — identifies sustainability leaders and laggards |
| Impact by Category | Tree Map | Products grouped by type — shows which categories pose highest environmental concern |
| High-Impact Ingredients | Table | Sorted by frequency — actionable list of ingredients to reformulate |
| Confidence Calibration | Scatter Plot | Confidence vs. frequency — identifies high-confidence, high-impact signals |
| Product Drill-Through | Detail Card | Ingredient composition with individual impacts and reformulation opportunities |

### Ingredient Intelligence Metrics

- Top high-impact ingredients sorted by product frequency
- Confidence score distribution histogram (0.0–1.0)
- Ingredient coverage: percentage of ingredients successfully classified

---

## 9. Validation & Limitations

### Sanity Checks

| Check | Expected | Action if Failed |
|-------|----------|-----------------|
| Impact score range | [1.0, 3.0] for all products | Review aggregation logic — indicates data integrity issue |
| Low-confidence rate | <20% of ingredients below 0.6 | Possible model instability or poor ingredient data |
| Ingredient coverage | ≥80% of products have lists | Review OpenBeautyFacts pipeline — source data quality issue |
| Duplicate detection | No variant spellings in final dataset | Re-run deduplication with normalized INCI names |

### Manual Validation

For critical product categories (medical-grade, high-risk), manual expert review is recommended:
1. Sample 100 random high-impact products
2. Verify ingredient classifications align with domain knowledge
3. Document discrepancies for model retraining

### Current Limitations

- **Binary Impact Coding** — Low/Medium/High loses granularity; future work: 5-point or continuous scale
- **Missing Contextual Data** — No sourcing info, manufacturing emissions, or packaging impact included
- **No Cumulative Toxicity** — Ingredients treated independently; no interaction or synergy effects modeled


## 11. References

### Primary Data Source

**OpenBeautyFacts** — https://openbeautyfacts.org/
- 100,000+ cosmetic product records (crowdsourced, variable quality)
- Product metadata: brand, category, country, quantity

### ML Model

**Hugging Face Transformers** — https://huggingface.co/models
- Model: `distilbart-12-1-MNLI`
