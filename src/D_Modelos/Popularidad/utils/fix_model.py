"""Código que arregla que el modelo acceda a la carpeta incorrecta. NO USAR PARA DOCKER"""

import sys
from pathlib import Path
from joblib import load, dump
from src.D_Modelos.Popularidad.xgboost_model import XGBoostPopularity

sys.modules['Popularidad'] = sys.modules['src.D_Modelos.Popularidad']
sys.modules['Popularidad.xgboost_model'] = sys.modules['src.D_Modelos.Popularidad.xgboost_model']

print("Cambiando el path")

model_path = 'models/popularidad/xgboost_model_log.pkl'
modelo = load(model_path)
dump(modelo, model_path)

print("Path cambiado")
