import pandas as pd

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

    return data
    
def find_row(appid : str, df : pd.DataFrame):
    """Dado un appid de un juego, obtiene la fila correspendiente a ese juego en el dataFrame
    """
    row = df.loc[df['id'] == appid]

    print(row)

    return row
