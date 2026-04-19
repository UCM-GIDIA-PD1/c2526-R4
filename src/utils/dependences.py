"""
Módulo de dependencias para informar al usuario las dependencias que tiene para la 
ejecución de ficheros.
"""

from .minio_server import file_exists_minio
from os import environ

from .files import file_exists
from .config import appidlist_file, gamelist_file, youtube_scraping_file, banners_file
from .config import steam_reviews_top100_file, steam_reviews_rest_file, yt_statslist_file
from .config import steam_reviews_file, steam_games_parquet_file_popularity, banners_file_popularity
from .config import yt_stats_parquet_file, steam_log_file, raw_game_info_popularity, raw_game_info_prices
from .config import banners_file_prices, steam_games_parquet_file, steam_games_parquet_file_prices
from .config import steam_reviews_parquet_file
from .config import P_banners_file, popularity, prices, reviews

# ------------ DEPENDENCIAS DE API ------------

class steam_api_dependence():
    @staticmethod
    def get_info():
        return "API de Steam"
    
    @staticmethod
    def check(minio = None):
        API_KEY = environ.get("STEAM_API_KEY")
        if API_KEY is None:
            return False
        else:
            return True

class youtube_api_dependence():
    @staticmethod
    def get_info():
        return "API de YouTube"
    
    @staticmethod
    def check(minio = None):
        API_KEY = environ.get("API_KEY_YT")
        if API_KEY is None:
            return False
        else:
            return True
    
class minio_dependence():
    @staticmethod
    def get_info():
        return "Claves (de acceso y secreta) de MinIO"
    
    @staticmethod
    def check(minio = None):
        API_KEY1 = environ.get("MINIO_ACCESS_KEY")
        API_KEY2 = environ.get("MINIO_SECRET_KEY")
        if API_KEY1 is None or API_KEY2 is None:
            return False
        else:
            return True
        
class ucm_vpn_dependence():
    @staticmethod
    def get_info():
        return "Estar conectado al wifi de la UCM o a la VPN"
    
    @staticmethod
    def check(minio = None):
        return file_exists_minio("grupo.txt")
    
class wandb_dependence():
    @staticmethod
    def get_info():
        return "Clave de W&B"
    
    @staticmethod
    def check(minio = None):
        API_KEY = environ.get("WANDB_API_KEY")
        if API_KEY is None:
            return False
        else:
            return True

# ------------ DEPENDENCIAS DE FICHEROS ------------

class appidlist_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {appidlist_file.name} (script A)"
    
    @staticmethod
    def check(minio):
        return file_exists(appidlist_file, minio)
    
class gamelist_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {gamelist_file.name} (script B)"
    
    @staticmethod
    def check(minio):
        return file_exists(gamelist_file, minio)

class youtube_scraping_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {youtube_scraping_file.name} (script C1)"
    
    @staticmethod
    def check(minio):
        return file_exists(youtube_scraping_file, minio)
    
class banners_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {banners_file.name} (script E)"
    
    @staticmethod
    def check(minio):
        return file_exists(youtube_scraping_file, minio)

class steam_reviews_top100_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_reviews_top100_file.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(steam_reviews_top100_file, minio)
    
class steam_reviews_rest_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_reviews_rest_file.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(steam_reviews_rest_file, minio)

class yt_statslist_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {yt_statslist_file.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(yt_statslist_file, minio)
    
class steam_reviews_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_reviews_file.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(steam_reviews_file, minio)

class steam_games_parquet_file_popularity_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_games_parquet_file_popularity.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(steam_games_parquet_file_popularity, minio)

class banners_file_popularity_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {banners_file_popularity.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(banners_file_popularity, minio)
    
class yt_stats_parquet_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {yt_stats_parquet_file.name}"
    
    @staticmethod
    def check(minio):
        return file_exists(yt_stats_parquet_file, minio)

class steam_log_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_log_file.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(steam_log_file, minio)

class raw_game_info_popularity_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {raw_game_info_popularity.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(raw_game_info_popularity, minio)

class raw_game_info_prices_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {raw_game_info_prices.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(raw_game_info_prices, minio)

class banners_file_prices_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {banners_file_prices.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(banners_file_prices, minio)

class steam_games_parquet_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_games_parquet_file.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(steam_games_parquet_file, minio)

class steam_games_parquet_file_prices_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_games_parquet_file_prices.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(steam_games_parquet_file_prices, minio)

class steam_reviews_parquet_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {steam_reviews_parquet_file.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(steam_reviews_parquet_file, minio)

class P_banners_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {P_banners_file.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(P_banners_file, minio)

class popularity_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {popularity.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(popularity, minio)

class prices_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {prices.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(prices, minio)

class reviews_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {reviews.name}"
    
    @staticmethod
    def check(minio = None):
        return file_exists(reviews, minio)