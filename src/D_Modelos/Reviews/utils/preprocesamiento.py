''''
Módulo de preprocesamiento de dataframe de reviews para el análisis de los comentarios de Steam
'''

from src.utils.files import read_file
from src.utils.config import reviews, new_data_reviews
import re
import nltk
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords
from src.utils.config import seed

def read_reviews(minio={"minio_write": False, "minio_read": False}):
    """Lee el dataset de reviews desde un archivo Parquet.

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

def read_new_data(minio={"minio_write": False, "minio_read": False}):
    
    
    df = read_file(filepath=new_data_reviews, minio=minio)
    assert df is not None, 'Error archivo reviews.parquet no encontrado'

    return df

def _get_stopwords():
    try:
        return set(stopwords.words("english"))
    except LookupError:
        nltk.download('stopwords')
        nltk.download('wordnet')
        return set(stopwords.words("english"))

def clean_text_stem(text, stemmer=None, stop_words=None):
    """Se queda solo lo que es texto, quitando stopwords y aplicando stemming"""
    if stemmer is None:
        stemmer = PorterStemmer()
    if stop_words is None:
        stop_words = _get_stopwords()

    text = re.sub(r"[^a-z\s]", "", text.lower())
    return " ".join(stemmer.stem(word) for word in text.split() if word not in stop_words)

def clean_text_lemma(text, lemmatizer=None, stop_words=None):
    """Se queda solo lo que es texto, quitando stopwords y aplicando stemming"""
    if lemmatizer is None:
        lemmatizer = WordNetLemmatizer()
    if stop_words is None:
        stop_words = _get_stopwords()

    text = re.sub(r"[^a-z\s]", "", text.lower())
    return " ".join(lemmatizer.lemmatize(word) for word in text.split() if word not in stop_words)