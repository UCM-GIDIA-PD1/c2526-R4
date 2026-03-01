import gzip
import json
from src.utils.config import members, raw_data_path
from src.utils.files import write_to_file


def get_filename(filestart):
    return [f"{filestart}_{id}.jsonl.gz" for id in range(1,members+1)]

def files_content(files):
    data = []
    for file in files:
        path = raw_data_path() / file
        with gzip.open(path, "rt", encoding="utf-8") as f:
            data.extend([json.loads(line) for line in f if line.strip()])
    return data



if __name__ == "__main__":
    try:
        filestart = input("Introduce nombre del fichero: ") # el comienzo del fichero, por ejemplo games_info_5.jsonl.gz --> games_info
        files = get_filename(filestart)
        data = files_content(files)
        path = raw_data_path() / f"{filestart}.jsonl.gz"
        write_to_file(data, path)
    except:
        print("Error al unir ficheros")