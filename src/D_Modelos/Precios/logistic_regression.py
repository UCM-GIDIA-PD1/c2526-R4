"""
Dado precios.parquet crea un modelo de Regresión Logística para predecir
en qué rango de precio se sitúa un juego según sus características.
Utiliza hiperparámetros previamente calculados en el notebook.
"""

import pandas as pd
import numpy as np
import os
import wandb
import optuna
import warnings

from src.utils.config import prices, load_env_file, seed
from src.utils.files import read_file, write_to_file
from src.utils.config import precios_logistic_regression_file, models_precios_path
from utils.utils import get_metrics

from sklearn.model_selection import train_test_split, StratifiedKFold, cross_validate, GridSearchCV
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.exceptions import ConvergenceWarning
from umap import UMAP

orden_precios = {
    '[0.01,4.99]': 0,
    '[5.00,9.99]': 1,
    '[10.00,14.99]': 2,
    '[15.00,19.99]': 3,
    '[20.00,29.99]': 4,
    '[30.00,39.99]': 5,
    '>40': 6
}
orden_inverso = {v: k for k, v in orden_precios.items()}
nombres_clases_ordenados = list(orden_precios.keys())

def transform_logistic_regression(df):
    return df.copy()

def predict_logistic_regression(model_data, test_df, train_df):
    df_prepared = _preprocess(test_df.copy())
    X_test = df_prepared.drop(columns=['price_range'])
    
    y_pred = model_data.predict(X_test)
    y_pred_labels = pd.Series(y_pred, index=X_test.index).map(orden_inverso).values
    return y_pred_labels

def _preprocess(df):
    """
    Función para limpiar y estructurar los datos para la Regresión Logística.
    No escala ni aplica PCA aquí para evitar el Data Leakage.
    """
    df_clean = df.copy()

    target_col = df_clean['price_range']
    y = target_col.map(orden_precios)

    erase_columns = ['id', 'name', 'price_overview', 'v_resnet', 'v_convnext', 'price_range']
    df_clean = df_clean.drop(columns=erase_columns, errors='ignore')

    # Expandimos los vectores de la imagen en múltiples columnas numéricas
    zero_vector = np.zeros(512)
    df_clean['v_clip'] = df_clean['v_clip'].apply(
        lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
    )

    img_df = pd.DataFrame(df_clean['v_clip'].tolist(), index=df_clean.index)
    img_df.columns = [f'v_clip_{i}' for i in range(img_df.shape[1])]
    df_clean = pd.concat([df_clean.drop(columns=['v_clip']), img_df], axis=1)

    obj_cols = df_clean.select_dtypes(include=['object', 'str']).columns
    for col in obj_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    X = df_clean.select_dtypes(include=[np.number]).fillna(0)

    return X, y

def _preprocess_search(df, image_col='v_clip', use_images=True):

    images_cols = ['v_clip', 'v_convnext', 'v_resnet']

    assert image_col in images_cols, "Seleccione una columna de imágenes válida"

    df_clean = df.copy()
    
    # Seleccionamos las variables de entrada útiles
    target_col = df_clean['price_range']
    erase_columns = ['id', 'name', 'price_overview']
    images_cols.remove(image_col)
    erase_columns.extend(images_cols)
    df_clean = df_clean.drop(columns=erase_columns, errors='ignore')

    if use_images:
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

    df_clean['price_range'] = target_col

    return df_clean

