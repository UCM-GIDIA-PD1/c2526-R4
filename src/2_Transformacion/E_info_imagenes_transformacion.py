"""
Dado el archivo banners_file.jsonl.gz aplica reducción de dimensionalidad sobre los vectores
de 512 dimensiones convirtiéndolos en vectores de 2 o 3 dimensiones para poder visualizarlos.
"""
from pandas import DataFrame, Series
from numpy import vstack
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from src.utils.files import read_file, write_to_file
from src.utils.config import banners_file, gamelist_file, P_banners_file, popularity

def join_B_and_E():
    """
    Unión de DataFrames resultantes de B y E

    Returns:
        pd.DataFrame: Dataframe resultante de juntar B y E
    """
    dfE = DataFrame(read_file(banners_file))
    dfB = DataFrame(read_file(gamelist_file))

    # Meter numero de reseñas
    dfB = dfB.join(dfB["appreviewhistogram"].apply(Series))
    dfB["total_recommendations"] = dfB["rollups"].apply(lambda x: x.get("total_recommendations"))
    dfB = dfB[["id", "total_recommendations"]]

    df_joined = dfE.merge(dfB, on="id")

    # Meter precio
    df = df.join(df["appdetails"].apply(Series))
    df["initial"] = df["price_overview"].apply(lambda x : x.get("initial"))
    df = df[["id", "initial"]]

    df_joined = df_joined.merge(df, on="id")
    return df_joined

def dim_reduction(df, mod, matrix, dimensions = 2, fast = False):
    """
    Se realiza una reducción de dimensionalidad usando PCA y TSNE.

    Args:
        df (pd.DataFrame): DataFrame a reducir dimensión
        mod (str): Modelo
        matrix (list(list)): Matriz a reducir
        dimensions (int, optional): Número de dimensiones para reducir. Defaults to 2.
        fast (bool, optional): Booleano para indicar que vaya más rápido. Defaults to False.
    """
    # PCA
    pca = PCA(n_components=dimensions)
    coords_pca = pca.fit_transform(matrix)
    
    for i in range(dimensions):
        df[f'pca_{mod}_{i+1}']= coords_pca[:, i]
    
    # TSNE
    # Al ser el TSNE muy lento, si se activa el parámetro de fast se hará antes un PCA hasta las 50 dimensiones
    if fast:
        pca_pre = PCA(n_components=50)
        matrix = pca_pre.fit_transform(matrix)
    
    tsne = TSNE(n_components=dimensions, perplexity=30, random_state=42, init='pca')
    coords_tsne = tsne.fit_transform(matrix)
    
    for i in range(dimensions):
        df[f'tsne_{mod}_{i+1}']= coords_tsne[:, i]

def reduct_dataframes_from_models(df):
    """
    Dado un dataFrame, realiza la reducción de dimensionalidad de cada modelo (resnet, convnext, clip)

    Args:
        df (pd.DataFrame): DataFrame para procesar por los distintos modelos
    """
    modelos = ['v_resnet', 'v_convnext', 'v_clip']
    for mod in modelos:
        print(f"Procesando reducción de dimensionalidad para: {mod}...")
        matrix = vstack(df[mod].values)
        dim_reduction(df, mod, matrix)

def info_imagenes_transformacion(minio = {"minio_write": False, "minio_read": False}):
    print("Ejecutano reducción de vectores de imágenes\n")
    df = read_file(popularity)
    reduct_dataframes_from_models(df)
    df.to_parquet(P_banners_file)

if __name__ == "__main__":
    info_imagenes_transformacion()