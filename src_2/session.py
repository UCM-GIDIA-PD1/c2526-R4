"""
Módulo para gestionar la configuración de las sesiones de extracción y el particionado de datos.
"""

from src_2.interface import handle_input
from src_2.config import TOTAL_MEMBERS, get_extraction_id
from src_2.extract.sampler import get_my_partition
from src_2.io_manager import read_file
from pathlib import Path

def _get_custom_range(max_len):
    """
    Gestiona la entrada del usuario para definir un rango de índices válido.
    """
    def is_valid_range(text):
        parts = text.split(",")
        if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
            return False
        start, end = [int(p.strip()) for p in parts]
        return 0 <= start < end <= max_len
        
    mensaje = f"Indica el rango (formato 'inicio,fin' - mín 0, máx {max_len}): "
    rango_str = handle_input(mensaje, is_valid_range)
    return [int(p.strip()) for p in rango_str.split(",")]

def configure_extraction_session(data_list : list, base_path : Path):
    """
    Configura la sesión de extracción determinando los elementos a procesar y la ruta de salida.

    Args:
        data_list: Lista de elementos a procesar (AppIDs, diccionarios, etc.).
        base_path: Objeto Path con la ruta del archivo de salida base.

    Returns:
        tuple: (lista_elementos_filtrada, ruta_salida_final)
    """
    message = (
        "\nIndica modo de extracción:\n\n"
        "1. Extraer datos según mi identificador\n"
        "2. Extraer todos los datos\n"
        "3. Rango personalizado\n\n"
        "Introduce elección: "
    )
    
    choice = handle_input(message, lambda x: x in {"1", "2", "3"})
    max_len = len(data_list)
    
    # Extraemos el nombre base del archivo (ej. 'steam_details.jsonl.gz' -> 'steam_details')
    file_extension = "".join(base_path.suffixes)
    file_base_name = base_path.name.replace(file_extension, "")
    
    if choice == "1": # Datos correpsondientes a identificador
        extraction_id = int(get_extraction_id())
        items_to_extract = get_my_partition(data_list, extraction_id, TOTAL_MEMBERS)
        output_path = base_path.parent / f"{file_base_name}_{extraction_id}{file_extension}"
        
    elif choice == "2": # Todos los datos
        items_to_extract = data_list
        output_path = base_path
        
    else: # Rango personalizado
        start_idx, end_idx = _get_custom_range(max_len)
        items_to_extract = data_list[start_idx:end_idx]
        output_path = base_path.parent / f"{file_base_name}_{start_idx}_{end_idx}{file_extension}"

    return items_to_extract, output_path

def get_pending_work(sample_list, base_path, id_key="appid"):
    """
    Configura la sesión de extracción y filtra los elementos que ya han sido procesados.

    Args:
        sample_list: Lista de elementos a procesar (IDs o diccionarios).
        base_path: Objeto Path con la ruta base del archivo de salida.
        id_key: Clave del diccionario que identifica al elemento (por defecto "appid").

    Returns:
        tuple: (lista_elementos_pendientes, ruta_salida_final)
    """

    to_extract, output_path = configure_extraction_session(sample_list, base_path)
    
    existing_data = read_file(output_path, default_return=[])
    
    processed_ids = {str(item.get(id_key)) for item in existing_data}
    
    pending = []
    for item in to_extract:
        current_id = str(item.get(id_key) if isinstance(item, dict) else item)
        if current_id not in processed_ids:
            pending.append(item)
            
    if not pending:
        print("No hay elementos pendientes por procesar en esta selección.")
    else:
        print(f"Pendientes: {len(pending)} | Ya procesados: {len(processed_ids)}")
        
    return pending, output_path