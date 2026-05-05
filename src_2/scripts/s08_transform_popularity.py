import pandas as pd
from src_2.config import steam_details_path, youtube_stats_path, steam_images_path, popularity_parquet, get_files_by_pattern, project_root
from src_2.io_manager import read_first_file_found, write_to_file
from src_2.transform.schemas import GENRES_SCHEMA, CATEGORIES_SCHEMA
from src_2.transform.features import calculate_entity_history, calculate_youtube_score
from src_2.transform.cleaners import parse_supported_languages, clean_entity_name, parse_steam_date

def process_steam_source(df_raw : pd.DataFrame):
    """Aplana y limpia los datos provenientes de Steam Details."""
    rows = []
    for _, row in df_raw.iterrows():
        details = row.get("appdetails") or {}
        rev_month = row.get("reviews_first_month") or {}

        raw_date = details.get("release_date", {}).get("date", "")
        clean_date_str = parse_steam_date(raw_date)
        data = {
            "id": str(row["appid"]),
            "name": details.get("name"),
            "recomendaciones_totales": rev_month.get("total_reviews_first_month", 0),
            "description_len": len(details.get("short_description", "")),
            "price_overview": details.get("price_overview", {}).get("initial", 0) / 100,
            "num_languages": len(parse_supported_languages(details.get("supported_languages", ""))),
            "release_date": clean_date_str,
            "developers": clean_entity_name(details.get("developers")),
            "publishers": clean_entity_name(details.get("publishers")),
        }
        
        genres = [g.get("description") for g in details.get("genres", [])]
        for g in GENRES_SCHEMA: data[g] = 1 if g in genres else 0
        
        cats = [c.get("description") for c in details.get("categories", [])]
        for c in CATEGORIES_SCHEMA: data[c] = 1 if c in cats else 0
        
        rows.append(data)
    return pd.DataFrame(rows)

def process_youtube_source(df_raw):
    """Aplana las estadísticas de los primeros 4 vídeos de YouTube."""
    yt_rows = []
    for _, row in df_raw.iterrows():
        yt_data = {"id": str(row["appid"])}
        for i, video in enumerate(row.get("video_statistics", [])[:4]):
            stats = video.get("video_statistics", {})
            for stat_name, val in stats.items():
                yt_data[f"video_{i}_video_statistics.{stat_name}"] = val
        yt_rows.append(yt_data)
    
    df = pd.DataFrame(yt_rows)

    stats_cols = [c for c in df.columns if "video_statistics" in c]
    for col in stats_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype("int64")
    
    return df

def process_images_source(df_raw):
    """Aplana vectores y renombra brightness a brillo."""
    df_raw["id"] = df_raw["appid"].astype(str)
    df_flat = pd.json_normalize(df_raw["image_features"])
    df_flat = df_flat.rename(columns={"brightness": "brillo"})
    df_flat["id"] = df_raw["id"]
    return df_flat


def main():
    print("--- Generando parquet de popularidad ---")

    print("Cargando archivos raw...")
    data_steam, _ = read_first_file_found(get_files_by_pattern(steam_details_path), [])
    data_yt, _ = read_first_file_found(get_files_by_pattern(youtube_stats_path), [])
    data_img, _ = read_first_file_found(get_files_by_pattern(steam_images_path), [])

    print("Procesando y aplanando dataframes...")
    df_steam = process_steam_source(pd.DataFrame(data_steam))
    df_yt = process_youtube_source(pd.DataFrame(data_yt))
    df_img = process_images_source(pd.DataFrame(data_img))


    print("Realizando join de tablas...")
    df_final = df_steam.merge(df_yt, on="id", how="left").fillna(0)
    df_final = df_final.merge(df_img, on="id", how="left")
    
    print("Calculando métricas (YT Score, EMA)...")
    df_final["yt_score"] = df_final.apply(calculate_youtube_score, axis=1)
    
    df_final["release_date_dt"] = pd.to_datetime(df_final["release_date"], errors="coerce")
    df_final = df_final.sort_values("release_date_dt").reset_index(drop=True)
    
    df_final = calculate_entity_history(df_final, "developers", "recomendaciones_totales", "reviews")
    df_final = calculate_entity_history(df_final, "publishers", "recomendaciones_totales", "reviews")

    df_final["release_year"] = df_final["release_date_dt"].dt.year
    df_final.drop(columns=["release_date", "release_date_dt", "developers", "publishers"], inplace=True)
    df_final = df_final.dropna().copy()

    write_to_file(df_final, popularity_parquet)
    print(f"Finalizado. Parquet guardado con {len(df_final)} filas. En: {popularity_parquet.relative_to(project_root())}")
if __name__ == "__main__":
    main()