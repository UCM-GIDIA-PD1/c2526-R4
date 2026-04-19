"""
Dado precios.parquet crea un modelo de knn para predecir en que rango de precio se sitúa un juego 
según sus características.
"""

from src.D_Modelos.Precios.utils.utils import get_metrics, read_prices, cluster_embedings, get_train_test
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

def transform_knn(df):
    return df.copy()

def predict_knn(model_data, test_df, train_df):
    from src.D_Modelos.Precios.utils.utils import cluster_embedings
    X_train = train_df.drop(columns=['price_range']).fillna(0)
    X_test = test_df.drop(columns=['price_range']).fillna(0)
    
    _, X_test_clustered = cluster_embedings(X_train, X_test, emb_col='v_clip')
    
    y_pred = model_data.predict(X_test_clustered)
    
    le = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    le.fit([[c] for c in le.categories[0]])
    y_pred_labels = le.inverse_transform(y_pred.reshape(-1, 1)).flatten()
    return y_pred_labels

def grid_search_knn_full(X_train,  y_train):
    """
    Optimización de hiperparámetros para K-NN usando los conjuntos de train y validation.

    Args:
        - X_train (pd.Dataframe):  Conjunto de entranamiento
        - y_train (pd.Dataframe): Variable objetivo del conjunto de entrenamiento

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
    """Modelo de KNN para el problema de precios con el dataFrame completo + Clusters de imagenes.
    
    Se realizan las siguientes transformaciones al conjunto X:
        - PowerTransformer Yeo-Johnson en columnas sesgadas
        - StandardScaler en columnas normales
        - MinMaxScaler en columnas que sigan un orden lógico

    Se almacena el pipeline del modelo.

    Args:
        df (pd.DataFrame): Dataframe de entrada con los datos del modelo
        minio (Dict): Diccionario que indica si se desea guardar el modelo en minio
        modelName (str, optional): Nombre del modelo para subir a WnB. Defaults to 'K-NN Complete Clusters'.
    """
    print(f'Creando modelo {modelName}...')
    df = df.dropna()

    le = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    df['price_range'] = le.fit_transform(df[['price_range']])

    X_train, X_test, y_train, y_test = get_train_test(df)

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
    
    preprocessor = ColumnTransformer(transformers=final_transformers, remainder='passthrough')

    X_train_transformed = preprocessor.fit_transform(X_train)

    run = wandb.init(entity="pd1-c2526-team4", project="Precios", name=modelName, job_type='knn')

    best_params = grid_search_knn_full(X_train_transformed, y_train)

    clf = KNeighborsClassifier(**best_params)
    clf.fit(X_train_transformed, y_train)

    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', clf)
    ])
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)
    y_test_labels = le.inverse_transform(y_test.values.reshape(-1, 1)).flatten()
    y_pred_labels = le.inverse_transform(y_pred.reshape(-1, 1)).flatten()
    
    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=le.categories_[0],
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
