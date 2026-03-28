""""
Módulo de preprocesamiento de dataframe de precios para los modelos de predicción de rango de precio de un juego.
"""

import pandas as pd
import numpy as np
from src.utils.files import read_file
from src.utils.config import prices
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split    

def prices_dataframe() -> pd.DataFrame:
    """
    Lee el archivo de precios.parquet y devuelve el dataframe quitando las columnas que no se usarán para el modelo.

    Se eliminan las siguientes columnas:
        - id
        - name
        - price_overview
        - v_resnet
        - v_convnext
    """
    df = read_file(prices)
    assert df, 'Error archivo precios.parquet no encontrado'

    df.drop(columns=['id','name','price_overview','v_resnet','v_convnext'], inplace=True)
    return df

def train_val_test_split(X, y):
    """
    Dado un conjunto de datos X e y, realiza una división Train/Validation/Test de un 0.7/0.15/0.15.
    """

    X_train, X_temp, y_train, y_temp = train_test_split( X, y, test_size=0.3, random_state=42, stratify=y )
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp )

    return X_train, X_val, X_test, y_train, y_val, y_test

def cluster_embedings(df : pd.DataFrame, emb_col : str) -> np.ndarray: 
    """
    Dado un dataFrame y una columna donde se encuentran los embeddings, devuelve un array resultado del clustering de esos embeddings.
    """
    kmeans = KMeans(random_state=42)

    embed = df[emb_col].apply(pd.Series)
    clusters = kmeans.fit_predict(embed)

    return clusters

def normalize_train_test(X_train, X_val, X_test):
    """
    Dados unos conjuntos de entrenamiento train y test los normaliza usando StandardScaler.
    """
    scaler = StandardScaler()

    X_train_scaled = scaler.fit_transform(X_train)
    X_val_scaled = scaler.transform(X_val)
    X_test_scaled = scaler.transform(X_test)

    return X_train_scaled, X_val_scaled, X_test_scaled

def pca_train_test(X_train, X_val, X_test, n_comp = 0.9):
    """
    Dados unos conjuntos train y test realiza un pca sobre ellos para reducir dimensionalidad.
    """
    pca = PCA(n_components=n_comp, random_state=42)

    X_train_pca = pca.fit_transform(X_train)
    X_val_pca = pca.transform(X_val)
    X_test_pca = pca.transform(X_test)

    return X_train_pca, X_val_pca, X_test_pca