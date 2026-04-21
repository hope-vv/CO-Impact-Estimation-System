# Database Setup Guide

## Quick Start

```bash
# 1. Initialize database schema
python db/start_db.py

# 2. Load data from CSVs
python db/to_db.py

# 3. Create analytics views
python db/analytics_db.py
```

## When to Use Each Script

| Script | Purpose | When to Run |
|--------|---------|------------|
| `start_db.py` | Creates base schema (`open_beauty`, tables, relationships) | Initial setup only |
| `to_db.py` | Loads CSV data (ingredient_emissions, co2_metrics) into tables | only in case of using a csv_pipeline, After schema creation or data refresh |
| `analytics_db.py` | Creates analytics views for reporting | After data loading |

## Prerequisites

- PostgreSQL database running
- `.env` file: see env.example
- Example: `postgresql://user:password@localhost:5432/beautydb`
