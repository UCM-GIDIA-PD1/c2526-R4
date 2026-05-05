''''
Módulo de preprocesamiento de dataframe de precios para los modelos de predicción de rango de precio de un juego.
'''

from src.utils.files import read_file, write_to_file
from src.utils.config import prices, reduced_prices, new_data_prices
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import train_test_split    
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix 
from sklearn.metrics import ConfusionMatrixDisplay, classification_report

import os
import joblib

from numpy import vstack
from pandas import concat
from src.utils.config import seed

def read_prices(minio = {"minio_write": False, "minio_read": False}):
    """Lee y limpia el dataset de precios desde un archivo Parquet.

    Args:
        minio (dict): Configuración de acceso a MinIO. 
            Diccionario con llaves 'minio_write' y 'minio_read' (bool).

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

def read_new_data(minio={"minio_write": False, "minio_read": False}):
    df = read_file(filepath=new_data_prices, minio=minio)
    assert df is not None, f'Error archivo {new_data_prices.name} no encontrado'

    return df


def read_prices_reduced(minio = {"minio_write": False, "minio_read": False}):
    df = read_file(filepath=reduced_prices, minio=minio)
    assert df is not None, 'Error archivo precios_reducido.parquet no encontrado'
    return df

def get_train_test(df):
    """Divide los datos en los conjuntos de entrenamiento (80%) y prueva (20%)
    
    Args:
        X (pd.DataFrame): Matriz de características.
        y (pd.Series): Vector de etiquetas.

    Returns:
        tuple: Una tupla conteniendo elementos en este orden:
            X_train, X_test, y_train, y_test.
    """ 
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=seed, stratify=y)
    return X_train, X_test, y_train, y_test

def train_val_test_split(X, y):
    """Divide los datos en conjuntos de entrenamiento (70%), validación (15%) y prueba (15%).

    Args:
        X (pd.DataFrame): Matriz de características.
        y (pd.Series): Vector de etiquetas.

    Returns:
        tuple: Una tupla conteniendo seis elementos en este orden:
            X_train, X_val, X_test, y_train, y_val, y_test.
    """

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=seed, stratify=y_temp)

    return X_train, X_val, X_test, y_train, y_val, y_test


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
    pca = PCA(n_components=n_comp, random_state=seed)

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

def combine_train_val(X_train, X_val, y_train, y_val):
    X_train = concat([X_train, X_val])
    y_train = concat([y_train, y_val])

    return X_train, y_train

def get_metrics(y_test, y_pred, classes=None, img_path=None, download_images=False):
    """Calcula y muestra las métricas de rendimiento para un modelo de clasificación.

    Args:
        y_test (pd.Dataframe): Etiquetas reales del conjunto de prueba.
        y_pred (pd.Dataframe): Etiquetas predichas por el modelo.
        classes (list, optional): Nombres de las categorías para el informe de 
            clasificación. Por defecto es None.
        img_path (str | Path, optional): ruta en donde guardar la imagen
        download_images (bool, optional): booleano que indica si guardar la imagen localmente

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

    wandb_matrix = None
    if classes is not None:
        import matplotlib.pyplot as plt
        import wandb
        fig, ax = plt.subplots(figsize=(10,6))
        disp = ConfusionMatrixDisplay.from_predictions(
            y_test, y_pred,
            labels=classes, 
            display_labels=classes,
            cmap='Blues',
            ax=ax,
            xticks_rotation=45
        )

        wandb_matrix = wandb.Image(fig)

        if img_path and download_images:
            os.makedirs(os.path.dirname(img_path), exist_ok=True)
            write_to_file(data=disp.figure_, filepath=img_path)
        else:
            plt.close()

    return {'accuracy': acc, 'precision': prec, 'recall': rec, 'f1-score': f1, 
            'confusion_matrix': wandb_matrix }

def save_model(output_file, final_model):
    os.makedirs('models/precios', exist_ok=True)
    joblib.dump(final_model, f"models/precios/{output_file}")
    print(f"Modelo guardado en models/precios/{output_file}")

def save_confusion_matrix(y_test, y_pred, classes, img_path='models/media/confusionmatrix.png', encoder=None):
    import matplotlib.pyplot as plt
    if encoder:
        y_test= encoder.inverse_transform(y_test)
        y_preds= encoder.inverse_transform(y_pred)
        
    fig, ax = plt.subplots(figsize=(10,6))
    disp = ConfusionMatrixDisplay.from_predictions(
        y_test, y_pred, 
        display_labels=classes,
        cmap='Blues',
        ax=ax,
        xticks_rotation=45
    )
    write_to_file(data=disp.figure_, filepath=img_path)


