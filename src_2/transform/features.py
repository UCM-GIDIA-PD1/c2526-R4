import pandas as pd
import numpy as np

def calculate_entity_history(df, group_col, value_col, prefix):
    """
    Calcula el historial (EMA, Max y Conteo).
    El df debe estar ordenado por fecha antes de llamar a esta función.
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
    """Calcula el impacto logarítmico de los vídeos de YouTube."""
    score_total = 0
    for i in range(4):
        v = float(row.get(f"video_{i}_video_statistics.viewCount", 0) or 0)
        l = float(row.get(f"video_{i}_video_statistics.likeCount", 0) or 0)
        c = float(row.get(f"video_{i}_video_statistics.commentCount", 0) or 0)
        
        if v > 0:
            sv = (0.5 * np.log10(v + 1)) + (0.3 * np.log10(l + 1)) + (0.2 * np.log10(c + 1))
            score_total += sv
    return score_total