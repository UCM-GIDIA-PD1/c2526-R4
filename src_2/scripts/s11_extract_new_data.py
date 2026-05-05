import shutil
import pandas as pd
from src_2.config import popularity_parquet, prices_parquet, reviews_parquet
from src_2.io_manager import merge_and_save

from src_2.scripts.s01_appid_list_full import main as update_census
from src_2.scripts.s02_appid_list_sample import main as generate_sample
from src_2.scripts.s03_steam_details import main as extract_details
from src_2.scripts.s04_steam_reviews import main as extract_reviews
from src_2.scripts.s05_youtube_video_ids import main as youtube_video_ids
from src_2.scripts.s06_youtube_video_stats import main as youtube_video_stats
from src_2.scripts.s07_image_features import main as image_features
from src_2.scripts.s08_transform_popularity import main as transform_popularity
from src_2.scripts.s09_transform_prices import main as transform_prices
from src_2.scripts.s10_transform_reviews import main as transform_reviews

def prepare_version_paths(base_path):
    directory = base_path.parent
    filename = base_path.stem
    extension = base_path.suffix
    
    old_path = directory / f"{filename}_old{extension}"
    new_path = directory / f"{filename}_new{extension}"
    final_path = directory / f"{filename}_final{extension}"
    
    if base_path.exists():
        shutil.move(base_path, old_path)
        
    return old_path, new_path, final_path

def main():
    
    print("Iniciando pipeline completo")
    
    old_popularity, new_popularity, final_popularity = prepare_version_paths(popularity_parquet)
    old_prices, new_prices, final_prices = prepare_version_paths(prices_parquet)
    old_reviews, new_reviews, final_reviews = prepare_version_paths(reviews_parquet)
    for final_path, old_path in [(final_popularity, old_popularity), (final_prices, old_prices), (final_reviews, old_reviews)]:
        if final_path.exists():
            shutil.move(final_path, old_path)
            
    print("Ejecutando scripts de extracción")
    update_census()
    generate_sample()
    extract_details()
    extract_reviews()
    youtube_video_ids()
    youtube_video_stats()
    image_features()

    print("Ejecutando scripts de transformación")
    transform_reviews()
    transform_popularity()
    transform_prices()

    print("Generando versiones finales")
    
    if popularity_parquet.exists():
        shutil.move(popularity_parquet, new_popularity)
        merge_and_save(old_popularity, new_popularity, final_popularity, "id")

    if prices_parquet.exists():
        shutil.move(prices_parquet, new_prices)
        merge_and_save(old_prices, new_prices, final_prices, "id")

    if reviews_parquet.exists():
        shutil.move(reviews_parquet, new_reviews)
        merge_and_save(old_reviews, new_reviews, final_reviews, "appid")

    print("Pipeline finalizado")

if __name__ == "__main__":
    main()