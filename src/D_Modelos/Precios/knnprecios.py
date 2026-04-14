"""
Dado precios.parquet crea un modelo de knn para predecir en que rango de precio se sitúa un juego 
según sus características. Realiza lo mismo con un PCA del 0.9 de varianza total.
"""

from utils.utils import get_metrics, read_prices, train_val_test_split,normalize_train_test, pca_train_test,cluster_embedings, read_prices_reduced
from src.utils.config import precios_knncompleteclusters_file, precios_knncompleteclusters_pca_file, precios_knnreduced_file, precios_knnreduced_oversampled_file, models_precios_path
from src.utils.files import write_to_file

from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder
from imblearn.over_sampling import SMOTE

import wandb
import os

import pandas as pd
from src.utils.config import seed

def grid_search_knn_full(X_train, X_val, y_train, y_val):
    """
    Optimización de hiperparámetros para K-NN usando los conjuntos de train y validation.

    Args:
        - X_train (pd.Dataframe):  Conjunto de entranamiento
        - X_val (pd.Dataframe): Conjunto de entranamiento
        - y_train (pd.Dataframe): Variable objetivo del conjunto de entrenamiento
        - y_val (pd.Dataframe): Variable objetivo del conjunto de validacion

    Returns:
        best_params (dict): Diccionario que contiene los parámetros (n_neighbors, weights, metric) del mejor modelo
    """
    param_grid = {
        'n_neighbors': list(range(1, 40, 1)),
        'weights': ['uniform', 'distance'],
        'metric': ['euclidean', 'manhattan']
    }

    best_params = None
    best_score = -1

    print('Optimizando')
    for n in param_grid['n_neighbors']:
        for w in param_grid['weights']:
            for m in param_grid['metric']:
                knn = KNeighborsClassifier(n_neighbors=n, weights=w, metric=m)
                knn.fit(X_train, y_train)
                score = f1_score(y_val, knn.predict(X_val), average='weighted')

                if score > best_score:
                    best_score = score
                    best_params = {'n_neighbors': n, 'weights': w, 'metric': m}
                
                print('Best Params: ', best_params)

    print("Mejor combinación de parámetros:", best_params)
    print("Mejor score en validación:", best_score)

    return best_params

def objective(trial, X_train, X_val, y_train, y_val):
    params = {
        'n_neighbors': trial.suggest_int('n_neighbors', 1, 40),
        'weights': trial.suggest_categorical('weights', ['uniform', 'distance']),
        'metric': trial.suggest_categorical('metric', ['euclidean', 'manhattan'])
    }
    knn = KNeighborsClassifier(**params)
    knn.fit(X_train, y_train)
    preds = knn.predict(X_val)
    
    score = f1_score(y_val, preds, average='weighted')
    
    return score

