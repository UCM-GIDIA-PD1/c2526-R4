import pandas as pd
from tqdm import tqdm
from src_2.config import steam_reviews_path, reviews_parquet, project_root, get_files_by_pattern
from src_2.io_manager import read_first_file_found, write_to_file
from src_2.transform.cleaners import clean_review_text, detect_language

def main():
    print("--- Generando parquet de reseñas ---")

    files = get_files_by_pattern(steam_reviews_path)
    raw_data, source_file = read_first_file_found(files, default_return=[])
    if not raw_data:
        print("Error: No se encontraron datos en el archivo de reseñas.")
        return
    
    print(f"Reseñas cargadas de: {source_file.name}")

    rows = []
    for game in raw_data:
        appid = game.get("appid")
        reviews_list = game.get("reviews", [])
        for rev in reviews_list:
            rows.append({
                "appid": str(appid),
                "is_positive": rev.get("voted_up"),
                "weight": float(rev.get("weighted_vote_score", 0)),
                "text": rev.get("review", "")
            })

    df = pd.DataFrame(rows)

    print(f"Total de reseñas cargadas: {len(df)}")

    tqdm.pandas(desc="Limpiando texto")
    df["text"] = df["text"].progress_apply(clean_review_text)
    
    df = df[df["text"] != ""].copy()

    print("Detectando idiomas (tarda un rato)...")
    df["language"] = df["text"].progress_apply(detect_language)
    
    df_en = df[df["language"] == "en"].copy()

    write_to_file(df_en, reviews_parquet)

    print(f"Finalizado. Parquet guardado con {len(df_en)} reseñas en inglés. En: {reviews_parquet.relative_to(project_root())}")

if __name__ == "__main__":
    main()