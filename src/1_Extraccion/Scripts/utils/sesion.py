from utils.files import read_file, write_to_file, erase_file
import os
from minio import Minio

def _get_extracted_data(jsonl_file, gzip_final_file):
    datos_nuevos = read_file(jsonl_file)
    if not datos_nuevos:
        print("No hay datos nuevos en el archivo temporal")
        erase_file(jsonl_file)
        return False

    # Si ya existe el archivo gz final o se ha traido desde el servidor.
    if os.path.exists(gzip_final_file):
        datos_existentes = read_file(gzip_final_file)
        if isinstance(datos_existentes, dict):
            datos_existentes = datos_existentes.get("data", [])
        
        if not datos_existentes: # NOTA: ¿es innecesario?
            datos_existentes = []
            print("Formato inesperado en archivo existente. Se crearán datos desde cero.")
        
        datos_totales = datos_existentes + datos_nuevos
    else:
        datos_totales = datos_nuevos
    
    return datos_totales

def minio_client():
    return Minio(endpoint = "minio.fdi.ucm.es",
                access_key = os.environ.get("MINIO_ACCESS_KEY"),
                secret_key = os.environ.get("MINIO_SECRET_KEY"))

def save_final_sesion(jsonl_file, gzip_final_file, minio = False): # IMPORTANTE: No sé cómo se hace lo de MinIO, que se encargue otro por fa
    """
    Borra un archivo jsonl pasando su contenido al json.gz especificado

    Args:
        jsonl_file (Path): Ruta del archivo jsonl temporal con los datos de la sesión
        gzip_final_file (Path): Ruta del archivo gz final donde se consolidarán los datos
        minio (bool): Activar para traer y guardar los datos en el servidor de MinIO
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        datos_totales = _get_extracted_data(jsonl_file, gzip_final_file)

        # Borramos los datos y nos aseguramos de que la lista de datos no esté vacía
        erase_file(jsonl_file)
        if not datos_totales:
            return False
        
        # Guardamos los datos extraídos
        dict_final = {"data": datos_totales}
        write_to_file(dict_final, gzip_final_file, minio)
        print(f"Datos guardados correctamente en {gzip_final_file}")
        return True
        
    except Exception as e:
        print(f"Error en guardar_sesion_final: {e}")
        return False

def cerrar_sesion(ruta_temp_jsonl, gzip_final_file, ruta_config, ultimo_idx_guardado, juego_fin, minio = False):
    """
    Cierra la sesión de extracción de datos: guarda datos temporales en un JSON comprimido, borra
    el archivo temporal y actualiza el archivo de configuración.

    Args:
        ruta_temp_jsonl (str): Ruta del archivo jsonl temporal con los datos de la sesión
        gzip_final_file (str): Ruta del archivo gz final donde se consolidarán los datos
        ruta_config (str): Ruta del archivo txt que describe la configuración usada
        ultimo_idx_guardado (int): ID de fila del último juego cargado
        juego_fin (int): Límite superior del archivo de configuración
    
    Returns:
        None
    """
    print("Cerrando sesión...")
    
    if save_final_sesion(ruta_temp_jsonl, gzip_final_file, minio):
        nuevo_inicio = ultimo_idx_guardado + 1 
        if nuevo_inicio > juego_fin:
            print("¡Rango completado!")
            #actualizar_configuracion(ruta_config, juego_fin + 1, juego_fin)
        else:
            #actualizar_configuracion(ruta_config, nuevo_inicio, juego_fin)
            print(f"Archivo guardado: {gzip_final_file}")
    else:
        print("No se generaron datos nuevos o hubo un error en el guardado final")