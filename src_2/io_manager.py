"""
Módulo de lectura y escritura de ficheros.
- Lectura de ficheros: primero se intenta leer el fichero local, si no se encuentra se lee del MinIO
- Escritura de ficheros: se escribe en local. Se puede escribir en MinIO llamando a upload_file_to_minio
"""

import io
import json
import gzip
import pandas as pd
import joblib
from pathlib import Path
from minio import Minio

from src_2.config import get_minio_access_key, get_minio_secret_key, project_root

# -------------------- MinIO --------------------
def get_minio_client():
    """
    Inicializa y devuelve un cliente de MinIO configurado con las credenciales del sistema.

    Returns:
        Minio: Instancia del cliente de MinIO lista para su uso.
    """
    return Minio(
        endpoint="minio.fdi.ucm.es",
        access_key=get_minio_access_key(),
        secret_key=get_minio_secret_key(),
    )

def get_minio_path(filename: Path):
    """
    Calcula la ruta de destino en el servidor MinIO basándose en la ubicación del archivo dentro del proyecto.

    Args:
        filename: Objeto Path que indica la ubicación del archivo local.

    Returns:
        str: Cadena de texto con la ruta relativa formateada para el almacenamiento en la nube.
    """

    relative_path = filename.relative_to(project_root())
    return f"grupo4/{relative_path.as_posix()}"

def check_minio_connection():
    """
    Verifica la disponibilidad de la conexión con el servidor de MinIO.

    Returns:
        bool: True si la conexión es exitosa y las credenciales son válidas, False en caso contrario.
    """
    try:
        client = get_minio_client()
        client.list_buckets()
        return True
    except:
        return False

