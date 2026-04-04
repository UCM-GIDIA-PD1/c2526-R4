"""
Dado precios.parquet crea diferentes modelos de MLP para predecir en que rango 
de precio se sitúa un juego según sus características.
"""

from src.utils.config import prices
from src.utils.files import read_file
from utils_modelo_precios.preprocesamiento import get_metrics, cluster_embedings

from sklearn.preprocessing import StandardScaler, PowerTransformer, OrdinalEncoder
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.neural_network import MLPClassifier
from sklearn.cluster import KMeans
from umap import UMAP

import wandb

from pandas import DataFrame, concat
from numpy import vstack

def _preprocess_train(df):
    """Función para transformar los datos para realiza MLP

    Args:
        df (DataFrame): Datos iniciales del modelo que van a ser procesados.
    
    Returns:
        DataFrame: Datos que contienen las variables regresoras.
        DataFrame: Datos que contienen las variables respuesta.
    """
    df = df.reset_index(drop=True)
    df = df.drop(columns=['price_overview'])

    # Separación de DataFrames en diferentes tipos de variables
    y = DataFrame(df['price_range'])
    X_num_log = df[['num_languages', 'total_games_by_publisher', 'total_games_by_developer']]
    X_num_std = df[['description_len', 'release_year', 'brillo']]
    X_trans = df.drop(columns=['price_range', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'description_len', 'release_year', 'brillo'])

    # Transformación de variables
    pt = PowerTransformer(method='yeo-johnson')
    X_num_log_trans = pt.fit_transform(X_num_log)

    std = StandardScaler()
    X_num_std_trans = std.fit_transform(X_num_std)

    ohe = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    y_trans = ohe.fit_transform(y)

    # Unificar datos transformados
    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_y_trans = DataFrame(y_trans, columns = ohe.get_feature_names_out())

    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)

    # Variables eliminadas por poca relevancia (el estudio está en el notebook de MLP)
    df2 = df2.drop(columns=['Family Sharing', 'Online Co-op', 'Custom Volume Controls'])

    # Variables no usadas en el análisis
    df2 = df2.drop(columns=['id', 'name'])
    df2 = df2.drop(columns=['v_resnet', 'v_convnext'])

    transformers = {'pt': pt, 'std': std, 'ohe': ohe}

    return df2, df_y_trans, transformers

def _preprocess_test(df, transformers):
    df = df.reset_index(drop=True)
    df = df.drop(columns=['price_overview'])

    y = DataFrame(df['price_range'])
    X_num_log = df[['num_languages', 'total_games_by_publisher', 'total_games_by_developer']]
    X_num_std = df[['description_len', 'release_year', 'brillo']]
    X_trans = df.drop(columns=['price_range', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'description_len', 'release_year', 'brillo'])

    pt = transformers['pt']
    X_num_log_trans = pt.transform(X_num_log)

    std = transformers['std']
    X_num_std_trans = std.transform(X_num_std)

    ohe = transformers['ohe']
    y_trans = ohe.transform(y)

    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_y_trans = DataFrame(y_trans, columns = ohe.get_feature_names_out())

    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)

    df2 = df2.drop(columns=['Family Sharing', 'Online Co-op', 'Custom Volume Controls'])
    df2 = df2.drop(columns=['id', 'name'])
    df2 = df2.drop(columns=['v_resnet', 'v_convnext'])

    return df2, df_y_trans

def _best_params_mlp(X_train, Y_train):
    param_grid = {
        'hidden_layer_sizes': [(64,32), (100,), (80,60), (64,50), (124,)],
        'activation': ['relu', 'tanh'],
        'alpha': [0.0001, 0.01, 0.1],
        'learning_rate_init': [0.001, 0.01]
    }

    grid = GridSearchCV(MLPClassifier(max_iter=5000, random_state=42), param_grid=param_grid, cv=5, n_jobs=-1)
    grid.fit(X_train, Y_train.values.flatten())

    params_mejor_modelo = grid.best_params_
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo

