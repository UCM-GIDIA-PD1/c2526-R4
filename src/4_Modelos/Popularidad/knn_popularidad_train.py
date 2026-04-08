from src.utils.config import popularity, load_env_file
from src.utils.files import read_file, seed

from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, mean_squared_log_error
from sklearn.model_selection import train_test_split, KFold, cross_validate
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor

import pandas as pd
import numpy as np
import optuna
import warnings
import xgboost as xgb

from umap import UMAP

import matplotlib.pyplot as plt

def get_metrics(y_test, y_pred):
    '''
    Dados el output predecido del modelo y los datos reales, se construyen
    las métricas necesarias para medir el rendimiento de un modelo de REGRESIÓN.
    '''
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)

    print(f'MAE (Error Absoluto Medio): {mae:.4f}')
    print(f'RMSE (Raíz del Error Cuadrático Medio): {rmse:.4f}')
    print(f'R2 Score (Coef. de Determinación): {r2:.4f}')

    return {'mae': mae, 'rmse': rmse, 'r2': r2}

def _preprocess(df, image_col='v_clip', use_images=True):
    images_cols = ['v_clip', 'v_convnext', 'v_resnet']

    assert image_col in images_cols, "Seleccione una columna de imágenes válida"

    df_clean = df.copy()
    
    # Encuentra todas las columnas que tengan "video_statistics" en su nombre
    video_cols = [col for col in df_clean.columns if 'video_statistics' in col]

    # Seleccionamos las variables de entrada útiles
    target_col = df_clean['recomendaciones_totales']
    erase_columns = ['id', 'name', 'price_range']
    erase_columns.extend(video_cols)
    images_cols.remove(image_col)
    erase_columns.extend(images_cols)
    df_clean = df_clean.drop(columns=erase_columns, errors='ignore')

    if use_images:
        # Vamos a preparar el DataFrame para que scikit-learn haga el PCA mas adelante
        # Forzamos a que todos los valores de la columna de los embeddings sean iterables
        zero_vector = np.zeros(512)
        df_clean[image_col] = df_clean[image_col].apply(
            lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
        )
        
        img_df = pd.DataFrame(df_clean[image_col].tolist(), index=df_clean.index)
        img_df.columns = [f'{image_col}_{i}' for i in range(img_df.shape[1])]
        df_clean = pd.concat([df_clean.drop(columns=[image_col]), img_df], axis=1)
    else:
        # Ya la columna de los embeddings originales no es necesaria
        df_clean = df_clean.drop(columns=[image_col], errors='ignore')

    obj_cols = df_clean.select_dtypes(include=['object', 'str']).columns
    for col in obj_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Solo nos quedamos con columnas numéricas y rellenamos nulos
    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.fillna(0)

    df_clean['recomendaciones_totales'] = target_col

    return df_clean

