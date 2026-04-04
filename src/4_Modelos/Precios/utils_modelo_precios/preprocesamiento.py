''''
Módulo de preprocesamiento de dataframe de precios para los modelos de predicción de rango de precio de un juego.
'''

from src.utils.files import read_file
from src.utils.config import prices
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split    
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report
from pandas import Series
from umap import UMAP
from numpy import vstack

def read_prices(minio={"minio_write": False, "minio_read": False}):
    """Lee y limpia el dataset de precios desde un archivo Parquet.

    Args:
        minio (dict): Configuración de acceso a MinIO. 
            Diccionario con llaves 'minio_write' y 'minio_read' (bool).
            Por defecto: {"minio_write": False, "minio_read": False}.

    Returns:
        pd.DataFrame: Conjunto de datos procesado.

    Raises:
        AssertionError: Si el archivo no se encuentra o la carga falla.
    """
    df = read_file(filepath=prices, minio=minio)
    assert df is not None, 'Error archivo precios.parquet no encontrado'

    df.drop(columns=['id','name','price_overview','v_resnet','v_convnext'], inplace=True)
    df['release_year'] = df['release_year'].apply(lambda x : int(x))

    return df

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

def umap_embeddings(X_train, X_val, X_test, emb_col, n_components=16):
    """
    Aplica UMAP a la columna de embeddings para train, validation y test.
    
    Args:
        X_train, X_val, X_test (pd.DataFrame): DataFrames con la columna de embeddings.
        emb_col (str): Nombre de la columna de embeddings.
        n_components (int): Número de componentes de UMAP.
        random_state (int): Semilla para reproducibilidad.
        
    Returns:
        tuple: (X_train_umap, X_val_umap, X_test_umap) con las columnas UMAP agregadas
               y la columna original de embeddings eliminada.
    """
    clip_matrix_train = vstack(X_train[emb_col].values)
    clip_matrix_val   = vstack(X_val[emb_col].values)
    clip_matrix_test  = vstack(X_test[emb_col].values)
    
    umap = UMAP(n_components=n_components, random_state=42)
    clip_reduced_train = umap.fit_transform(clip_matrix_train)
    clip_reduced_val   = umap.transform(clip_matrix_val)
    clip_reduced_test  = umap.transform(clip_matrix_test)
    
    for i in range(n_components):
        X_train[f'clip_umap_{i}'] = clip_reduced_train[:, i]
        X_val[f'clip_umap_{i}']   = clip_reduced_val[:, i]
        X_test[f'clip_umap_{i}']  = clip_reduced_test[:, i]
    
    # Eliminar la columna original
    X_train = X_train.drop(columns=[emb_col])
    X_val   = X_val.drop(columns=[emb_col])
    X_test  = X_test.drop(columns=[emb_col])
    
    return X_train, X_val, X_test


def cluster_embedings(X_train, X_val, X_test, emb_col,  n_clusters=8): 
    """
    Dado un dataFrame y una columna donde se encuentran los embeddings, devuelve un array resultado del clustering de esos embeddings.
    """
    clip_matrix_train = vstack(X_train[emb_col].values)
    clip_matrix_val   = vstack(X_val[emb_col].values)
    clip_matrix_test  = vstack(X_test[emb_col].values)
    
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    cluster_train = kmeans.fit_predict(clip_matrix_train)
    cluster_val   = kmeans.predict(clip_matrix_val)
    cluster_test  = kmeans.predict(clip_matrix_test)
    
    X_train['cluster'] = cluster_train
    X_val['cluster']   = cluster_val
    X_test['cluster']  = cluster_test
    
    X_train = X_train.drop(columns=[emb_col])
    X_val   = X_val.drop(columns=[emb_col])
    X_test  = X_test.drop(columns=[emb_col])

    return X_train, X_val, X_test

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

def get_metrics(y_test, y_pred, classes=None):
    """Calcula y muestra las métricas de rendimiento para un modelo de clasificación.

    Args:
        y_test (pd.Dataframe): Etiquetas reales del conjunto de prueba.
        y_pred (pd.Dataframe): Etiquetas predichas por el modelo.
        classes (list, optional): Nombres de las categorías para el informe de 
            clasificación. Por defecto es None.

    Returns:
        dict: Diccionario con las métricas calculadas:
            - 'accuracy': Exactitud global.
            - 'precision': Precisión media ponderada.
            - 'recall': Sensibilidad media ponderada.
            - 'f1': Puntuación F1 media ponderada.
    """
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, average='weighted')
    rec = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')

    print(f'Accuracy:  {acc}')
    print(f'Precision: {prec}')
    print(f'Recall:    {rec}')
    print(f'F1 Score:  {f1}')
    print(classification_report(y_test, y_pred, target_names=classes))

    cm = confusion_matrix(y_test, y_pred)
    print(cm)

    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1-score': f1 }