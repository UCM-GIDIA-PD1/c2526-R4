""""
Modelo de XGBoost para la clasificación multiclase de rango de precio de un juego a partir de sus características.

En este script se realizarán los siguientes modelos:
    - Modelo sin información de las imágenes
    - Modelo con embeddings de imagenes (Procesado con un PCA)

Dependencias:
    - precios.parquet
"""


from .utils_modelo_precios.preprocesamiento import read_prices, train_val_test_split, class_weights, get_metrics, normalize_train_test, pca_train_test
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from sklearn.metrics import f1_score
import optuna
import wandb
import pandas as pd

def model_noimg(df):    
    # Hacemos encoding de la variable objetivo ya que no acepta str XGBoost
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    sample_weights = class_weights(y_train)

    def objective(trial):
        param = {
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
        model = xgb.XGBClassifier(**param)
        model.fit(
            X_train, y_train,
            sample_weight=sample_weights,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        preds = model.predict(X_val)
        score = f1_score(y_val, preds, average='weighted')        
        return score

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name='XGBoost-Base NoImg',
        job_type='xgboost'
    )

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)
    
    print(f"Mejor F1-Score: {study.best_value}")
    print(f"Mejores parámetros: {study.best_params}")
    best_params = study.best_params

    final_model = xgb.XGBClassifier(
        **best_params,
        objective='multi:softprob',
        num_class=len(le.classes_),
        random_state=42
    )
    
    final_model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    metrics_dict = get_metrics(y_test, y_pred)
    
    run.log(metrics_dict)
    run.finish()

def model_img(df):
    emb = df['v_clip'].apply(pd.Series)
    df = pd.concat([df.drop(columns=['v_clip']), emb], axis=1)
    
    columnas_categoricas = ['Action','Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation',
       'Strategy', 'Co-op', 'Custom Volume Controls', 'Family Sharing',
       'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP',
       'Partial Controller Support', 'Playable without Timed Input', 'PvP',
       'Remote Play Together', 'Shared/Split Screen', 'Single-player',
       'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']
    
    columnas_numericas = df.columns.difference(columnas_categoricas).tolist()

    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    X_train, X_val, X_test = normalize_train_test(X_train, X_val, X_test, columnas_numericas)
    X_train, X_val, X_test = pca_train_test(X_train, X_val, X_test, n_comp=50)
    sample_weights = class_weights(y_train)

    def objective(trial):
        param = {
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
        model = xgb.XGBClassifier(**param)
        model.fit(
            X_train, y_train,
            sample_weight=sample_weights,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        preds = model.predict(X_val)
        score = f1_score(y_val, preds, average='weighted')        
        return score

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name='XGBoost-Base Img PCA 50',
        job_type='xgboost'
    )

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=50)
    
    print(f"Mejor F1-Score: {study.best_value}")
    print(f"Mejores parámetros: {study.best_params}")
    best_params = study.best_params

    final_model = xgb.XGBClassifier(
        **best_params,
        objective='multi:softprob',
        num_class=len(le.classes_),
        random_state=42
    )
    
    final_model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    metrics_dict = get_metrics(y_test, y_pred)
    
    run.log(metrics_dict)
    run.finish()

def xgboost_base():
    df = read_prices()

    df_noimg = df.drop(columns=['brillo', 'v_clip'])
    model_noimg(df_noimg)

    df_img = df.copy()
    model_img(df_img)

if __name__ == '__main__':
    xgboost_base()