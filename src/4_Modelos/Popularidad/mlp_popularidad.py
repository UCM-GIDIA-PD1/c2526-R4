"""
Dado precios.parquet crea diferentes modelos de MLP para predecir en que rango 
de precio se sitúa un juego según sus características.
"""

from src.utils.config import popularity
from src.utils.files import read_file

from sklearn.preprocessing import StandardScaler, PowerTransformer, MinMaxScaler, FunctionTransformer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.model_selection import cross_val_score
from sklearn.neural_network import MLPRegressor
from sklearn.decomposition import PCA
from umap import UMAP
import optuna

import wandb

from pandas import DataFrame, concat
from numpy import vstack, log1p, expm1
import joblib
import os

def _preprocess_train(df):
    """Función para transformar los datos para realiza MLP

    Args:
        df (DataFrame): Datos iniciales del modelo que van a ser procesados.
    
    Returns:
        DataFrame: Datos que contienen las variables regresoras.
        DataFrame: Datos que contienen las variables respuesta.
    """
    df = df.reset_index(drop=True)
    df = df.drop(columns=['price_range', 'id', 'name', 'v_resnet', 'v_convnext', 'yt_score'])

    # Separación de DataFrames en diferentes tipos de variables
    y = DataFrame(df['recomendaciones_totales'])
    X_num_log = df[['num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'price_overview']]
    X_num_minmax = df[['release_year']] # Fechas
    X_num_std = df[['brillo', 'description_len']]
    X_youtube = df[[c for c in df.columns if 'video_statistics' in c]]
    X_trans = df[['Action', 'Adventure', 'Casual', 'Early Access', 'Free To Play', 'Indie', 'RPG', 'Simulation', 'Strategy', 'Co-op', 
                  'Custom Volume Controls', 'Family Sharing', 'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP', 
                  'Partial Controller Support', 'Playable without Timed Input', 'PvP', 'Remote Play Together', 'Shared/Split Screen', 
                  'Single-player', 'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']]

    # Transformación de variables
    pt1 = FunctionTransformer(func=log1p, inverse_func=expm1, validate=True, feature_names_out="one-to-one")
    pt2 = PowerTransformer(method='yeo-johnson')
    y_trans = pt1.fit_transform(y)
    X_num_log_trans = pt2.fit_transform(X_num_log)

    std = StandardScaler()
    X_num_std_trans = std.fit_transform(X_num_std)

    mm = MinMaxScaler()
    X_num_minmax_trans = mm.fit_transform(X_num_minmax)

    pty = PowerTransformer(method='yeo-johnson')
    X_youtube_log = pty.fit_transform(X_youtube)
    pca = PCA(n_components=0.95)
    youtube_pca_trans = pca.fit_transform(X_youtube_log)

    # Datos a dataframes
    df_y_trans = DataFrame(y_trans, columns = pt1.get_feature_names_out())
    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt2.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_minmax_trans = DataFrame(X_num_minmax_trans, columns = mm.get_feature_names_out())
    df_youtube_pca_trans = DataFrame(youtube_pca_trans, columns = pca.get_feature_names_out())

    # Unificar datos transformados
    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)
    df3 = concat([df2, df_minmax_trans], axis=1)
    df4 = concat([df3, df_youtube_pca_trans], axis=1)

    # Aplicamos UMAP para reducir la dimensionalidad de los vectores de imágenes
    clip_matrix = vstack(df['v_clip'].values)
    umap = UMAP(n_components=18, random_state=42) 
    clip_reduced = umap.fit_transform(clip_matrix)
    
    for i in range(18):
        df4[f'clip_umap_{i}'] = clip_reduced[:, i]
    
    # Transformers usados para la transformación de los modelos
    transformers = {
        'pt1': pt1, 'pt2': pt2, 'std': std, 'mm': mm, 
        'pty': pty, 'pca': pca, 'umap': umap
    }

    return df4, df_y_trans, transformers

def _preprocess_test(df, transformers):
    df = df.reset_index(drop=True)
    df = df.drop(columns=['price_range', 'id', 'name', 'v_resnet', 'v_convnext', 'yt_score'])

    # Separación de DataFrames
    y = DataFrame(df['recomendaciones_totales'])
    X_num_log = df[['num_languages', 'total_games_by_publisher', 'total_games_by_developer', 'price_overview']]
    X_num_minmax = df[['release_year']]
    X_num_std = df[['brillo', 'description_len']]
    X_youtube = df[[c for c in df.columns if 'video_statistics' in c]]
    X_trans = df[['Action', 'Adventure', 'Casual', 'Early Access', 'Free To Play', 'Indie', 'RPG', 'Simulation', 'Strategy', 'Co-op', 
                  'Custom Volume Controls', 'Family Sharing', 'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP', 
                  'Partial Controller Support', 'Playable without Timed Input', 'PvP', 'Remote Play Together', 'Shared/Split Screen', 
                  'Single-player', 'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']]

    # Transformación de variables usando transform()
    pt1 = transformers['pt1']
    pt2 = transformers['pt2']
    y_trans = pt1.transform(y)
    X_num_log_trans = pt2.transform(X_num_log)

    std = transformers['std']
    X_num_std_trans = std.transform(X_num_std)

    mm = transformers['mm']
    X_num_minmax_trans = mm.transform(X_num_minmax)

    pty = transformers['pty']
    X_youtube_log = pty.transform(X_youtube)
    pca = transformers['pca']
    youtube_pca_trans = pca.transform(X_youtube_log)

    # Datos a dataframes
    df_y_trans = DataFrame(y_trans, columns = pt1.get_feature_names_out())
    df_num_log_trans = DataFrame(X_num_log_trans, columns = pt2.get_feature_names_out())
    df_num_std_trans = DataFrame(X_num_std_trans, columns = std.get_feature_names_out())
    df_minmax_trans = DataFrame(X_num_minmax_trans, columns = mm.get_feature_names_out())
    df_youtube_pca_trans = DataFrame(youtube_pca_trans, columns = pca.get_feature_names_out())

    # Unificar datos transformados
    df1 = concat([df_num_log_trans, df_num_std_trans], axis=1)
    df2 = concat([df1, X_trans], axis=1)
    df3 = concat([df2, df_minmax_trans], axis=1)
    df4 = concat([df3, df_youtube_pca_trans], axis=1)

    # Aplicamos UMAP usando la matriz generada durante el entrenamiento
    clip_matrix = vstack(df['v_clip'].values)
    umap = transformers['umap']
    clip_reduced = umap.transform(clip_matrix)
    
    for i in range(18):
        df4[f'clip_umap_{i}'] = clip_reduced[:, i] 
    
    return df4, df_y_trans

def _best_params_mlp(X_train, Y_train):
    param_grid = {
        'hidden_layer_sizes': [(64,32), (128, 64, 32), (128,64), (128,)],
        'activation': ['relu', 'tanh'],
        'alpha': [0.0001, 0.01, 0.1],
        'learning_rate_init': [0.001, 0.01]
    }

    grid = GridSearchCV(MLPRegressor(max_iter=5000, random_state=42), param_grid=param_grid, cv=5, n_jobs=-1)
    grid.fit(X_train, Y_train.values.flatten())

    params_mejor_modelo = grid.best_params_
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo


def _best_params_mlp_optuna(X_train, Y_train):
    def objective(trial):
        params = {
            'hidden_layer_sizes': trial.suggest_categorical('hidden_layer_sizes', [(64,32), (128, 64, 32), (128,64), (128,)]),
            'activation': trial.suggest_categorical('activation', ['relu', 'tanh']),
            'alpha': trial.suggest_categorical('alpha', [0.0001, 0.01, 0.1]),
            'learning_rate_init': trial.suggest_categorical('learning_rate_init', [0.001, 0.01])
        }

        modelo = MLPRegressor(max_iter=5000, random_state=42, **params)
        return cross_val_score(modelo, X_train, Y_train.values.flatten(), cv=5, n_jobs=-1).mean()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=30)

    params_mejor_modelo = study.best_params
    
    print(f'Los parámetros del mejor modelo son:\n{params_mejor_modelo}')

    return params_mejor_modelo

