import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from src.utils.files import read_file
from src.utils.config import prices
import wandb
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler
import numpy as np

def _PCA_matrix(col):
    '''
    La entrada es una Series de pandas con embeddings de imágenes, 
    la salida es un array de numpy con el PCA de dichos embeddings
    '''
    col_matrix = np.vstack(col.values)
    pca = PCA(n_components=10, random_state=42)
    col_pca = pca.fit_transform(col_matrix)
    return col_pca


def transform_df_prices_logistic_regression(df):
    df_clean = df.copy()
    
    # Seleccionamos las variables de entrada útiles
    target_col = df_clean['price_range']
    erase_columns = ['id', 'name', 'price_overview', 'v_resnet', 'v_convnext']
    df_clean = df_clean.drop(columns=erase_columns, errors='ignore')

    # Vamos a hacer un PCA de los embeddings
    # Forzamos a que todos los valores de la columna de los embeddings sean iterables
    zero_vector = np.zeros(512)
    df_clean['v_clip'] = df_clean['v_clip'].apply(
        lambda x: x if isinstance(x, (list, np.ndarray)) else zero_vector
    )
    
    imgs_pca = _PCA_matrix(df_clean['v_clip'])
    
    for i in range(10):
        df_clean[f'v_clip_pca_{i}'] = imgs_pca[:, i]
    
    # Ya la columna de los embeddings originales no es necesaria
    df_clean = df_clean.drop(columns=['v_clip'])

    obj_cols = df_clean.select_dtypes(include=['object', 'str']).columns
    for col in obj_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    # Solo nos quedamos con columnas numéricas y rellenamos nulos
    df_clean = df_clean.select_dtypes(include=[np.number])
    df_clean = df_clean.fillna(0)

    scaler = StandardScaler()
    df_clean[df_clean.columns] = scaler.fit_transform(df_clean)

    df_clean['price_range'] = target_col

    return df_clean

df = read_file(prices)
df_transformed = transform_df_prices_logistic_regression(df)

X = df_transformed.drop(columns=['price_range'])
y = df_transformed['price_range']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)


run = wandb.init(
    entity="pd1-c2526-team4",
    project="Precios", 
    name='logistic-regression',
    job_type='logistic-regression'
)

best_params = {
    'C': 0.564857,
    'solver': 'lbfgs',
    'l1_ratio': 0.0
}

final_model = LogisticRegression(**best_params)
final_model.fit(X_train, y_train)

y_pred = final_model.predict(X_test)

print("Classification Report:")
cal = classification_report(y_test, y_pred)
print(cal)

print("Confusion Matrix:")
conf_matrix = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(conf_matrix)

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred, average='weighted')
recall = recall_score(y_test, y_pred, average='weighted')
f1 = f1_score(y_test, y_pred, average='weighted')

run.log({
    'accuracy': accuracy,
    'precision': precision,
    'recall': recall,
    'f1-score': f1,
    'confusion-matrix': conf_matrix.tolist() 
})

run.finish()