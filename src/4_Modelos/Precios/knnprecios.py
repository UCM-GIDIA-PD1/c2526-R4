"""
Dado precios.parquet crea un modelo de knn para predecir en que rango de precio se sitúa un juego 
según sus características. Realiza lo mismo con un PCA del 0.9 de varianza total.
"""

from .utils_modelo_precios.preprocesamiento import get_metrics, read_prices, train_val_test_split,normalize_train_test, pca_train_test,cluster_embedings, read_prices_reduced
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import f1_score
from sklearn.preprocessing import LabelEncoder
import wandb
import pandas as pd
from imblearn.over_sampling import SMOTE


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

def _complete_model(df, modelName= 'K-NN Complete Clusters'):
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

    metrics_dict = get_metrics(y_test, y_pred)

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _complete_pca_mode(df, modelName= 'K-NN Complete Clusters PCA'):
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

    metrics_dict = get_metrics(y_test, y_pred)

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _reduced_model(df, modelName= 'K-NN Reduced'):
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

    metrics_dict = get_metrics(y_test, y_pred)

    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def _oversampled_reduced(df, modelName= 'K-NN Reduced Oversampled'):
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

    smote = SMOTE(random_state=42)
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
    metrics_dict = get_metrics(y_test, y_pred)
    run.config.update(best_params)
    run.log(metrics_dict)
    run.finish()

def knnprecios():
    df = read_prices()
    df_reduced = read_prices_reduced()

    print('Selecciona qué modelo quieres entrenar:')
    print('1. K-NN Complete Clusters')
    print('2. K-NN Complete Clusters PCA')
    print('3. K-NN Reduced')
    print('4. K-NN Reduced Oversampled')
    print('0. Salir')
    opcion = input('Ingresa el número de la opción: ')

    if opcion == '1':
        _complete_model(df.copy(), modelName='K-NN Complete Clusters')
    elif opcion == '2':
        _complete_pca_mode(df.copy(), modelName='K-NN Complete Clusters PCA')
    elif opcion == '3':
        _reduced_model(df_reduced.copy(), modelName='K-NN Reduced')
    elif opcion == '4':
        _oversampled_reduced(df_reduced.copy(), modelName='K-NN Reduced Oversampled')
    elif opcion == '0':
        return
    else:
        print('Opción no válida')
        return

    
if __name__ == '__main__':
    knnprecios()
