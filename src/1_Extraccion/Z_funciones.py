import json
import requests
from datetime import datetime
import gzip
import pandas as pd

def cargar_datos_locales(ruta_archivo):
    """
    Carga y decodifica un archivo desde una ruta local.

    Args:
        ruta_archivo (str): La ubicación física del archivo en el sistema.

    Returns:
        dict | None: Los datos contenidos en el JSON convertidos a tipos de Python. 
        Retorna None si el archivo no se encuentra o si el contenido no es un JSON válido.
    """
    try:
        if ruta_archivo.endswith('.json'):
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                datos = json.load(archivo)
            return datos
        elif ruta_archivo.endswith('.json.gzip'):
            with gzip.open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                datos = json.load(archivo)
            return datos
        elif ruta_archivo.endswith('.parquet'):
            datos = pd.read_parquet(ruta_archivo)
            return datos
    except FileNotFoundError:
        print(f"Error: El archivo en {ruta_archivo} no existe.")
        return None
    except json.JSONDecodeError:
        print("Error: El archivo no tiene un formato JSON válido.")
        return None
    except gzip.BadGzipFile:
        print("Error: El archivo no tiene un formato gzip.JSON válido.")
        return None
    except Exception:
        print("Error desconocido al cargar el archivo")
        return None

def guardar_datos_dict(datos, ruta_archivo):
    """
    Guarda un diccionario en el formato indicado en la ruta especificada.

    Args:
        datos (dict): Diccionario con la información a exportar.
        ruta_archivo (str): Ruta del sistema de archivos.
    
    Returns:
        None
    """
    try:
        if ruta_archivo.endswith('.json'):
            with open(ruta_archivo, "w", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False, indent = 2)
        elif ruta_archivo.endswith('.json.gzip'):
            with gzip.open(ruta_archivo, "w", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False, indent = 2)
        elif ruta_archivo.endswith('.parquet'):
            pd.DataFrame(datos).to_parquet(ruta_archivo)
    except TypeError as e:
        # Ocurre cuando hay tipos no serializables (sets, objetos, etc.)
        print(f"Error de tipo en la serialización: {e}")
    except Exception as e:
        # Cualquier otro tipo de error
        print(f"Error inesperado {e}")

def solicitud_url(sesion, params_info, url):
    """
    Realiza una petición GET a una URL específica utilizando una sesión.

    Args:
        sesion (requests.Session): Sesión de la librería requests para 
            'reciclar' la conexión.
        params_info (dict): Diccionario con los parámetros de consulta.
        url (str): Dirección URL del endpoint de la API.

    Returns:
        dict | None: Datos decodificados del JSON si la petición es exitosa. 
        Retorna None si ocurre un error de conexión o un estado HTTP erróneo.
    """
    try:
        r = sesion.get(url, params=params_info)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print("HTTP error occurred:", e)
        return
    except requests.exceptions.RequestException as e:
        print("A request error occurred:", e)
        return
    
def convertir_fecha_datetime(fecha_str):
    """Convierte una fecha de formato "21 Nov, 1998" a objeto datetime"""
    if not fecha_str: return None
    try:
        return datetime.strptime(fecha_str, "%d %b, %Y")
    except ValueError:
        return None
    
import sys

def barra_progreso(iterable):
    """
    Para tener una barra de carga fancy en la terminal en los bucles for.

    Args:
        iterable: elemento sobre el que se va a ejecutar el for.
    
    Returns:
        None
    """
    total = len(iterable)
    
    def imprimir_barra(iteracion):
        porcentaje = int(100 * (iteracion / total))
        llenado = int(50 * iteracion // total)
        barra = '█' * llenado + '-' * (50 - llenado)

        print(f'\r{barra}| {porcentaje}%', end='', flush=True)

    imprimir_barra(0)
    for i, item in enumerate(iterable):
        yield item 
        imprimir_barra(i + 1)
    print()