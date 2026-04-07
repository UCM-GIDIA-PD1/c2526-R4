from utils.utils import read_prices, train_val_test_split, get_metrics
from utils.utils import normalize_train_test, cluster_embedings, umap_embeddings
from mlp_precios import _preprocess_test
from src.utils.config import precios_xgboostumap_file, precios_mlp_file, precios_knncompleteclusters_file
from src.utils.config import precios_catboostClustered_file, precios_logistic_regression_file
from src.utils.files import read_file

from sklearn.preprocessing import LabelEncoder
import os
import joblib

import wandb

import pandas as pd
from numpy import vstack

def catboostModel(df, table, model_path= 'models/precios/catboostClustered.pkl'):
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

    if os.path.exists(model_path):
        model = joblib.load(model_path)

        y_pred = model.predict(X_test)
        metrics_dict = get_metrics(y_test, y_pred)

        table.add_data(
            'CatBoost Clustered',
            metrics_dict['accuracy'],
            metrics_dict['f1-score'],
            metrics_dict['precision'],
            metrics_dict['recall']
        )
    else:
        raise FileNotFoundError

def xgboostUmap(df, table, model_path= 'models/precios/xgboostumap.pkl'):
    # Hacemos encoding de la variable objetivo ya que no acepta str XGBoost
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = umap_embeddings(X_train, X_val, X_test, emb_col='v_clip')

    if os.path.exists(model_path):
        model = joblib.load(model_path)

        y_pred = model.predict(X_test)
        metrics_dict = get_metrics(y_test, y_pred)

        table.add_data(
            'XGBoost Umap',
            metrics_dict['accuracy'],
            metrics_dict['f1-score'],
            metrics_dict['precision'],
            metrics_dict['recall']
        )
    else:
         raise FileNotFoundError

def knnModel(df, table, model_path= 'models/precios/knncompleteclusters.pkl'):
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

    le = LabelEncoder()
    y_train = le.fit_transform(y_train)
    y_val   = le.transform(y_val)
    y_test  = le.transform(y_test)

    columnas_categoricas = ['Action','Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation',
    'Strategy', 'Co-op', 'Custom Volume Controls', 'Family Sharing',
    'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP',
    'Partial Controller Support', 'Playable without Timed Input', 'PvP',
    'Remote Play Together', 'Shared/Split Screen', 'Single-player',
    'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']

    columnas_numericas = X_train.columns.difference(columnas_categoricas).tolist()
    X_train, X_val, X_test = normalize_train_test(X_train, X_val, X_test, columnas_numericas)

    if os.path.exists(model_path):
        model = joblib.load(model_path)

        y_pred = model.predict(X_test)
        metrics_dict = get_metrics(y_test, y_pred)

        table.add_data(
            'K-NN Complete Clusters',
            metrics_dict['accuracy'],
            metrics_dict['f1-score'],
            metrics_dict['precision'],
            metrics_dict['recall']
        )
    else:
         raise FileNotFoundError

def mlpModel(df, table):
    mlp_data = read_file(precios_mlp_file, {"minio_write": False, "minio_read": False}) # CAMBIAR MINIO
    if mlp_data:
        mlp_model = mlp_data["model"]
        transformers_dict = mlp_data["transformers"]
        
        y_all = pd.DataFrame(df['price_range'])
        X_all = df.drop(columns=['price_range'])

        X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X_all, y_all)
        
        X_test_mlp, Y_test_mlp = _preprocess_test(X_test, y_test, transformers_dict)
        
        clip_matrix_test = vstack(X_test_mlp['v_clip'].values)
        umap = transformers_dict['umap']
        clip_reduced_test = umap.transform(clip_matrix_test)
        
        for i in range(19):
            X_test_mlp[f'clip_umap_{i}'] = clip_reduced_test[:, i]
            
        X_test_mlp = X_test_mlp.drop(columns=['v_clip'])
        
        y_pred_mlp = mlp_model.predict(X_test_mlp)

        metricas = get_metrics(Y_test_mlp.values.flatten(), y_pred_mlp)
        
        table.add_data(
            'MLP GridSearchCV UMAP',
            metricas['accuracy'],
            metricas['f1-score'],
            metricas['precision'],
            metricas['recall']
        )

def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios",
        name="model-evaluation",
        job_type="evaluation"
    )

    df = read_prices()
    table = wandb.Table(columns=["Model", "accuracy", "f1-score", "precision", 'recall'])

    print('Subiendo baseline')
    table.add_data(
        'Baseline Mode',
        0.49749916638879627,
        0.3305583416842948,
        0.2475054205575472,
        0.49749916638879627
    )
    print('Subiendo modelo de Catboost')
    catboostModel(df.copy(), table)
    print('Subiendo modelo XGBoost UMAP')
    xgboostUmap(df.copy(), table)
    print('Subiendo modelo KNN Complete Clusters')
    knnModel(df.copy(), table)
    print('Subiendo modelo MLP UMAP')
    mlpModel(df.copy(), table)
                
    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")
    run.finish()

if __name__ == "__main__":
    evaluate_models()