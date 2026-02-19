import json
import gzip
import pandas as pd
from os import remove, path, environ
from minio import Minio
from minio.error import S3Error
from utils.config import steam_log_file

def minio_client():
    return Minio(endpoint = "minio.fdi.ucm.es",
                access_key = environ.get("MINIO_ACCESS_KEY"),
                secret_key = environ.get("MINIO_SECRET_KEY"))

def log_appid_errors(appid, reason):
    data = {appid : reason}
    write_to_file(data, steam_log_file)

# Guardar datos a ficheros
def _save_json(data, filepath):
    with open(filepath, "wt", encoding = "utf-8") as f:
        json.dump(data, f, ensure_ascii = False)

def _save_json_gz(data, filepath):
    with gzip.open(filepath, "wt", encoding = "utf-8") as f:
        json.dump(data, f, ensure_ascii = False)

def _append_jsonl(data, filepath):
    with open(filepath, "at", encoding="utf-8") as f:
        if isinstance(data, list):
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

def _append_jsonl_gz(data, filepath):
    with gzip.open(filepath, "at", encoding="utf-8") as f:
        if isinstance(data, list):
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        else:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

def _save_parquet(data, filepath):
    pd.DataFrame(data).to_parquet(filepath)

def _save_txt(data, filepath):
    with open(filepath, "wt", encoding = "utf-8") as f:
        f.write(str(data))


# Cargar datos de ficheros existentes
def _read_json(filepath):
    with open(filepath, "rt", encoding="utf-8") as archivo:
        data = json.load(archivo)
        return data
    
def _read_json_gz(filepath):
    with gzip.open(filepath, "rt", encoding="utf-8") as archivo:
        data = json.load(archivo)
        return data

def _read_jsonl(filepath):
    with open(filepath, "rt", encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
        return data
    
def _read_jsonl_gz(filepath):
    with gzip.open(filepath, "rt", encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
        return data
 
def _read_parquet(filepath):
    data = pd.read_parquet(filepath)
    return data

def _read_txt(filepath):
    with open(filepath, "rt", encoding="utf-8") as f:
        data = f.read()
        return data

# Funciones publicas

def write_to_file(data, filepath, minio = False):
    """
    Guarda un diccionario en el formato indicado en la ruta especificada.

    Args:
        datos (dict): Diccionario con la información a exportar. (Lista de diccionarios en caso de ser un jsonl)
        filepath (str): Ruta del sistema de archivos.
        minio (bool): Activar para traer y guardar los datos en el servidor de MinIO
    
    Returns:
        boolean: True si se ha escrito en el archivo correctamente, false en caso contrario.
    """
    try:
        if filepath.suffix == ".json":
            _save_json(data, filepath)
        elif filepath.suffixes == [".json", ".gz"]:
            _save_json_gz(data, filepath)
        elif filepath.suffix == ".jsonl":
            _append_jsonl(data, filepath)
        elif filepath.suffixes == [".jsonl", ".gz"]:
            _append_jsonl_gz(data, filepath)
        elif filepath.suffix == ".parquet":
            _save_parquet(data, filepath)
        elif filepath.suffix == ".txt":
            _save_txt(data, filepath)
        else:
            print(f"File extension not supported: {filepath.name}")
            return
        
        if minio:
            client = minio_client()
            minio_path = f"grupo4/{filepath.name}"
            client.fput_object(bucket_name = "pd1", object_name = minio_path, file_path = filepath)

    except TypeError as e:
        # Ocurre cuando hay tipos no serializables (sets, objetos, etc.)
        print(f"Serialization error: {e}")
    except Exception as e:
        # Cualquier otro tipo de error
        print(f"Unexpected error occurred : {e}")

def read_file(filepath, minio = False, default_return = None):  # HACE FALTA CAMBIAR PARTE MINIO?
    """
    Carga y decodifica un archivo desde una ruta local.

    Args:
        filepath (str): La ubicación física del archivo en el sistema.
        minio (bool): Activar para traer los datos del servidor de MinIO

    Returns:
        dict | None: Los datos contenidos en el JSON convertidos a tipos de Python. 
        Retorna None si el archivo no se encuentra o si el contenido no es un JSON válido.
    """
    try:
        if minio:
            client = minio_client()
            minio_path = f"grupo4/{filepath.name}"
            client.fget_object(bucket_name = "pd1", object_name = minio_path, file_path = filepath)

        datos = default_return
        if filepath.suffix == ".json":
            return _read_json(filepath)
        elif filepath.suffixes == [".json", ".gz"]:
            return _read_json_gz(filepath)
        elif filepath.suffix == ".jsonl":
            return _read_jsonl(filepath)
        elif filepath.suffixes == [".jsonl", ".gz"]:
            return _read_jsonl_gz(filepath)
        elif filepath.suffix == ".parquet":
            return _read_parquet(filepath)
        elif filepath.suffix == ".txt":
            return _read_txt(filepath)
        else:
            print(f"File extension not supported: {filepath.name}")
        return datos
    except S3Error as e:
        print(f"Error de MinIO: {e}\n Se intentará leer el fichero localmente")
        return read_file(filepath)
    except FileNotFoundError:
        print(f"Error: File {filepath.name} does not exist.")
        return default_return
    except json.JSONDecodeError:
        print("Error: invalid JSON format.")
        return default_return
    except gzip.BadGzipFile:
        print("Error: invalid gzip.JSON format.")
        return default_return
    except Exception as e:
        print(f"Unexpected error occurred while reading {filepath.name}: {e}")
        return default_return

def erase_file(filepath):
    """
    Borra el archivo pasado por parámetro.

    Args:
        filepath (path): La ubicación física del archivo en el sistema.

    Returns:
        boolean: devuelve True si borra el archivo y False si no encuentra y no lo puede borrar.
    """
    if path.exists(filepath):
        remove(filepath)
        print(f"Archivo temporal eliminado: {filepath}")
        return True
    else:
        return False