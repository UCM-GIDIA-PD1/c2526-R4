'''
Dado youtube_statistics.jsonl.gz procesa el json para crear un dataframe y crear las columnas
rellenado nulos, guardando ese dataframe base. Acto seguido, se hace un PCA para reducir la
dimensionalidad del dataset, guardando también ese dataframe.
'''

import pandas as pd
from src.utils.config import yt_statslist_file, yt_stats_parquet_file, yt_statsPCA_parquet_file
from src.utils.files import read_file
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def _flatten_dict(d, prefix):
    """
    Aplana un diccionario y añade prefijo de nombre las columnas (prefix_col).
    """
    if pd.isna(d):
        return pd.Series(dtype=object)

    flat = pd.json_normalize(d).iloc[0]
    flat.index = [f"{prefix}_{col}" for col in flat.index]
    return flat

def _transform_to_dataframe(data):
    # Se crea el dataframe base
    df = pd.DataFrame(data)
    
    # Por cada miembro de la lista se crea una columna, rellenando con nulos las filas que no tienen esos datos
    df = df.join(df["video_statistics"].apply(pd.Series))
    # Se eliminan las columnas que más nulos tienen y la columna base video_statistics
    df.drop(df.columns[7:],axis=1, inplace=True)
    df.drop('video_statistics', axis=1, inplace=True)


    # Procesamos los diccionarios para transformarlos en columnas
    video_cols = [0, 1, 2, 3]
    dfs = []
    for col in video_cols:
        flattened = df[col].apply(lambda x: _flatten_dict(x, f"video_{col}"))
        dfs.append(flattened)
    df_final = pd.concat([df] + dfs, axis=1)

    # Volvemos a eliminar columnas innecesarias y sustituimos los nulos con 0
    df_final.drop([0,1,2,3, 'video_0_id', 'video_1_id', 'video_2_id', 'video_3_id'], axis=1,inplace=True)
    df_final = df_final.fillna(0)

    cols_to_int = [
    c for c in df_final.columns
    if "video_statistics" in c
    ]

    # Para evitar problemas de tipos transformamos todas las columnas de estadísticas a int
    df_final[cols_to_int] = (
        df_final[cols_to_int]
            .apply(pd.to_numeric, errors="coerce") 
            .astype("Int64")                       
    )

    return df_final

def _PCA_analysis(df):
    video_cols = [0, 1, 2, 3]

    for i in video_cols:
        # Cogemos las columnas de estadísticas relativas al vídeo
        cols = [
            c for c in df.columns
            if c.startswith(f"video_{i}_") and "statistics" in c
        ]
        X = df[cols].select_dtypes(include="number").fillna(0)

        # Estandarizamos las métricas
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # 5️PCA (2 componentes)
        pca = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X_scaled)
        
        # Añadir al dataframe
        df[f"video_{i}_pca_1"] = X_pca[:, 0]
        df[f"video_{i}_pca_2"] = X_pca[:, 1]

    # Eliminamos las columnas previas al PCA
    cols_to_drop = [
    c for c in df.columns
    if any(c.startswith(f"video_{i}_") and "statistics" in c for i in [0,1,2,3])
    ]
    df.drop(cols_to_drop, axis=1, inplace=True)


    rename_map = {}
    for i in [0, 1, 2, 3]:
        rename_map[f"video_{i}_pca_1"] = f"video_{i}_popularity_score"
        rename_map[f"video_{i}_pca_2"] = f"video_{i}_engagement_score"

    df = df.rename(columns=rename_map)
        
    return df

if __name__ == '__main__':

    print('Obteniendo archivo')
    data = read_file(yt_statslist_file)
    assert data, 'No se ha podido leer el archivo'
    
    print('Tranformando a dataframe')
    df = _transform_to_dataframe(data)

    # Guardamos dataframe antes del PCA
    print('Guardando dataframe base')
    df.to_parquet(yt_stats_parquet_file)

    print('Analizando PCA')
    df = _PCA_analysis(df)

    print('Guardando dataframe reducido con PCA')
    df.to_parquet(yt_statsPCA_parquet_file)


