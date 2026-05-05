import pandas as pd
from src_2.config import (
    steam_details_path, steam_images_path, prices_parquet, 
    get_files_by_pattern, project_root
)
from src_2.io_manager import read_first_file_found, write_to_file
from src_2.transform.schemas import GENRES_SCHEMA, CATEGORIES_SCHEMA
from src_2.transform.features import calculate_entity_history
from src_2.transform.cleaners import parse_supported_languages, clean_entity_name, get_price_range, parse_steam_date 

def process_steam_prices_source(df_raw):
    """Aplana y limpia los datos de Steam enfocados a precios."""
    rows = []
    for _, row in df_raw.iterrows():
        details = row.get("appdetails") or {}
    
        raw_date = details.get("release_date", {}).get("date", "")
        clean_date_str = parse_steam_date(raw_date)
        
        price = details.get("price_overview", {}).get("initial", 0) / 100
        
        data = {
            "id": str(row["appid"]),
            "name": details.get("name"),
            "description_len": len(details.get("short_description", "")),
            "price_overview": price,
            "price_range": get_price_range(price),
            "num_languages": len(parse_supported_languages(details.get("supported_languages", ""))),
            "release_date": clean_date_str,
            "developers": clean_entity_name(details.get("developers")),
            "publishers": clean_entity_name(details.get("publishers")),
            "is_free": details.get("is_free", False)
        }
        
        genres = [g.get("description") for g in details.get("genres", [])]
        for g in GENRES_SCHEMA: data[g] = 1 if g in genres else 0
        
        cats = [c.get("description") for c in details.get("categories", [])]
        for c in CATEGORIES_SCHEMA: data[c] = 1 if c in cats else 0
        
        rows.append(data)
    return pd.DataFrame(rows)

def process_images_source(df_raw):
    """Aplana vectores de imágenes y normaliza nombres."""
    df_raw["id"] = df_raw["appid"].astype(str)
    df_flat = pd.json_normalize(df_raw["image_features"])
    df_flat = df_flat.rename(columns={"brightness": "brillo"})
    df_flat["id"] = df_raw["id"]
    return df_flat

def main():
    print("--- Ejecutando Transformación de Precios ---")

    print("Cargando archivos raw...")
    data_steam, _ = read_first_file_found(get_files_by_pattern(steam_details_path), [])
    data_img, _ = read_first_file_found(get_files_by_pattern(steam_images_path), [])

    print("Procesando fuentes...")
    df_steam = process_steam_prices_source(pd.DataFrame(data_steam))
    df_img = process_images_source(pd.DataFrame(data_img))

    df_steam = df_steam[(df_steam["is_free"] == False) & (df_steam["price_overview"] > 0)].copy()

    print("Realizando join...")
    df_final = df_steam.merge(df_img, on="id", how="left")

    print("Calculando historial de precios (EMA)...")
    df_final["release_date_dt"] = pd.to_datetime(df_final["release_date"], errors="coerce")

    df_final = df_final.sort_values("release_date_dt").reset_index(drop=True)
    
    df_final = calculate_entity_history(df_final, "developers", "price_overview", "precio")
    df_final = calculate_entity_history(df_final, "publishers", "price_overview", "precio")

    df_final["release_year"] = df_final["release_date_dt"].dt.year

    cols_to_drop = ["release_date", "release_date_dt", "developers", "publishers", "is_free"]
    df_final.drop(columns=cols_to_drop, inplace=True, errors="ignore")
    df_final = df_final.dropna().copy()

    write_to_file(df_final, prices_parquet)
    print(f"Finalizado. Parquet guardado con {len(df_final)} filas. En: {prices_parquet.relative_to(project_root())}")
if __name__ == "__main__":
    main()