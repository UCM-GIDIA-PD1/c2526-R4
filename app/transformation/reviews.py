"""Módulo de transformación para los 2 problemas de reviews:

    - Puntos positivos y negativos de un juego
    - Predecir si una reseña es positva o negativa
"""
import pandas as pd

from src.B_Transformacion.D2_limpieza_reviews import to_dataframe, detect_language, limpieza_final, limpieza_inicial

def transform_reviews_list(game_reviews : list[dict]) -> pd.DataFrame:
    """Dada una lista de reviews de un juego los transforma para que sean aptos para el problema de top
    Devuelve las siguientes columnas:
        - appid: ID del juego en Steam.
        - is_positive: Si la review es positiva o negativa.
        - weight: Peso/utilidad de la review.
        - text: Texto de la review limpio y normalizado.

    """
    reviews_df = to_dataframe(game_reviews) # columnas: appid, is_positive, weight, text

    reviews_df["text"] = reviews_df["text"].apply(limpieza_inicial) # quitar links y tags markdown

    reviews_df["language"] = reviews_df["text"].apply(detect_language)
    eng_reviews_df = reviews_df[reviews_df["language"] == "en"].copy()

    eng_reviews_df["text"] = eng_reviews_df["text"].apply(limpieza_final) # emojis, unicode, ascii
    eng_reviews_df["weight"] = eng_reviews_df["weight"].astype(float)

    return eng_reviews_df

def clean_text(text : str) -> pd.DataFrame:
    """Dado un texto realiza la limpieza para poder meterlo al modelo de predecir si es positivo o negativo
    """
    text = limpieza_inicial(text)
    text = limpieza_final(text)

    return text




