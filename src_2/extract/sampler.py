import random

def get_my_partition(data_list: list, member_id: int, total_members=6):
    """
    Obtiene la parte de una lista que corresponde a un miembro específico del equipo.

    Args:
        data_list: Lista completa de elementos a repartir.
        member_id: Identificador del miembro (1 a N).
        total_members: Número total de miembros en el equipo.

    Returns:
        list: Sublista con los elementos asignados al miembro.
    """
    start_index = member_id - 1
    return data_list[start_index::total_members]

def get_new_sample(full_list, processed_ids, sample_size=40000, seed=42):
    """
    Genera una muestra aleatoria de IDs que aún no han sido procesados.

    Args:
        full_list: Lista con los IDs disponibles.
        processed_ids: Lista de IDs que ya han sido completados.
        sample_size: Tamaño deseado para la nueva muestra.
        seed: Semilla para reproducibilidad.

    Returns:
        list: Lista con la muestra de IDs pendientes.
    """
    available_ids = list(set(full_list) - set(processed_ids))
    
    if not available_ids:
        return []

    random.seed(seed)
    
    actual_size = min(len(available_ids), sample_size)
    return random.sample(available_ids, k=actual_size)