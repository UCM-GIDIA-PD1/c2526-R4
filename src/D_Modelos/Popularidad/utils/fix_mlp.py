"""Código que arregla que el modelo MLP acceda a la carpeta incorrecta (Popularidad / src.D_Modelos.Popularidad)."""

import sys
from joblib import load, dump
from src.utils.files import file_exists
from src.utils.config import popularidad_mlp_file

# Importamos los módulos con su ruta correcta para que existan en sys.modules
import src.D_Modelos.Popularidad.mlp as mlp
import src.D_Modelos.Popularidad.popularity_model as popularity_model

# Mapeamos los nombres antiguos a los nuevos en sys.modules para que joblib pueda cargar el modelo
sys.modules['Popularidad'] = sys.modules['src.D_Modelos.Popularidad']
sys.modules['Popularidad.mlp'] = mlp
sys.modules['Popularidad.popularity_model'] = popularity_model

print("Cambiando el path del modelo MLP...")

if file_exists(popularidad_mlp_file):
    modelo = load(popularidad_mlp_file)
    dump(modelo, popularidad_mlp_file)
    print(f"Modelo {popularidad_mlp_file} arreglado y guardado.")
else:
    print(f"Error: No se encontró el archivo {popularidad_mlp_file}")
