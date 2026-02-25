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
from utils.config import banners_file, project_root, data_path
from utils_extraccion.sesion import tratar_existe_fichero, update_config, get_pending_games, overwrite_confirmation, handle_input
from sentence_transformers import SentenceTransformer
"""
Script que extrae de las imágenes el brillo medio y un vector de embeddings mediante una red neuronal
preentrenada de la librería pytorch.

Requisitos:
- Módulos 'thorch', 'torchvision' y 'pillow'

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def analiza_imagen(img_path, url,  trans, appid, download_images, model_resnet, model_clip, model_convnext):
    """
    Analiza las características de una imagen

    Args:
        img_path (str): ruta del archivo de imagen.
        trans (callable): transformaciones de preprocesamiento (ej. Resize, Normalize).
        appid (int): appid del juego analizado
        download_images (bool): hay o no hay que descargar la imagen
        model_resnet (torch.nn.Module): modelo preentrenado para extracción de embeddings.
        model_clip (sentence_transformers.SentenceTransformer): modelo preentrenado para extracción de embeddings.
        model_convnext (torch.nn.Module): modelo preentrenado para extracción de embeddings.

    Returns:
        caracteristicas (dict): diccionario con el brillo medio y vector de características de la imagen
    """
    # Descargamos imagen y la metemos en la ruta    
    nombre_imagen = f"{appid}_header.jpg"
    ruta_temporal = os.path.join(img_path, nombre_imagen)
    
    if download_images:
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
        # Inferencia ResNet
        feat_resnet = model_resnet(batch_t)
        vector_resnet = [round(float(x), 4) for x in feat_resnet.flatten().tolist()]

        # Inferencia ConvNeXt
        feat_convnext = model_convnext(batch_t)
        vector_convnext = [round(float(x), 4) for x in feat_convnext.flatten().tolist()]

        # Inferencia CLIP (Usa la imagen PIL 'img' directamente)
        feat_clip = model_clip.encode(img)
        vector_clip = [round(float(x), 4) for x in feat_clip.tolist()]

    img.close() 
    
    caracteristicas = {
        "brillo_medio": brillo,
        "vector_resnet": vector_resnet,
        "vector_convnext": vector_convnext,
        "vector_clip": vector_clip
    }

    return caracteristicas
    
def E_metadatos_imagenes(minio):
    os.environ['TORCH_HOME'] = str(data_path() / "torch_cache")

    # Configuración de modelos
    
    # Resnet, entrenado para reconocer formas
    model_resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model_resnet = torch.nn.Sequential(*(list(model_resnet.children())[:-1]))
    model_resnet.eval()

    # ConvNeXt, optimizado para texturas y detalles finos
    model_convnext = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    model_convnext.classifier = torch.nn.Identity() # Quitamos la capa de clasificación
    model_convnext.eval()

    # Clip, modelo de OpenAI que reconoce conceptos semánticos, estilos y estética
    model_clip = SentenceTransformer('clip-ViT-B-32')
    model_clip.eval()

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
                
    message = "¿Quieres que se descarguen las imágenes? [Y/N] :"
    response = handle_input(message, lambda x: x.lower() in {"y", "n", ""})
    download_images = True if response.lower() == "y" or response.lower() == "" else False
    
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
                
                if download_images:
                    url = juego.get("appdetails", {}).get("header_url")
                    if not url:
                        curr_idx += 1
                        continue
                else:
                    url = None

                try:
                    caracteristicas = analiza_imagen(ruta_imagenes, url, trans, appid, download_images, model_resnet, model_clip, model_convnext)

                    resultado_juego = {
                        "id": appid,
                        "brillo": caracteristicas["brillo_medio"],
                        "v_resnet": caracteristicas["vector_resnet"],
                        "v_convnext": caracteristicas["vector_convnext"],
                        "v_clip": caracteristicas["vector_clip"]
                    }

                    write_to_file(resultado_juego, banners_file)
                    curr_idx += 1
                    
                    if download_images: 
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