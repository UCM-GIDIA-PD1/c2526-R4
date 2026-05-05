import pandas as pd
import numpy as np

def calculate_entity_history(df, group_col, value_col, prefix):
    """
    Calcula métricas históricas (conteo, EMA y máximo) para una entidad específica.

    Args:
        df: DataFrame de pandas ordenado cronológicamente.
        group_col: Columna por la que agrupar (ej. desarrollador).
        value_col: Columna numérica para calcular el historial.
        prefix: Prefijo para los nombres de las nuevas columnas.

    Returns:
        pd.DataFrame: DataFrame con las nuevas columnas de historial añadidas.
    """

    df[f"num_juegos_previos_{group_col}"] = df.groupby(group_col).cumcount()
    
    df[f"es_primer_juego_{group_col}"] = (df[f"num_juegos_previos_{group_col}"] == 0).astype(int)
    
    grupo = df.groupby(group_col)[value_col]
    
    df[f"ema_{prefix}_{group_col}"] = grupo.transform(
        lambda x: x.ewm(alpha=0.5, adjust=False).mean().shift(1)
    ).fillna(0)
    
    df[f"max_historico_{prefix}_{group_col}"] = grupo.transform(
        lambda x: x.expanding().max().shift(1)
    ).fillna(0)
    
    return df

def calculate_youtube_score(row):
    """
    Calcula una puntuación de impacto basada en las estadísticas de hasta cuatro vídeos de YouTube.

    Args:
        row: Fila de datos que contiene las métricas de visualizaciones, likes y comentarios.

    Returns:
        float: Puntuación total de impacto calculada.
    """
    score_total = 0
    for video_index in range(4):
        views = float(row.get(f"video_{video_index}_video_statistics.viewCount", 0) or 0)
        likes = float(row.get(f"video_{video_index}_video_statistics.likeCount", 0) or 0)
        comments = float(row.get(f"video_{video_index}_video_statistics.commentCount", 0) or 0)
        
        if views > 0:
            # Ponderación: 50% vistas, 30% likes, 20% comentarios
            score_video = (0.5 * np.log10(views + 1)) + \
                          (0.3 * np.log10(likes + 1)) + \
                          (0.2 * np.log10(comments + 1))
            score_total += score_video
            
    return score_total