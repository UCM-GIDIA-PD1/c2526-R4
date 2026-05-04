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

def get_custom_range(max_len):
    def is_valid_range(text):
            parts = text.split(",")
            if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
                return False
            start, end = [int(p.strip()) for p in parts]
            return 0 <= start < end <= max_len
        
    mensaje = f"Indica el rango (formato 'inicio,fin' - mín {0}, máx {max_len}): "    # Comportamiento del slice de python, primer índice incluido, segundo excluido
    rango_str = handle_input(mensaje, is_valid_range)
    return[int(p.strip()) for p in rango_str.split(",")]

def get_extraction_config():
    """
    Determina los AppIDs a procesar y la ruta de guardado.
    """
    message = "Indica elección:\n\n1. Extraer datos del identificador\n2. Extraer todos los datos\n3. Rango personalizado\n\nIntroduce elección: "
    choice = handle_input(message, lambda x: x in {"1", "2", "3"})
    
    appids = read_file(sample_appid_list_path, default_return=[])
    max_len = len(appids)

    steam_details_file_name = get_filename(steam_details_path)
    if choice == "1":   # Extraer datos del identificador
        extraction_id = int(get_extraction_id())
        appids_to_extract = get_my_partition(appids, extraction_id, TOTAL_MEMBERS)
        path = steam_details_path.parent / f"{steam_details_file_name}_{extraction_id}.jsonl.gz"
    elif choice == "2": # Extraer todos los datos
        appids_to_extract = appids
        path = steam_details_path
    elif choice == "3": # Rango personalizado
        start_idx, end_idx = get_custom_range(max_len)
        appids_to_extract = appids[start_idx:end_idx]
        path = steam_details_path.parent / f"{steam_details_file_name}_{start_idx}_{end_idx}_custom.jsonl.gz"
    return appids_to_extract, path
def main():
    print("--- Ejecutando s03_steam_details.py ---")
    
    appids_to_extract, current_output_path = get_extraction_config()
    
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
