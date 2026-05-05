import numpy as np
import re
import unicodedata
from unidecode import unidecode
from langdetect import detect
def clean_price(appdetails):
    """Extrae el precio inicial en euros."""
    if not appdetails or appdetails.get("is_free"):
        return 0.0
    price_info = appdetails.get("price_overview", {})
    # Steam da el precio en céntimos (1999 -> 19.99)
    return price_info.get("initial", 0) / 100.0

def clean_genres(genres_list):
    """Devuelve lista de nombres de géneros."""
    if not genres_list: return []
    return [g.get("description") for g in genres_list if "description" in g]

# ------ NLP ------
def detect_language(text):
    """Detecta el idioma del texto. Retorna 'unknown' si falla."""
    try:
        return detect(text)
    except Exception:
        return "unknown"

def clean_review_text(text):
    """
    Realiza la limpieza completa del texto:
    1. Elimina URLs y etiquetas de Steam [b], [i], etc.
    2. Normaliza Unicode y quita acentos.
    3. Elimina caracteres no alfanuméricos (ruido y ASCII art).
    """
    if not text:
        return ""
    
    # Limpieza inicial (URLs y Markdown de Steam)
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    
    # Normalización y limpieza final
    try:
        text = unicodedata.normalize("NFKC", text)
        text = unidecode(text)
        # Solo dejamos letras, números y puntuación básica
        text = re.sub(r"[^a-zA-Z0-9\s.,!?'()$%;\-&/]", " ", text)
        return " ".join(text.split()).lower().strip()
    except Exception:
        return ""