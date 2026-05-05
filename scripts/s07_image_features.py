import os
import requests
import time
from tqdm import tqdm
from src_2.config import steam_details_path, steam_images_path, project_root, images_folder, get_files_by_pattern
from src_2.io_manager import read_first_file_found, write_to_file
from src_2.session import get_pending_work
from src_2.extract.image_processor import get_image_models, analyze_image_features

def main():
    print("--- Ejecutando s07_image_features.py ---")

    files = get_files_by_pattern(steam_details_path)
    games_info, file = read_first_file_found(files, [])

    if not games_info:
        print("Error: No se pudo cargar la información de los juegos.")
        return
    print(f"Juegos leídos de fichero: {file.name}")

    pending_games, current_output_path = get_pending_work(games_info, steam_images_path)

    if not pending_games:
        return

    print("Cargando modelos...")
    models_dict = get_image_models()
    
    session = requests.Session()
    img_dir = images_folder()

    try:
        for game in tqdm(pending_games, desc="Procesando imágenes", unit="juego"):
            appid = str(game.get("appid"))
            url = game.get("appdetails", {}).get("header_image")
            
            if not url: 
                continue
            
            img_path = img_dir / f"{appid}_header.jpg"

            if not img_path.exists():
                try:
                    res = session.get(url, timeout=10)
                    res.raise_for_status()
                    with open(img_path, "wb") as f:
                        f.write(res.content)
                except Exception as e:
                    tqdm.write(f"Error descargando imagen {appid}: {e}")
                    continue

            if img_path.exists():
                try:
                    features = analyze_image_features(img_path, models_dict)
                    result = {
                        "appid": appid, 
                        "image_features": features
                    }
                    write_to_file(result, current_output_path)
                except Exception as e:
                    tqdm.write(f"Error analizando imagen {appid}: {e}")

            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")
    finally:
        session.close()

    print(f"Finalizado. Datos en: {current_output_path.relative_to(project_root())}")

if __name__ == "__main__":
    main()