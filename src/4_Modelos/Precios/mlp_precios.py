"""
Dado precios.parquet crea diferentes modelos de MLP para predecir en que rango 
de precio se sitúa un juego según sus características.
"""

from utils.utils import get_metrics, read_prices, train_val_test_split
from src.utils.config import precios_mlp_file, models_precios_path

from sklearn.preprocessing import StandardScaler, PowerTransformer, OrdinalEncoder, MinMaxScaler, OneHotEncoder
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPClassifier
from sklearn.cluster import KMeans
from sklearn.model_selection import cross_val_score
from umap import UMAP
import optuna
import joblib
import os

import wandb

from pandas import DataFrame, concat
from numpy import vstack

def _preprocess_train(df_X, df_y):
    """Función para transformar los datos para realiza MLP

    Args:
        df (DataFrame): Datos iniciales del modelo que van a ser procesados.
    
    Returns:
        DataFrame: Datos que contienen las variables regresoras.
        DataFrame: Datos que contienen las variables respuesta.
    """
    df_X = df_X.reset_index(drop=True)
    df_y = df_y.reset_index(drop=True)

    # Separación de DataFrames en diferentes tipos de variables
    X_num_log = df_X[['num_languages', 'total_games_by_publisher', 'total_games_by_developer']]
    X_num_std = df_X[['description_len', 'brillo']]
    X_num_minmax = df_X[['release_year']] # Fechas
    X_trans = df_X.drop(columns=['num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'description_len', 'release_year', 'brillo'])

    # Transformación de variables
    pt = PowerTransformer(method='yeo-johnson')
    X_num_log_trans = pt.fit_transform(X_num_log)

    mm = MinMaxScaler()
    X_num_minmax_trans = mm.fit_transform(X_num_minmax)

    std = StandardScaler()
    X_num_std_trans = std.fit_transform(X_num_std)

    ohe = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    y_trans = ohe.fit_transform(df_y)

    # Unificar datos transformados
    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_num_minmax_trans = DataFrame(X_num_minmax_trans, columns = mm.get_feature_names_out())
    df_y_trans = DataFrame(y_trans, columns = ohe.get_feature_names_out())

    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)
    df3 = concat([df2, df_num_minmax_trans], axis=1)

    # Variables eliminadas por poca relevancia (el estudio está en el notebook de MLP)
    df3 = df3.drop(columns=['Family Sharing', 'Online Co-op', 'Custom Volume Controls'])

    transformers = {'pt': pt, 'std': std, 'ohe': ohe, 'mm': mm}

    return df3, df_y_trans, transformers

def _preprocess_test(df_X, df_y, transformers):
    df_X = df_X.reset_index(drop=True)
    df_y = df_y.reset_index(drop=True)

    X_num_log = df_X[['num_languages', 'total_games_by_publisher', 'total_games_by_developer']]
    X_num_std = df_X[['description_len', 'brillo']]
    X_num_minmax = df_X[['release_year']] # Fechas
    X_trans = df_X.drop(columns=['num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'description_len', 'release_year', 'brillo'])

    pt = transformers['pt']
    X_num_log_trans = pt.transform(X_num_log)

    mm = transformers['mm']
    X_num_minmax_trans = mm.transform(X_num_minmax)

    std = transformers['std']
    X_num_std_trans = std.transform(X_num_std)

    ohe = transformers['ohe']
    y_trans = ohe.transform(df_y)

    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_num_minmax_trans = DataFrame(X_num_minmax_trans, columns = mm.get_feature_names_out())
    df_y_trans = DataFrame(y_trans, columns = ohe.get_feature_names_out())

    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)
    df3 = concat([df2, df_num_minmax_trans], axis=1)

    df3 = df3.drop(columns=['Family Sharing', 'Online Co-op', 'Custom Volume Controls'])

    return df3, df_y_trans

def _best_params_mlp(X_train, Y_train):
    """ GRIDSEARCH """
    param_grid = {
        'hidden_layer_sizes': [(64,32), (100,), (80,60), (64,50), (124,)],
        'activation': ['relu', 'tanh'],
        'alpha': [0.0001, 0.01, 0.1],
        'learning_rate_init': [0.001, 0.01]
    }
    """ MEJORES HIPERPARÁMETROS
    param_grid = {
        'hidden_layer_sizes': [(64,32)],
        'activation': ['tanh'],
        'alpha': [0.1],
        'learning_rate_init': [0.001]
    }"""

    grid = GridSearchCV(MLPClassifier(max_iter=5000, random_state=42), param_grid=param_grid, cv=5, n_jobs=-1)
    grid.fit(X_train, Y_train.values.flatten())

    params_mejor_modelo = grid.best_params_
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo

def _best_params_mlp_optuna_umap(X_train, Y_train):
    """ OPTUNA + UMAP """
    def objective(trial):
        params = {
            'hidden_layer_sizes': trial.suggest_categorical('hidden_layer_sizes', [(64,), (128,), (64, 32), (128, 64), (128, 64, 32)]),
            'activation': trial.suggest_categorical('activation', ['relu', 'tanh']),
            'alpha': trial.suggest_float('alpha', 1e-4, 1e-1, log=True),
            'learning_rate_init': trial.suggest_float('learning_rate_init', 1e-4, 1e-1, log=True)
        }

        n_components = trial.suggest_int('n_components', 2, 32) 

        X_train_trial = X_train.copy()
        clip_matrix_train = vstack(X_train_trial['v_clip'].values)
        
        umap = UMAP(n_components=n_components, random_state=42)
        clip_reduced_train = umap.fit_transform(clip_matrix_train)
        
        for i in range(n_components):
            X_train_trial[f'clip_umap_{i}'] = clip_reduced_train[:, i]
            
        X_train_trial = X_train_trial.drop(columns=['v_clip'])

        model = MLPClassifier(max_iter=5000, random_state=42, **params)
        
        score = cross_val_score(model, X_train_trial, Y_train.values.flatten(), cv=5, n_jobs=-1)
        return score.mean()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=20) 

    params_mejor_modelo = study.best_params
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo

def _best_params_mlp_optuna(X_train, Y_train):
    """ OPTUNA """
    def objective(trial):
        params = {
            'hidden_layer_sizes': trial.suggest_categorical('hidden_layer_sizes', [(64,), (128,), (64, 32), (128, 64), (128, 64, 32)]),
            'activation': trial.suggest_categorical('activation', ['relu', 'tanh']),
            'alpha': trial.suggest_float('alpha', 1e-4, 1e-1, log=True),
            'learning_rate_init': trial.suggest_float('learning_rate_init', 1e-4, 1e-1, log=True)
        }

        model = MLPClassifier(max_iter=5000, random_state=42, **params)
        
        score = cross_val_score(model, X_train, Y_train.values.flatten(), cv=5, n_jobs=-1)
        return score.mean()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)

    params_mejor_modelo = study.best_params
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo

