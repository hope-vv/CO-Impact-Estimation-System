import sys
import os
from typing import Iterator, Dict, Any
from psycopg2.extras import Json

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from shared.database import get_db
from init.config import get_config
from psycopg2.extras import execute_values

class RawDataIngestion:
    def __init__(self, source: str = "openbeautyfacts"):
        self.source = source
        self.db = get_db()
        self.config = get_config()
        self.batch_size = self.config.DATA_BATCH_SIZE

        print(f"Initialized ingestion for source: {source}")
    
    def ingest_products(self, data_iterator: Iterator[Dict[str, Any]]) -> int:
        insert_query = """
            INSERT INTO open_beauty.raw_products 
            (source, product_code, raw_json)
            VALUES %s
            ON CONFLICT (product_code) DO NOTHING
        """
        
        total_inserted = 0
        batch = []

        conn = self.db._connect()
        cur = conn.cursor()
        print("Testing DB connection...")
        
        try:
            for i, product in enumerate(data_iterator):
                product_code = product.get("code")
                if not product_code:
                    continue
                batch.append((self.source, product_code, Json(product)))
                
                if len(batch) >= self.batch_size:
                    execute_values(
                        cur,
                        insert_query,
                        batch,
                        template="(%s, %s, %s)"
                    )
                    conn.commit()
                    total_inserted += len(batch)
                    print(f"Inserted {total_inserted:,} records")
                    batch.clear()
            
            if batch:
                execute_values(
                        cur,
                        insert_query,
                        batch,
                        template="(%s, %s, %s)"
                    )
                conn.commit()
                total_inserted += len(batch)
            
            print(f"Total inserted: {total_inserted:,} records")
            return total_inserted
        
        except Exception as e:
            conn.rollback()
            print(f"Ingestion failed: {e}")
            raise

        finally:
            cur.close()
            conn.close()
    
    def insert_batch(self, query: str, batch: list):
        try:
            self.db.execute_many(query, batch)
        except Exception as e:
            print(f"Batch insert failed: {e}")
            raise
    
    def get_record_count(self) -> int:
        query = "SELECT COUNT(*) FROM open_beauty.raw_products WHERE source = %s"
        
        with self.db.get_cursor() as cur:
            cur.execute(query, (self.source,))
            return cur.fetchone()[0]


def ingest_from_file(file_path: str, source: str = "openbeautyfacts"):
    from .raw_loader import load_raw_data
    
    ingestion = RawDataIngestion(source=source)
    data_iter = load_raw_data(file_path)
    
    return ingestion.ingest_products(data_iter)
