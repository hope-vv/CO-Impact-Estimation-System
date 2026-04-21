import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from contextlib import contextmanager
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from init.config import get_config

class DatabaseManager:
    def __init__(self):
        self.config = get_config()

    def _connect(self):
        if self.config.DATABASE_URL:
            return psycopg2.connect(dsn=self.config.DATABASE_URL)

        return psycopg2.connect(
            host=self.config.DB_HOST,
            port=self.config.DB_PORT,
            dbname=self.config.DB_NAME,
            user=self.config.DB_USER,
            password=self.config.DB_PASSWORD,
        )

    @contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        conn = self._connect()
        cursor_factory = RealDictCursor if dict_cursor else None
        cur = conn.cursor(cursor_factory=cursor_factory)

        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True):
        with self.get_cursor() as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()

    def execute_many(self, query: str, data: list):
        if not data:
            return

        with self.get_cursor() as cur:
            execute_values(
                cur,
                query,
                data,
                template="(%s, %s, %s)",
                page_size=1000
            )


_db_manager = None

def get_db() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager