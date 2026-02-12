import os
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image, ImageStat
import Z_funciones
import requests

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
    
        with open(ruta_temporal, 'wb') as f:
            f.write(requests.get(url).content)

        # Análisis de la imagen
        img = Image.open(ruta_temporal).convert('RGB')
            
        # Extraer el brillo medio
        stat = ImageStat.Stat(img)
        brillo = stat.mean[0] 

        # Extraer vector de características
        img_preprocesada = trans(img)
        batch_t = torch.unsqueeze(img_preprocesada, 0)

        with torch.no_grad():
            embedding = model(batch_t)
            # Convertimos el tensor a una lista de Python para el JSON
            vector = embedding.flatten().tolist()

        # Borramos la imagen
        img.close() 
        os.remove(ruta_temporal)
        
        caracteristicas = {"brillo_medio": brillo,"vector_caracteristicas": vector} # Vector de 512 elementos
        return caracteristicas
    
def extraer_metadatos_imagenes():
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

    ruta_origen = r"data\info_steam_games.json.gz"
    ruta_imagenes = r"data\images"
    os.makedirs(ruta_imagenes, exist_ok=True)

    data = Z_funciones.cargar_datos_locales(ruta_origen)
    resultados = {}

    if not os.path.exists(ruta_origen):
        print(f"Error: No se encuentra la ruta {ruta_origen}")
        return

    # Análisis de las imágenes
    for juego in Z_funciones.barra_progreso(data["data"], keys=["id"]):
        
        appid = juego.get("id")
        url = juego.get("appdetails", {}).get("header_url")

        resultados[appid] = analiza_imagen(ruta_imagenes, url, trans, model)


    # Guardamos el json
    ruta_destino = r"data\info_imagenes.json.gz"
    Z_funciones.guardar_datos_dict(resultados, ruta_destino)

if __name__ == "__main__":
    extraer_metadatos_imagenes()