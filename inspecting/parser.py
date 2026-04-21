import re
from psycopg2.extras import execute_values
from shared.database import get_db
from init.config import get_config


class ProductParser:
    def __init__(self):
        self.db = get_db()
        self.config = get_config()
        self.batch_size = self.config.DATA_BATCH_SIZE
        self.ingredient_cache = {}
        self.load_cache()
        print(f"Initialized ProductParser with {len(self.ingredient_cache)} cached ingredients")

    def clean_text(self, value):
        if not value or value.strip() == "":
            return None
        return value.strip()

    def clean_ingredient_name(self, text):
        """Improved cleaning for noisy OCR (quantities, prefixes, etc.)"""
        if not text:
            return None

        name = str(text).strip()

        name = re.sub(r'^(ingredients?|ingrédients?|inci|fr)[:/\s]*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^\s*:\s*', '', name)

        name = re.sub(r'\b\d+(\.\d+)?\s*(ml|l|g|kg|%)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\be\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\bfr:\s*\d+', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\b10ml\b', '', name, flags=re.IGNORECASE)

        name = re.split(r'[\(\[\{]', name)[0]
        name = re.sub(r'^\W+|\W+$', '', name)
        name = re.sub(r'\s+', ' ', name).strip()

        return name if len(name) >= 3 else None

    def is_garbage_ingredient(self, name):
        """Negative filter: remove obvious trash"""
        if not name or len(name.strip()) < 3:
            return True

        n = name.lower().strip()

        garbage_keywords = [
            'fabriqué', 'made in', 'responsable', 'distributeur', 'tel', 'tél',
            'apply', 'massant', 'usage', 'mode d\'emploi', 'external', 'enfants',
            'parabens', 'alcohol', 'silicone', 'vaseline', 'paraffin', 'www.',
            'septona', 'providence', 'bouskoura', 'exports', 'crème', 'krem',
            'crema', 'hydratante', 'producdtor', 'производител', 'дистрибутор',
            'beneficios', 'consideraciones', 'puede causar', 'irritación',
            'sana s.a', 'ste flower', 'hatrielle', 'loguy', 'prd', 'exp', 'batch',
            'ingredien'
        ]

        if any(kw in n for kw in garbage_keywords):
            return True

        if re.fullmatch(r'[\d+\-\(\)\s/.:%]+', n):
            return True

        if len(re.sub(r'[^a-z]', '', n)) < 2:
            return True

        return False

    def is_valid_ingredient(self, name: str) -> bool:
        """Final professional check: garbage filter + positive validation"""
        cleaned = self.clean_ingredient_name(name)
        if not cleaned:
            return False

        if self.is_garbage_ingredient(cleaned):
            return False

        return True

    def parse_quantity(self, quantity_text):
        if not quantity_text:
            return None, None

        text = quantity_text.replace(',', '.').lower().strip()

        match = re.search(r'(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*(ml|l|g|kg)', text)
        if match:
            try:
                count = float(match.group(1))
                amount = float(match.group(2))
                unit = match.group(3)
                return count * amount, unit
            except ValueError:
                pass

        match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|l|g|kg)\s*x\s*(\d+)', text)
        if match:
            try:
                amount = float(match.group(1))
                unit = match.group(2)
                count = float(match.group(3))
                return count * amount, unit
            except ValueError:
                pass

        match = re.search(r'(\d+(?:\.\d+)?)\s*(ml|l|g|kg)', text)
        if match:
            try:
                return float(match.group(1)), match.group(2)
            except ValueError:
                pass

        match = re.search(r'([\d,.]+)\s*([a-zA-Z]+)', text, re.IGNORECASE)
        if not match:
            return None, None

        try:
            amount = float(match.group(1))
        except ValueError:
            return None, None

        unit_raw = match.group(2).lower()
        unit_map = {'ml': 'ml', 'l': 'l', 'g': 'g', 'kg': 'kg'}
        unit = unit_map.get(unit_raw)

        return amount, unit

    def clean_categories(self, raw):
        if not raw:
            return None

        items = re.split(r'[;,]', raw)
        cleaned = []

        for item in items:
            item = item.strip()
            if not item:
                continue

            lower = item.lower()

            if re.fullmatch(r'\d+(\.\d+)?', item):
                continue
            if re.search(r'\b(ml|l|kg|g|°c|c)\b', lower):
                continue
            if '°' in item or '+' in item:
                continue
            if re.fullmatch(r'[a-z]?\d{1,4}', lower):
                continue
            if len(item.split()) > 4:
                continue

            alpha_ratio = sum(c.isalpha() for c in item) / max(len(item), 1)
            if alpha_ratio < 0.6:
                continue

            item = re.sub(r'\s+', ' ', item).title()
            cleaned.append(item)

        cleaned = sorted(set(cleaned))
        return ', '.join(cleaned) if cleaned else None

    def clean_brands(self, raw):
        if not raw:
            return None

        items = re.split(r'[;,]', raw)
        cleaned = []

        for item in items:
            item = item.strip()
            if not item:
                continue
            if len(item.split()) > 5:
                continue

            alpha_ratio = sum(c.isalnum() for c in item) / max(len(item), 1)
            if alpha_ratio < 0.5:
                continue

            item = re.sub(r'\s+', ' ', item).title()
            cleaned.append(item)

        cleaned = sorted(set(cleaned))
        return ', '.join(cleaned) if cleaned else None

    def clean_countries(self, raw):
        if not raw:
            return None

        items = re.split(r'[;,]', raw)
        cleaned = []

        for item in items:
            item = item.strip()
            if not item:
                continue

            lower = item.lower()
            if re.search(r'\d', item):
                continue
            if len(item) < 3:
                continue
            if len(item.split()) > 3:
                continue

            alpha_ratio = sum(c.isalpha() for c in item) / max(len(item), 1)
            if alpha_ratio < 0.7:
                continue

            item = re.sub(r'\s+', ' ', item).title()
            cleaned.append(item)

        cleaned = sorted(set(cleaned))
        return ', '.join(cleaned) if cleaned else None

    def load_cache(self):
        with self.db.get_cursor() as cur:
            cur.execute("SELECT inci_name, id FROM open_beauty.ingredients")
            self.ingredient_cache = {row[0]: row[1] for row in cur.fetchall()}

    def parse_ingredients_smart(self, text):
        if not text:
            return []

        lower_text = text.lower()

        markers = [
            r'ingredients?\s*[:/]\s*',
            r'ingrédients?\s*[:/]\s*',
            r'inci\s*[:/]\s*',
            r'composition\s*[:/]\s*'
        ]

        start_pos = 0
        for marker in markers:
            match = re.search(marker, lower_text)
            if match:
                start_pos = match.end()
                break

        ingredients_part = text[start_pos:]
        items = re.split(r',\s*(?![^(]*\))', ingredients_part)

        cleaned = []
        for item in items:
            item = item.strip()
            if not item:
                continue

            main = re.split(r'[\(\[\{]', item)[0].strip(' .,:;')

            if len(main) < 3:
                continue

            if self.is_valid_ingredient(main):
                cleaned.append(main)

        return cleaned

    def process_product(self, cur, row):
        source = row["source"]
        product_code = row["product_code"]
        raw_json = row["raw_json"]
        raw_product_id = row["id"]

        p_name = self.clean_text(raw_json.get('product_name'))
        if not p_name:
            return

        qty_text = self.clean_text(raw_json.get('quantity'))
        total_qty, unit = self.parse_quantity(qty_text)

        insert_query = """
            INSERT INTO open_beauty.products
            (raw_product_id, product_name, code, brands, categories, countries, quantity_text, source, 
             total_quantity, unit, has_ingredients)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (source, code) DO NOTHING
            RETURNING id
        """
        cur.execute(insert_query, (
            raw_product_id, p_name, product_code,
            self.clean_brands(raw_json.get('brands')),
            self.clean_categories(raw_json.get('categories')),
            self.clean_countries(raw_json.get('countries')),
            qty_text, source, total_qty, unit, False
        ))

        result = cur.fetchone()
        product_id = result[0] if result else None

        if not product_id:
            cur.execute("""
                SELECT id FROM open_beauty.products 
                WHERE source = %s AND code = %s
            """, (source, product_code))
            product_id = cur.fetchone()[0]

        self.process_ingredients_bulk(cur, product_id, raw_json)

    def process_ingredients_bulk(self, cur, product_id, raw_json):
        to_process = []

        structured = raw_json.get("ingredients") or []
        if structured:
            for i, ing in enumerate(structured, 1):
                raw_name = ing.get("text") or ing.get("id") or ""
                name = self.clean_ingredient_name(raw_name)
                if name and self.is_valid_ingredient(name):
                    pct = ing.get("percent_estimate")
                    try:
                        pct = float(pct) if 0 <= float(pct) <= 100 else None
                    except:
                        pct = None
                    to_process.append({'name': name, 'pct': pct, 'rank': ing.get("rank", i)})

        if not to_process:
            raw_text = (
                raw_json.get("ingredients_text") or
                raw_json.get("ingredients_text_xx") or
                raw_json.get("ingredients_text_en") or ""
            )
            if raw_text:
                parsed_names = self.parse_ingredients_smart(raw_text)
                for i, name in enumerate(parsed_names, 1):
                    if self.is_valid_ingredient(name):
                        to_process.append({'name': name, 'pct': None, 'rank': i})

        if not to_process:
            return

        ingredient_links = []
        for item in to_process:
            name = item['name']

            if name not in self.ingredient_cache:
                cur.execute("""
                    INSERT INTO open_beauty.ingredients (inci_name)
                    VALUES (%s)
                    ON CONFLICT (inci_name) DO NOTHING
                    RETURNING id
                """, (name,))
                row = cur.fetchone()
                if row:
                    self.ingredient_cache[name] = row[0]
                else:
                    cur.execute("SELECT id FROM open_beauty.ingredients WHERE inci_name = %s", (name,))
                    self.ingredient_cache[name] = cur.fetchone()[0]

            ingredient_links.append((
                product_id,
                self.ingredient_cache[name],
                item.get('pct'),
                item['rank']
            ))

        if ingredient_links:
            execute_values(cur, """
                INSERT INTO open_beauty.product_ingredients 
                (product_id, ingredient_id, percentage_estimated, rank)
                VALUES %s
                ON CONFLICT (product_id, ingredient_id) DO NOTHING
            """, ingredient_links)

            cur.execute("UPDATE open_beauty.products SET has_ingredients = TRUE WHERE id = %s", (product_id,))

    def parse_all_products(self):
        last_id = 0
        while True:
            with self.db.get_cursor(dict_cursor=True) as cur:
                cur.execute("""
                    SELECT id, source, product_code, raw_json 
                    FROM open_beauty.raw_products 
                    WHERE id > %s ORDER BY id LIMIT %s
                """, (last_id, self.batch_size))
                rows = cur.fetchall()

            if not rows:
                break

            with self.db.get_cursor() as cur:
                for row in rows:
                    self.process_product(cur, row)
                    last_id = row["id"]

            print(f"Processed batch up to raw product ID: {last_id}")