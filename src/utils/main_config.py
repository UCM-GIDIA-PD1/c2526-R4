from src.utils.dependences import appidlist_file_dependence, gamelist_file_dependence, youtube_scraping_file_dependence
from src.utils.dependences import steam_api_dependence, youtube_api_dependence, banners_file_dependence
from src.utils.dependences import steam_reviews_top100_file_dependence, steam_reviews_rest_file_dependence
from src.utils.dependences import yt_statslist_file_dependence, steam_reviews_file_dependence
from src.utils.dependences import steam_games_parquet_file_popularity_dependence, banners_file_popularity_dependence
from src.utils.dependences import yt_statsPCA_parquet_file_dependence
from src.utils.config import appidlist_file, gamelist_file, youtube_scraping_file, yt_statslist_file, P_banners_file
from src.utils.config import steam_reviews_file, banners_file, steam_reviews_top100_file, steam_reviews_rest_file
from src.utils.config import steam_games_parquet_file, yt_stats_parquet_file, yt_statsPCA_parquet_file
from src.utils.config import steam_reviews_parquet_file, popularity, prices

main_extraccion_info = {
        "A": {"fichero": "A_lista_juegos", 
              "salida": appidlist_file.name, 
              "ejecutable": "A_lista_juegos", 
              "usar": False, 
              "dependences" : [steam_api_dependence]
        },
        "B": {"fichero": "B_informacion_juegos", 
              "salida": gamelist_file.name, 
              "ejecutable": "B_informacion_juegos", 
              "usar": False, 
              "dependences" : [appidlist_file_dependence]
        },
        "C1": {"fichero": "C1_informacion_youtube_busquedas", 
               "salida": youtube_scraping_file.name, 
               "ejecutable": "C1_informacion_youtube_busquedas", 
               "usar": False, 
               "dependences" :[gamelist_file_dependence]
        },
        "C2": {"fichero": "C2_informacion_youtube_videos", 
               "salida": yt_statslist_file.name, 
               "ejecutable": "C2_informacion_youtube_videos", 
               "usar": False, 
               "dependences" : [youtube_api_dependence, youtube_scraping_file_dependence]
        },
        "D": {"fichero": "D_informacion_resenyas", 
              "salida": steam_reviews_file.name, 
              "ejecutable": "D_informacion_resenyas", 
              "usar": False, 
              "dependences" : [steam_reviews_top100_file_dependence, steam_reviews_rest_file_dependence]
        },
        "E": {"fichero": "E_metadatos_imagenes", 
              "salida": banners_file.name, 
              "ejecutable": "E_metadatos_imagenes", 
              "usar": False, 
              "dependences" : [gamelist_file_dependence]
        }
    }

main_transformacion_info = {
        "B": {"fichero": "B_games_info_transformacion", 
              "salida": steam_games_parquet_file.name, 
              "ejecutable": "B_games_info_transformacion", 
              "usar": False, 
              "dependences" : [gamelist_file_dependence]
        },
        "C": {"fichero": "C_estadisticas_youtube", 
              "salida": [yt_stats_parquet_file.name, yt_statsPCA_parquet_file.name], 
              "ejecutable": "C_estadisticas_youtube", 
              "usar": False, 
              "dependences" : [yt_statslist_file_dependence]
        },
        "D1": {"fichero": "D1_games_reviews_filter", 
              "salida": [steam_reviews_top100_file.name, steam_reviews_rest_file.name], 
              "ejecutable": "D1_games_reviews_filter", 
              "usar": False, 
              "dependences" : [gamelist_file_dependence]
        },
        "D2": {"fichero": "D2_limpieza_reviews", 
              "salida": steam_reviews_parquet_file.name, 
              "ejecutable": "D2_limpieza_reviews", 
              "usar": False, 
              "dependences" : [steam_reviews_file_dependence]
        },
        "E": {"fichero": "E_info_imagenes_transformacion", 
              "salida": P_banners_file.name, 
              "ejecutable": "info_imagenes_transformacion", 
              "usar": False, 
              "dependences" : [gamelist_file_dependence, banners_file_dependence]
        },
        "P": {"fichero": "P_crear_parquets_definitivos", 
              "salida": [popularity.name, prices.name], 
              "ejecutable": "crear_parquets", 
              "usar": False, 
              "dependences" : [steam_games_parquet_file_popularity_dependence, banners_file_popularity_dependence, 
                               yt_statsPCA_parquet_file_dependence]
        },
    }