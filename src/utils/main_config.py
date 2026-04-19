"""
Módulo que contiene la configuración del archivo main.py.
"""

import src.utils.dependences as dep
from src.utils.config import appidlist_file, gamelist_file, youtube_scraping_file, yt_statslist_file, P_banners_file
from src.utils.config import steam_reviews_file, banners_file, steam_reviews_top100_file, steam_reviews_rest_file
from src.utils.config import steam_games_parquet_file, yt_stats_parquet_file
from src.utils.config import steam_reviews_parquet_file, popularity, prices
from src.utils.config import popularidad_xgboost_file, popularidad_xgboost_log_file, popularidad_mlp_file
from src.utils.config import popularidad_linear_regression_file, popularidad_linear_regression_log_file, popularidad_knn_log_file
from src.utils.config import precios_xgboostumap_file, precios_mlp_file, precios_knncompleteclusters_file
from src.utils.config import precios_catboostClustered_file, precios_logistic_regression_file
from src.utils.config import reviews_logistic_regression_optuna_file, reviews_logistic_regression_gridsearch_file

main_extraccion_info = {
        "A": {"fichero": "A_lista_juegos", 
              "salida": appidlist_file.name, 
              "path": appidlist_file, 
              "ejecutable": "A_lista_juegos", 
              "usar": False, 
              "dependences" : [dep.steam_api_dependence]
        },
        "B": {"fichero": "B_informacion_juegos", 
              "salida": gamelist_file.name, 
              "path": gamelist_file, 
              "ejecutable": "B_informacion_juegos", 
              "usar": False, 
              "dependences" : [dep.appidlist_file_dependence]
        },
        "C1": {"fichero": "C1_informacion_youtube_busquedas", 
               "salida": youtube_scraping_file.name, 
               "path": youtube_scraping_file, 
               "ejecutable": "C1_informacion_youtube_busquedas", 
               "usar": False, 
               "dependences" :[dep.gamelist_file_dependence]
        },
        "C2": {"fichero": "C2_informacion_youtube_videos", 
               "salida": yt_statslist_file.name, 
               "path": yt_statslist_file, 
               "ejecutable": "C2_informacion_youtube_videos", 
               "usar": False, 
               "dependences" : [dep.youtube_api_dependence, dep.youtube_scraping_file_dependence]
        },
        "D": {"fichero": "D_informacion_resenyas", 
              "salida": steam_reviews_file.name, 
              "path": steam_reviews_file, 
              "ejecutable": "D_informacion_resenyas", 
              "usar": False, 
              "dependences" : [dep.steam_reviews_top100_file_dependence, dep.steam_reviews_rest_file_dependence]
        },
        "E": {"fichero": "E_metadatos_imagenes", 
              "salida": banners_file.name, 
              "path": banners_file, 
              "ejecutable": "E_metadatos_imagenes", 
              "usar": False, 
              "dependences" : [dep.gamelist_file_dependence]
        }
    }

