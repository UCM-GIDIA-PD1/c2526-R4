import numpy as np
import re
import unicodedata
from unidecode import unidecode
from langdetect import detect
from datetime import datetime
def clean_price(appdetails):
    """
    Extrae el precio inicial en euros a partir de los detalles de la aplicación.

    Args:
        appdetails: Diccionario con la información de la aplicación.

    Returns:
        float: Precio inicial convertido a euros.
    """

    if not appdetails or appdetails.get("is_free"):
        return 0.0
    price_info = appdetails.get("price_overview", {})
    # Steam da el precio en céntimos (1999 -> 19.99)
    return price_info.get("initial", 0) / 100.0

def get_price_range(price):
    """
    Categoriza un precio numérico en un rango de texto predefinido.

    Args:
        price: Valor numérico del precio.

    Returns:
        str: Etiqueta del rango de precio correspondiente.
    """
    if price == 0:
        return "Free"
    elif 0 < price < 5:
        return "[0.01,4.99]"
    elif 5 <= price < 10:
        return "[5.00,9.99]"
    elif 10 <= price < 15:
        return "[10.00,14.99]"
    elif 15 <= price < 20:
        return "[15.00,19.99]"
    elif 20 <= price < 30:
        return "[20.00,29.99]"
    elif 30 <= price < 40:
        return "[30.00,39.99]"
    else:
        return ">40"
    
def clean_genres(genres_list):
    """
    Extrae los nombres de los géneros a partir de una lista de diccionarios.

    Args:
        genres_list: Lista de diccionarios con la información de los géneros.

    Returns:
        list[str]: Lista con las descripciones de los géneros.
    """

    if not genres_list: return []
    return [g.get("description") for g in genres_list if "description" in g]

def parse_supported_languages(raw_html):
    """
    Parsea los idiomas soportados a partir de una cadena de texto HTML de Steam.

    Args:
        raw_html: Cadena de texto con el HTML original de la API.

    Returns:
        list[str]: Lista de idiomas extraídos.
    """

    if not raw_html or not isinstance(raw_html, str):
        return []
    
    # Steam separa los idiomas de audio con <br>, nos quedamos con la primera parte
    raw_languages = raw_html.split("<br>")[0]
    processed_languages = raw_languages.replace("<strong>*</strong>", "")
    language_list = [language.strip() for language in processed_languages.split(",")]
    return language_list

def parse_steam_date(date_str: str):
    """
    Convierte una fecha de texto de Steam al formato "YYYY-MM-DD".

    Args:
        date_str: Cadena de texto con la fecha original de Steam.

    Returns:
        str | None: Fecha formateada o None si el formato es inválido o el juego no se ha lanzado.
    """

    if not date_str or "Coming Soon" in date_str or "To be announced" in date_str:
        return None
        
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    try:
        parts = date_str.replace(",", "").split()
        if len(parts) != 3:
            return None
            
        day = int(parts[0])
        month = months.get(parts[1])
        year = int(parts[2])
        
        if not month:
            return None
            
        dt = datetime(year, month, day)
        
        return dt.strftime("%Y-%m-%d")
        
    except Exception:
        return None
    
def clean_entity_name(entity_list):
    """
    Extrae el nombre principal de una lista de desarrolladores o editores.

    Args:
        entity_list: Lista de nombres de entidades.

    Returns:
        str: El primer nombre de la lista o "Unknown" si no está disponible.
    """
    if not entity_list or not isinstance(entity_list, list):
        return "Unknown"
    return entity_list[0]

# ------ NLP ------
def detect_language(text):
    """
    Detecta el idioma de un texto utilizando la librería langdetect.

    Args:
        text: Cadena de texto a analizar.

    Returns:
        str: Código del idioma detectado o "unknown" en caso de error.
    """

    try:
        return detect(text)
    except Exception:
        return "unknown"

def clean_review_text(text):
    """
    Realiza una limpieza exhaustiva de texto eliminando URLs, etiquetas y caracteres especiales.

    Args:
        text: Cadena de texto original.

    Returns:
        str: Texto normalizado y limpio en minúsculas.
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