def _mlp(X_train, X_test, Y_train, Y_test, best_params, model_name, transformers):
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

    run.log(metricas)

    
    os.makedirs(models_precios_path(), exist_ok=True)
    data = {
        'model': best_mlp,
        'transformers': transformers
    }
    joblib.dump(data, precios_mlp_file)
    print(f"Modelo guardado en {precios_mlp_file}")

    run.finish()


def main():
    # Preprocesado de datos
    print('Leyendo y preprocesando datos...')
    df = read_prices()

    y_all = DataFrame(df['price_range'])
    X_all = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X_all, y_all)

    # Para el entrenamiento de los MLP vamos a usar cross validation, por lo que vamos a usar 
    # la enteridad de los datos de entrenamiento para entrenar y validar el modelo
    X_train = concat([X_train, X_val], axis=0)
    y_train = concat([y_train, y_val], axis=0)

    X_train, Y_train, transformers = _preprocess_train(X_train, y_train)
    X_test, Y_test = _preprocess_test(X_test, y_test, transformers)

    """
    # MLP sin imágenes
    print('Buscando mejores parámetros para modelo sin imágenes...')
    X_train_no_img = X_train.drop(columns=['v_clip'])
    X_test_no_img = X_test.drop(columns=['v_clip'])
    best_params = _best_params_mlp(X_train_no_img, Y_train)

    print('Creando mejor modelo MLP sin imágenes...')
    _mlp(X_train_no_img, X_test_no_img, Y_train, Y_test, best_params, 'mlp-no-img')


    # MLP con imágenes (clusters)
    print('Buscando mejores parámetros para modelo con imágenes con clusters...')
    X_train_clusters = X_train.copy()
    X_test_clusters = X_test.copy()

    kmeans = KMeans(random_state=42, n_clusters=8)
    matrix_train = vstack(X_train_clusters['v_clip'].values)
    matrix_test = vstack(X_test_clusters['v_clip'].values)

    clusters_train = kmeans.fit_predict(matrix_train).reshape(-1, 1)
    clusters_test = kmeans.predict(matrix_test).reshape(-1, 1)

    ohe_clusters = OneHotEncoder(sparse_output=False)
    clusters_train_ohe = ohe_clusters.fit_transform(clusters_train)
    clusters_test_ohe = ohe_clusters.transform(clusters_test)

    for i in range(clusters_train_ohe.shape[1]):
        X_train_clusters[f'v_clip_cluster_{i}'] = clusters_train_ohe[:, i]
        X_test_clusters[f'v_clip_cluster_{i}'] = clusters_test_ohe[:, i]

    X_train_clusters = X_train_clusters.drop(columns=['v_clip'])
    X_test_clusters = X_test_clusters.drop(columns=['v_clip'])

    best_params = _best_params_mlp(X_train_clusters, Y_train)

    print('Creando mejor modelo MLP con imágenes con clusters...')
    _mlp(X_train_clusters, X_test_clusters, Y_train, Y_test, best_params, 'mlp-cluster-img')
    """

    # MLP con imágenes (UMAP)
    print('Buscando mejores parámetros para modelo con imágenes con UMAP...')
    X_train_umap = X_train.copy()
    X_test_umap = X_test.copy()

    clip_matrix_train = vstack(X_train_umap['v_clip'].values)
    clip_matrix_test = vstack(X_test_umap['v_clip'].values)

    umap = UMAP(n_components=19, random_state=42) # n_components = 19 es la reducción de dimensionalidad óptima

    clip_reduced_train = umap.fit_transform(clip_matrix_train)
    clip_reduced_test = umap.transform(clip_matrix_test)

    transformers['umap'] = umap

    for i in range(19):
        X_train_umap[f'clip_umap_{i}'] = clip_reduced_train[:, i]
        X_test_umap[f'clip_umap_{i}'] = clip_reduced_test[:, i]

    X_train_umap = X_train_umap.drop(columns=['v_clip'])
    X_test_umap = X_test_umap.drop(columns=['v_clip'])

    best_params_umap = _best_params_mlp(X_train_umap, Y_train)

    print('Creando mejor modelo MLP con imágenes con UMAP...')
    _mlp(X_train_umap, X_test_umap, Y_train, Y_test, best_params_umap, 'mlp-umap-img', transformers)


if __name__ == "__main__":
    main()
