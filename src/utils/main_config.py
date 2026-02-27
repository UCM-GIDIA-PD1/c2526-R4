from src.utils.dependences import appidlist_file_dependence, gamelist_file_dependence, youtube_scraping_file_dependence, steam_api_dependence, youtube_api_dependence, minio_dependence, ucm_vpn_dependence
from src.utils.config import appidlist_file, gamelist_file, youtube_scraping_file, yt_statslist_file, steam_reviews_file, banners_file

main_scripts_info = {
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
              "dependences" : [appidlist_file_dependence]
        },
        "E": {"fichero": "E_metadatos_imagenes", 
              "salida": banners_file.name, 
              "ejecutable": "E_metadatos_imagenes", 
              "usar": False, 
              "dependences" : [gamelist_file_dependence]}
    }