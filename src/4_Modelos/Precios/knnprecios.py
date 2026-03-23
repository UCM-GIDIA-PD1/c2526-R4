"""
Dado precios.parquet crea un modelo de knn para predecir en que rango de precio se sitúa un juego según sus características.
Realiza lo mismo con un PCA del 0.9 de varianza total.
"""

import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split    
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from src.utils.config import prices
from src.utils.files import read_file
from sklearn.decomposition import PCA
import wandb

def _preprocess(df):
    """
    Elimina columnas que no se usan en el modelo y realiza las transformaciones necesarias sobre el dataframe
    """
    df.drop(columns=['id','name', 'price_overview', 'v_convnext', 'v_resnet'], inplace=True, errors='ignore')
    
    # Transformamos categóricas
    le = LabelEncoder()
    le.fit(df['release_year'])
    encoding = le.transform(df['release_year'])
    df['release_year'] = pd.Series(encoding)

    # Transformamos vectores de imágenes
    df_clip = df['v_clip'].apply(pd.Series)
    df.drop(columns=['v_clip'], inplace=True, errors='ignore')
    df = pd.concat([df, df_clip], axis=1)
    df.columns = df.columns.astype(str)
    return df

def _normalize(X_train, X_test, columns_to_normalize):
    """
    Dado una división de train y test y una lista de columnas, normaliza los valores de esas columnas.
    """
    X_train = X_train.copy()
    X_test = X_test.copy()

    scaler = StandardScaler()
    X_train[columns_to_normalize] = scaler.fit_transform(X_train[columns_to_normalize])
    X_test[columns_to_normalize] = scaler.transform(X_test[columns_to_normalize])
    
    return X_train, X_test

def _best_k(X_train, y_train):
    """
    Dado el conjunto de entrenamiento calcula el mejor valor de k desde 1 hasta 50.
    """
    print('Calculating K')
    knn_scores = []
    k_values = range(1,50)
    for k_value in k_values:
        print(k_value, end=" ")
        knn = KNeighborsClassifier(n_neighbors=k_value)

        scores = cross_val_score(knn, X_train, y_train, cv=5)
        knn_scores.append(scores.mean())

    best_k = k_values[np.argmax(knn_scores)]
    
    print("\n")
    print(knn_scores)
    print(best_k, knn_scores[best_k])

    return best_k

def _create_model(X_train, y_train, best_k, X_test, y_test, modelName, modelJobtype):
    """
    Crea el modelo de k-nn y saca sus métricas de evaluación, subiendo los resultados a Weigths and Baises.
    """
    run = wandb.init(
        entity="pd1-c2526-team4",
        project="Precios", 
        name=modelName,
        job_type=modelJobtype
    )
        
    knn = KNeighborsClassifier(n_neighbors=best_k)
    knn.fit(X_train,y_train)
    y_pred = knn.predict(X_test)

    # Métricas
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    print(f'Acurracy: {accuracy}')
    print(f'Precision: {precision}')
    print(f'Recall: {recall}')
    print(f'F1-Score: {f1}')
    print(f'Confusion-Matrix: {conf_matrix}')

    run.log({
        'accuracy' : accuracy,
        'precision' : precision,
        'Recall' : recall,
        'f1-score' : f1,
        'confusion-matrix' : conf_matrix
    })

    run.finish()

def _complete_model(df):
    """
    Crea un modelo k-nn con variable objetivo 'price_range', diviendo el dataset en test y train, normalizando y ajustando el hiperparámetro k
    """
    df_copy = df.copy()

    y = df_copy['price_range']
    X = df_copy.drop(columns=['price_range'])
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)    

    columns_to_normalize = ['description_len', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']
    X_train, X_test = _normalize(X_train, X_test, columns_to_normalize)


    k_value  = _best_k(X_train, y_train)
    
    _create_model(X_train,y_train, k_value, X_test, y_test, modelName='complete-knn',modelJobtype='knn' )

def _pca_model(df):
    """
    Crea un modelo k-nn con variable objetivo 'price_range' haciendo un PCA para reducir dimensiones, diviendo el dataset en test y train,
    normalizando y ajustando el hiperparámetro k.
    """
    df_copy = df.copy()

    y = df_copy['price_range']
    X = df_copy.drop(columns=['price_range'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)    

    columns_to_normalize = X_train.columns
    X_train, X_test = _normalize(X_train, X_test, columns_to_normalize)

    pca = PCA(n_components=0.90)  
    X_train_pca = pca.fit_transform(X_train)
    X_test_pca = pca.transform(X_test)

    k_value  = _best_k(X_train_pca, y_train)

    _create_model(X_train_pca,y_train, k_value, X_test_pca, y_test, modelName='pca-knn',modelJobtype='knn' )

if __name__ == '__main__':
    print('Reading')
    df = read_file(prices)
    
    print('Preprocessing')
    df = _preprocess(df)

    print('Creating Complete DataFrame Model')
    _complete_model(df)

    print('Creating PCA DataFrame Model')
    _pca_model(df)
