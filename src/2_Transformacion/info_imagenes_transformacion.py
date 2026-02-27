import pandas as pd
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

from utils.files import read_file, write_to_file
from utils.config import banners_file, gamelist_file, P_banners_file

def join_B_and_E():
    dfE = pd.DataFrame(read_file(banners_file))
    dfB = pd.DataFrame(read_file(gamelist_file))

    # Meter numero de reseñas
    dfB = dfB.join(dfB["appreviewhistogram"].apply(pd.Series))
    dfB["total_recommendations"] = dfB["rollups"].apply(lambda x: x.get("total_recommendations"))
    dfB = dfB[["id", "total_recommendations"]]

    df_joined = dfE.merge(dfB, on="id")

    # Meter precio

    df = df.join(df["appdetails"].apply(pd.Series))
    df["initial"] = df["price_overview"].apply(lambda x : x.get("initial"))
    df = df[["id", "initial"]]

    df_joined = df_joined.merge(df, on="id")
    return df_joined

def dim_reduction(df, mod, matrix, dimensions = 2, fast = False):
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
    modelos = ['v_resnet', 'v_convnext', 'v_clip']
    for mod in modelos:
        print(f"Procesando reducción de dimensionalidad para: {mod}...")
        matrix = np.vstack(df[mod].values)
        dim_reduction(df, mod, matrix)

def info_imagenes_transformacion(minio = {"minio_write": False, "minio_read": False}):
    df = join_B_and_E()
    reduct_dataframes_from_models(df)
    write_to_file(df.to_dict(), P_banners_file)