""""
Modelo de XGBoost para la clasificación multiclase de rango de precio de un juego a partir de sus características.

En este script se realizarán los siguientes modelos:
    - Modelo sin información de las imágenes
    - Modelo con embeddings de imagenes (Procesado con un PCA)

Dependencias:
    - precios.parquet
"""

from utils.utils import read_prices, train_val_test_split, class_weights, get_metrics
from utils.utils import normalize_train_test, pca_train_test, cluster_embedings, umap_embeddings, save_model
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
from sklearn.metrics import f1_score
import optuna
import wandb
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import f1_score
from sklearn.model_selection import RandomizedSearchCV
import joblib
import os
from imblearn.over_sampling import SMOTE
from src.utils.config import seed

def model_noimg(df, modelName='XGBoost-Base NoImg'):
    """
        Modelo completo de XGBoost sin infromación de las imágenes.

        Args:
            - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
            - modelName (String): Nombre del modelo a subir a wandb
        Returns:
            None
    """     

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
        name= modelName,
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
        random_state=seed
    )
    
    final_model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def model_img(df, modelName='XGBoost-Base Img PCA 50'):
    """
        Modelo completo de XGBoost con información de las imágenes (los vectores de los embeddings) y un PCA para reducir la dimensionalidad.

        Args:
            - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
            - modelName (String): Nombre del modelo a subir a wandb
        Returns:
            None
    """     
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])
    emb = df['v_clip'].apply(pd.Series)
    df = pd.concat([df.drop(columns=['v_clip']), emb], axis=1)
    
    columnas_categoricas = ['Action','Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation',
       'Strategy', 'Co-op', 'Custom Volume Controls', 'Family Sharing',
       'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP',
       'Partial Controller Support', 'Playable without Timed Input', 'PvP',
       'Remote Play Together', 'Shared/Split Screen', 'Single-player',
       'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']
    

    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X.columns = X.columns.astype(str)

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    columnas_numericas = X_train.columns.difference(columnas_categoricas).tolist()

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
        name= modelName,
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
        random_state=seed
    )

    final_model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def catModel(df, modelName='XGBoost Clustered'):
    """
    Modelo completo de CatBoosst.

    Args:
        - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
        - modelName (String): Nombre del modelo a subir a wandb
    Returns:
        None
    """     

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    
    train_weights = class_weights(y_train)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')
    
    cat_cols = [
               'Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation',
                   'Strategy', 'Co-op', 'Custom Volume Controls', 'Family Sharing',
                   'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP',
                   'Partial Controller Support', 'Playable without Timed Input', 'PvP',
                   'Remote Play Together', 'Shared/Split Screen', 'Single-player',
                   'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards',
                   'Steam Trading Cards', 'cluster'
    ]

    def objective(trial):
            params = {
                "iterations": trial.suggest_int("iterations", 300, 800),
                "depth": trial.suggest_int("depth", 4, 10),
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
                "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-3, 10, log=True),
                "border_count": trial.suggest_int("border_count", 32, 255),
                "loss_function": "MultiClass",
                "eval_metric": "TotalF1",
                "random_state": 42,
                "verbose": 0
            }

            model = CatBoostClassifier(**params)
            model.fit(
                X_train,
                y_train,
                sample_weight=train_weights,
                cat_features=cat_cols,
                eval_set=(X_val, y_val),
                early_stopping_rounds=50,
                verbose=False
            )
            preds = model.predict(X_val)
            return f1_score(y_val, preds, average='weighted')

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)
    

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='xgboost'
    )
        
    print(f"Mejor F1-Score: {study.best_value}")
    print(f"Mejores parámetros: {study.best_params}")
    best_params = study.best_params
    
    final_model = CatBoostClassifier(**best_params)
    final_model.fit(
                X_train,
                    y_train,
                    cat_features=cat_cols,
                    eval_set=(X_val, y_val),
                    early_stopping_rounds=50,
                    verbose=False
            )

    y_pred = final_model.predict(X_test)
    
    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test, y_pred,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    save_model(output_file='catboostClustered.pkl', final_model=final_model)

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def model_umap(df, modelName=None):
    """
    Modelo completo de XGBoost realizando un UMap sobre los embeddings de imagenes.

        Args:
            - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
            - modelName (String): Nombre del modelo a subir a wandb
        Returns:
            None
    """     

    # Hacemos encoding de la variable objetivo ya que no acepta str XGBoost
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    # sample_weights = class_weights(y_train)
    
    X_train, X_val, X_test = umap_embeddings(X_train, X_val, X_test, emb_col='v_clip')

    smote = SMOTE(random_state=seed)
    X_train, y_train = smote.fit_resample(X_train, y_train)

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
            #sample_weight=sample_weights,
            eval_set=[(X_val, y_val)],
            verbose=False
        )
        preds = model.predict(X_val)
        score = f1_score(y_val, preds, average='weighted')        
        return score

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
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
        random_state=seed
    )
    
    final_model.fit(
        X_train, y_train, 
        #sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )

    save_model(output_file='xgboostumapOS.pkl', final_model=final_model)


    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def model_cluster(df, modelName=None):
    """
    Modelo completo de XGBoost usando un clustering en los embeddings de imágenes.

    Args:
        - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
        - modelName (String): Nombre del modelo a subir a wandb
    Returns:
        None
    """     

    # Hacemos encoding de la variable objetivo ya que no acepta str XGBoost
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    sample_weights = class_weights(y_train)
    
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

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
        name= modelName,
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
        random_state=seed
    )
    
    final_model.fit(
        X_train, y_train, 
        sample_weight=sample_weights,
        verbose=False
    )

    y_pred = final_model.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def random_search(X_train, y_train, sample_weights=None):
    model = xgb.XGBClassifier(
        objective='multi:softprob',
        num_class=len(set(y_train)),
        random_state=seed,
        tree_method='hist', 
        device='cuda',
        eval_metric='mlogloss'
    )
    param_dist = {
        'n_estimators': [200, 400, 600],
        'learning_rate': [0.03, 0.05, 0.1],
        'max_depth': [4, 6, 8],
        'subsample': [0.7, 0.9, 1.0],
        'colsample_bytree': [0.7, 0.9, 1.0],
        'gamma': [0, 0.1, 1],
        'min_child_weight': [1, 3, 5]
    }
    search = RandomizedSearchCV(
        estimator=model,
        param_distributions=param_dist,
        n_iter=120,
        cv=3,
        verbose=1,
        n_jobs=1,
        scoring='f1_weighted',
        random_state=seed
    )
    search.fit(X_train, y_train, sample_weight=sample_weights)

    return search   