main_transformacion_info = {
        "B": {"fichero": "B_games_info_transformacion", 
              "salida": steam_games_parquet_file.name, 
              "path": steam_games_parquet_file, 
              "ejecutable": "B_games_info_transformacion", 
              "usar": False, 
              "dependences" : [dep.raw_game_info_popularity_dependence, dep.raw_game_info_prices_dependence,
                               dep.gamelist_file_dependence]
        },
        "C": {"fichero": "C_estadisticas_youtube", 
              "salida": yt_stats_parquet_file.name, 
              "path": yt_stats_parquet_file, 
              "ejecutable": "C_estadisticas_youtube", 
              "usar": False, 
              "dependences" : [dep.yt_statslist_file_dependence, dep.raw_game_info_popularity_dependence]
        },
        "D1": {"fichero": "D1_games_reviews_filter", 
              "salida": [steam_reviews_top100_file.name, steam_reviews_rest_file.name], 
              "path": [steam_reviews_top100_file, steam_reviews_rest_file], 
              "ejecutable": "D1_games_reviews_filter", 
              "usar": False, 
              "dependences" : [dep.gamelist_file_dependence]
        },
        "D2": {"fichero": "D2_limpieza_reviews", 
              "salida": steam_reviews_parquet_file.name, 
              "path": steam_reviews_parquet_file, 
              "ejecutable": "D2_limpieza_reviews", 
              "usar": False, 
              "dependences" : [dep.steam_reviews_file_dependence]
        },
        "E": {"fichero": "E_info_imagenes_transformacion", 
              "salida": P_banners_file.name, 
              "path": P_banners_file, 
              "ejecutable": "info_imagenes_transformacion", 
              "usar": False, 
              "dependences" : [dep.popularity_dependence]
        },
        "P": {"fichero": "P_crear_parquets_definitivos", 
              "salida": [popularity.name, prices.name], 
              "path": [popularity, prices], 
              "ejecutable": "crear_parquets", 
              "usar": False, 
              "dependences" : [dep.steam_games_parquet_file_popularity_dependence, dep.banners_file_popularity_dependence, 
                               dep.yt_stats_parquet_file_dependence, dep.steam_games_parquet_file_prices_dependence, dep.banners_file_prices_dependence]
      },
}

main_modelos_info = {
    "A1": {"fichero": "Popularidad.xgboost", 
           "salida": popularidad_xgboost_file.name, 
           "path": popularidad_xgboost_file, 
           "ejecutable": "main1", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A2": {"fichero": "Popularidad.xgboost", 
           "salida": popularidad_xgboost_log_file.name, 
           "path": popularidad_xgboost_log_file, 
           "ejecutable": "main2", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A3": {"fichero": "Popularidad.mlp", 
           "salida": popularidad_mlp_file.name, 
           "path": popularidad_mlp_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A4": {"fichero": "Popularidad.linear_regression", 
           "salida": popularidad_linear_regression_file.name, 
           "path": popularidad_linear_regression_file, 
           "ejecutable": "main1", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A5": {"fichero": "Popularidad.linear_regression", 
           "salida": popularidad_linear_regression_log_file.name, 
           "path": popularidad_linear_regression_log_file, 
           "ejecutable": "main2", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A6": {"fichero": "Popularidad.knn", 
           "salida": popularidad_knn_log_file.name, 
           "path": popularidad_knn_log_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },
    "A": {"fichero": "Popularidad.Z_evaluacion", 
           "salida": None, 
           "path": None, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.popularity_dependence]
    },


    "B1": {"fichero": "Precios.xgboost", 
           "salida": precios_xgboostumap_file.name, 
           "path": precios_xgboostumap_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },
    "B2": {"fichero": "Precios.mlp", 
           "salida": precios_mlp_file.name, 
           "path": precios_mlp_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },
    "B3": {"fichero": "Precios.knn", 
           "salida": precios_knncompleteclusters_file.name, 
           "path": precios_knncompleteclusters_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },
    "B4": {"fichero": "Precios.xgboost", 
           "salida": precios_catboostClustered_file.name, 
           "path": precios_catboostClustered_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },
    "B5": {"fichero": "Precios.logistic_regression", 
           "salida": precios_logistic_regression_file.name, 
           "path": precios_logistic_regression_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },
    "B": {"fichero": "Precios.Z_evaluacion", 
           "salida": None, 
           "path": None, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.prices_dependence]
    },

    "C1": {"fichero": "Reviews.logistic_regression", 
           "salida": reviews_logistic_regression_optuna_file.name, 
           "path": reviews_logistic_regression_optuna_file, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.reviews_dependence]
    },
    "C": {"fichero": "Reviews.Z_evaluacion", 
           "salida": None, 
           "path": None, 
           "ejecutable": "main", 
           "usar": False, 
           "dependences": [dep.reviews_dependence]
    }
}