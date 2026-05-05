"""Código que arregla que el modelo acceda a la carpeta incorrecta. NO USAR PARA DOCKER"""

import sys
from joblib import load, dump
from src.utils.config import precios_knncompleteclusters_retrained_file
from src.D_Modelos.Precios import knn
from src.D_Modelos.Precios.knn import ClusterEmbeddingsTransformer

sys.modules['Precios'] = sys.modules['src.D_Modelos.Precios']
sys.modules['Precios.knn'] = knn

print("Cambiando path")
model_path = precios_knncompleteclusters_retrained_file
modelo = load(model_path)
dump(modelo, model_path)
print("Path cambiado")