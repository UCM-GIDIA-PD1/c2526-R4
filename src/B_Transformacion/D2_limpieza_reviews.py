"""
Dado el fichero que contiene la información de los ficheros, limpia todos los aspectos del texto que no son relevantes o
que van a dificultar tratar los datos.
"""

from src.utils.config import steam_reviews_parquet_file, steam_reviews_file
from src.utils.files import read_file, erase_file
from src.utils.minio_server import upload_to_minio
import pandas as pd
import unicodedata
import re
from unidecode import unidecode
from langdetect import detect

def to_dataframe(raw):
    """
    Crea el DataFrame procesando la información de las reviews de cada juego.

    Args:
        raw (list): Lista de diccionarios con la información de cada review de cada juego
    Returns:
        pd.DataFrame: DataFrame procesado con la información de cada juego.
    """
    seen = set()
    appid_list = []
    is_positive = []
    texto = []
    peso = []
    for game in raw:
        appid = game["id"]
        for review in game["reviews"]["lista_resenyas"]:
            if review["id_resenya"] in seen:
                continue
            seen.add(review["id_resenya"])
            appid_list.append(appid)
            is_positive.append(review["valoracion"])
            texto.append(review["texto"])
            peso.append(review["peso"])
    df = pd.DataFrame({"appid": appid_list,
                    "is_positive" : is_positive,
                    "weight" : peso,
                    "text" : texto,
                })
    return df

def detect_language(text):
    """
    Usando detect del módulo langdetect, devolvemos el lenguaje en el que está escrito.

    Args:
        text (str): Texto de una review

    Returns:
        str: String que describe el lenguaje en el que está escrito, se devuelve 'unknown' si es desconocido.
    """
    try:
        return detect(text)
    except:
        return "unknown"
    
def limpieza_inicial(texto):
    """
    Eliminamos aspectos del texto que no intenresan (corchetes, enlaces...) 

    Args:
        texto (str): Texto de una review

    Returns:
        str: Texto procesado 
    """
    texto = re.sub(r'http\S+', "", texto) # eliminar links
    texto = re.sub(r"\[.*?\]", "", texto) # texto entre corchetes, era principalmente markdown 
    texto = " ".join(texto.split())
    return texto.strip()

def limpieza_final(texto): 
    """
    Normalizamos el texto de una review, quitando carácteres raros, acentos, pasar idiomas a unidecode...

    Args:
        texto (str): Texto de una review

    Returns:
        str: Texto procesado 
    """
    try:
        texto = unicodedata.normalize('NFKC', texto) # normaliza caracteres raros
        texto = unidecode(texto) # quita acentos y trata idiomas
        texto = re.sub(r'[^a-zA-Z0-9\s.,!?"\'()$%;\-&/]', ' ', texto) # elimina ruido y ascii art
        texto = " ".join(texto.split()) 
        return texto.lower().strip()
    except:
        return ""

def D2_limpieza_reviews(minio):
    print("Ejecutando limpieza reseñas\n")
    raw = read_file(steam_reviews_file, minio)
    df = to_dataframe(raw) # columnas: appid, is_positive, weight, text

    print("Primera fase limpieza...")
    df["text"] = df["text"].apply(limpieza_inicial) # quitar links y tags markdown

    print("Clasificando idiomas (tarda un rato)...") 
    df["language"] = df["text"].apply(detect_language)
    df_en = df[df["language"] == "en"].copy()

    print("Segunda fase limpieza...")
    df_en["text"] = df_en["text"].apply(limpieza_final) # emojis, unicode, ascii
    df_en["weight"] = df_en["weight"].astype(float)
    df.drop(columns=["language"], inplace=True)
    df_en.to_parquet(steam_reviews_parquet_file)

    if minio["minio_write"]:
            if upload_to_minio(steam_reviews_parquet_file):
                erase_file(steam_reviews_parquet_file)


if __name__ == "__main__":
    D2_limpieza_reviews()

