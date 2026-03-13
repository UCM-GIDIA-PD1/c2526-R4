from src.utils.files import read_file, write_to_file
from src.utils.config import steam_publishers_count, steam_developers_count, gamelist_file
from collections import Counter

tasks = [
    (steam_publishers_count, "publishers"),
    (steam_developers_count, "developers")
]

for file_path, key in tasks:
    raw_jsonl = read_file(gamelist_file)
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

    counts = Counter(items_list).most_common()
    print(type(counts))
    print(len(counts))
    print(f"Hay {repetidos} juegos repetidos")
    write_to_file(counts, file_path)