"""
Dado precios.parquet crea un modelo de knn para predecir en que rango de precio se sitúa un juego 
según sus características.
"""

from src.D_Modelos.Precios.utils.utils import get_metrics, read_prices, train_val_test_split, normalize_train_test, cluster_embedings, get_train_test
from src.utils.config import precios_knncompleteclusters_file, models_precios_path
from src.utils.files import write_to_file

from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import PowerTransformer, StandardScaler, MinMaxScaler, OrdinalEncoder, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.model_selection import cross_validate
from sklearn.pipeline import Pipeline


import wandb
import os

import pandas as pd
from src.utils.config import seed

def grid_search_knn_full(X_train,  y_train):
    """
    Optimización de hiperparámetros para K-NN usando los conjuntos de train y validation.

    Args:
        - X_train (pd.Dataframe):  Conjunto de entranamiento
        - X_val (pd.Dataframe): Conjunto de entranamiento
        - y_train (pd.Dataframe): Variable objetivo del conjunto de entrenamiento
        - y_val (pd.Dataframe): Variable objetivo del conjunto de validacion

    Returns:
        best_params (dict): Diccionario que contiene los parámetros (n_neighbors, weights, metric) del mejor modelo
    """
    param_grid = {
        'n_neighbors': list(range(1, 40, 1)),
        'weights': ['uniform', 'distance'],
        'metric': ['euclidean', 'manhattan']
    }

    best_params = None
    best_score = -1

    print('Optimizando')
    for n in param_grid['n_neighbors']:
        for w in param_grid['weights']:
            for m in param_grid['metric']:
                knn = KNeighborsClassifier(n_neighbors=n, weights=w, metric=m)
                score = cross_validate(knn, X_train, y_train, cv=5, scoring= 'f1_weighted', return_train_score= False)
                score = score['test_score'].mean()

                if score > best_score:
                    best_score = score
                    best_params = {'n_neighbors': n, 'weights': w, 'metric': m}
                
                print('Best Params: ', best_params)

    print("Mejor combinación de parámetros:", best_params)
    print("Mejor score en validación:", best_score)

    return best_params

def _complete_model(df, minio, modelName='K-NN Complete Clusters'):
    """
    Modelo completo de K-NN usando clusters de los embeddings.

    Args:
        - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
        - modelName (String): Nombre del modelo a subir a wandb
    Returns:
        None
    """
    print(f'Creando modelo {modelName}...')
    df = df.dropna()

    # Tranformación del target
    le = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    df['price_range'] = le.fit_transform(df[['price_range']])

    # División del train y test
    X_train, X_test, y_train, y_test = get_train_test(df)

    # Transformaciones del modelo
    X_train, X_test = cluster_embedings(X_train, X_test, emb_col='v_clip')
    cols_sesgadas = ['num_languages', 'num_juegos_previos_developers', 'ema_precio_developers', 'max_historico_precio_developers',
                     'num_juegos_previos_publishers', 'ema_precio_publishers', 'max_historico_precio_publishers']
    cols_normales = ['description_len']
    cols_minmax = ['release_year', 'brillo']
    cols_ohe = ['cluster']

    final_transformers = [
        ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
        ('normales', StandardScaler(), cols_normales),
        ('minmax', MinMaxScaler(), cols_minmax),
        ('ohe', OneHotEncoder(handle_unknown='ignore', sparse_output=False), cols_ohe)
    ]
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='knn'
    )
    
    preprocessor  = ColumnTransformer(transformers=final_transformers, remainder='passthrough')
    best_params = grid_search_knn_full(X_train, y_train)

    # Creamos el pipeline del modelo
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', KNeighborsClassifier(**best_params))
    ])

    # Obtenemos predicciones
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_test_labels = le.inverse_transform(y_test.values.reshape(-1, 1)).flatten()
    y_pred_labels = le.inverse_transform(y_pred.reshape(-1, 1)).flatten()

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path='models/precios/graficos/confusionMatrix/knn_complete_clusters.png',
        download_images=False
    )

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(pipeline, precios_knncompleteclusters_file, minio)
    print(f"Modelo guardado en {precios_knncompleteclusters_file}")

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def knnprecios(minio):
    df = read_prices(minio)
    _complete_model(df.copy(), minio, modelName='K-NN Complete Clusters')

def main(minio = {"minio_write": False, "minio_read": False}):
    knnprecios(minio)

if __name__ == "__main__":
    main()