def _complete_model(df, minio, modelName= 'K-NN Complete Clusters', ):
    """
    Modelo completo de K-NN usando clusters de los embeddings.

    Args:
        - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
        - modelName (String): Nombre del modelo a subir a wandb
    Returns:
        None
    """
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

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='knn'
    )

    best_params = grid_search_knn_full(X_train, X_val, y_train, y_val)

    knn = KNeighborsClassifier(**best_params)
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_complete_clusters.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(knn, precios_knncompleteclusters_file, minio)
    print(f"Modelo guardado en {precios_knncompleteclusters_file}")

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _complete_pca_mode(df, minio, modelName= 'K-NN Complete Clusters PCA'):
    """
        Modelo completo de K-NN usando clusters de los embeddings y realizando un PCA para reducir dimensionalidad.

        Args:
            - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
            - modelName (String): Nombre del modelo a subir a wandb
        Returns:
            None
    """

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
    X_train, X_val, X_test = pca_train_test(X_train, X_val, X_test, n_comp=0.9)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='knn'
    )

    best_params = grid_search_knn_full(X_train, X_val, y_train, y_val)

    knn = KNeighborsClassifier(**best_params)
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_complete_clusters_pca.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(knn, precios_knncompleteclusters_pca_file, minio)
    print(f"Modelo guardado en {precios_knncompleteclusters_pca_file}")

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _reduced_model(df, minio, modelName= 'K-NN Reduced'):
    """
        Modelo completo de K-NN usando el conjunto de datos reducido.

        Args:
            - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
            - modelName (String): Nombre del modelo a subir a wandb
        Returns:
            None
    """     
    y = df['price_range']
    X = df.drop(columns=['price_range'])
    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

    le = LabelEncoder()
    y_train = le.fit_transform(y_train)
    y_val   = le.transform(y_val)
    y_test  = le.transform(y_test)

    all_genres = pd.concat([X_train['genres'], X_val['genres'], X_test['genres']])
    le = LabelEncoder()
    le.fit(all_genres)
    X_train['genres'] = le.transform(X_train['genres'])
    X_val['genres']   = le.transform(X_val['genres'])
    X_test['genres']  = le.transform(X_test['genres'])

    columnas_categoricas = ['Custom Volume Controls', 'Family Sharing', 'Playable without Timed Input', 'Single-player', 'has_multiplayer']
    columnas_numericas = X_train.columns.difference(columnas_categoricas).tolist()
    X_train, X_val, X_test = normalize_train_test(X_train, X_val, X_test, columnas_numericas)
    X_train, X_val, X_test = pca_train_test(X_train, X_val, X_test, n_comp=0.9)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name= modelName,
        job_type='knn'
    )

    best_params = grid_search_knn_full(X_train, X_val, y_train, y_val)

    knn = KNeighborsClassifier(**best_params)
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)

    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)

    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced.png'

    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )

    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(knn, precios_knnreduced_file, minio)
    print(f"Modelo guardado en {precios_knnreduced_file}")

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _oversampled_reduced(df, minio, modelName= 'K-NN Reduced Oversampled'):
    """
    Modelo completo de K-NN usando el conjunto de datos reducido y haciendo oversampling para tratar de paliar el desbalance.

    Args:
        - df (pd.DataFrame): DataFrame con el que se realizará el modelo.
        - modelName (String): Nombre del modelo a subir a wandb
    Returns:
            None
    """

    y = df['price_range']
    X = df.drop(columns=['price_range'])

    X_train, X_val, X_test, y_train, y_val, y_test = train_val_test_split(X, y)
    X_train, X_val, X_test = cluster_embedings(X_train, X_val, X_test, emb_col='v_clip')

    le = LabelEncoder()
    y_train = le.fit_transform(y_train)
    y_val   = le.transform(y_val)
    y_test  = le.transform(y_test)

    all_genres = pd.concat([X_train['genres'], X_val['genres'], X_test['genres']])
    le_genres = LabelEncoder()
    le_genres.fit(all_genres)
    X_train['genres'] = le_genres.transform(X_train['genres'])
    X_val['genres']   = le_genres.transform(X_val['genres'])
    X_test['genres']  = le_genres.transform(X_test['genres'])

    columnas_categoricas = ['Custom Volume Controls', 'Family Sharing', 'Playable without Timed Input', 'Single-player', 'has_multiplayer']
    columnas_numericas = X_train.columns.difference(columnas_categoricas).tolist()

    X_train, X_val, X_test = normalize_train_test(X_train, X_val, X_test, columnas_numericas)
    X_train, X_val, X_test = pca_train_test(X_train, X_val, X_test, n_comp=0.9)

    smote = SMOTE(random_state=seed)
    X_train, y_train = smote.fit_resample(X_train, y_train)

    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios",
        name=modelName,
        job_type='knn'
    )
    best_params = grid_search_knn_full(X_train, X_val, y_train, y_val)
    knn = KNeighborsClassifier(**best_params)
    knn.fit(X_train, y_train)
    y_pred = knn.predict(X_test)
    y_test_labels = le.inverse_transform(y_test)
    y_pred_labels = le.inverse_transform(y_pred)
    cm_path = 'models/precios/graficos/confusionMatrix/knn_reduced_oversampled.png'
    metrics_dict = get_metrics(
        y_test_labels, y_pred_labels,
        classes=['[0.01,4.99]', '[5.00,9.99]', '[10.00,14.99]', '[15.00,19.99]', '[20.00,29.99]', '[30.00,39.99]', '>40'],
        img_path=cm_path, download_images=True
    )
    
    os.makedirs(models_precios_path(), exist_ok=True)
    write_to_file(knn, precios_knnreduced_oversampled_file, minio)
    print(f"Modelo guardado en {precios_knnreduced_oversampled_file}")

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def knnprecios(minio):
    df = read_prices(minio)
    df_reduced = read_prices_reduced(minio)

    print('Selecciona qué modelo quieres entrenar:')
    print('1. K-NN Complete Clusters')
    print('2. K-NN Complete Clusters PCA')
    print('3. K-NN Reduced')
    print('4. K-NN Reduced Oversampled')
    print('5. K-NN Best Variables')
    print('0. Salir')
    opcion = input('Ingresa el número de la opción: ')

    if opcion == '1':
        _complete_model(df.copy(), minio, modelName='K-NN Complete Clusters')
    elif opcion == '2':
        _complete_pca_mode(df.copy(), minio, modelName='K-NN Complete Clusters PCA')
    elif opcion == '3':
        _reduced_model(df_reduced.copy(), minio, modelName='K-NN Reduced')
    elif opcion == '4':
        _oversampled_reduced(df_reduced.copy(), minio, modelName='K-NN Reduced Oversampled')
    elif opcion == '0':
        return
    elif opcion == '5':
        df_bestv = df.copy()
        df_bestv = df_bestv[['Indie', 'Family Sharing', 'Casual', 'Online PvP', 'Single-player', 'Steam Cloud', 'Custom Volume Controls',
                              'total_games_by_publisher', 'num_languages', 'v_clip', 'PvP', 'price_range']]
        _complete_model(df_bestv, minio, modelName='K-NN Best Variables')
    else:
        print('Opción no válida')
        return
    

def main(minio = {"minio_write": False, "minio_read": False}):
    knnprecios(minio)

if __name__ == "__main__":
    main()