def _create_lr_model(X_train, X_test, y_train, y_test, best_params, minio):
    """
    Crea el pipeline del modelo, evalúa y sube las métricas a Weights & Biases.
    """
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios",
        name='logistic-regression',
        job_type='logistic-regression'
    )

    params = best_params.copy()
    solver = params.get('solver', 'lbfgs')
    l1_ratio = params.get('l1_ratio', 0.0)
    C = params.get('C', 1.0)

    best_model = LogisticRegression(
        C=C, solver=solver, l1_ratio=l1_ratio,
        max_iter=1500, random_state=seed, class_weight='balanced'
    )

    cols_sesgadas = ['num_languages', 'total_games_by_publisher', 'total_games_by_developer']
    cols_normales = ['description_len', 'release_year', 'brillo']
    img_cols = [col for col in X_train.columns if col.startswith("v_clip_")]
    cols_binarias = [col for col in X_train.columns if col not in cols_sesgadas + cols_normales + img_cols]

    final_transformers = [
        ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
        ('normales', StandardScaler(), cols_normales),
        ('binarias', 'passthrough', cols_binarias)
    ]

    final_reducer = PCA(n_components=10, random_state=seed)

    final_transformers.append(('img_reducer', final_reducer, img_cols))
    final_preprocessor = ColumnTransformer(transformers=final_transformers, remainder='passthrough')

    final_pipeline = Pipeline([
        ('prep', final_preprocessor),
        ('clf', best_model)
    ])

    final_pipeline.fit(X_train, y_train)
    y_pred = final_pipeline.predict(X_test)

    y_test_labels = y_test.map(orden_inverso)
    y_pred_labels = pd.Series(y_pred, index=y_test.index).map(orden_inverso)

    cm_path = 'models/precios/graficos/confusionMatrix/logisticregression.png'

    metricas = get_metrics(
        y_test_labels, y_pred_labels,
        classes=nombres_clases_ordenados,
        img_path=cm_path, download_images=True
    )

    run.log(metricas)

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(final_pipeline, precios_logistic_regression_file, minio)
    print(f"Modelo guardado en {precios_logistic_regression_file}")

    run.finish()

