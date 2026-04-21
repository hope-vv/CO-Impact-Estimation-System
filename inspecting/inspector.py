import sys
import os
import pandas as pd
from typing import Dict, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.database import get_db


class DataInspector:
    def __init__(self):
        self.db = get_db()
        print("Initialized DataInspector")
    
    def run_full_inspection(self) -> Dict[str, Any]:
        print("Running full data quality inspection")
        
        results = {
            'raw_products': self._inspect_raw_products(),
            'products': self._inspect_products(),
            'ingredients': self._inspect_ingredients(),
            'product_ingredients': self._inspect_product_ingredients(),
            'data_quality': self._inspect_data_quality()
        }
        
        self._log_results(results)
        
        return results
    
    def _inspect_raw_products(self) -> Dict[str, Any]:
        query = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(DISTINCT source) as unique_sources,
                MIN(ingested_at) as earliest_date,
                MAX(ingested_at) as latest_date
            FROM open_beauty.raw_products
        """
        
        with self.db.get_cursor(dict_cursor=True) as cur:
            cur.execute(query)
            return dict(cur.fetchone())
    
    def _inspect_products(self) -> Dict[str, Any]:
        query = """
            SELECT 
                COUNT(*) as total_count,
                COUNT(*) FILTER (WHERE has_ingredients) as with_ingredients,
                COUNT(*) FILTER (WHERE NOT has_ingredients) as without_ingredients,
                COUNT(DISTINCT brands) as unique_brands,
                COUNT(*) FILTER (WHERE brands IS NULL OR brands = '') as missing_brands
            FROM open_beauty.products
        """
        
        with self.db.get_cursor(dict_cursor=True) as cur:
            cur.execute(query)
            result = dict(cur.fetchone())
            
            if result['total_count'] > 0:
                result['ingredients_coverage'] = (
                    result['with_ingredients'] / result['total_count'] * 100
                )
            
            return result
    
    def _inspect_ingredients(self) -> Dict[str, Any]:
        query = """
            SELECT 
                COUNT(*) as total_ingredients,
                COUNT(DISTINCT inci_name) as unique_ingredients
            FROM open_beauty.ingredients
        """
        
        with self.db.get_cursor(dict_cursor=True) as cur:
            cur.execute(query)
            return dict(cur.fetchone())
    
    def _inspect_product_ingredients(self) -> Dict[str, Any]:
        query = """
            SELECT 
                COUNT(*) as total_relationships,
                COUNT(*) FILTER (WHERE percentage_estimated IS NOT NULL) as with_percentage,
                AVG(rank) as avg_ingredients_per_product
            FROM open_beauty.product_ingredients
        """
        
        with self.db.get_cursor(dict_cursor=True) as cur:
            cur.execute(query)
            return dict(cur.fetchone())
    
    def _inspect_data_quality(self) -> Dict[str, Any]:
        dup_query = """
            SELECT inci_name, COUNT(*) as count
            FROM open_beauty.ingredients
            GROUP BY inci_name
            HAVING COUNT(*) > 1
        """
        
        with self.db.get_cursor(dict_cursor=True) as cur:
            cur.execute(dup_query)
            duplicates = cur.fetchall()
        
        return {
            'duplicate_ingredients': len(duplicates),
            'duplicate_examples': [dict(d) for d in duplicates[:5]]
        }
    
    def _log_results(self, results: Dict[str, Any]):
        print("DATA QUALITY INSPECTION RESULTS")
        
        print(f"\nRaw Products:")
        for key, value in results['raw_products'].items():
            print(f"  {key}: {value}")
        
        print(f"\nProducts:")
        for key, value in results['products'].items():
            print(f"  {key}: {value}")
        
        print(f"\nIngredients:")
        for key, value in results['ingredients'].items():
            print(f"  {key}: {value}")
        
        print(f"\nProduct-Ingredient Relationships:")
        for key, value in results['product_ingredients'].items():
            print(f"  {key}: {value}")
        
        print(f"\nData Quality:")
        for key, value in results['data_quality'].items():
            print(f"  {key}: {value}")
        
    
    def export_to_csv(self, output_dir: str = './data/processed'):
        """Export inspection data to CSV files."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        query = """
            SELECT 
                COUNT(*) FILTER (WHERE product_name IS NOT NULL) as has_name,
                COUNT(*) FILTER (WHERE brands IS NOT NULL) as has_brands,
                COUNT(*) FILTER (WHERE categories IS NOT NULL) as has_categories,
                COUNT(*) FILTER (WHERE has_ingredients) as has_ingredients
            FROM open_beauty.products
        """
        
        df = pd.read_sql(query, self.db.get_connection())
        df.to_csv(f"{output_dir}/data_field_counts.csv", index=False)
        
        logger.info(f"Exported inspection data to {output_dir}")
