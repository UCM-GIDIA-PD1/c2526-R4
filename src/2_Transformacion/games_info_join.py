import gzip
import json

filenames = []
for i in range(1, 7):
        filename = "games_info_" + str(i) + ".jsonl.gz"
        filenames.append(filename)

data = []
for filename in filenames:
        with gzip.open(filename, "rt", encoding="utf-8") as f:
                data.extend([json.loads(line) for line in f if line.strip()])

with gzip.open("games_info.jsonl.gz", "at", encoding="utf-8") as f:
        for j_son in data:
                f.write(json.dumps(j_son, ensure_ascii=False) + "\n")