def training_optuna(df):
    # Silenciar específicamente los avisos de convergencia de Scikit-Learn
    warnings.filterwarnings("ignore", category=ConvergenceWarning)

    def objective(trial, X_t, y_t, image_col, use_images):
        C = trial.suggest_float('C', 1e-4, 10.0, log=True)
        solver = trial.suggest_categorical('solver', ['lbfgs', 'saga', 'newton-cg'])
        
        if solver == 'saga':
            l1_ratio = trial.suggest_float('l1_ratio', 0.0, 1.0)
        else:
            l1_ratio = 0.0
            
        model = LogisticRegression(C=C, solver=solver, l1_ratio=l1_ratio, max_iter=1500, random_state=seed, class_weight='balanced')
        steps = []
        
        cols_sesgadas = ['num_languages', 'total_games_by_publisher', 'total_games_by_developer']
        cols_normales = ['description_len', 'release_year', 'brillo']
        img_cols = [c for c in X_t.columns if c.startswith(f'{image_col}_')] if use_images else []
        cols_binarias = [c for c in X_t.columns if c not in cols_sesgadas + cols_normales + img_cols]
        
        transformers_list = [
            ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
            ('normales', StandardScaler(), cols_normales),
            ('binarias', 'passthrough', cols_binarias)
        ]
        
        if use_images:
            dim_reduction = trial.suggest_categorical('dim_reduction', ['pca', 'umap'])
            
            if dim_reduction == 'pca':
                reducer = PCA(n_components=10, random_state=seed)
            else:
                n_neighbors = trial.suggest_int('umap_n_neighbors', 5, 50)
                min_dist = trial.suggest_float('umap_min_dist', 0.0, 0.5)
                reducer = UMAP(n_components=10, n_neighbors=n_neighbors, min_dist=min_dist)
                
            transformers_list.append(('reducer', reducer, img_cols))
            
        preprocessor = ColumnTransformer(transformers=transformers_list, remainder='passthrough')
        steps.append(('prep', preprocessor))
        steps.append(('clf', model))
        
        pipeline = Pipeline(steps)
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
        
        scores = cross_validate(pipeline, X_t, y_t, cv=cv, scoring='f1_weighted', return_train_score=True)
        trial.set_user_attr("train_f1", scores['train_score'].mean())
        
        return scores['test_score'].mean()

    optuna.logging.set_verbosity(optuna.logging.WARNING)

    combinations = [['v_clip', True], ['v_clip', False],
                    ['v_resnet', True], ['v_convnext', True]]

    results = []

    for c in combinations:
        print(f"\n{'='*50}")
        print(f"Evaluando combinación con Optuna: {c}")
        
        df_prepared = _preprocess_search(df, image_col=c[0], use_images=c[1])

        X = df_prepared.drop(columns=['price_range'])
        y_raw = df_prepared['price_range']
        y = y_raw.map(orden_precios)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)

        study = optuna.create_study(direction='maximize')
        study.optimize(lambda trial: objective(trial, X_train, y_train, c[0], c[1]), n_trials=50, n_jobs=-1)

        print(f"Mejor f1_weighted en Validación (CV): {study.best_value:.4f}")
        print(f"Mejores hiperparámetros: {study.best_params}")
        
        # Test validation of the best combinations
        best_params = dict(study.best_params)
        solver = best_params['solver']
        l1_ratio = best_params.get('l1_ratio', 0.0)

        best_model = LogisticRegression(C=best_params['C'], solver=solver, l1_ratio=l1_ratio, 
                                        max_iter=3000, random_state=seed, class_weight='balanced')
                                        
        final_steps = []
        cols_sesgadas = ['num_languages', 'total_games_by_publisher', 'total_games_by_developer']
        cols_normales = ['description_len', 'release_year', 'brillo']
        img_cols = [col for col in X_train.columns if col.startswith(f"{c[0]}_")] if c[1] else []
        cols_binarias = [col for col in X_train.columns if col not in cols_sesgadas + cols_normales + img_cols]
        
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
                final_reducer = UMAP(
                    n_components=10,
                    n_neighbors=best_params['umap_n_neighbors'],
                    min_dist=best_params['umap_min_dist']
                )
            final_transformers.append(('reducer', final_reducer, img_cols))
            
        final_preprocessor = ColumnTransformer(transformers=final_transformers, remainder='passthrough')
        final_steps.append(('prep', final_preprocessor))
        final_steps.append(('clf', best_model))
        
        final_pipeline = Pipeline(final_steps)
        final_pipeline.fit(X_train, y_train)
        final_preds = final_pipeline.predict(X_test)
        
        y_test_labels = y_test.map(orden_inverso)
        final_preds_labels = pd.Series(final_preds, index=y_test.index).map(orden_inverso)
        
        metricas_test = get_metrics(y_test_labels, final_preds_labels, classes=nombres_clases_ordenados)
        test_f1 = metricas_test['f1']
        
        results.append({
            'image_col':    c[0],
            'use_images':   c[1],
            'val_f1': study.best_value,
            'train_f1': study.best_trial.user_attrs['train_f1'],
            'test_f1':  test_f1,
            'best_params':  study.best_params
        })

    df_results = pd.DataFrame(results).sort_values('test_f1', ascending=False)
    print("\nRESUMEN FINAL DE MODELOS (OPTUNA):")
    print(df_results)


