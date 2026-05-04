"""
Script para extraer los detalles de los juegos de Steam, esto incluye información obtenida de appdetails y appreviewhistogram.
"""

import requests
from tqdm import tqdm
import random
import time
from src_2.extract.steam_api import get_appdetails, get_reviews_first_month, _parse_steam_date
from src_2.io_manager import write_to_file, read_file
from src_2.interface import handle_input
from src_2.config import sample_appid_list_path, steam_details_path, TOTAL_MEMBERS, project_root, get_extraction_id, get_filename
from src_2.extract.sampler import get_my_partition
from src_2.session import configure_extraction_session


def main():
    print("--- Ejecutando s03_steam_details.py ---")
    
    appids_to_extract, current_output_path = configure_extraction_session(sample_appid_list_path, steam_details_path)
    
    existing_data = read_file(current_output_path, default_return=[])
    processed_ids = {str(item.get("appid")) for item in existing_data}
    
    pending_appids = [str(appid) for appid in appids_to_extract if str(appid) not in processed_ids]
    
    if not pending_appids:
        print("No hay AppIDs pendientes por procesar en esta selección.")
        return

    print(f"Pendientes: {len(pending_appids)} | Ya procesados: {len(processed_ids)}")
    
    session = requests.Session()
    
    try:
        for appid in tqdm(pending_appids, desc="Extrayendo datos de Steam", unit="juego"):
            details = get_appdetails(session, appid)
            
            if not details:
                continue
                
            date_text = details.get("release_date", {}).get("date", "")
            release_timestamp = _parse_steam_date(date_text)
            
            reviews_stats = None

            if release_timestamp:
                reviews_stats = get_reviews_first_month(session, appid, release_timestamp)

            full_game_data = {
                "appid": appid,
                "appdetails": details,
                "reviews_first_month": reviews_stats
            }
            
            write_to_file(full_game_data, current_output_path)
            wait = random.uniform(1.7, 2.5)
            time.sleep(wait)    
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")
    finally:
        session.close()

    relative_path = current_output_path.relative_to(project_root)
    print(f"Proceso finalizado. Datos guardados en: {relative_path}")
    
if __name__ == "__main__":
    main()
