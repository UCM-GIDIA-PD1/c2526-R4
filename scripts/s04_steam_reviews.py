"""
Script para extraer las reseñas de los juegos de Steam.
Los datos se utilizarán posteriormente para modelos de procesamiento de lenguaje natural (NLP).
"""

import requests
from tqdm import tqdm
from src_2.extract.steam_api import get_reviews
from src_2.io_manager import write_to_file, read_file
from src_2.config import sample_appid_list_path, steam_reviews_path, project_root
from src_2.session import get_pending_work

def main():
    print("--- Ejecutando s04_steam_reviews.py ---")
    
    sample_appid_list = read_file(sample_appid_list_path, default_return=[])
    if not sample_appid_list:
        print("Error: No se pudo cargar la muestra de AppIDs.")
        return

    pending_appids, current_output_path = get_pending_work(sample_appid_list, steam_reviews_path)
    
    if not pending_appids:
        print("No hay AppIDs pendientes por procesar en esta selección.")
        return

    session = requests.Session()

    try:
        for appid in tqdm(pending_appids, desc="Extrayendo reseñas", unit="juego"):
            reviews = get_reviews(session, str(appid), reviews_to_extract=50, filter_type="all")
            full_data = {"appid": appid, "reviews": reviews}
            write_to_file(full_data, current_output_path)
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")
    finally:
        session.close()

    relative_path = current_output_path.relative_to(project_root())
    print(f"Proceso finalizado. Datos guardados en: {relative_path}")
    
if __name__ == "__main__":
    main()