from utils.utils import read_prices, train_val_test_split, class_weights, get_metrics
from utils.utils import normalize_train_test, pca_train_test, cluster_embedings, umap_embeddings

from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import f1_score
from sklearn.model_selection import RandomizedSearchCV
from sklearn.preprocessing import LabelEncoder
from catboost import CatBoostClassifier
import xgboost as xgb
import optuna
import os
import joblib
import statsmodels.api as sm
from sklearn.neighbors import KNeighborsClassifier

import wandb

import pandas as pd

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


def evaluate_models():
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios",
        name="model-evaluation",
        job_type="evaluation"
    )

    df = read_prices()
    table = wandb.Table(columns=["Model", "accuracy", "f1-score", "precision", 'recall'])

    print('Subiendo modelo de Catboost')
    catboostModel(df.copy(), table)
    print('Subiendo modelo XGBoost UMap')
    xgboostUmap(df.copy(), table)
    print('Subiendo modelo KNN Complete Clusters')
    knnModel(df.copy(), table)
                
                
    wandb.log({"comparative_table": table})
    print("Evaluación completada. Resultados en W&B.")
    run.finish()

if __name__ == "__main__":
    evaluate_models()