'''
Dado games_info.jsonl.gz procesa el json, lo convierte en un dataframe 
de pandas creando columnas nuevas y eliminando columnas innecesarias.
'''

import pandas as pd
import json
import pathlib as Path

base_dir = Path().resolve().parents[1] # Nos situamos en la carpeta del proyecto
data_dir = base_dir / 'data' # cd data

# No usa variable de entorno pues la ruta será el archivo final con todos los juegos,
# no partes individuales de cada identificador
ruta = Path(data_dir / f'info_steam_games_3.json.gz')

if not ruta.exists():
    raise FileNotFoundError(f'No se encuentra la ruta: {ruta}')

with gzip.open(ruta, 'rt', encoding='UTF-8') as f:
    data = json.load(f)
    
df = pd.DataFrame(data['data'])
df