from src.utils.files import read_file, write_to_file
from src.utils.config import raw_data_path
from collections import Counter
path = raw_data_path() / "games_info.jsonl.gz"
publisher_path = raw_data_path() / "publisher_dict.json"
raw_jsonl = read_file(path)
publisher_list = list()
seen = set()
repetidos  = 0
for line in raw_jsonl:
    if line["id"] in seen:
        repetidos += 1
        continue
    else:
        seen.add(line["id"])
    p = line["appdetails"].get("publishers")
    if p is None or not p:
        continue
    publisher_list.extend(line["appdetails"].get("publishers"))

publisher_count = Counter(publisher_list)

publisher_count = publisher_count.most_common()
print(type(publisher_count))
print(len(publisher_count))
print(f"Hay {repetidos} juegos repetidos")
write_to_file(publisher_count, publisher_path)

