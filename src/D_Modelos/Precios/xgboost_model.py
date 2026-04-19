""""
Modelo de XGBoost para la clasificación multiclase de rango de precio de un juego a partir de sus características.

En este script se realizarán los siguientes modelos:
    - Modelo con embeddings de imagenes (Procesado con un UMAP)

Dependencias:
    - precios.parquet
"""

from src.utils.config import precios_xgboostumap_file, precios_catboostClustered_file, models_precios_path
from src.utils.files import write_to_file
from src.D_Modelos.Precios.utils.utils import read_prices, class_weights, get_metrics,get_train_test

from sklearn.preprocessing import OrdinalEncoder,FunctionTransformer
from sklearn.model_selection import  cross_validate
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

import xgboost as xgb
from umap import UMAP
import optuna
import wandb
import os
import pandas as pd
import numpy as np

def unpack_embeddings(X):
    """Dada una lista de vectores o una columna de dataFrame realiza un vstack. Esta función es usada
    para poder convertirla en objeto usan FunctionTransformer

    Args:
        X (pd.DataFrame | list): Columna de dataframe al que transformar, debe ser una lista los valores

    Returns:
        np.array: Array de valores resultante de vstack
    """
    if isinstance(X, pd.DataFrame):
        return np.vstack(X.iloc[:, 0].values)
    return np.vstack(X[:, 0])

def transform_xgboost(df):
    return df.copy()

def predict_xgboost(model_data, test_df, train_df):
    X_test = test_df.drop(columns=['price_range'])
    y_pred = model_data.predict(X_test)
    
    le = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    le.fit([[c] for c in le.categories[0]])
    y_pred_labels = le.inverse_transform(y_pred.reshape(-1, 1)).flatten()
    return y_pred_labels

def _optimize_params_xgboost(X_train, y_train):
    """Dado el conjunto de valores de entrenamiento, realiza la optimización de hiperparámetros del XGBoost
    usando Optuna,

    Args:
        X_train (pd.DataFrame): Conjunto de entrenamiento (Entrada)
        y_train (_type_): Conjunto de entrenamiento (Target)

    Returns: 
        best_params (dict): Diccionario con los mejores parámetros del study de optuna
    """
    def objective(trial):
        params = {
            'verbosity': 0,
            'objective': 'multi:softprob',
            'num_class': len(set(y_train)),
            'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
            'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3, log=True),
            'max_depth': trial.suggest_int('max_depth', 3, 10),
            'subsample': trial.suggest_float('subsample', 0.5, 1.0),
            'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
            'gamma': trial.suggest_float('gamma', 1e-8, 1.0, log=True),
            'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
            'random_state': 42,
            'device': 'cuda' if False else 'cpu',
        }
        model = xgb.XGBClassifier(**params)
        score = cross_validate(model, X_train, y_train, cv=5, scoring='f1_weighted', n_jobs=-1)
        return score['test_score'].mean()
    
    print("Iniciando optimización de hiperparámetros")
    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)
    
    print(f"Mejor F1-Score: {study.best_value}")
    print(f"Mejores parámetros: {study.best_params}")
    best_params = study.best_params
    
    return best_params

def model_umap(df, modelName='XGBoost Umap'):
    """Modelo de XGBoost realizando un UMAP sobre la columna de embeddings de imagenes. Almacena el pipeline del modelo.

    Args:
        df (pd.DataFrame): Dataframe de entrada con los datos del modelo
        modelName (str, optional): Nombre del modelo para subir a WnB. Defaults to None..
    """
    print(f'Creando modelo {modelName}...')
    
    le = OrdinalEncoder(categories=[['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40']])
    df['price_range'] = le.fit_transform(df[['price_range']])

    X_train, X_test, y_train, y_test = get_train_test(df)

    embedding_pipeline = Pipeline([
        ('stacker', FunctionTransformer(unpack_embeddings)),
        ('umap', UMAP(n_components=16, random_state=42))
    ])

    preprocessor = ColumnTransformer([
        ('clip_umap', embedding_pipeline, ['v_clip']),
    ], remainder='passthrough')

    X_train_transformed = preprocessor.fit_transform(X_train)
    X_test_transformed = preprocessor.transform(X_test)

    run = wandb.init(entity="pd1-c2526-team4",
                project="Precios",
                name=modelName,
                job_type='xgboost'
            )
    
    best_params = _optimize_params_xgboost(X_train_transformed, y_train)
    
    clf = xgb.XGBClassifier(
        **best_params, 
        objective='multi:softprob', 
        num_class=len(le.categories_[0]), 
        random_state=42
    )

    final_pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('classifier', clf)
    ])

    sample_weights = class_weights(y_train)
    final_pipeline.fit(X_train, y_train, classifier__sample_weight=sample_weights)
    y_pred = final_pipeline.predict(X_test)

    y_test_labels = le.inverse_transform(y_test.values.reshape(-1, 1)).flatten()
    y_pred_labels = le.inverse_transform(y_pred.reshape(-1, 1)).flatten()

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=le.categories_[0],
        img_path='models/precios/graficos/confusionMatrix/knn_reduced.png',
        download_images=True
    )

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(final_pipeline, precios_xgboostumap_file, {"minio_write": False, "minio_read": False})
    
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def xgboost_base(minio):
    df = read_prices(minio)
    df_umap = df.copy()
    model_umap(df_umap, modelName='XGBoost Umap')

def main(minio = {"minio_write": False, "minio_read": False}):
    xgboost_base(minio)

if __name__ == "__main__":
    main()
