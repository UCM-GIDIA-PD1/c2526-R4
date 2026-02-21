import os
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image, ImageStat
import requests
import time
from tqdm import tqdm
import numpy as np
from utils.minio_server import upload_to_minio
from utils.files import write_to_file, erase_file, file_exists
from utils.config import banners_file, project_root
from utils.sesion import tratar_existe_fichero, update_config, get_pending_games, overwrite_confirmation

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
    
def E_metadatos_imagenes(minio):
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

    # Carga de datos usando la nueva utilidad de sesión
    pending_games, start_idx, curr_idx, end_idx = get_pending_games("E", minio)
    
    if not pending_games:
            print(f"No hay juegos en el rango [{curr_idx}, {end_idx}]")
            return
    
    # Si existe fichero preguntar si sobreescribir o insertar al final, esta segunda opción no controla duplicados
    if file_exists(banners_file, minio):
            origen = " en MinIO" if minio["minio_read"] else ""
            mensaje = f"El fichero de lista de appids ya existe{origen}:\n\n1. Añadir contenido al fichero existente\n2. Sobreescribir fichero\n\nIntroduce elección: "
            overwrite_file = tratar_existe_fichero(mensaje)
            if overwrite_file:
                # asegurarse de que se quiere eliminar toda la información
                if overwrite_confirmation():
                    erase_file(banners_file, minio)
                else:
                    print("Operación cancelada")
                    return
    
    # Configuracion de direcciones
    data_dir = project_root() / "data"
    ruta_imagenes = data_dir / "images"
    os.makedirs(ruta_imagenes, exist_ok=True)

    # Procesamiento de las imágenes
    try:
        with tqdm(pending_games, unit="juegos") as pbar:
            for juego in pbar:
                appid = juego.get("id")
                pbar.set_description(f"Procesando appid: {appid}")
                
                url = juego.get("appdetails", {}).get("header_url")

                if not url:
                    curr_idx += 1
                    continue

                try:
                    caracteristicas = analiza_imagen(ruta_imagenes, url, trans, model)
                    
                    resultado_juego = {
                        "id": appid,
                        "brillo": caracteristicas["brillo_medio"],
                        "vector_c": caracteristicas["vector_caracteristicas"]
                    }

                    write_to_file(resultado_juego, banners_file)
                    curr_idx += 1

                    time.sleep(np.random.uniform(0.1, 0.2))

                except Exception as e:
                    print(f"Error procesando imagen del juego {appid}: {e}")
                    curr_idx += 1
                    continue

    except KeyboardInterrupt:
        print("\n\nDetenido por el usuario. Guardando antes de salir...")
    finally:
        if minio["minio_write"]: 
            corrrectly_uploaded = upload_to_minio(banners_file)
            if corrrectly_uploaded: erase_file(banners_file)
        # Guardamos el progreso en el config.json
        gamelist_info = {"start_idx" : start_idx, "curr_idx" : curr_idx, "end_idx" : end_idx}
        if curr_idx > end_idx:
            print("Rango completado")
        update_config("E", gamelist_info)

if __name__ == "__main__":
    E_metadatos_imagenes()