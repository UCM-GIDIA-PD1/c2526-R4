from tqdm import tqdm
from src_2.config import youtube_stats_path, youtube_video_ids_path, project_root
from src_2.io_manager import read_file, write_to_file
from src_2.session import get_pending_work
from src_2.extract.youtube_api import process_game_youtube_data, get_youtube_service, REQUEST_LIMIT

def main():
    print("--- Ejecutando s06_youtube_video_stats.py ---")
    youtube_video_ids = read_file(youtube_video_ids_path, {})
    if not youtube_video_ids:
        print("Error: No se pudo cargar los el fichero de ids de videos.")
        return
    
    pending_games, current_output_path = get_pending_work(youtube_video_ids, youtube_stats_path)

    if not pending_games:
        print("No hay juegos pendientes por procesar en esta selección.")
        return
    
    try:
        for game in tqdm(pending_games, desc="Extrayendo estadísticas de videos", unit="juego"):
            service = get_youtube_service()
            result = process_game_youtube_data(game, service)
            write_to_file(result, current_output_path)
    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")
    finally:
        if service:
            service.close()

    relative_path = current_output_path.relative_to(project_root())
    print(f"Proceso finalizado. Datos guardados en: {relative_path}")
if __name__ == "__main__":
    main()