# -------------------- Escritura Local --------------------
def _save_json(data, filepath: Path, is_gz: bool = False):
    opener = gzip.open if is_gz else open
    with opener(filepath, "wt", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def _append_jsonl(data, filepath: Path, is_gz: bool = False):
    opener = gzip.open if is_gz else open
    with opener(filepath, "at", encoding="utf-8") as f:
        items = data if isinstance(data, list) else [data]
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def write_to_file(data, filepath: Path):
    ext = "".join(filepath.suffixes)
    try:
        if ext == ".json": 
            _save_json(data, filepath, False)
        elif ext == ".json.gz": 
            _save_json(data, filepath, True)
        elif ext == ".jsonl": 
            _append_jsonl(data, filepath, False)
        elif ext == ".jsonl.gz": 
            _append_jsonl(data, filepath, True)
        elif ext == ".parquet": 
            pd.DataFrame(data).to_parquet(filepath, index=False)
        elif ext == ".txt":
            with open(filepath, "wt", encoding="utf-8") as f: 
                f.write(str(data))
        elif ext == ".pkl": 
            joblib.dump(data, filepath)
        else:
            print(f"Extensión no soportada: {filepath.name}")
            return
    except TypeError as e:
        print(f"Error de serialización: {e}")
    except Exception as e:
        print(f"Error inesperado escribiendo {filepath.name}: {e}")

def merge_and_save(old_path: Path, new_path: Path, final_path: Path, id_col="id"):
    """
    Fusiona archivos parquet antiguos y nuevos eliminando duplicados por identificador.

    Args:
        old_path: Ruta del archivo previo.
        new_path: Ruta del archivo recién generado.
        final_path: Ruta de destino para el archivo unificado.
        id_col: Columna utilizada para identificar duplicados.
    """
    df_old = read_file(old_path, default_return=pd.DataFrame())
    df_new = read_file(new_path, default_return=pd.DataFrame())
    
    if df_old.empty:
        write_to_file(df_new, final_path)
        return

    df_final = pd.concat([df_new, df_old]).drop_duplicates(subset=[id_col], keep="first")
    write_to_file(df_final, final_path)
# -------------------- Subida MinIO --------------------
def upload_file_to_minio(filepath: Path):
    """
    Sube un archivo local al servidor MinIO manteniendo la estructura de carpetas del proyecto.

    Args:
        filepath: Objeto Path que indica la ubicación del archivo en el sistema local.

    Returns:
        bool: True si el archivo se subió correctamente, False si ocurrió un error o el archivo no existe.
    """
    if not filepath.exists():
        print(f"Error: El archivo {filepath.name} no existe localmente.")
        return False

    try:
        client = get_minio_client()
        minio_path = get_minio_path(filepath)

        client.fput_object(
            bucket_name="pd1",
            object_name=minio_path,
            file_path=str(filepath)
        )
        
        print(f"Archivo {filepath.name} subido correctamente a: {minio_path}")
        return True
    except Exception as e:
        print(f"Error al subir a MinIO: {e}")
        return False
    
# -------------------- Lectura Local --------------------
def _read_json(filepath: Path, is_gz: bool = False):
    opener = gzip.open if is_gz else open
    with opener(filepath, "rt", encoding="utf-8") as f:
        return json.load(f)

def _read_jsonl(filepath: Path, is_gz: bool = False):
    opener = gzip.open if is_gz else open
    with opener(filepath, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def read_file_local(filepath: Path, default_return=None):
    """
    Lee un archivo local detectando automáticamente su formato basándose en la extensión.

    Args:
        filepath: Objeto Path con la ubicación del archivo.
        default_return: Valor devuelto en caso de error o archivo inexistente.

    Returns:
        Contenido del archivo parseado o el valor por defecto.
    """

    if not filepath.exists():
        print(f"Archivo no encontrado: {filepath.name}")
        return default_return
        
    ext = "".join(filepath.suffixes)
    try:
        if ext == ".json": 
            return _read_json(filepath, False)
        elif ext == ".json.gz": 
            return _read_json(filepath, True)
        elif ext == ".jsonl": 
            return _read_jsonl(filepath, False)
        elif ext == ".jsonl.gz": 
            return _read_jsonl(filepath, True)
        elif ext == ".parquet": 
            return pd.read_parquet(filepath)
        elif ext == ".txt": 
            with open(filepath, "rt", encoding="utf-8") as f: 
                return f.read()
        elif ext == ".pkl": 
            return joblib.load(filepath)
        else:
            print(f"Extensión no soportada: {filepath.name}")
            return default_return     
    except (json.JSONDecodeError, gzip.BadGzipFile) as e:
        print(f"Error de formato en {filepath.name}: {e}")
        return default_return
    except Exception as e:
        print(f"Error inesperado leyendo {filepath.name}: {e}")
        return default_return

# -------------------- Lectura MinIO --------------------
def read_file_minio(filepath: Path, default_return=None):
    """
    Descarga y parsea un archivo desde MinIO directamente a la memoria RAM.

    Args:
        filepath: Objeto Path que indica la ruta del archivo.
        default_return: Valor devuelto si ocurre un error o el archivo no existe.

    Returns:
        Contenido del archivo procesado en el formato correspondiente o el valor por defecto.
    """

    ext = "".join(filepath.suffixes)
    response = None
    try:
        minio_client = get_minio_client()
        minio_path = get_minio_path(filepath)
        response = minio_client.get_object(bucket_name="pd1", object_name=minio_path)
        data_bytes = response.read()
        
        if ext == ".json":
            return json.loads(data_bytes.decode("utf-8"))
        elif ext == ".json.gz":
            return json.loads(gzip.decompress(data_bytes).decode("utf-8"))
        elif ext == ".jsonl":
            return [json.loads(line) for line in data_bytes.decode("utf-8").splitlines() if line.strip()]
        elif ext == ".jsonl.gz":
            lines = gzip.decompress(data_bytes).decode("utf-8").splitlines()
            return [json.loads(line) for line in lines if line.strip()]
        elif ext == ".parquet":
            return pd.read_parquet(io.BytesIO(data_bytes))
        elif ext == ".txt":
            return data_bytes.decode("utf-8")
        elif ext == ".pkl":
            return joblib.load(io.BytesIO(data_bytes))
        else:
            print(f"Extensión no soportada en MinIO: {ext}")
            return default_return

    except Exception as e:
        print(f"Error leyendo desde MinIO ({filepath.name}): {e}")
        return default_return
    finally:
        if response:
            response.close()
            response.release_conn()

# -------------------- Lectura General --------------------
def read_file(filepath: Path, default_return=None):
    """
    Lee un archivo buscando primero en el sistema local y, si no existe, en el servidor MinIO.

    Args:
        filepath: Objeto Path con la ubicación del archivo.
        default_return: Valor devuelto si el archivo no se encuentra en ninguna de las fuentes.

    Returns:
        Contenido del archivo procesado o el valor por defecto.
    """

    if filepath.exists():
        return read_file_local(filepath, default_return)
    
    if check_minio_connection():
        print(f"Archivo no encontrado: {filepath.name}, intentando leer desde MinIO")
        return read_file_minio(filepath, default_return)
    
    return default_return

def read_first_file_found(files: list[Path], default_return=None):
    """
    Busca y lee el primer archivo disponible de una lista de rutas proporcionada.

    Args:
        files: Lista de objetos Path para verificar secuencialmente.
        default_return: Valor devuelto si no se encuentra ningún archivo válido.

    Returns:
        tuple: Una tupla con el contenido del primer archivo leído y su objeto Path correspondiente.
    """
    for file in files:
        data = read_file(file, default_return)
        if data:
            return data, file
    return default_return, files[0]

def file_exists_minio(filename):
    """
    Comprueba si existe un fichero en el servidor de MinIO.

    Args:
        filename (Path): Nombre del fichero a a comprobar.
    
    Returns:
        boolean: True si existe, False en caso contrario.
    """
    client = get_minio_client()
    minio_path = get_minio_path(filename)

    try:
        client.stat_object(bucket_name="pd1", object_name=minio_path)
        return True
    except:
        return False

def file_exists(filepath):
    """
    Comprueba si un archivo existe en el sistema local o en el servidor MinIO.

    Args:
        filepath: Objeto Path con la ruta del archivo a verificar.

    Returns:
        bool: True si el archivo se encuentra en alguna de las fuentes, False en caso contrario.
    """
    return filepath.exists() or file_exists_minio(filepath)

