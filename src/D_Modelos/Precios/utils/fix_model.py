"""Código que arregla que el modelo acceda a la carpeta incorrecta. NO USAR PARA DOCKER"""

import sys
from pathlib import Path
from joblib import load, dump
from src.D_Modelos.Precios.knn import ClusterEmbeddingsTransformer

sys.modules['Precios'] = sys.modules['src.D_Modelos.Precios']
sys.modules['Precios.knn'] = sys.modules['src.D_Modelos.Precios.knn']

model_path = 'models/precios/knncompleteclusters.pkl'
modelo = load(model_path)
dump(modelo, model_path)