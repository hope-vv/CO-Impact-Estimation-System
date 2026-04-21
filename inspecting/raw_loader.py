import gzip
import json
from typing import Iterator, Dict, Any
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def load_raw_data(file_path: str, file_format: str = 'jsonl') -> Iterator[Dict[str, Any]]:
    path = Path(file_path)
    
    if not path.exists():
        print(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")
    
    print(f"Loading data from: {file_path}")
    
    if path.suffix == '.gz':
        open_func = lambda p: gzip.open(p, 'rt', encoding='utf-8')
    else:
        open_func = lambda p: open(p, 'r', encoding='utf-8')
    
    if file_format == 'jsonl':
        yield from _load_jsonl(path, open_func)
    elif file_format == 'json':
        yield from _load_json(path, open_func)
    else:
        raise ValueError(f"Unsupported format: {file_format}")


def _load_jsonl(path: Path, open_func) -> Iterator[Dict[str, Any]]:
    line_count = 0
    error_count = 0
    
    with open_func(path) as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                yield data
                line_count += 1
                
                if line_count % 10000 == 0:
                    print(f"Processed {line_count:,} lines")
                    
            except json.JSONDecodeError as e:
                error_count += 1
                if error_count <= 10:
                    print(f"JSON decode error on line {line_number}: {e}")
    
    print(f"Loaded {line_count:,} records with {error_count} errors")


def _load_json(path: Path, open_func) -> Iterator[Dict[str, Any]]:
    with open_func(path) as f:
        data = json.load(f)

        if isinstance(data, list):
            yield from data
        else:
            yield data
