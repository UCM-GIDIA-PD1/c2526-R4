"""Módulo de transformación para los 2 problemas de reviews:

    - Puntos positivos y negativos de un juego
    - Predecir si una reseña es positva o negativa
"""
import unicodedata
import re
from unidecode import unidecode
from langdetect import detect
import pandas as pd


def transform_reviews_list(game_reviews : list) -> pd.DataFrame:
    """Dada una lista de reviews de un juego los transforma para que sean aptos para el problema de top
    """
    reviews_df = to_dataframe(game_reviews) # columnas: appid, is_positive, weight, text

    reviews_df["text"] = reviews_df["text"].apply(initial_text_filter) # quitar links y tags markdown

    reviews_df["language"] = reviews_df["text"].apply(detect_language)
    eng_reviews_df = reviews_df[reviews_df["language"] == "en"].copy()

    eng_reviews_df["text"] = eng_reviews_df["text"].apply(limpieza_final) # emojis, unicode, ascii
    eng_reviews_df["weight"] = eng_reviews_df["weight"].astype(float)
    # df.drop(columns=["language"], inplace=True)

    return eng_reviews_df

def transform_text(text : str) -> pd.DataFrame:
    pass

def to_dataframe(raw : list) -> pd.DataFrame:
    
    """
    Crea el DataFrame procesando la información de las reviews de cada juego.
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

def clean_text(text : str) -> str:
    pass

def detect_language(text : str) -> str:
    """
    Usando detect del módulo langdetect, devolvemos el lenguaje en el que está escrito.
    """
    try:
        return detect(text)
    except:
        return "unknown"


def initial_text_filter(texto : str) -> str:
    """
    Eliminamos aspectos del texto que no intenresan (corchetes, enlaces...) 
    """
    texto = re.sub(r'http\S+', "", texto) # eliminar links
    texto = re.sub(r"\[.*?\]", "", texto) # texto entre corchetes, era principalmente markdown 
    texto = " ".join(texto.split())
    return texto.strip()


def limpieza_final(texto : str) -> str: 
    """
    Normalizamos el texto de una review, quitando carácteres raros, acentos, pasar idiomas a unidecode...
    """
    try:
        texto = unicodedata.normalize('NFKC', texto) # normaliza caracteres raros
        texto = unidecode(texto) # quita acentos y trata idiomas
        texto = re.sub(r'[^a-zA-Z0-9\s.,!?"\'()$%;\-&/]', ' ', texto) # elimina ruido y ascii art
        texto = " ".join(texto.split()) 
        return texto.lower().strip()
    except:
        return ""
    


