
import time
from tqdm import tqdm
from src_2.config import project_root, youtube_video_ids_path, steam_details_path
from src_2.extract.youtube_api import get_video_ids, new_configured_chromium_page, _parse_steam_date
from src_2.io_manager import write_to_file, read_file
from src_2.session import get_pending_work
from src_2.network.tor_manager import start_tor, renew_tor_identity

def main():
    print("--- Ejecutando s05_youtube_video_ids.py ---")
    games_info = read_file(steam_details_path, [])
    if not games_info:
        print("Error: No se pudo cargar la información de los juegos.")
        return
    
    pending_games, current_output_path = get_pending_work(games_info, youtube_video_ids_path)
    if not pending_games:
        print("No hay AppIDs pendientes por procesar en esta selección.")
        return
    print("Iniciando tor...")
    start_tor()
    session = new_configured_chromium_page()
    next_rotation = time.time() + 300
    
    try:
        for game in tqdm(pending_games, desc="Buscando videos", unit="juego"):
            if time.time() > next_rotation:
                session.quit()
                renew_tor_identity()
                session = new_configured_chromium_page()
                next_rotation = time.time() + 300

            app_details = game.get("appdetails", {})
            game_name = app_details.get("name")
            date_text = app_details.get("release_date", {}).get("date", "")
            release_date = _parse_steam_date(date_text)
            
            if not game_name or not release_date:
                continue

            video_ids = get_video_ids(session, game_name, release_date)
            full_data = {"appid": game.get("appid"), "video_ids": video_ids}
            write_to_file(full_data, current_output_path)

    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")
    finally:
        if session:
            session.quit()

    relative_path = current_output_path.relative_to(project_root())
    print(f"Proceso finalizado. Datos guardados en: {relative_path}")
if __name__ == "__main__":
    main()