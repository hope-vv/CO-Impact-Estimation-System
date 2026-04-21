"""
CO₂ Impact Estimation System - Main Entry Point

Usage:
    python main.py <command> [options]

Commands:
    ingest      - Ingest raw data files into database
    parse       - Parse raw products into structured tables
    inspect     - Run data quality inspection
    classify    - Run CO₂ impact classification pipeline
    help        - Show this help message

Examples:
    python main.py ingest data/products.jsonl.gz
    python main.py parse --limit 10000
    python main.py inspect
    python main.py classify
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared import get_db
from inspecting import RawDataIngestion, ProductParser, DataInspector, load_raw_data
from co2_impact import CO2Pipeline
from init.config import get_config


def cmd_ingest(args):
    print("STARTING DATA INGESTION")

    file_path = args.file
    source = args.source
    
    if not Path(file_path).exists():
        print(f"File not found: {file_path}")
        sys.exit(1)
    
    print(f"Loading data from: {file_path}")
    print(f"Source: {source}")
    
    data_iter = load_raw_data(file_path)
    ingestion = RawDataIngestion(source=source)
    count = ingestion.ingest_products(data_iter)
    
    print(f"Successfully ingested {count:,} records")


def cmd_parse(args):
    print("STARTING PRODUCT PARSING")
    
    parser = ProductParser()
    print("Parsing all products")
    
    parser.parse_all_products()

    print("Parsing complete")


def cmd_inspect(args):
    print("STARTING DATA INSPECTION")

    inspector = DataInspector()
    results = inspector.run_full_inspection()
    
    if args.export:
        output_dir = "./data/processed"
        inspector.export_to_csv(output_dir)
        print(f"Exported inspection data to {output_dir}")
    
    print("Inspection complete")

def cmd_classify(args):
    print("STARTING CO₂ CLASSIFICATION PIPELINE")
    use_threshold = args.use_threshold
    chunk_size = args.chunk_size
    
    pipeline = CO2Pipeline(use_threshold=use_threshold)
    pipeline.run_pipeline(chunk_size=chunk_size)
    print("Classification complete")


def cmd_help(args):
    print(__doc__)


def main():
    parser = argparse.ArgumentParser(
        prog="co2-impact-estimator",
        description="CO₂ Impact Estimation System"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    config = get_config()
    print("DATABASE_URL:", config.DATABASE_URL)
    print("DB_HOST:", config.DB_HOST)
    print("DB_NAME:", config.DB_NAME)
    #ingest
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw data files")
    ingest_parser.add_argument("file", help="Path to data file")
    ingest_parser.add_argument("--source", default="openbeautyfacts", 
                              help="Data source identifier")
    ingest_parser.set_defaults(func=cmd_ingest)
    
    # Parse
    parse_parser = subparsers.add_parser("parse", help="Parse raw products")
    parse_parser.add_argument("--limit", type=int, default=0,
                            help="Maximum number of products to parse (0 = all)")
    parse_parser.set_defaults(func=cmd_parse)

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Run data quality inspection")
    inspect_parser.add_argument("--export", action="store_true",
                              help="Export inspection data to CSV")
    inspect_parser.set_defaults(func=cmd_inspect)

    # Classify command
    classify_parser = subparsers.add_parser("classify", help="Run CO₂ classification")
    classify_parser.add_argument("--use-threshold", type=lambda x: x.lower() in ('true', '1', 'yes'), 
                                default=True, help="Enable/disable confidence threshold (true/false, default: true)")
    classify_parser.add_argument("--chunk-size", type=int, default=1000,
                                help="Number of ingredients to process per chunk (default: 1000)")
    classify_parser.set_defaults(func=cmd_classify)

    # help
    help_parser = subparsers.add_parser("help", help="Show help message")
    help_parser.set_defaults(func=cmd_help)
    
    args = parser.parse_args()
    
    if hasattr(args, "func"):
        try:
            args.func(args)
        except Exception as e:
            print(f"Command failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
