import pandas as pd
from utils.files import read_file
from utils.config import banners_file_popularity, banners_file_prices, steam_games_parquet_file_popularity, steam_games_parquet_file_prices, prices, popularity, yt_statsPCA_parquet_file

def create_prices_parquet():
    df_B = pd.DataFrame(read_file(steam_games_parquet_file_prices))
    df_E = pd.DataFrame(read_file(banners_file_prices))

    df_E["id"] = df_E["id"].astype(str)

    df = pd.merge(df_B, df_E, on="id")

    df.dropna()
    df.to_parquet(prices)

def create_popularity_parquet():
    df_B = pd.DataFrame(read_file(steam_games_parquet_file_popularity))
    df_E = pd.DataFrame(read_file(banners_file_popularity))
    df_C = pd.DataFrame(read_file(yt_statsPCA_parquet_file))

    df_E["id"] = df_E["id"].astype(str)
    df_C["id"] = df_C["id"].astype(str)

    df = pd.merge(df_B, df_E, on = "id")
    df = pd.merge(df, df_C, on = ["id", "name"])

    df.dropna()
    df.to_parquet(popularity)

if __name__ == '__main__':
    create_popularity_parquet()
    create_prices_parquet()