from utils.utils import read_prices, train_val_test_split, class_weights, get_metrics, combine_train_val
from utils.utils import normalize_train_test, pca_train_test, cluster_embedings, umap_embeddings,save_model

from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import f1_score
from sklearn.model_selection import GridSearchCV
from sklearn.metrics import f1_score
from catboost import CatBoostClassifier
import xgboost as xgb
import optuna

import wandb

import pandas as pd

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
    X_train, y_train =  combine_train_val(X_train, X_val, y_train, y_val)

    sample_weights = class_weights(y_train)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='xgboost'
    )
    best_params = {
        'colsample_bytree':0.5548684904189958,
        'gamma':0.05885948641707637,
        'learning_rate':0.04579492491369452,
        'max_depth':10,
        'min_child_weight':1,
        'n_estimators':380,
        'subsample':0.9608130856104324
    }

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
    X_train, y_train =  combine_train_val(X_train, X_val, y_train, y_val)
    sample_weights = class_weights(y_train)

    best_params = {
        'colsample_bytree':0.9673925243965164,
        'gamma':0.304701258781668,
        'learning_rate':0.06640101870529921,
        'max_depth':8,
        'min_child_weight':4,
        'n_estimators':188,
        'subsample':0.8114823523287747,
    }

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
    
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')
    X_train, y_train =  combine_train_val(X_train, X_val, y_train, y_val)

    cat_cols = [
               'Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation',
                   'Strategy', 'Co-op', 'Custom Volume Controls', 'Family Sharing',
                   'Full controller support', 'Multi-player', 'Online Co-op', 'Online PvP',
                   'Partial Controller Support', 'Playable without Timed Input', 'PvP',
                   'Remote Play Together', 'Shared/Split Screen', 'Single-player',
                   'Steam Achievements', 'Steam Cloud', 'Steam Leaderboards',
                   'Steam Trading Cards', 'cluster'
    ]
    
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='xgboost'
    )
        
    best_params = {'iterations': 431, 'depth': 10, 'learning_rate': 0.049814771667902324, 'l2_leaf_reg': 0.1422433602427104, 'border_count': 60}
    
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
    metrics_dict = get_metrics(y_test, y_pred)
    
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

    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = umap_embeddings(X_train, X_val, X_test, emb_col='v_clip')
    X_train, y_train =  combine_train_val(X_train, X_val, y_train, y_val)
    sample_weights = class_weights(y_train)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='xgboost'
    )

    best_params = {
        'colsample_bytree':0.6671264654920448,
        'gamma':0.022859752952621184,
        'learning_rate':0.01912097362524424,
        'max_depth':10,
        'min_child_weight':1,
        'n_estimators':686,
        'subsample':0.6255483615395034
    }

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
    save_model(output_file='xgboostumap.pkl', final_model=final_model)

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
    le = LabelEncoder()
    df['price_range'] = le.fit_transform(df['price_range'])

    # División Train, Validation, Test
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    sample_weights = class_weights(y_train)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

    X_train, y_train =  combine_train_val(X_train, X_val, y_train, y_val)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='xgboost'
    )
    
    best_params = {
        'colsample_bytree':0.5327779689329123,
        'gamma':0.00005474029242191838,
        'learning_rate':0.0272617630976022,
        'max_depth':8,
        'min_child_weight':2,
        'n_estimators':859,
        'subsample':0.9405826954214862,
    }

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
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def xgboost_base():
    print('Selecciona qué modelo quieres entrenar:')
    print('1. XGBoost Base sin imágenes')
    print('2. XGBoost Base con imágenes (PCA 50)')
    print('3. XGBoost Clustered')
    print('4. CatBoost Clustered')
    print('5. XGBoost Umap')
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
    else:
        return

if __name__ == '__main__':
    xgboost_base()