def training_gridsearchcv(df):
    warnings.filterwarnings('ignore')

    combinations = [['v_clip', True], ['v_clip', False],
                    ['v_resnet', True], ['v_convnext', True]]

    results_grid = []

    for c in combinations:
        print(f"\n{'='*60}")
        print(f"Evaluando combinación con GridSearchCV: {c}")
        
        df_prepared = _preprocess_search(df, image_col=c[0], use_images=c[1])

        X = df_prepared.drop(columns=['price_range'])
        y_raw = df_prepared['price_range']
        y = y_raw.map(orden_precios)
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)

        cols_sesgadas = ['num_languages', 'total_games_by_publisher', 'total_games_by_developer']
        cols_normales = ['description_len', 'release_year', 'brillo']
        img_cols = [col for col in X_train.columns if col.startswith(f"{c[0]}_")] if c[1] else []
        cols_binarias = [col for col in X_train.columns if col not in cols_sesgadas + cols_normales + img_cols]
        
        transformers_list = [
            ('sesgadas', PowerTransformer(method='yeo-johnson'), cols_sesgadas),
            ('normales', StandardScaler(), cols_normales),
            ('binarias', 'passthrough', cols_binarias)
        ]
        
        if c[1]:
            transformers_list.append(('img_reducer', PCA(n_components=10, random_state=seed), img_cols))
            
        preprocessor = ColumnTransformer(transformers=transformers_list)

        pipeline = Pipeline([
            ('prep', preprocessor),
            ('clf', LogisticRegression(max_iter=1500, random_state=seed, class_weight='balanced'))
        ])
        
        C_values = np.logspace(-4, 1, 3) 
        grid_params = []
        
        if c[1]:
            reducers_list = [
                PCA(n_components=10, random_state=seed),
                UMAP(n_components=10, n_neighbors=15, min_dist=0.1)
            ]
            grid_params.extend([
                {'prep__img_reducer': reducers_list, 'clf__solver': ['lbfgs', 'newton-cg'], 'clf__C': C_values, 'clf__l1_ratio': [0.0]},
                {'prep__img_reducer': reducers_list, 'clf__solver': ['saga'], 'clf__C': C_values, 'clf__l1_ratio': [0.0, 0.5, 1.0]}
            ])
        else:
            grid_params.extend([
                {'clf__solver': ['lbfgs', 'newton-cg'], 'clf__C': C_values, 'clf__l1_ratio': [0.0]},
                {'clf__solver': ['saga'], 'clf__C': C_values, 'clf__l1_ratio': [0.0, 0.5, 1.0]}
            ])

        cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=seed)
        grid_search = GridSearchCV(
            estimator=pipeline,
            param_grid=grid_params,
            scoring='f1_weighted',
            cv=cv,
            n_jobs=-1,
            verbose=1 
        )
        
        grid_search.fit(X_train, y_train)
        
        print(f"Mejor f1_weighted en Validación (CV): {grid_search.best_score_:.4f}")
        print(f"Mejores hiperparámetros: {grid_search.best_params_}")
        
        final_preds = grid_search.predict(X_test)
        y_test_labels = y_test.map(orden_inverso)
        final_preds_labels = pd.Series(final_preds, index=y_test.index).map(orden_inverso)
        
        metricas_test = get_metrics(y_test_labels, final_preds_labels, classes=nombres_clases_ordenados)
        
        results_grid.append({
            'image_col':    c[0],
            'use_images':   c[1],
            'val_f1': grid_search.best_score_,
            'test_f1':  metricas_test['f1'],
            'best_params':  grid_search.best_params_
        })

    print(f"\n{'='*60}\nRESUMEN FINAL DE MODELOS (GRIDSEARCH):")
    df_results_grid = pd.DataFrame(results_grid).sort_values('test_f1', ascending=False)
    print(df_results_grid)

def train_best_model(df, minio):
    """
    Función que entrena y guarda el mejor modelo identificado empíricamente, enviando
    los resultados a wandb.
    """
    X, y = _preprocess(df)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)

    best_params = {
        'C': 0.041948246911196446,
        'solver': 'lbfgs',
        'l1_ratio': 0.0
    }

    _create_lr_model(X_train, X_test, y_train, y_test, best_params, minio)

def main(minio = {"minio_write": False, "minio_read": False}):
    load_env_file()
    df = read_file(prices, minio)

    # PARA HACER LA BÚSQUEDA DE HIPERPARÁMETROS DESCOMENTAR
    # (hay que poner esto bien para que siempre los haga, pero por ahora solo he juntado los 2 fichero que había)
    # training_optuna(df)
    # training_gridsearchcv(df)

    train_best_model(df, minio)

if __name__ == "__main__":
    main()
