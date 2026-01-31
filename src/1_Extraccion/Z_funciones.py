import json
import requests

def cargar_datos_locales(ruta_archivo):
    """
    Carga y decodifica un archivo JSON desde una ruta local.

    Args:
        ruta_archivo (str): La ubicación física del archivo en el sistema.

    Returns:
        dict | None: Los datos contenidos en el JSON convertidos a tipos de Python. 
        Retorna None si el archivo no se encuentra o si el contenido no es un JSON válido.
    """
    try:
        with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
            datos = json.load(archivo)
        return datos
    except FileNotFoundError:
        print(f"Error: El archivo en {ruta_archivo} no existe.")
        return None
    except json.JSONDecodeError:
        print("Error: El archivo no tiene un formato JSON válido.")
        return None

def guardar_datos_json(datos, ruta_archivo):
    """
    Guarda un diccionario en formato JSON en la ruta especificada.

    Args:
        datos (dict): Diccionario con la información a exportar.
        ruta_archivo (str): Ruta del sistema de archivos.
    
    Returns:
        None
    """
    with open(ruta_archivo, "w", encoding = "utf-8") as f:
        json.dump(datos, f, ensure_ascii = False, indent = 2)

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
    sesion.get(url, params=params_info)
    try:
        sesion.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("HTTP error occurred:", e)
        return
    except requests.exceptions.RequestException as e:
        print("A request error occurred:", e)
        return
    return sesion.json()