def _xgb_variable_selection(df):
    # Silenciar específicamente los avisos para que la salida sea limpia
    warnings.filterwarnings("ignore")
    optuna.logging.set_verbosity(optuna.logging.WARNING)

    def objective_xgb(trial, X_t, y_t, image_col, use_images):
        '''
        Función objetivo a optimizar por Optuna para XGBoost
        '''
        params = {
            'n_estimators': trial.suggest_int('n_estimators', 50, 300),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'subsample': trial.suggest_float('subsample', 0.6, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
            'random_state': 42,
            'n_jobs': -1
        }
        
        model = xgb.XGBRegressor(**params)
        
        steps = []
        
        img_cols = [c for c in X_t.columns if c.startswith(f'{image_col}_')] if use_images else []
        tabular_cols = [c for c in X_t.columns if c not in img_cols]
        
        transformers_list = [
            ('tabular', 'passthrough', tabular_cols)
        ]
        
        if use_images:
            dim_reduction = trial.suggest_categorical('dim_reduction', ['pca', 'umap'])
            
            if dim_reduction == 'pca':
                reducer = PCA(n_components=10, random_state=seed)
            else:
                n_neighbors = trial.suggest_int('umap_n_neighbors', 5, 50)
                min_dist = trial.suggest_float('umap_min_dist', 0.0, 0.5)
                reducer = UMAP(n_components=10, n_neighbors=n_neighbors, min_dist=min_dist, random_state=seed)
                
            transformers_list.append(('reducer', reducer, img_cols))
            
        preprocessor = ColumnTransformer(transformers=transformers_list, remainder='drop')
        steps.append(('prep', preprocessor))
        steps.append(('xgb', model))
        
        pipeline = Pipeline(steps)
        
        # Transformación de la variable respuesta
        final_model = TransformedTargetRegressor(
            regressor=pipeline,
            func=np.log1p,
            inverse_func=np.expm1
        )
        
        cv = KFold(n_splits=5, shuffle=True, random_state=seed)
        scores = cross_validate(final_model, X_t, y_t, cv=cv, scoring='neg_mean_absolute_error', return_train_score=True,
                                n_jobs=-1)
        
        trial.set_user_attr("train_mae", -scores['train_score'].mean())
        
        return -scores['test_score'].mean()

    combinations = [['v_clip', True]]

    results = []
    top_tabular_variables = []

    for c in combinations:
        print(f"\n{'='*50}")
        print(f"Evaluando combinación: {c}")
        
        df_prepared = _preprocess(df, image_col=c[0], use_images=c[1])

        X = df_prepared.drop(columns=['recomendaciones_totales'])
        y = df_prepared['recomendaciones_totales']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed)

        study = optuna.create_study(direction='minimize')
        study.optimize(lambda trial: objective_xgb(trial, X_train, y_train, c[0], c[1]), n_trials=35)

        print(f"Mejor MAE Validación: {study.best_value:.4f} | MAE Train: {study.best_trial.user_attrs['train_mae']:.4f}")
        
        best_params = study.best_params
        
        if c[1]:
            tecnica_ganadora = best_params.get('dim_reduction')
            print(f"Técnica de reducción de imágenes: {tecnica_ganadora.upper()}")
            
            if tecnica_ganadora == 'umap':
                print(f"n_neighbors óptimo para UMAP: {best_params.get('umap_n_neighbors')}")
                print(f"min_dist óptimo para UMAP: {best_params.get('umap_min_dist')}")

        xgb_params = {k: v for k, v in best_params.items() if k not in ['dim_reduction', 'umap_n_neighbors', 'umap_min_dist']}
        best_xgb = xgb.XGBRegressor(**xgb_params, random_state=seed, n_jobs=-1)
        
        cols_sesgadas = [col for col in ['price_overview', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer'] if col in X_train.columns]
        img_cols = [col for col in X_train.columns if col.startswith(f"{c[0]}_")] if c[1] else []
        cols_binarias = [col for col in X_train.columns if set(X_train[col].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
        cols_normales = [col for col in X_train.columns if col not in cols_sesgadas + img_cols + cols_binarias]
        
        final_transformers = [
            ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
            ('normales', StandardScaler(), cols_normales),
            ('binarias', 'passthrough', cols_binarias)
        ]
        
        if c[1]:
            dim_reduction = best_params.get('dim_reduction', 'pca')
            if dim_reduction == 'pca':
                final_reducer = PCA(n_components=10, random_state=seed)
            else:
                final_reducer = UMAP(n_components=10, n_neighbors=best_params['umap_n_neighbors'], min_dist=best_params['umap_min_dist'], random_state=seed)
            final_transformers.append(('reducer', final_reducer, img_cols))
            
        final_preprocessor = ColumnTransformer(transformers=final_transformers, remainder='drop')
        final_pipeline = Pipeline([('prep', final_preprocessor), ('xgb', best_xgb)])
        final_model = TransformedTargetRegressor(regressor=final_pipeline, func=np.log1p, inverse_func=np.expm1)
        
        final_model.fit(X_train, y_train)
        final_preds = final_model.predict(X_test)
        
        metricas = get_metrics(y_test, final_preds)
        
        results.append({
            'image_col': c[0], 
            'use_images': c[1], 
            'val_mae': study.best_value,
            'train_mae': study.best_trial.user_attrs['train_mae'], 
            'test_mae': metricas['mae'],
            'test_rmse': metricas['rmse'],
            'test_r2': metricas['r2']
        })

        modelo_entrenado = final_model.regressor_['xgb']
        # Obtenemos los pesos de cada variable
        pesos = modelo_entrenado.feature_importances_
        
        # Creamos nuestra propia lista de nombres en el mismo orden
        # en el que metimos las variables en el ColumnTransformer
        mis_nombres = cols_sesgadas + cols_normales + cols_binarias
        
        # Si usamos PCA o UMAP, añadimos 10 nombres extra
        if c[1] == True:
            mis_nombres = mis_nombres + [f"img_reducida_{i}" for i in range(10)]

        df_importancias = pd.DataFrame({
            'Variable': mis_nombres,
            'Importancia': pesos
        })
        
        print("\nTOP 10 Variables más importantes")
        print(df_importancias.sort_values(by='Importancia', ascending=False).head(10))
        
        top_tabular_variables = df_importancias[~df_importancias['Variable'].str.startswith('img_reducida')].sort_values(by='Importancia', ascending=False).head(20)['Variable'].tolist()

    # Imprimimos el resumen de resultados final
    df_results = pd.DataFrame(results).sort_values('test_mae', ascending=True)
    print("\nRESUMEN FINAL DE RESULTADOS:")
    print(df_results)
    
    return top_tabular_variables

def _train_knn(top_tabular_variables, df):
    df_prepared = _preprocess(df, use_images=True)
    X = df_prepared.drop(columns=['recomendaciones_totales'])
    y = df_prepared['recomendaciones_totales']

    bins_strat = [-1, 10, 100, 1000, 10000, float('inf')]
    y_binned = pd.cut(y, bins=bins_strat, labels=False)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2,
        random_state=seed,
        stratify=y_binned
    )

    def rmsle_scorer(y_true, y_pred):
        """RMSLE clipeando negativos por si el modelo devuelve algo negativo."""
        y_pred_safe = np.clip(y_pred, 0, None)
        return np.sqrt(mean_squared_log_error(y_true, y_pred_safe))

    def objective(trial, X_t, y_t):
        img_cols = [c for c in X_t.columns if c.startswith('v_clip_')]
        tabular_cols = [c for c in top_tabular_variables if c in X_t.columns]

        variables_elegidas = [col for col in tabular_cols if trial.suggest_categorical(f'usar_{col}', [True, False])]
        if len(variables_elegidas) == 0:
            return float('inf')

        columnas_finales = variables_elegidas + img_cols
        X_filtrada = X_t[columnas_finales]

        n_neighbors = trial.suggest_int('n_neighbors', 3, 50)
        weights = trial.suggest_categorical('weights', ['uniform', 'distance'])
        p = trial.suggest_int('p', 1, 2)

        todas_sesgadas = ['price_overview', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']
        cols_sesgadas = [c for c in variables_elegidas if c in todas_sesgadas]
        cols_binarias = [c for c in variables_elegidas if set(X_t[c].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
        cols_normales = [c for c in variables_elegidas if c not in cols_sesgadas + cols_binarias]

        transformers_list = [
            ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
            ('normales', StandardScaler(), cols_normales),
            ('binarias', 'passthrough', cols_binarias)
        ]

        if len(img_cols) > 0:
            dim_reduction = trial.suggest_categorical('dim_reduction', ['pca', 'umap'])
            if dim_reduction == 'pca':
                reducer = Pipeline([
                    ('pca', PCA(n_components=10, random_state=seed)),
                    ('scaler', StandardScaler())
                ])
            else:
                reducer = Pipeline([
                    ('umap', UMAP(
                        n_components=10,
                        n_neighbors=trial.suggest_int('umap_n_neighbors', 5, 50),
                        min_dist=trial.suggest_float('umap_min_dist', 0.0, 0.5),
                        random_state=seed
                    )),
                    ('scaler', StandardScaler())
                ])
            transformers_list.append(('reducer', reducer, img_cols))

        preprocessor = ColumnTransformer(transformers=transformers_list, remainder='drop')
        pipeline = Pipeline([
            ('prep', preprocessor),
            ('knn', KNeighborsRegressor(n_neighbors=n_neighbors, weights=weights, p=p, n_jobs=-1))
        ])
        final_model = TransformedTargetRegressor(regressor=pipeline, func=np.log1p, inverse_func=np.expm1)

        cv = KFold(n_splits=5, shuffle=True, random_state=seed)

        scores = cross_validate(
            final_model, X_filtrada, y_t,
            cv=cv,
            scoring='neg_mean_squared_log_error',
            n_jobs=-1
        )
        # Optuna minimiza, devolvemos RMSLE (positivo)
        return np.sqrt(-scores['test_score'].mean())

    print("Iniciando optimización de 300 trials ...")
    study = optuna.create_study(direction='minimize')
    study.optimize(lambda trial: objective(trial, X_train, y_train), n_trials=300)

    mejores_parametros = study.best_params
    img_cols = [c for c in X_train.columns if c.startswith('v_clip_')]
    variables_ganadoras = [col for col in top_tabular_variables if mejores_parametros.get(f'usar_{col}') == True]

    X_train_final = X_train[variables_ganadoras + img_cols]
    X_test_final  = X_test[variables_ganadoras + img_cols]

    todas_sesgadas = ['price_overview', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']
    cols_sesgadas = [c for c in variables_ganadoras if c in todas_sesgadas]
    cols_binarias = [c for c in variables_ganadoras if set(X_train[c].dropna().unique()).issubset({0, 1, 0.0, 1.0})]
    cols_normales = [c for c in variables_ganadoras if c not in cols_sesgadas + cols_binarias]

    final_transformers = [
        ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
        ('normales', StandardScaler(), cols_normales),
        ('binarias', 'passthrough', cols_binarias)
    ]

    if len(img_cols) > 0:
        dim_reduction = mejores_parametros.get('dim_reduction', 'pca')
        if dim_reduction == 'pca':
            final_reducer = Pipeline([
                ('pca', PCA(n_components=10, random_state=seed)),
                ('scaler', StandardScaler())
            ])
        else:
            final_reducer = Pipeline([
                ('umap', UMAP(
                    n_components=10,
                    n_neighbors=mejores_parametros['umap_n_neighbors'],
                    min_dist=mejores_parametros['umap_min_dist'],
                    random_state=seed
                )),
                ('scaler', StandardScaler())
            ])
        final_transformers.append(('reducer', final_reducer, img_cols))

    final_pipeline = Pipeline([
        ('prep', ColumnTransformer(transformers=final_transformers, remainder='drop')),
        ('knn', KNeighborsRegressor(
            n_neighbors=mejores_parametros['n_neighbors'],
            weights=mejores_parametros['weights'],
            p=mejores_parametros['p'],
            n_jobs=-1
        ))
    ])

    modelo_definitivo = TransformedTargetRegressor(
        regressor=final_pipeline,
        func=np.log1p,
        inverse_func=np.expm1
    )

    modelo_definitivo.fit(X_train_final, y_train)
    predicciones = modelo_definitivo.predict(X_test_final)

    print("\nMÉTRICAS GENERALES EN TEST")
    get_metrics(y_test, predicciones)

    rmsle_test = rmsle_scorer(y_test, predicciones)
    print(f"RMSLE (métrica de optimización): {rmsle_test:.4f}")

    def check_performance_by_bins(y_real, y_pred):
        results = pd.DataFrame({'Real': y_real, 'Pred': y_pred})
        bins   = [-1, 10, 100, 1000, 10000, float('inf')]
        labels = ['0-10', '10-100', '100-1k', '1k-10k', '>10k']
        results['Rango'] = pd.cut(results['Real'], bins=bins, labels=labels)

        performance = results.groupby('Rango', observed=True).apply(
            lambda x: mean_absolute_error(x['Real'], x['Pred']) if len(x) > 0 else 0
        )

        print("\nMAE POR RANGO DE POPULARIDAD")
        print(performance)

        plt.figure(figsize=(10, 5))
        plt.scatter(y_real, y_pred, alpha=0.4, color='blue')
        plt.plot([y_real.min(), y_real.max()], [y_real.min(), y_real.max()], 'r--')
        plt.xscale('log')
        plt.yscale('log')
        plt.title('Dispersión Real vs Predicho (Escala Logarítmica)')
        plt.xlabel('Recomendaciones Reales')
        plt.ylabel('Predicciones')
        plt.grid(True, which="both", ls="-", alpha=0.2)
        plt.show()

    check_performance_by_bins(y_test, predicciones)

    print("\nMEJORES PARÁMETROS")
    print(mejores_parametros)

def main(minio = {"minio_write": False, "minio_read": False}):
    load_env_file()

    df = read_file(popularity, minio)
    top_tabular_variables = _xgb_variable_selection(df)
    _train_knn(top_tabular_variables, df)

if __name__ == "__main__":
    main()