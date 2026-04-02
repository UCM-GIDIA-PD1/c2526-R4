''''
Módulo de preprocesamiento de dataframe de precios para los modelos de predicción de rango de precio de un juego.
'''

import pandas as pd
import numpy as np
from src.utils.files import read_file
from src.utils.config import prices
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split    
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report



def prices_dataframe() -> pd.DataFrame:
    '''
    Lee el archivo de precios.parquet y devuelve el dataframe quitando las columnas que no se usarán para el modelo.

    Se eliminan las siguientes columnas:
        - id
        - name
        - price_overview
        - v_resnet
        - v_convnext
    '''
    df = read_file(prices)
    assert df is not None, 'Error archivo precios.parquet no encontrado'

    df.drop(columns=['id','name','price_overview','v_resnet','v_convnext'], inplace=True)
    df['release_year'] = df['release_year'].apply(lambda x : int(x))

    return df

def train_val_test_split(X, y):
    '''
    Dado un conjunto de datos X e y, realiza una división Train/Validation/Test de un 0.7/0.15/0.15.
    '''

    X_train, X_temp, y_train, y_temp = train_test_split( X, y, test_size=0.3, random_state=42, stratify=y )
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp )

    return X_train, X_val, X_test, y_train, y_val, y_test

def cluster_embedings(df : pd.DataFrame, emb_col : str) -> np.ndarray: 
    '''
    Dado un dataFrame y una columna donde se encuentran los embeddings, devuelve un array resultado del clustering de esos embeddings.
    '''
    kmeans = KMeans(random_state=42)

    embed = df[emb_col].apply(pd.Series)
    clusters = kmeans.fit_predict(embed)

    return clusters

def normalize_train_test(X_train, X_val, X_test, columnas_numericas):
    '''
    Dados unos conjuntos de entrenamiento train y test los normaliza usando StandardScaler.
    '''
    scaler = StandardScaler()
    
    X_train = X_train.copy()
    X_val = X_val.copy()
    X_test = X_test.copy()
    
    X_train[columnas_numericas] = scaler.fit_transform(X_train[columnas_numericas])
    X_val[columnas_numericas] = scaler.transform(X_val[columnas_numericas])
    X_test[columnas_numericas] = scaler.transform(X_test[columnas_numericas])
    
    return X_train, X_val, X_test

def pca_train_test(X_train, X_val, X_test, n_comp = 0.9):
    '''
    Dados unos conjuntos train y test realiza un pca sobre ellos para reducir dimensionalidad.
    '''
    pca = PCA(n_components=n_comp, random_state=42)

    X_train_pca = pca.fit_transform(X_train)
    X_val_pca = pca.transform(X_val)
    X_test_pca = pca.transform(X_test)

    return X_train_pca, X_val_pca, X_test_pca

def class_weights(y):
    '''
    Dado el conjunto y saca los pesos de las clases, usado para tratar el desbalance entre clases al clasificar.
    '''
    sample_weights = compute_sample_weight(class_weight='balanced', y=y)
    return sample_weights

def get_metrics(y_test, y_pred, classes=None, confusion_m=True):
    '''
    Dados el output predecido del modelo con los datos de validación y los datos reales de validación se construyen
    las métricas necesarias para medir el rendimiento del modelo.
    '''
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted')
    rec = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')


    print(f'Accuracy:  {acc}')
    print(f'Precision: {prec}')
    print(f'Recall:    {rec}')
    print(f'F1 Score:  {f1}')
    print(classification_report(y_test, y_pred, target_names=classes))

    # 3. Matriz de Confusión Visual
    if confusion_m:
        cm = confusion_matrix(y_test, y_pred)
        print(cm)

    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1': f1 }