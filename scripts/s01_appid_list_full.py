"""
Script para obtener la lista completa de AppIDs de Steam y guardarla en un archivo local.
No se extraerán los datos de todos los juegos de esta lista, sino que se usará para extraer una muestra.
"""

import requests
from src_2.config import full_appid_list_path, project_root
from src_2.extract.steam_api import get_appid_list
from src_2.io_manager import write_to_file


def main():
    print("--- Ejecutando s01_appid_list_full.py ---")
    sessionRequest = requests.Session()
    print("Obteniendo lista completa de AppIDs de Steam...")

    appids_to_extract = 200000 # por ahora no hay más de 200000 juegos en Steam
    last_appid = 0
    appid_list = get_appid_list(sessionRequest, appids_to_extract, last_appid)

    if not appid_list:
        print("No se pudo obtener la lista de AppIDs de Steam.")
        return
    
    write_to_file(appid_list, full_appid_list_path)

    relative_path = full_appid_list_path.relative_to(project_root())
    print(f"Lista completa de AppIDs de Steam obtenida y guardada en: {relative_path}")
    print(f"Número de AppIDs en la lista: {len(appid_list)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Proceso cancelado por el usuario.")