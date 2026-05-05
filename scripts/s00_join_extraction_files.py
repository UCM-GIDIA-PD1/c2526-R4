from src_2.config import steam_details_path, steam_reviews_path, youtube_video_ids_path, youtube_stats_path, steam_images_path
from src_2.io_manager import consolidate_raw_parts

def main():
    print("Uniendo archivos de extracción")
    
    targets = [
        steam_details_path, 
        steam_reviews_path, 
        youtube_video_ids_path, 
        youtube_stats_path, 
        steam_images_path
    ]
    
    for target in targets:
        consolidate_raw_parts(target)
        print(f"Archivos unidos, guardados en: {target.name}")

if __name__ == "__main__":
    main()