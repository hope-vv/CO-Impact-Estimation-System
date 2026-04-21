import pandas as pd
import torch
import os
from typing import Dict, List
from transformers import pipeline
from google.colab import files
from datetime import datetime

# --- 1. THE MODEL WRAPPER (Optimized for GPU) ---
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
        template = "This ingredient has a {} environmental impact due to production and sourcing."
        # template = "The environmental CO2 impact of this ingredient is {}"

        results = self.classifier(
            texts,
            candidate_labels=labels,
            hypothesis_template=template,
            batch_size=32
        )

        if isinstance(results, dict): results = [results]
        return [{
            'ingredient': res['sequence'],
            'estimated_impact': res['labels'][0],
            'confidence_score': float(res['scores'][0])
        } for res in results]

# --- 2. THE INGREDIENT CLASSIFIER ---
class IngredientClassifier:
    def __init__(self, confidence_threshold: float = 0.6, use_threshold: bool = True):
        self.model = CO2Model()
        self.threshold = confidence_threshold
        self.use_threshold = use_threshold

    def classify_ingredients(self, ingredients: List[str]) -> List[Dict]:
        batch_results = self.model.classify_batch(ingredients)
        if self.use_threshold:
            return [res for res in batch_results if res['confidence_score'] >= self.threshold]
        return batch_results

# --- 3. THE MAIN PIPELINE (CSV/PANDAS VERSION) ---
class CO2CSVPipeline:
    def __init__(self, confidence_threshold: float = 0.6, use_threshold: bool = True):
        self.classifier = IngredientClassifier(confidence_threshold=confidence_threshold,
                                               use_threshold=use_threshold)

        # Load your uploaded files
        self.ingredients_df = pd.read_csv("ingredients.csv")
        self.ingredients_df = self.ingredients_df.dropna(subset=['inci_name'])
        self.ingredients_df['inci_name'] = self.ingredients_df['inci_name'].astype(str)
        self.ingredients_df = self.ingredients_df[self.ingredients_df['inci_name'].str.strip() != ""]

        # Create a mapping for ID lookup
        self.id_map = dict(zip(self.ingredients_df['inci_name'], self.ingredients_df['id']))

        self.products_df = pd.read_csv("products.csv")
        self.pi_df = pd.read_csv("product_ingredients.csv")

        # Filenames changed to match your SQL tables
        self.emissions_file = "ingredient_emissions.csv"
        self.metrics_file = "co2_metrics.csv"

    def get_ingredients_to_process(self) -> List[str]:
        all_ingredients = self.ingredients_df['inci_name'].unique().tolist()

        if os.path.exists(self.emissions_file):
            try:
                existing_results = pd.read_csv(self.emissions_file)
                # Map existing IDs back to names to skip them
                reverse_id_map = {v: k for k, v in self.id_map.items()}
                done_names = [reverse_id_map[idx] for idx in existing_results['ingredient_id'] if idx in reverse_id_map]
                return [i for i in all_ingredients if i not in done_names]
            except Exception as e:
                print(f"Warning: Could not read existing results file ({e}). Starting fresh.")
                return all_ingredients

        return all_ingredients

    def calculate_product_metrics(self):
        print("Calculating final product metrics...")
        if not os.path.exists(self.emissions_file):
            print("No emissions data found.")
            return

        # 1. Load classification results (Matches Table: ingredient_emissions)
        emissions_df = pd.read_csv(self.emissions_file)

        # 2. Join with Product_Ingredients
        merged = pd.merge(self.pi_df, emissions_df, on='ingredient_id')

        # 3. Convert Labels to Scores
        score_map = {'low': 1, 'medium': 2, 'high': 3}
        merged['impact_value'] = merged['estimated_impact'].map(score_map)

        merged['weight'] = merged['percentage_estimated'].fillna(1 / merged.groupby('product_id')['ingredient_id'].transform('count'))
        # merged['weight'] = merged['percentage_estimated'].fillna(1.0)
        merged['weighted_score'] = merged['impact_value'] * merged['weight']

        # 4. Aggregate
        grouped = merged.groupby('product_id').agg({
            'weighted_score': 'sum',
            'weight': 'sum'
        })
        grouped['avg_score'] = grouped['weighted_score'] / grouped['weight']

        def score_to_label(s):
            if s < 1.5: return 'low'
            if s < 2.5: return 'medium'
            return 'high'

        # 5. Format for Table: co2_metrics
        final_metrics = pd.DataFrame()
        final_metrics['product_id'] = grouped.index
        final_metrics['estimated_impact'] = grouped['avg_score'].apply(score_to_label)
        final_metrics['method'] = 'weighted_ingredient_aggregation'
        final_metrics['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        final_metrics.to_csv(self.metrics_file, index=False)
        print(f"Product metrics saved to {self.metrics_file}")

    def run_pipeline(self, chunk_size=500):
        print("--- STARTING PANDAS CO2 PIPELINE ---")

        to_process = self.get_ingredients_to_process()
        if not to_process:
            print("All ingredients already classified.")
        else:
            print(f"Processing {len(to_process)} ingredients...")

            for i in range(0, len(to_process), chunk_size):
                chunk = to_process[i : i + chunk_size]
                print(f"Chunk {i//chunk_size + 1}: Processing {len(chunk)} items...")

                results = self.classifier.classify_ingredients(chunk)

                # Transform to Table: ingredient_emissions
                formatted_results = []
                for res in results:
                    formatted_results.append({
                        'ingredient_id': self.id_map[res['ingredient']],
                        'estimated_impact': res['estimated_impact'],
                        'confidence_score': round(res['confidence_score'], 4),
                        'method': 'zero-shot-distilbart',
                        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    })

                if formatted_results:
                    res_df = pd.DataFrame(formatted_results)
                    res_df.to_csv(self.emissions_file, mode='a', index=False, header=not os.path.exists(self.emissions_file))

        self.calculate_product_metrics()
        print("--- PIPELINE COMPLETE ---")

# --- EXECUTION ---
pipeline = CO2CSVPipeline(use_threshold=False)
pipeline.run_pipeline(chunk_size=5000)

