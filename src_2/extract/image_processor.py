import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image, ImageStat
from sentence_transformers import SentenceTransformer
from pathlib import Path

def get_image_models():
    """
    Inicializa y configura los modelos de redes neuronales para la extracción de características de imágenes.

    Returns:
        dict: Diccionario con los modelos (ResNet, ConvNeXt, CLIP) y el pipeline de preprocesamiento.
    """
    # Resnet18
    model_resnet = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    model_resnet = nn.Sequential(*(list(model_resnet.children())[:-1]))
    model_resnet.eval()

    # ConvNeXt
    model_convnext = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.DEFAULT)
    model_convnext.classifier = nn.Identity()
    model_convnext.eval()

    # CLIP
    model_clip = SentenceTransformer("clip-ViT-B-32")
    model_clip.eval()

    # Transformaciones
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    return {
        "resnet": model_resnet,
        "convnext": model_convnext,
        "clip": model_clip,
        "preprocess": preprocess
    }

def analyze_image_features(image_path: Path, models_dict: dict):
    """
    Analiza una imagen local para extraer su brillo medio y vectores de características (embeddings).

    Args:
        image_path: Objeto Path con la ruta de la imagen.
        models_dict: Diccionario que contiene los modelos y el pipeline de preprocesamiento.

    Returns:
        dict: Diccionario con el brillo y los vectores generados por ResNet, ConvNeXt y CLIP.
    """

    img = Image.open(image_path).convert("RGB")
    
    # 1. Brillo medio
    stat = ImageStat.Stat(img)
    brightness = round(stat.mean[0], 4)

    # 2. Preprocesamiento para modelos de Torch
    img_t = models_dict["preprocess"](img)
    batch = torch.unsqueeze(img_t, 0)

    with torch.no_grad():
        feat_resnet = models_dict["resnet"](batch)
        v_resnet = [round(float(x), 4) for x in feat_resnet.flatten().tolist()]

        feat_convnext = models_dict["convnext"](batch)
        v_convnext = [round(float(x), 4) for x in feat_convnext.flatten().tolist()]

        feat_clip = models_dict["clip"].encode(img)
        v_clip = [round(float(x), 4) for x in feat_clip.tolist()]

    img.close()
    
    return {
        "brightness": brightness,
        "v_resnet": v_resnet,
        "v_convnext": v_convnext,
        "v_clip": v_clip
    }