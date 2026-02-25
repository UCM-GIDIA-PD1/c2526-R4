'''
Dado games_info.jsonl.gz procesa el json, lo convierte en un dataframe 
de pandas creando columnas nuevas y eliminando columnas innecesarias.
'''

import pandas as pd
import json
from  pathlib import Path
import gzip
import os

ROOT_DIR = os.getcwd()

def _get_datapath():
    data_path = ROOT_DIR / 'data'
    return data_path

def _read_jsonl(filepath):
    with open(filepath, "rt", encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
        return data
    
def _get_name(x):
    if isinstance(x,dict):
        return x.get("name")
    else:
        return None

def _get_genres(x):
    if not isinstance(x, dict):
        return []
    genres = x.get('genres', [])
    if not isinstance(genres, list):
        return []
    return [g.get('description') for g in genres if isinstance(g, dict)]

def _get_categories(x):
    if not isinstance(x,dict):
        return []
    categories = x.get("categories", [])
    if not isinstance(categories, list):
        return []
    return [c.get("description") for c in categories if isinstance(c, dict)]

def _is_free(x):
    if not isinstance(x,dict):
        return []
    price_ov = x.get("price_overview", [])
    if not isinstance(price_ov, dict):
        return []
    return price_ov.get("initial") == 0
        

if __name__ == '__main__':
    # Obtenemos el path a al archivo 'games_info.jsonl.gz' 
    data_path = _get_datapath()
    games_info_path = data_path / 'games_info.jsonl.gz'
    games_info = _read_jsonl(games_info_path)

    # Creamos el dataframe base
    df = pd.DataFrame(games_info)
    df = df.join(df["appdetails"].apply(pd.Series))



    
    
