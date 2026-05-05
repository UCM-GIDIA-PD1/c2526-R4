from tqdm import tqdm
from src_2.config import youtube_stats_path, youtube_video_ids_path, project_root, get_files_by_pattern
from src_2.io_manager import write_to_file, read_first_file_found
from src_2.session import get_pending_work
from src_2.extract.youtube_api import process_game_youtube_data, get_youtube_service, REQUEST_LIMIT

def main():
    print("--- Ejecutando s06_youtube_video_stats.py ---")
    possible_paths = get_files_by_pattern(youtube_video_ids_path)
    youtube_video_ids, file = read_first_file_found(possible_paths, [])
    if not youtube_video_ids:
        print("Error: No se pudo cargar la información de los juegos.")
        return
    print(f"Juegos leidos de fichero: {file.name}")
    
    pending_games, current_output_path = get_pending_work(youtube_video_ids, youtube_stats_path)

    if not pending_games:
        print("No hay juegos pendientes por procesar en esta selección.")
        return
    contador = 0
    try:
        service = get_youtube_service()
        for game in tqdm(pending_games, desc="Extrayendo estadísticas de videos", unit="juego"):
            try:
                
                result = process_game_youtube_data(game, service)
                write_to_file(result, current_output_path)
            except Exception as e:
                tqdm.write(f"Error al procesar el juego {game['appid']}: {e}")
                continue
            finally:
                contador += 1
                if contador > REQUEST_LIMIT:
                    tqdm.write("Limite de solicitudes alcanzado. Cerrando sesión.")
                    break

    except KeyboardInterrupt:
        print("\nProceso interrumpido por el usuario. Progreso guardado.")

    relative_path = current_output_path.relative_to(project_root())
    print(f"Proceso finalizado. Datos guardados en: {relative_path}")
if __name__ == "__main__":
    main()

