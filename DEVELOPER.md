# Developer Documentation

## Overview

This document provides a concise guide for developers working on the CO-Impact-Estimation-System.

---

## Architecture

The system follows a modular pipeline architecture:

```
JSONL.gz Data → Ingestion → Parsing → Classification → Aggregation → Analytics
```

**Key Design Principles:**
- Modular stages can run independently
- Incremental processing (resumable on failure)
- All state persisted in PostgreSQL
- Batch operations for performance
- Database-first approach

---

## Project Structure

```
CO-Impact-Estimation-System/
├── main.py                    # CLI entry point
├── init/config.py             # Environment configuration
├── inspecting/                # Data ingestion & parsing
│   ├── ingestion.py          # Load JSONL.gz files
│   ├── parser.py             # Extract & clean products/ingredients
│   ├── inspector.py          # Data quality checks
│   └── raw_loader.py         # File decompression
├── co2_impact/               # ML classification
│   ├── pipeline.py           # Classification orchestrator (database-backed)
│   └── csv_pipeline.py       # Alternative: Offline CSV-based pipeline
├── shared/                   # Shared utilities
│   └── database.py           # PostgreSQL connection management
├── schema/
│   └── database.sql          # Database schema
└── db/
    ├── start_db.py           # Schema initialization
    └── analytics_db.py       # Analytics views
```

---

## Core Modules

### Configuration (`init/config.py`)
Loads environment variables with fallback defaults. Uses singleton pattern.

```python
from init.config import get_config
config = get_config()
```

### Database (`shared/database.py`)
Manages PostgreSQL connection pooling and batch operations.

```python
from shared.database import get_db
db = get_db()
db.execute_query("SELECT * FROM products LIMIT 10", fetch=True)
```

### Ingestion (`inspecting/ingestion.py`)
Loads raw JSONL.gz files in batches (default 2,000 records). Deduplicates via SQL constraints.

### Parsing (`inspecting/parser.py`)
Extracts metadata and ingredients from raw products. Multi-stage cleaning pipeline:
1. Remove prefixes and quantity indicators
2. Parse quantities (e.g., "100ml" → 100 ml)
3. Extract ingredient lists
4. Normalize ingredient names (lowercase, remove special chars)
5. Filter garbage and invalid entries

### Classification (`co2_impact/pipeline.py`)
Uses Hugging Face zero-shot model (distilBART-MNLI) to classify ingredients. Supports flexible batch processing and confidence threshold control.

**Key Parameters:**
- `use_threshold` (bool): Apply confidence filtering (default: True, min: 0.6)
- `chunk_size` (int): Process N ingredients per batch (default: 1000)

**Process:**
1. Query unclassified ingredients
2. Process in configurable chunks
3. Batch classify (32 per batch)
4. Apply confidence threshold if enabled
5. Store results in database
6. Aggregate to product level (SQL)

### Data Inspection (`inspecting/inspector.py`)
Generates data quality reports with coverage metrics.

---

## Database Schema

**Core Tables:**
- `raw_products` - Original unprocessed data (JSONB storage)
- `products` - Parsed product metadata
- `ingredients` - Unique ingredient registry
- `product_ingredients` - Many-to-many relationship with percentages
- `ingredient_emissions` - Classification results with confidence scores
- `co2_metrics` - Product-level aggregated impact scores

**Analytics Views:**
- `analytics.products_co2` - Product metrics for reporting
- `analytics.ingredients_co2` - Ingredient impacts with trust levels
- `analytics.product_ingredients` - Drill-through data
- `analytics.dim_impact` - Shared impact dimension

See [schema/database.sql](schema/database.sql) for full schema definition.

---

## Development Setup

### Initialize Environment
```bash
python -m venv venv
source venv/bin/activate
pip install -r requiements..txt
cp env.example .env
# Edit .env with database credentials
```

### Initialize Database
```bash
python db/start_db.py
```

### Run Pipeline
```bash
python main.py ingest data/products.jsonl.gz --source openbeautyfacts
python main.py parse
python main.py classify --use-threshold true --chunk-size 1000
```

---

## Common Tasks

### Test Database Connection
```bash
psql -U $DB_USER -d $DB_NAME -h $DB_HOST -c "SELECT COUNT(*) FROM products"
```

### Check Pipeline Progress
```sql
SELECT 'Raw Products' as stage, COUNT(*) FROM raw_products
UNION ALL
SELECT 'Parsed Products', COUNT(*) FROM products
UNION ALL
SELECT 'Classified Ingredients', COUNT(*) FROM ingredient_emissions
UNION ALL
SELECT 'Product Metrics', COUNT(*) FROM co2_metrics;
```

### Run Data Quality Inspection
```bash
python main.py inspect --export
```

### Check Unclassified Ingredients
```sql
SELECT COUNT(*) FROM ingredients 
WHERE id NOT IN (SELECT ingredient_id FROM ingredient_emissions);
```

---

## Performance

| Operation | Time | Memory |
|-----------|------|--------|
| Ingestion (100K) | ~30 seconds | <500MB |
| Parsing (100K) | ~45 seconds | ~1GB |
| Classification (60K ingredients, GPU) | ~15 minutes | 2-3GB |
| Classification (60K ingredients, CPU) | ~2 hours | 2-3GB |

**Optimization Tips:**
- GPU provides 5-8x speedup over CPU
- Adjust `--chunk-size` based on memory: smaller chunks = lower memory
- `--use-threshold false` to include low-confidence results
- Incremental processing skips already-classified ingredients

---

## Deployment

1. Configure `.env` with production credentials
2. Initialize database: `python db/start_db.py`
3. Ingest data: `python main.py ingest <file> --source <name>`
4. Parse products: `python main.py parse`
5. Classify ingredients:
   ```bash
   # With confidence threshold (default)
   python main.py classify
   
   # Without threshold, custom chunk size
   python main.py classify --use-threshold false --chunk-size 5000
   ```
6. Create analytics views: `python db/analytics_db.py`
7. Connect Power BI to `analytics.*` views

---


## References

- See [README.md](README.md) for system overview
- See [IMPACT.md](IMPACT.md) for methodology
- See [schema/database.sql](schema/database.sql) for database structure