def _mlp(X_train, X_test, Y_train, Y_test, best_params, model_name):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name=model_name,
        job_type='mlp',
        config=best_params
    )
    
    best_mlp = MLPClassifier(max_iter=10000, random_state=42, activation=best_params['activation'],
                             hidden_layer_sizes=best_params['hidden_layer_sizes'], alpha=best_params['alpha'],
                             learning_rate_init=best_params['learning_rate_init'])
    best_mlp.fit(X_train, Y_train.values.flatten())

    Y_pred = best_mlp.predict(X_test)
    metricas = get_metrics(Y_test.values.flatten(), Y_pred, classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'])

    run.log({
        'accuracy' : metricas['accuracy'],
        'precision' : metricas['precision'],
        'recall' : metricas['recall'],
        'f1-score' : metricas['f1']
    })

    run.finish()

if __name__ == '__main__':
    # Preprocesado de datos
    print('Leyendo y preprocesando datos...')
    df = read_file(prices)
    df_train, df_test = train_test_split(df, test_size=0.3, random_state=42)
    X_train, Y_train, transformers = _preprocess_train(df_train)
    X_test, Y_test = _preprocess_test(df_test, transformers)


    # MLP sin imágenes
    print('Buscando mejores parámetros para modelo sin imágenes...')
    X_train_no_img = X_train.drop(columns=['v_clip'])
    X_test_no_img = X_test.drop(columns=['v_clip'])
    best_params = _best_params_mlp(X_train_no_img, Y_train)

    print('Creando mejor modelo MLP sin imágenes...')
    _mlp(X_train_no_img, X_test_no_img, Y_train, Y_test, best_params, 'sklearn-mlp-no-img')
    

    # MLP con imágenes (clusters)
    print('Buscando mejores parámetros para modelo con imágenes con clusters...')
    X_train_clusters = X_train.copy()
    X_test_clusters = X_test.copy()

    kmeans = KMeans(random_state=42, n_clusters=8)
    matrix_train = vstack(X_train_clusters['v_clip'].values)
    matrix_test = vstack(X_test_clusters['v_clip'].values)

    X_train_clusters['v_clip_cluster'] = kmeans.fit_predict(matrix_train)
    X_test_clusters['v_clip_cluster'] = kmeans.predict(matrix_test)

    X_train_clusters = X_train_clusters.drop(columns=['v_clip'])
    X_test_clusters = X_test_clusters.drop(columns=['v_clip'])

    best_params = _best_params_mlp(X_train_clusters, Y_train)

    print('Creando mejor modelo MLP con imágenes con clusters...')
    _mlp(X_train_clusters, X_test_clusters, Y_train, Y_test, best_params, 'sklearn-mlp-cluster-img')
    

    # MLP con imágenes (UMAP)
    print('Buscando mejores parámetros para modelo con imágenes con UMAP...')
    X_train_umap = X_train.copy()
    X_test_umap = X_test.copy()

    clip_matrix_train = vstack(X_train_umap['v_clip'].values)
    clip_matrix_test = vstack(X_test_umap['v_clip'].values)

    umap = UMAP(n_components=16, random_state=42) 

    clip_reduced_train = umap.fit_transform(clip_matrix_train)
    clip_reduced_test = umap.transform(clip_matrix_test)
    
    for i in range(16):
        X_train_umap[f'clip_umap_{i}'] = clip_reduced_train[:, i]
        X_test_umap[f'clip_umap_{i}'] = clip_reduced_test[:, i]
    
    X_train_umap = X_train_umap.drop(columns=['v_clip'])
    X_test_umap = X_test_umap.drop(columns=['v_clip'])
    
    best_params_umap = _best_params_mlp(X_train_umap, Y_train)

    print('Creando mejor modelo MLP con imágenes con UMAP...')
    _mlp(X_train_umap, X_test_umap, Y_train, Y_test, best_params_umap, 'sklearn-mlp-umap-img')