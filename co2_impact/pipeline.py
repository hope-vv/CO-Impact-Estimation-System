import sys
import os
import torch
from typing import Dict, List
from transformers import pipeline
from psycopg2.extras import execute_values

from shared.database import get_db

class CO2Model:
    DEFAULT_ZEROSHOT_MODEL = "valhalla/distilbart-mnli-12-1"

    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1
        print(f"Loading model on {'GPU' if self.device == 0 else 'CPU'}...")
        self.classifier = pipeline(
            "zero-shot-classification",
            model=self.DEFAULT_ZEROSHOT_MODEL,
            device=self.device
        )

    def classify_batch(self, texts: List[str]):
        labels = ["low", "medium", "high"]

        template = "The environmental CO2 impact of this ingredient is {}"
        
        results = self.classifier(
            texts,
            candidate_labels=labels,
            hypothesis_template=template
        )
        
        formatted = []
        if isinstance(results, dict): results = [results]
            
        for res in results:
            formatted.append({
                'ingredient': res['sequence'],
                'label': res['labels'][0],
                'score': float(res['scores'][0])
            })
        return formatted

class IngredientClassifier:
    def __init__(self, confidence_threshold: float = 0.6, use_threshold: bool = True):
        self.model = CO2Model()
        self.threshold = confidence_threshold
        self.use_threshold = use_threshold

    def classify_ingredients(self, ingredients: List[str]) -> Dict[str, Dict]:
        results = {}
        batch_size = 32
        
        print(f"Classifying {len(ingredients)} ingredients in batches...")
        for i in range(0, len(ingredients), batch_size):
            batch = ingredients[i:i + batch_size]
            batch_results = self.model.classify_batch(batch)
            
            for res in batch_results:
                if self.use_threshold:
                    if res['score'] >= self.threshold:
                        results[res['ingredient']] = {
                            'ingredient': res['ingredient'],
                            'label': res['label'],
                            'score': res['score'],
                            'method': 'zero-shot-distilbart'
                        }
                else:
                    results[res['ingredient']] = {
                        'ingredient': res['ingredient'],
                        'label': res['label'],
                        'score': res['score'],
                        'method': 'zero-shot-distilbart'
                    }
        return results

class CO2Pipeline:
    def __init__(self, confidence_threshold: float = 0.6, use_threshold: bool = True):
        self.db = get_db()
        self.classifier = IngredientClassifier(
            confidence_threshold=confidence_threshold,
            use_threshold=use_threshold
        )

    def get_ingredient_id_map(self):
        query = "SELECT id, inci_name FROM open_beauty.ingredients"
        rows = self.db.execute_query(query, fetch=True)
        return {row[1]: row[0] for row in rows} if rows else {}

    def store_ingredient_emissions(self, results: Dict[str, Dict]):
        self.db.execute_query("TRUNCATE open_beauty.ingredient_emissions", fetch=False)
        
        id_map = self.get_ingredient_id_map()
        insert_query = """
            INSERT INTO open_beauty.ingredient_emissions
            (ingredient_id, estimated_impact, confidence_score, method)
            VALUES %s
        """
        
        data = []
        for res in results.values():
            if res['ingredient'] in id_map:
                data.append((
                    id_map[res['ingredient']], 
                    res['label'], 
                    res['score'], 
                    res['method']
                ))

        if not data:
            return

        with self.db.get_cursor() as cur:
            execute_values(cur, insert_query, data)
        
        print(f"Saved {len(data)} ingredient classifications.")

    def calculate_product_metrics(self):
        self.db.execute_query("TRUNCATE open_beauty.co2_metrics", fetch=False)

        insert_query = """
            INSERT INTO open_beauty.co2_metrics 
            (product_id, estimated_impact, method)
            SELECT
                sub.product_id,
                CASE
                    WHEN sub.avg_score < 1.5 THEN 'low'
                    WHEN sub.avg_score < 2.5 THEN 'medium'
                    ELSE 'high'
                END AS estimated_impact,
                'weighted_ingredient_aggregation'
            FROM (
                SELECT
                    p.id AS product_id,
                    SUM(
                        CASE
                            WHEN ie.estimated_impact = 'low' THEN 1
                            WHEN ie.estimated_impact = 'medium' THEN 2
                            WHEN ie.estimated_impact = 'high' THEN 3
                        END * COALESCE(pi.percentage_estimated, 1)
                    ) / SUM(COALESCE(pi.percentage_estimated, 1)) AS avg_score
                FROM open_beauty.products p
                JOIN open_beauty.product_ingredients pi ON pi.product_id = p.id
                INNER JOIN open_beauty.ingredient_emissions ie ON ie.ingredient_id = pi.ingredient_id
                WHERE p.has_ingredients = true
                GROUP BY p.id
            ) sub
        """
        self.db.execute_query(insert_query, fetch=False)
        print("Product CO2 metrics calculated and stored.")

    def get_unique_ingredients(self) -> List[str]:
        query = """
            SELECT DISTINCT i.inci_name 
            FROM open_beauty.ingredients i
            LEFT JOIN open_beauty.ingredient_emissions ie ON i.id = ie.ingredient_id
            WHERE ie.ingredient_id IS NULL
            ORDER BY i.inci_name
        """
        rows = self.db.execute_query(query, fetch=True)
        return [row[0] for row in rows] if rows else []

    def run_pipeline(self, chunk_size: int = 1000):
        print("--- STARTING CO2 PIPELINE ---")
        ingredients = self.get_unique_ingredients()
        
        if not ingredients:
            print("No new ingredients to classify. Everything is up to date!")
            self.calculate_product_metrics()
            return

        print(f"Found {len(ingredients)} new ingredients to process.")
        
        for i in range(0, len(ingredients), chunk_size):
            chunk = ingredients[i:i + chunk_size]
            print(f"Processing chunk {i//chunk_size + 1}...")
            
            results = self.classifier.classify_ingredients(chunk)
            self.store_ingredient_emissions_incremental(results)
            
        self.calculate_product_metrics()
        print("--- PIPELINE COMPLETE ---")

    def store_ingredient_emissions_incremental(self, results: Dict[str, Dict]):
        id_map = self.get_ingredient_id_map()
        insert_query = """
            INSERT INTO open_beauty.ingredient_emissions
            (ingredient_id, estimated_impact, confidence_score, method)
            VALUES %s
            ON CONFLICT (ingredient_id) DO NOTHING
        """
        data = [(id_map[res['ingredient']], res['label'], res['score'], res['method']) 
                for res in results.values() if res['ingredient'] in id_map]
        
        if data:
            with self.db.get_cursor() as cur:
                from psycopg2.extras import execute_values
                execute_values(cur, insert_query, data)


# --- EXECUTION EXAMPLE ---
# Uncomment to run directly
# if __name__ == "__main__":
#     pipeline = CO2Pipeline(use_threshold=False)
#     pipeline.run_pipeline(chunk_size=5000)
