from pathlib import Path
import pandas as pd
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split 
from plotly import express as px
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from imblearn.over_sampling import SMOTE
from src.utils.config import prices
from src.utils.files import read_file


def _preprocess(df):
    df.drop(columns=['id','name'], inplace=True, errors='ignore')
    # print(df.dtypes)
    # df.head(2)

    le = LabelEncoder()
    le.fit(df['release_year'])
    encoding = le.transform(df['release_year'])

    df['release_year'] = pd.Series(encoding)
    
    columns_to_normalize = ['description_len', 'num_languages', 'total_games_by_publisher', 'total_games_by_developer']

    scaler = StandardScaler()
    df[columns_to_normalize] = scaler.fit_transform(df[columns_to_normalize])

def _create_model(X_train, y_train, best_k, X_test, y_test):
    knn = KNeighborsClassifier(n_neighbors=best_k)
    knn.fit(X_train,y_train)
    y_pred = knn.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    print(accuracy)

    precision = precision_score(y_test, y_pred, average='weighted')
    recall = recall_score(y_test, y_pred, average='weighted')
    f1 = f1_score(y_test, y_pred, average='weighted')
    print(precision)
    print(recall)
    print(f1)
    conf_matrix = confusion_matrix(y_test, y_pred)
    print(conf_matrix)

def _best_k(X_train, y_train):
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

def _model(df):
    y = df['price_range']
    X = df.drop(columns=['price_range'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=.2, random_state=42)    

    k_value  = _best_k(X_train, y_train)
    
    _create_model(X_train,y_train, k_value, X_test, y_test)
    
 

if __name__ == '__main__':
    df = read_file(prices)
    _preprocess(df)