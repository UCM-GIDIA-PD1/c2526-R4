import pandas as pd
import numpy as np

from sklearn.preprocessing import KBinsDiscretizer

def clean_df(df, avoid_multicollinearity):
    """
    Limpia el dataframe eliminando columnas innecesarias y formateando tipos de datos.
    Opcionalmente aplica lógica para reducir la multicolinealidad.
    """
    df_clean = df.copy()
    erase_columns = ['id', 'name', 'v_resnet', 'v_convnext']

    df_clean = df_clean.dropna(subset=["num_juegos_previos_developers", "num_juegos_previos_publishers"], how="all")

    cols_devs = [
        "num_juegos_previos_developers", 
        "es_primer_juego_developers", 
        "ema_reviews_developers", 
        "max_historico_reviews_developers"
    ]

    cols_pubs = [
        "num_juegos_previos_publishers", 
        "es_primer_juego_publishers", 
        "ema_reviews_publishers", 
        "max_historico_reviews_publishers"
    ]

    filtro_devs = df_clean["num_juegos_previos_developers"].isna()
    filtro_pubs = df_clean["num_juegos_previos_publishers"].isna()

    df_clean.loc[filtro_devs, cols_devs] = df_clean.loc[filtro_devs, cols_pubs].values
    df_clean.loc[filtro_pubs, cols_pubs] = df_clean.loc[filtro_pubs, cols_devs].values
    
    if avoid_multicollinearity:
        # Sumamos las interacciones de video para tener una sola variable fuerte
        df_clean["commentCountTotal"] = df_clean.filter(like="video_statistics.commentCount").sum(axis=1)

        # Eliminamos variables altamente correlacionadas o redundantes
        erase_columns.extend([
            'num_juegos_previos_developers', 'es_primer_juego_developers', 
            'ema_reviews_developers', 'max_historico_reviews_developers',
            'num_juegos_previos_publishers', 'es_primer_juego_publishers', 
            'max_historico_reviews_publishers'
        ])
        
        cols_videos = df_clean.filter(like="video_statistics").columns
        erase_columns.extend(cols_videos)
    
    # Eliminamos solo aquellas columnas que realmente existan en el dataframe
    df_clean = df_clean.drop(columns=[col for col in erase_columns if col in df_clean.columns])

    # Convertimos los objetos a numéricos para evitar fallos en XGBoost
    obj_cols = df_clean.select_dtypes(include=['object']).columns
    for col in obj_cols:
        if col != 'v_clip':
            df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
    
    return df_clean.fillna(0)


def create_stratified_bins(y, n_bins=5, random_state=42):
    """
    Crea bins estratificados para la variable objetivo.
    Reserva el bin 0 para los fracasos (0 recomendaciones) y divide el resto
    en cuantiles para capturar la cola larga de los éxitos de forma equilibrada.
    """
    bins = np.zeros(len(y), dtype=int)
    mask_pos = y > 0
    
    if mask_pos.sum() > n_bins:
        kb = KBinsDiscretizer(n_bins=n_bins-1, encode='ordinal', strategy='quantile', random_state=random_state)
        bins[mask_pos] = kb.fit_transform(y[mask_pos].values.reshape(-1, 1)).flatten() + 1
        
    return bins