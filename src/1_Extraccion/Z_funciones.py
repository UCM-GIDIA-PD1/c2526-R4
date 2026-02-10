import json
import requests
from datetime import datetime
import gzip
import pandas as pd
import os

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
            with gzip.open(ruta_archivo, 'rt', encoding='utf-8') as archivo:
                datos = json.load(archivo)
            return datos
        elif ruta_archivo.endswith('.parquet'):
            datos = pd.read_parquet(ruta_archivo)
            return datos
        elif ruta_archivo.endswith('.jsonl'):
            datos = []
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                for linea in f:
                    if linea.strip():
                        datos.append(json.loads(linea))
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
        datos (dict | list(dict)): Diccionario con la información a exportar. (Lista de diccionarios en caso de ser un jsonl)
        ruta_archivo (str): Ruta del sistema de archivos.
    
    Returns:
        None
    """
    try:
        if ruta_archivo.endswith('.json'):
            with open(ruta_archivo, "w", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False, indent = 2)
        elif ruta_archivo.endswith('.json.gzip'):
            with gzip.open(ruta_archivo, "wt", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False, indent = 2)
        elif ruta_archivo.endswith('.parquet'):
            pd.DataFrame(datos).to_parquet(ruta_archivo)
        elif ruta_archivo.endswith('.jsonl'):
            with open(ruta_archivo, 'a', encoding='utf-8') as f:
                for d in datos:
                    f.write(json.dumps(d, ensure_ascii=False) + '\n')
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
    """Convierte una fecha de formato "21 Nov, 1998" a objeto datetime
    
    Args:
        fecha_str: La fecha en el formato string "%d %b, %Y"
    
    Returns:
        datetime | None: Si no se puede convertir devuelve None
    """
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

def leer_configuracion(ruta_txt):
    """Lee el inicio y fin de una sesión de scrapping desde un archivo de texto
    Los indices que se guardan corresponden a los de una lista, no corresponden con un appid concreto

    Args:
        ruta_txt: ruta del fichero de texto. Debe contener los datos en formato: 'index_inicial,index_final'
    
    Returns:
        Tupla de enteros con los valores de inicio y fin
    """
    try:
        with open(ruta_txt, 'r') as f:
            contenido = f.read().strip()
            partes = contenido.split(',')
            return int(partes[0]), int(partes[1])
    except Exception as e:
        print(f"Error leyendo txt: {e}. Se usarán valores por defecto.")
        return 0, 0

def actualizar_configuracion(ruta_txt, nuevo_inicio, mismo_fin):
    """Sobrescribe el archivo txt con el nuevo punto de partida
    
    Args:
        ruta_txt: ruta del fichero de texto
        nuevo_inicio: indice de inicio actualizado para la próxima sesión
        mismo_fin: el ultimo indice se mantiene igual
    """
    try:
        with open(ruta_txt, 'w') as f:
            f.write(f"{nuevo_inicio},{mismo_fin}")
    except Exception as e:
        print(f"Error actualizando config: {e}")

def guardar_sesion_final(ruta_jsonl, ruta_final_gzip):
    """
    Borra un archivo jsonl pasando su contenido al json.gzip especificado

    Args:
        ruta_jsonl (str): Ruta del archivo jsonl temporal con los datos de la sesión
        ruta_final_gzip (str): Ruta del archivo gzip final donde se consolidarán los datos
    
    Returns:
        bool: True si la operación fue exitosa, False en caso contrario
    """
    try:
        datos_nuevos = cargar_datos_locales(ruta_jsonl)
        
        if not datos_nuevos:
            print("No hay datos nuevos en el archivo temporal")
            if os.path.exists(ruta_jsonl):
                os.remove(ruta_jsonl)
            return False
        
        
        # Si ya existe el archivo gzip final
        if os.path.exists(ruta_final_gzip):
            datos_existentes = cargar_datos_locales(ruta_final_gzip)
            
            if datos_existentes is None:
                print("Error al cargar datos existentes. Se crearán desde cero.")
                datos_existentes = []
            else:
                if isinstance(datos_existentes, dict) and "data" in datos_existentes:
                    datos_existentes = datos_existentes["data"]
                else:
                    print("Formato inesperado en archivo existente. Se crearán datos desde cero.")
                    datos_existentes = []
            
            # Control de duplicados. Para confirmar que no se añaden datos duplicados al json.gzip
            ids_existentes = {juego.get("id") for juego in datos_existentes if isinstance(juego, dict)}
            datos_nuevos_filtrados = [j for j in datos_nuevos if j.get("id") not in ids_existentes]
            
            if len(datos_nuevos) != len(datos_nuevos_filtrados):
                print(f"Se omitieron {len(datos_nuevos) - len(datos_nuevos_filtrados)} juegos duplicados")
            
            datos_totales = datos_existentes + datos_nuevos_filtrados
        else:
            datos_totales = datos_nuevos
        
        dict_final = {"data": datos_totales}
        
        try:
            guardar_datos_dict(dict_final, ruta_final_gzip)
            print(f"Datos guardados correctamente en {ruta_final_gzip}")
        except Exception as e:
            print(f"Error al guardar datos finales: {e}")
            return False
        
        # Eliminar el archivo jsonl temporal
        if os.path.exists(ruta_jsonl):
            os.remove(ruta_jsonl)
            print(f"Archivo temporal eliminado: {ruta_jsonl}")
        
        return True
        
    except Exception as e:
        print(f"Error en guardar_sesion_final: {e}")
        return False
    