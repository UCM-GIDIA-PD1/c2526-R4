'''
Dado youtube_statistics.jsonl.gz procesa el json para crear un dataframe, crear las columnas de estadísticas,
rellenado nulos.

Además, se realiza una reducción de dimensionalidad basado en ponderaciones de los pesos de cada estadística y cada vídeo,
que está ordenado según el número de visualizaciones.
'''

import pandas as pd
import numpy as np
from src.utils.config import yt_statslist_file, yt_stats_parquet_file
from src.utils.files import read_file, erase_file
from src.utils.minio_server import upload_to_minio
from filtrado_youtube_llm import filtrado_por_clasificacion

def _flatten_dict(d, prefix):
    '''
    Dada una columna de un dataframe (pd.Series), que contiene un diccionario,
    usa .json_normalize para crear un nuevo dataframe y le altera el nombre a las columnas
    para que tengan un prefijo.

    Args:
        d (pd.Serie): Columna de un dataframe que deberá ser transformado a varias columnas, contiene un diccionario.
    
    Returns:
        flat (pd.DataFrame): Dataframe resultante con las columnas formateadas.
    '''
    if pd.isna(d):
        return pd.Series(dtype=object)

    # Crear el dataframe a partir del json
    flat = pd.json_normalize(d).iloc[0]
    # Cambiar el nombre de las columnas
    flat.index = [f"{prefix}_{col}" for col in flat.index]
    return flat

def _transform_to_dataframe(data):
    '''
    Dada la lista de diccionarios resultante de leer youtube_statistics.jsonl.gz, crea un dataframe 
    separando los campos del diccionario en columnas y procesando los datos.

    Args:
        data (list): Lista de diccionarios con la información de los vídeos.
    
    Returns:
        df (pd.DataFrame): Dataframe resultante de la transformación.
    '''
    # Se crea el dataframe base
    df = pd.DataFrame(data)
    
    # Por cada miembro de la lista se crea una columna, rellenando con nulos las filas que no tienen esos datos
    df = df.join(df["video_statistics"].apply(pd.Series))
    # Se eliminan las columnas que más nulos tienen (nos quedamos solamente con 4 vídeos) y la columna base video_statistics
    df.drop(df.columns[7:],axis=1, inplace=True)
    df.drop('video_statistics', axis=1, inplace=True)

    # Procesamos los diccionarios para transformarlos en columnas
    video_cols = [col for col in [0, 1, 2, 3] if col in df.columns]
    dfs = []
    for col in video_cols:
        flattened = df[col].apply(lambda x: _flatten_dict(x, f"video_{col}"))
        dfs.append(flattened)
    df_final = pd.concat([df] + dfs, axis=1)

    # Eliminamos las columnas ya procesadas y las columnas de ID de vídeos generadas durante el procesamiento.
    df_final.drop([0,1,2,3, 'video_0_id', 'video_1_id', 'video_2_id', 'video_3_id'], axis=1,inplace=True,errors='ignore')
    
    # Rellenamos nulos
    df_final = df_final.fillna(0)

    # Drop de duplicados
    df_final = df_final.drop_duplicates(subset=['id'], keep='first')

    # Lista de columnas que vamos a transformar a un tipo numérico
    cols_transform = [ c for c in df_final.columns if "video_statistics" in c ]

    # Para evitar problemas de tipos transformamos todas las columnas de estadísticas a int
    df_final[cols_transform] = (
        df_final[cols_transform]
            .apply(pd.to_numeric, errors="coerce") 
            .astype("Int64")                       
    )

    return df_final

def procesar_impacto_youtube(df_original):
    '''
    Dado el dataframe ya procesado de las estadísticas, crea nuevas variables para medir el impacto en Youtube.

    Args:
        df_original (pd.DataFrame): Dataframe procesado con las estadísticas de Youtube. 
    
    Returns:
        df (pd.DataFrame): Dataframe resultante de la transformación.
    
    '''
    def calcular_fila(row):
        """
        Calcula la ponderación de youtube_score de cada fila (para usar en pd.DataFrame.apply())

        Args:
            row ( pandas.core.series.Series ): Fila de dataframe

        Returns:
            pd.DataFrame: Dataframe con la nueva columna yt_score
        """
        score_total = 0
        encontrado_alguna_metrica = False
        
        for i in range(4):
            v = row.get(f'video_{i}_video_statistics.viewCount', 0)
            l = row.get(f'video_{i}_video_statistics.likeCount', 0)
            c = row.get(f'video_{i}_video_statistics.commentCount', 0)
            
            vals = pd.to_numeric([v, l, c], errors='coerce')
            v, l, c = np.nan_to_num(vals) 
            
            if v > 0 or l > 0 or c > 0:
                encontrado_alguna_metrica = True
                sv = (0.5 * np.log10(v + 1)) + \
                     (0.3 * np.log10(l + 1)) + \
                     (0.2 * np.log10(c + 1))
                score_total += sv
        
        return score_total if encontrado_alguna_metrica else 0
    
    df_original['yt_score'] = df_original.apply(calcular_fila, axis=1)
    df_original.drop(columns=["name"],inplace=True,errors="ignore")

    # Normalización
    max_impacto = df_original['yt_score'].max()
    if max_impacto > 0:
        df_original['yt_score'] = df_original['yt_score'] / max_impacto
        
    return df_original

def C_estadisticas_youtube(minio):
    print('Obteniendo archivo')
    data = read_file(yt_statslist_file, minio)
    assert data, 'No se ha podido leer el archivo'

    data_filtrado = filtrado_por_clasificacion(data, minio)
    
    print('Transformando a dataframe')
    df = _transform_to_dataframe(data_filtrado)

    # Para la métrica de YT
    df_metrica = procesar_impacto_youtube(df)
    print('Guardando dataframe con métrica de YouTube')
    df_metrica.to_parquet(yt_stats_parquet_file)

    if minio["minio_write"]:
            if upload_to_minio(yt_stats_parquet_file):
                erase_file(yt_stats_parquet_file)

if __name__ == '__main__':
    C_estadisticas_youtube()