def _mlp(X_train, y_train, best_params, model_name, transformers):
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Popularidad", 
        name=model_name,
        job_type='mlp',
        config=best_params
    )
    
    best_mlp = MLPRegressor(max_iter=10000, random_state=42, activation=best_params['activation'],
                             hidden_layer_sizes=best_params['hidden_layer_sizes'], alpha=best_params['alpha'],
                             learning_rate_init=best_params['learning_rate_init'], early_stopping=True,
                             n_iter_no_change=20)
    best_mlp.fit(X_train, y_train.values.flatten())

    os.makedirs('data/models', exist_ok=True)
    model_path = 'data/models/mlp_model_popularidad.pkl'
    joblib.dump({
        'model': best_mlp,
        'transformers': transformers,
        'y_train_min': y_train.values.min(),
        'y_train_max': y_train.values.max()
    }, model_path)
    print(f"Modelo guardado en {model_path}")
    
    run.finish()


if __name__ == '__main__':
    # Lectura y división de datos
    print('Leyendo y preprocesando datos...')
    df = read_file(popularity)
    df_train, df_test = train_test_split(df, test_size=0.2, random_state=42)

    # Preprocesamiento
    X_train_base, y_train, transformers = _preprocess_train(df_train)
    
    # MLP Regressor con imágenes (umap)
    print('Encontrando el mejor modelo de MLP con imágenes...')
    best_params = _best_params_mlp(X_train_base, y_train)

    print('Creando mejor modelo MLP con imágenes...')
    _mlp(X_train_base, y_train, best_params, 'mlp-umap-img', transformers)
    