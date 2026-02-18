import os
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image, ImageStat
import Z_funciones
from Z_funciones import proyect_root
import requests
import time
import numpy as np
from pathlib import Path

"""
Script que extrae de las imágenes el brillo medio y un vector de embeddings mediante una red neuronal
preentrenada de la librería pytorch.

Requisitos:
- Módulos 'thorch', 'torchvision' y 'pillow'

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def analiza_imagen(img_path, url,  trans, model):
    """
    Analiza las características de una imagen

    Args:
        img_path (str): ruta del archivo de imagen.
        trans (callable): transformaciones de preprocesamiento (ej. Resize, Normalize).
        model (torch.nn.Module): modelo preentrenado para extracción de embeddings.

    Returns:
        caracteristicas (dict): diccionario con el brillo medio y vector de características de la imagen
    """
    # Descargamos imagen y la metemos en la ruta    
    ruta_temporal = os.path.join(img_path, "header.jpg")
    
    response = requests.get(url, timeout=10)
    response.raise_for_status() # Para lanzar excepción si da error la petición
    
    with open(ruta_temporal, 'wb') as f:
        f.write(response.content)

    # Análisis de la imagen
    img = Image.open(ruta_temporal).convert('RGB')
        
    # Extraer el brillo medio
    stat = ImageStat.Stat(img)
    brillo = round(stat.mean[0], 4)

    # Extraer vector de características
    img_preprocesada = trans(img)
    batch_t = torch.unsqueeze(img_preprocesada, 0)

    with torch.no_grad():
        embedding = model(batch_t)
        # Convertimos el tensor a una lista de Python para el JSON y nos quedamos solo con 4 decimales
        vector = embedding.flatten().tolist()
        vector = [round(float(x), 4) for x in vector]

    # Borramos la imagen
    img.close() 
    if os.path.exists(ruta_temporal):
        os.remove(ruta_temporal)
    
    caracteristicas = {"brillo_medio": brillo,"vector_caracteristicas": vector} # Vector de 512 elementos
    return caracteristicas
    
def E_metadatos_imagenes(minio = False):
    """
    Itera por todas las imágenes en data/images y obtiene sus características, guardándolas en data/info_imagenes.json

    Args:
        None
    
    Returns:
        None
    """
    
    os.environ['TORCH_HOME'] = r'data\torch_cache'

    # Se configura el modelo (ResNet18, preentrenado para reconocer formas).
    model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model = torch.nn.Sequential(*(list(model.children())[:-1]))
    model.eval()

    # Definimos las trasnformaciones que vamos a hacer a cada imagen (para poder meterlas en el modelo)
    trans = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    # Carga de datos
    origin = "info_steam_games.json.gz"
    final = "info_imagenes.json.gz"
    juego_ini, juego_fin, juegos_pendientes, ruta_temp_jsonl, ruta_destino, ruta_config = Z_funciones.abrir_sesion(origin, final, False, minio)    

    if juego_ini == None:
        return
    
    # Configuracion de direcciones
    data_dir = proyect_root() / "data"
    ruta_imagenes = data_dir / "images"
    os.makedirs(ruta_imagenes, exist_ok=True)

    # Procesamiento de las imágenes
    idx_actual = juego_ini - 1
    ultimo_idx_guardado = juego_ini - 1
    try:
        for i, juego in enumerate(Z_funciones.barra_progreso([x[1] for x in juegos_pendientes], keys=['id'])):
            appid = juego.get("id")
            idx_actual = juegos_pendientes[i][0]

            url = juego.get("appdetails", {}).get("header_url")

            if not url:
                ultimo_idx_guardado = idx_actual
                continue

            try:
                caracteristicas = analiza_imagen(ruta_imagenes, url, trans, model)
                
                resultado_juego = {
                    "id": appid,
                    "brillo": caracteristicas["brillo_medio"],
                    "vector_c": caracteristicas["vector_caracteristicas"]
                }

                Z_funciones.guardar_datos_dict(resultado_juego, ruta_temp_jsonl)
                ultimo_idx_guardado = idx_actual

                time.sleep(np.random.uniform(0.1, 0.2))

            except Exception as e:
                print(f"Error procesando imagen del juego {appid}: {e}")
                continue

    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    
    finally:
        Z_funciones.cerrar_sesion(ruta_temp_jsonl, ruta_destino, ruta_config, ultimo_idx_guardado, juego_fin, minio)

if __name__ == "__main__":
    # Poner a True para traer y mandar los datos a MinIO
    E_metadatos_imagenes(False)