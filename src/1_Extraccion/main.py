import os
import sys
import importlib
from Scripts.utils.config import appidlist_file, gamelist_file, youtube_scraping_file, yt_statslist_file, steam_reviews_file, banners_file
from Scripts.utils.visuals import show_menu
from Scripts.utils.dependences import appidlist_file_dependence, gamelist_file_dependence, youtube_scraping_file_dependence, steam_api_dependence, youtube_api_dependence, minio_dependence

# Para que pueda usar los ficheros importados que están dentro de Scripts
sys.path.append(os.path.join(os.path.dirname(__file__), "Scripts"))

def ejecutar_scripts(scripts_info, minio_info):
    print("\n--- INICIANDO EJECUCIÓN ---")

    for clave, info in sorted(scripts_info.items()):
        if info["usar"]:
            print(f">> Importando y ejecutando {clave}: {info['fichero']}...")
            modulo = importlib.import_module(f"Scripts.{info['fichero']}")
            funcion = getattr(modulo, info["ejecutable"])
            minio = minio_info if minio_dependence.check(minio_info) else {"minio_write": False, "minio_read": False}
            funcion(minio)
            info["usar"] = False

    input("\nProceso terminado. Presiona Enter para volver al menú.")

def main():
    # Cuando tengamos el fichero de config general esto lo muevo ahí 
    minio_info = {"minio_write": False, "minio_read": False}
    scripts_info = {
        "A": {"fichero": "A_lista_juegos", "salida": appidlist_file.name, "ejecutable": "A_lista_juegos", "usar": False, "dependences" : [steam_api_dependence]},
        "B": {"fichero": "B_informacion_juegos", "salida": gamelist_file.name, "ejecutable": "B_informacion_juegos", "usar": False, "dependences" : [appidlist_file_dependence]},
        "C1": {"fichero": "C1_informacion_youtube_busquedas", "salida": youtube_scraping_file.name, "ejecutable": "C1_informacion_youtube_busquedas", "usar": False, "dependences" :[gamelist_file_dependence]},
        "C2": {"fichero": "C2_informacion_youtube_videos", "salida": yt_statslist_file.name, "ejecutable": "C2_informacion_youtube_videos", "usar": False, "dependences" : [youtube_api_dependence, youtube_scraping_file_dependence]},
        "D": {"fichero": "D_informacion_resenyas", "salida": steam_reviews_file.name, "ejecutable": "D_informacion_resenyas", "usar": False, "dependences" : [appidlist_file_dependence]},
        "E": {"fichero": "E_metadatos_imagenes", "salida": banners_file.name, "ejecutable": "E_metadatos_imagenes", "usar": False, "dependences" : [gamelist_file_dependence]}
    }

    while True:
        show_menu(scripts_info, minio_info)
        opcion = input("\nSelección > ").upper().strip()
        
        if opcion == "EXIT":
            break
        elif opcion == "RUN":
            ejecutar_scripts(scripts_info, minio_info)
        elif opcion == "MINIOS":
            minio_info["minio_write"] = not minio_info["minio_write"]
        elif opcion == "MINIOD":
            minio_info["minio_read"] = not minio_info["minio_read"]
        elif opcion in scripts_info:
            scripts_info[opcion]["usar"] = not scripts_info[opcion]["usar"]

if __name__ == "__main__":
    main()