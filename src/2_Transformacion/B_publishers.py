"""
Dado el fichero general con todos los datos de juegos de Steam 'games_info.jsonl.gz', extrae los datos de los publishers y los
developers de cada juego y crea 2 diccionarios para contar cuantas veces aparece cada uno, 'publisher_dict.json', 'developer_dict.json'.

Dependecncias:
    - games_info.jsonl.gz
"""

from src.utils.files import read_file, write_to_file
from src.utils.config import steam_publishers_count, steam_developers_count, gamelist_file
from collections import Counter

TASKS = [
    (steam_publishers_count, "publishers"),
    (steam_developers_count, "developers")
]

def _count_keys(key, raw_jsonl):
    """
    Dada una key de la lista de diccionarios de 'games_info.jsonl.gz' crea un contador que cuenta la cantidad de veces que aparece cada
    valor de la key en la lista de diccionarios.

    Args:
        key (str): Campo del diccionario
        raw_jsonl (list): Lista de diccionarios de 'games_info.jsonl.gz' 

    Returns:
        Counter (dict subclass): Contador de cada valor de key 
    """
    items_list = list()
    seen = set()
    repetidos = 0
    for line in raw_jsonl:
        if line["id"] in seen:
            repetidos += 1
            continue
        else:
            seen.add(line["id"])
        
        p = line["appdetails"].get(key)
        if p is None or not p:
            continue
        items_list.extend(p)
    print(f"Hay {repetidos} juegos repetidos")

    counts = Counter(items_list).most_common()
    return counts


if __name__ == '__main__':
    for file_path, key in TASKS:
        raw_jsonl = read_file(gamelist_file)
        counts =  _count_keys(key)
    
        print(type(counts))
        print(len(counts))

        write_to_file(counts, file_path)