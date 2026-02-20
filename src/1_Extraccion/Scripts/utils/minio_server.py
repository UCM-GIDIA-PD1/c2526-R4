from minio import Minio
from minio.error import S3Error
from os import environ

def minio_client():
    return Minio(endpoint = "minio.fdi.ucm.es",
                access_key = environ.get("MINIO_ACCESS_KEY"),
                secret_key = environ.get("MINIO_SECRET_KEY"))

def upload_to_minio(filepath):
    """
    Guarda en MinIO el fichero que está en local en la ruta indicada.

    Args:
        filepath (str): Ruta del sistema de archivos.
    
    Returns:
        boolean: True si se ha guardado archivo correctamente, False en caso contrario.
    """
    client = minio_client()
    minio_path = f"grupo4/{filepath.name}"
    try:
        client.fput_object(bucket_name = "pd1", object_name = minio_path, file_path = filepath)
        print("Se ha subido el fichero correctamente")
        return True
    except Exception as e:
        print(f"Error de conexión con el servidor : {e}")
        return False

def download_from_minio(download_path, filename = None):
    """
    Descarga desde minio el fichero con el nombre especificado y lo guarda en data con el mismo nombre

    Args:
        download_path (str): Ruta donde se guardará el fichero
        filename (str): Nombre del fichero a descargar, si no se especifica se buscará el mismo nombre que filepath
    
    Returns:
        boolean: True si se ha descargado el archivo correctamente, False en caso contrario.
    """
    if not filename:
        filename = download_path

    client = minio_client()
    minio_path = f"grupo4/{filename.name}"
    try:
        client.fget_object(bucket_name = "pd1", object_name = minio_path, file_path = download_path)
        print("Se ha descargado el fichero correctamente")
        return True
    except S3Error as e:
        print(f"Error de MinIO : {e}")
        return False
    except Exception as e:
        print(f"Error de conexión con el servidor : {e}")
        return False
    