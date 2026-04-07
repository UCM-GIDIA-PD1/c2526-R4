"""
Dado precios.parquet crea un modelo de Regresión Logística para predecir
en qué rango de precio se sitúa un juego según sus características.
Utiliza hiperparámetros previamente calculados en el notebook.
"""

import pandas as pd
import numpy as np
import wandb

from src.utils.config import prices
from src.utils.files import read_file
from utils.utils import get_metrics, save_model

from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, PowerTransformer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

import os
from src.utils.config import seed

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

def _create_lr_model(X_train, X_test, y_train, y_test, best_params):
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
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )

    run.log(metricas)

    model_name = "logistic_regression_precios.pkl"
    save_model(model_name, final_pipeline)

    run.finish()


def main():
    print('Leyendo datos...')
    df = read_file(prices)

    print('Preprocesando los datos...')
    X, y = _preprocess(df)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)

    best_params = {
        'C': 0.041948246911196446,
        'solver': 'lbfgs',
        'l1_ratio': 0.0
    }

    print('Creando modelo...')
    _create_lr_model(X_train, X_test, y_train, y_test, best_params)

if __name__ == "__main__":
    main()
