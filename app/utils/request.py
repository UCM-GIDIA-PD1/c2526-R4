import pandas as pd
import numpy as np 
from sklearn.cluster import KMeans

#TODO: Implementar lectura de minio para los modelos y datos

def read_popularity():
    """Obtiene el dataFrame de popularidad.parquet
    """
    print('Reading parquet')
    data = pd.read_parquet('data/popularidad.parquet')
    
    if data.empty:
        raise ValueError("El dataframe de popularidad está vacío")

    print('Data read correctly')

    return data


def read_prices():
    """Obtiene el dataFrame de precios.parquet
    """
    print('Reading parquet')
    data = pd.read_parquet('data/precios.parquet')
    
    if data.empty:
        raise ValueError("El dataframe de precios está vacío")

    print('Data read correctly')

    matrix = np.stack(data['v_clip'].values)
    kmeans = KMeans(n_clusters=8, random_state=42)
    data['cluster'] = kmeans.fit_predict(matrix)
    data = data.drop(columns=['v_clip'])

    return data
    
def find_row(appid : str, df : pd.DataFrame):
    """Dado un appid de un juego, obtiene la fila correspendiente a ese juego en el dataFrame
    """
    row = df.loc[df['id'] == appid]

    print(row)

    return row

def prices_transform(data):
    #NOTE: Se usa el modelo de knn de precios (para probar porque era el más 'sencillo')

    data = data.drop(columns= ['id','name','price_overview','v_resnet','v_convnext'])
    data['release_year'] = df['release_year'].apply(lambda x : int(x))
    return data



