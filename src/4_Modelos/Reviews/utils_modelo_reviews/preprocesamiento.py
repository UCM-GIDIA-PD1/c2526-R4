''''
Módulo de preprocesamiento de dataframe de reviews para el análisis de los comentarios de Steam
'''

from src.utils.files import read_file
from src.utils.config import reviews
from sklearn.model_selection import train_test_split
import re
from nltk.stem import PorterStemmer
from nltk.stem import WordNetLemmatizer
from nltk.corpus import stopwords

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

def clean_text(text, ps=PorterStemmer(), stop_words=set(stopwords.words("english"))):
    """Se queda solo lo que es texto, quitando stopwords y aplicando stemming"""
    text = re.sub(r"[^a-z\s]", "", text)
    return " ".join(ps.stem(word) for word in text.split() if word not in stop_words)


def clean_text_lemma(text, lemmatizer=WordNetLemmatizer(), stop_words=set(stopwords.words("english"))):
    """Se queda solo lo que es texto, quitando stopwords y aplicando stemming"""
    text = re.sub(r"[^a-z\s]", "", text)
    return " ".join(lemmatizer.lemmatize(word) for word in text.split() if word not in stop_words)

def train_val_test_split(X, y):
    """Divide los datos en conjuntos de entrenamiento (70%), validación (15%) y prueba (15%).

    Args:
        X (pd.DataFrame): Matriz de características.
        y (pd.Series): Vector de etiquetas.

    Returns:
        tuple: Una tupla conteniendo seis elementos en este orden:
            X_train, X_val, X_test, y_train, y_val, y_test.
    """

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    return X_train, X_val, X_test, y_train, y_val, y_test

