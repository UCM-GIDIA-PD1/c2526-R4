"""
Script para generar una muestra aleatoria de AppIDs a partir de la lista completa completo.
Evita seleccionar IDs que ya han sido procesados previamente en el archivo de detalles.
"""

import pandas as pd
from src_2.config import full_appid_list_path, steam_details_path, sample_appid_list_path, project_root
from src_2.extract.sampler import get_new_sample
from src_2.io_manager import read_file, write_to_file
from src_2.interface import handle_input

def main():
    print("--- Ejecutando s02_appid_list_sample.py ---")
    
    print("Cargando lista completa de AppIDs...")
    full_list = read_file(full_appid_list_path, default_return=[])
    if not full_list:
        print("Error: Lista vacia o no existe. Ejecuta primero el script s01_appid_list_full.py.")
        return
    
    print("Verificando juegos ya procesados...")
    processed_data = read_file(steam_details_path, default_return=pd.DataFrame())
    processed_ids = []

    if not processed_data.empty:
        processed_ids = processed_data["appid"].unique().tolist()


    size_input = handle_input("Introduce el tamaño de la muestra deseada: ", lambda x: x.isdigit())
    sample_size = int(size_input)

    print(f"Generando muestra aleatoria de {sample_size} juegos...")
    sample = get_new_sample(full_list, processed_ids, sample_size)

    if not sample:
        print("No hay nuevos AppIDs disponibles.")
        return

    write_to_file(sample, sample_appid_list_path)
    
    relative_path = sample_appid_list_path.relative_to(project_root())
    print(f"Muestra generada y guardada en: {relative_path}")
    print(f"Número de AppIDs en la lista: {len(sample)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Proceso cancelado por el usuario.")