"""
Script que procesa el dataset de precios para reducir el número de variables. Se realizan las siguientes transformaciones:

    - Steam features: Se transforman las variables para indicar el número de features que aparecen en un juego, además se almacena el número de que cumplen en
      'num_steam_features'
    - Controller Support: Se transforman las variables relacionadas con el soporte a controles 0 si es completo, 1 si es parcial y 2 si no tiene.
    - Genres: Se agrupan los géneros por combinaciones formateado de la siguiente forma 'Genre1|Genre2|Genre3', se escogen las 50 combinaciones más comunes
      y se categoriza el resto como 'other'. Además se almacena el número de géneros totales que tiene un juego.

Output:
    precios_reducido.parquet
"""

from utils.utils import read_prices

def reducir_precios():
    df = read_prices()
    
    # Multiplayer
    multiplayer_columns = ['Multi-player', 'Online Co-op', 'Online PvP', 'PvP', 'Shared/Split Screen', 'Remote Play Together', 'Co-op']
    df["has_multiplayer"] = df[multiplayer_columns].max(axis=1)
    df["num_multiplayer_modes"] = df[multiplayer_columns].sum(axis=1)
    df.drop(columns=multiplayer_columns, inplace=True)
    
    # Steam features
    steam_functions = ['Steam Achievements', 'Steam Cloud', 'Steam Leaderboards', 'Steam Trading Cards']
    
    def steam_category(row):
        total = row[steam_functions].sum()
        if total == 0:
            return 0
        elif total == len(steam_functions):
            return 1
        else:
            return 2
    
    df["steam_features"] = df.apply(steam_category, axis=1)
    df["num_steam_features"] = df[steam_functions].sum(axis=1)
    df.drop(columns=steam_functions, inplace=True)
    
    # Controller support
    controller_columns = ['Full controller support', 'Partial Controller Support']
    
    def controller_map(row):
        if row['Full controller support'] == 1:
            return 0
        elif row['Partial Controller Support'] == 1:
            return 1
        else:
            return 2
    
    df["controller_support"] = df.apply(controller_map, axis=1)
    df.drop(columns=controller_columns, inplace=True)
    
    # Genres
    genre_cols = ['Action', 'Adventure', 'Casual', 'Indie', 'RPG', 'Simulation', 'Strategy']
    df["genres"] = df[genre_cols].apply(
        lambda row: "|".join([col for col in genre_cols if row[col] == 1]),
        axis=1
    )
    df["genres"] = df["genres"].replace("", "none")
    top_genres = df["genres"].value_counts().nlargest(50).index
    df["genres"] = df["genres"].where(df["genres"].isin(top_genres), "other")
    
    genre_cols = ['Action', 'Adventure', 'Casual', 'Early Access', 'Indie', 'RPG', 'Simulation', 'Strategy']
    df["num_genres"] = df[genre_cols].sum(axis=1)
    df.drop(columns=genre_cols, inplace=True)
    
    df.to_parquet('precios_reducido.parquet')


def main():
    reducir_precios()

if __name__ == "__main__":
    main()
