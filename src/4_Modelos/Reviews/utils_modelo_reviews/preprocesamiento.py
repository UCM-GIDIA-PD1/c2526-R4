''''
Módulo de preprocesamiento de dataframe de reviews para el análisis de los comentarios de Steam
'''

from src.utils.files import read_file
from src.utils.config import reviews

import re
from nltk.stem import PorterStemmer

def read_reviews(minio={"minio_write": False, "minio_read": False}):
    """Lee y limpia el dataset de reviews desde un archivo Parquet.

    Args:
        minio (dict): Configuración de acceso a MinIO. 
            Diccionario con llaves 'minio_write' y 'minio_read' (bool).
            Por defecto: {"minio_write": False, "minio_read": False}.

    Returns:
        pd.DataFrame: Conjunto de datos procesado.

    Raises:
        AssertionError: Si el archivo no se encuentra o la carga falla.
    """
    df = read_file(filepath=reviews, minio=minio)
    assert df is not None, 'Error archivo reviews.parquet no encontrado'

    return df

def clean_text(text, ps, stop_words):
    """Se queda solo lo que es texto, quitando stopwords y aplicando stemming"""
    text = re.sub(r"[^a-z\s]", "", text)
    return " ".join(ps.stem(word) for word in text.split() if word not in stop_words)
    