def model_search(df, modelName=None):
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])


    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)

    sample_weights = class_weights(y_train)

    X_train, X_val, X_test = umap_embeddings(X_train, X_val, X_test, emb_col='v_clip')


    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name=modelName,
        job_type='xgboost'
    )
    search_result = random_search(X_train, y_train, sample_weights=sample_weights)
    
    best_params = search_result.best_params_
    final_model = search_result.best_estimator_
    
    print(f"Mejor F1-Score (CV): {search_result.best_score_}")
    print(f"Mejores parámetros: {best_params}")
    y_pred = final_model.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def xgboost_base():
    print('Selecciona qué modelo quieres entrenar:')
    print('1. XGBoost Base sin imágenes')
    print('2. XGBoost Base con imágenes (PCA 50)')
    print('3. XGBoost Clustered')
    print('4. CatBoost Clustered')
    print('5. XGBoost  Umap')
    print('6. XGBoost Umap RandomSearch')
    print('0. Salir')

    opcion = input('Ingresa el número de la opción: ')
    df = read_prices()
    if opcion == '1':
        df_noimg = df.drop(columns=['brillo', 'v_clip'])
        model_noimg(df_noimg, modelName='XGBoost-Base NoImg')
    elif opcion == '2':
        df_img = df.copy()
        model_img(df_img, modelName='XGBoost-Base Img PCA 50')
    elif opcion == '3':
        df_clustered = df.copy()
        model_cluster(df_clustered, modelName='XGBoost Clustered')
    elif opcion == '4':
        df_clustered = df.copy()
        catModel(df_clustered, modelName='Cat Clustered')
    elif opcion == '5':
        df_umap = df.copy()
        model_umap(df_umap, modelName='XGBoost Umap')
    elif opcion == '6':
        df_umap = df.copy()
        model_search(df_umap, modelName='XGBoost Umap RandomSearch')
    else:
        return


def main():
    xgboost_base()

if __name__ == "__main__":
    main()
