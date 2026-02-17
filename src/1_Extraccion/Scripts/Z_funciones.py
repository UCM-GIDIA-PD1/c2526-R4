import json
import requests
from datetime import datetime
import gzip
import pandas as pd
import os
from pathlib import Path

def proyect_root():
    return Path(__file__).resolve().parents[3]

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
        datos = None
        if ruta_archivo.suffix == ".json":
            with open(ruta_archivo, 'r', encoding='utf-8') as archivo:
                datos = json.load(archivo)
        elif ruta_archivo.suffixes == [".json", ".gz"]:
            with gzip.open(ruta_archivo, 'rt', encoding='utf-8') as archivo:
                datos = json.load(archivo)
        elif ruta_archivo.suffix == ".parquet":
            datos = pd.read_parquet(ruta_archivo)
        elif ruta_archivo.suffix == ".jsonl":
            with open(ruta_archivo, 'r', encoding='utf-8') as f:
                datos = [json.loads(linea) for linea in f if linea.strip()]
        else:
            print(f"Extension no soportada: {ruta_archivo}")
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
    except Exception as e:
        print(f"Error desconocido al cargar el archivo: {e}")
        return None

def guardar_datos_dict(datos, ruta_archivo):
    """
    Guarda un diccionario en el formato indicado en la ruta especificada.

    Args:
        datos (dict): Diccionario con la información a exportar. (Lista de diccionarios en caso de ser un jsonl)
        ruta_archivo (str): Ruta del sistema de archivos.
    
    Returns:
        None
    """
    try:
        if ruta_archivo.suffix == ".json":
            with open(ruta_archivo, "w", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False)
        elif ruta_archivo.suffixes == [".json", ".gz"]:
            with gzip.open(ruta_archivo, "wt", encoding = "utf-8") as f:
                json.dump(datos, f, ensure_ascii = False)
        elif ruta_archivo.suffix == ".parquet":
            pd.DataFrame(datos).to_parquet(ruta_archivo)
        elif ruta_archivo.suffix == ".jsonl":
            with open(ruta_archivo, 'a', encoding='utf-8') as f:
                f.write(json.dumps(datos, ensure_ascii=False) + '\n')
        else:
            print(f"Extension no soportada: {ruta_archivo}")
    except TypeError as e:
        # Ocurre cuando hay tipos no serializables (sets, objetos, etc.)
        print(f"Error de tipo en la serialización: {e}")
    except Exception as e:
        # Cualquier otro tipo de error
        print(f"Error inesperado: {e}")

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
        content_type = r.headers.get("content-type", "")
        if("application/json" not in content_type):
            print("The request does not return a json")
            return None
        return r.json()
    except requests.exceptions.HTTPError as e:
        print("Error HTTP:", e)
        return None
    except requests.exceptions.RequestException as e:
        print("Error de petición:", e)
        return None
    except ValueError as e:
        print("Fallo en decodificación JSON:",e)
        return None
    
def convertir_fecha_datetime(fecha_str):
    """Convierte una fecha de Steam a objeto datetime
    Args:
        fecha_str: La fecha como un string"
    
    Returns:
        datetime | None: Si no se puede convertir devuelve None
    """
    if not fecha_str: 
        return None

    # Todos las posibles formas de poner meses
    meses = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12
    }

    try:
        fecha_limpia = fecha_str.strip().lower().replace(',', '').replace('.', '')
        partes = fecha_limpia.split()

        if len(partes) == 1:
            partes = partes[0].split('-')
        
        if len(partes) != 3:
            return None

        dia = None
        mes = None
        anio = None

        # Si son todo numeros
        all_number = True
        for parte in partes:
            if not parte.isdigit():
                all_number = False

        if not all_number:
            for parte in partes:
                if parte in meses:
                    mes = meses[parte]
                
                elif parte.isdigit():
                    numero = int(parte)
                    
                    if numero >= 1900 and numero <= 2100:
                        anio = numero
                    elif numero >= 1 and numero <= 31:
                        dia = numero
        else:
             # Soporta YYYY-MM-DD y DD-MM-YYYY
            primero = int(partes[0])
            if primero >= 1900 and primero <= 2100:
                anio = primero
                mes = int(partes[1])
                dia = int(partes[2])
            else:
                dia = primero
                mes = int(partes[1])
                anio = int(partes[2])
            return datetime(anio, mes, dia)
        
        if anio and mes and dia:
                return datetime(anio, mes, dia)
        elif anio and mes:
            # Si solo tenemos mes y año, usar día 1
            return datetime(anio, mes, 1)
        elif anio:
            # Si solo tenemos año, usar 1 de enero
            return datetime(anio, 1, 1)
        else:
            return None
    except Exception:
        return None


def barra_progreso(iterable, total=None, keys=None):
    """Barra de progreso para meter a los bucles for.
    
    Args:
        iterable (iterable): Colección de elementos sobre la que se va a iterar.
        total (int, opcional): El número total de elementos. Necesario si el iterable 
            no tiene len() (como en enumerate).
        attrs (list, opcional): Lista de strings con los nombres de los atributos a mostrar.
    
    Returns:
        any: Los elementos del iterable original de forma secuencial.
    """
    if total is None:
        try:
            total = len(iterable)
        except TypeError:
            raise TypeError("El iterable no tiene longitud. Pasa el argumento 'total' manualmente.")

    def imprimir_barra(i, item=None, keys=None):
        porcentaje = int(100 * (i / total))
        llenado = int(50 * i // total)
        barra = '█' * llenado + '-' * (50 - llenado)

        info_extra = ""
        if item and keys:
            detalles = [f"{k}: {item.get(k, 'N/A')}" for k in keys]
            info_extra = " | " + " | ".join(detalles)

        print(f'\r\033[K{barra}| {porcentaje}%{info_extra}', end='', flush=True)

    imprimir_barra(0)
    for i, item in enumerate(iterable):
        yield item 
        imprimir_barra(i + 1, item, keys)
    print()

def convertir_fecha_steam(fecha_str):
    """
    Convierte fechas de Steam a formato 'YYYY-MM-DD'.
    Soporta múltiples formatos.

    Args:
        fecha_str (str): Fecha en formato 'DD Mon, YYYY'.

    Returns:
        str | None: La fecha en formato RFC 3339 ('YYYY-MM-DD')
        Retorna None si la fecha no se carga correctamente.
    """
    if not fecha_str:
        return None
    
    # Para pasar de formato mes -> mes_num
    meses = {
        'jan': '01', 'january': '01',
        'feb': '02', 'february': '02',
        'mar': '03', 'march': '03',
        'apr': '04', 'april': '04',
        'may': '05',
        'jun': '06', 'june': '06',
        'jul': '07', 'july': '07',
        'aug': '08', 'august': '08',
        'sep': '09', 'sept': '09', 'september': '09',
        'oct': '10', 'october': '10',
        'nov': '11', 'november': '11',
        'dec': '12', 'december': '12'
    }

    try:
        # Dividimos el string en partes
        limpia = fecha_str.strip().lower().replace(',', '').replace('.','')
        partes = limpia.split()

        if len(partes) == 1:
            partes = partes[0].split('-')
        
        if len(partes) not in [1, 2, 3]:
            return None

        dia = None
        mes = None
        anio = None

        # Si son todo numeros
        all_number = True
        for parte in partes:
            if not parte.isdigit():
                all_number = False

        if not all_number:
            for parte in partes:
                if parte in meses:
                    mes = meses[parte]
                    
                elif parte.isdigit():
                    numero = int(parte)
                        
                    if numero >= 1900 and numero <= 2100:
                        anio = str(numero)
                    elif numero >= 1 and numero <= 31:
                        dia = str(numero).zfill(2)
        else: # Soporta YYYY-MM-DD y DD-MM-YYYY
            primero = int(partes[0])
            if primero >= 1900 and primero <= 2100:
                anio = str(primero).zfill(2)
                mes = partes[1].zfill(2)
                dia = partes[2].zfill(2)
            else:
                dia = str(primero).zfill(2)
                mes = partes[1].zfill(2)
                anio = partes[2].zfill(2)
            return f"{anio}-{mes}-{dia}"


        if anio and mes and dia:
            return f"{anio}-{mes}-{dia}"
        elif anio and mes:
            # Si solo tenemos mes y año, usar día 1
            return f"{anio}-{mes}-01"
        elif anio:
            # Si solo tenemos año, usar 1 de enero
            return f"{anio}-01-01"
        else:
            return None

    except Exception as e:
        print(f"Error convirtiendo fecha '{fecha_str}': {e}")
        return None

def leer_configuracion(ruta_txt, longitud, identif):
    """Lee el inicio y fin de una sesión de scrapping desde un archivo de texto
    Los indices que se guardan corresponden a los de una lista, no corresponden con un appid concreto
    Si no existe el archivo se asigna la parte correspondiente a identif

    Args:
        ruta_txt: ruta del fichero de texto. Debe contener los datos en formato: 'index_inicial,index_final'
        identif: Parte de los datos que se va a extraer
        longitud: Numero de elementos del archivo
    
    Returns:
        Tupla de enteros con los valores de inicio y fin
    """
    # Si existe archivo 
    if os.path.exists(ruta_txt):
        try:
            with open(ruta_txt, 'r') as f:
                contenido = f.read().strip()
                partes = contenido.split(',')
                return int(partes[0]), int(partes[1])
        except Exception as e:
            print(f"Error leyendo txt: {e}. Se usarán valores por defecto.")
            return 0, 0
    
    # Si no existe archivo
    if identif is not None:
        assert identif.isdigit(), f"Error: El identificador no es un entero válido (valor actual: {identif})."
        int_identif = int(identif)
        assert 1 <= int_identif <= 6, f"El identificador debe estar entre 1 y 6 (valor actual: {identif})."

        bloque = longitud // 6
        inicio = (int_identif - 1) * bloque
    
        if int_identif == 6:
            fin = longitud - 1
        else:
            fin = (int_identif * bloque) - 1
    else:
        inicio = 0
        fin = longitud - 1

    actualizar_configuracion(ruta_txt, inicio, fin)            
    return inicio, fin

def actualizar_configuracion(ruta_txt, nuevo_inicio, mismo_fin):
    """Sobrescribe el archivo txt con el nuevo punto de partida
    
    Args:
        ruta_txt: ruta del fichero de texto
        nuevo_inicio (int): indice de inicio actualizado para la próxima sesión
        mismo_fin (int): el ultimo indice se mantiene igual
    
    Returns:
        None
    """
    try:
        with open(ruta_txt, 'w') as f:
            f.write(f"{nuevo_inicio},{mismo_fin}")
    except Exception as e:
        print(f"Error actualizando config: {e}")

def guardar_sesion_final(ruta_jsonl, ruta_final_gzip):
    """
    Borra un archivo jsonl pasando su contenido al json.gz especificado

    Args:
        ruta_jsonl (Path): Ruta del archivo jsonl temporal con los datos de la sesión
        ruta_final_gzip (Path): Ruta del archivo gz final donde se consolidarán los datos
    
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
        
        
        # Si ya existe el archivo gz final
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
            
            # Control de duplicados. Para confirmar que no se añaden datos duplicados al json.gz
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

def cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, ultimo_idx_guardado, juego_fin):
    """
    Cierra la sesión de extracción de datos: guarda datos temporales en un JSON comprimido, borra
    el archivo temporal y actualiza el archivo de configuración.

    Args:
        ruta_temp_jsonl (str): Ruta del archivo jsonl temporal con los datos de la sesión
        ruta_final_gzip (str): Ruta del archivo gz final donde se consolidarán los datos
        ruta_config (str): Ruta del archivo txt que describe la configuración usada
        ultimo_idx_guardado (int): ID de fila del último juego cargado
        juego_fin (int): Límite superior del archivo de configuración
    
    Returns:
        None
    """
    print("Cerrando sesión...")

    exito = guardar_sesion_final(ruta_temp_jsonl, ruta_final_gzip)
    
    if exito:
        nuevo_inicio = ultimo_idx_guardado + 1 
        if nuevo_inicio > juego_fin:
            print("¡Rango completado!")
            actualizar_configuracion(ruta_config, juego_fin + 1, juego_fin)
        else:
            actualizar_configuracion(ruta_config, nuevo_inicio, juego_fin)
        print(f"Archivo guardado: {ruta_final_gzip}")
    else:
        print("No se generaron datos nuevos o hubo un error en el guardado final")

def abrir_sesion(archivo_origen, archivo_final, requires_identif = True):
    """
    Generaliza la carga de datos para todos los scripts, devolviendo varios elementos necesarios para
    la ejecución de los mismos.

    Args:
        origin (str): Nombre del archivo de los datos origen sin extensión
        final (str): Nombre del archivo de los datos finales sin extensión

    Returns:
        juego_ini (int): Juego por el que se va a empezar a extraer datos
        juego_fin (int): Juego por el que se va a terminar de extraer datos
        juegos_pendientes (list): Lista de juegos que van a ser extraídos
        ruta_temp_jsonl (str): Ruta del archivo jsonl temporal con los datos de la sesión
        ruta_final_gzip (str): Ruta del archivo gz final donde se consolidarán los datos
        ruta_config (str): Ruta del archivo txt que describe la configuración usada
    """
    identif = os.environ.get("PD1_ID")
    
    # Rutas que van a ser usadas
    data_dir = proyect_root() / "data"
    ruta_origen = data_dir / archivo_origen
    if requires_identif:
        archivo_final = archivo_final.replace(".json.gz", f"_{identif}.json.gz")
    ruta_final_gzip = data_dir / archivo_final

    # Cargamos el JSON comprimido de la lista de appids
    lista_juegos = cargar_datos_locales(ruta_origen)
    if not lista_juegos:
        print("Error al cargar los juegos")
        return None, None, None, None, None, None

    # Cargamos los puntos de inicio y final
    ruta_config = data_dir / "config_rango.txt"
    idx_juego_ini, idx_juego_fin = leer_configuracion(ruta_config, len(lista_juegos), identif)

    ruta_temp_jsonl = data_dir / f"temp_session_{idx_juego_ini}_{idx_juego_fin}.jsonl"
    if os.path.exists(ruta_temp_jsonl):
        os.remove(ruta_temp_jsonl)

    # Juegos a procesar
    juegos_a_procesar = lista_juegos[idx_juego_ini : idx_juego_fin + 1]

    if not juegos_a_procesar:
        print("¡No queda nada pendiente en este rango!")
        cerrar_sesion(ruta_temp_jsonl, ruta_final_gzip, ruta_config, idx_juego_fin, idx_juego_fin)
        return None, None, None, None, None, None
    
    print(f"Sesión configurada: del índice {idx_juego_ini} al {idx_juego_fin}")

    return idx_juego_ini, idx_juego_fin, juegos_a_procesar, ruta_temp_jsonl, ruta_final_gzip, ruta_config

def log_fallos(appid, razon, ruta_jsonl = proyect_root() / "data" / "log_fallos.jsonl"):
    datos = {appid : razon}
    with open(ruta_jsonl, "a" , encoding="utf-8") as f:
        f.write(json.dumps(datos, ensure_ascii=False) + "\n")

def timestamp_a_fecha(timestamp):
    """
    Convierte un timestamp Unix a formato YYYY-MM-DD
    
    Args:
        timestamp (int): Timestamp Unix
    
    Returns:
        str: Fecha en formato YYYY-MM-DD
    """
    dt = datetime.fromtimestamp(timestamp)
    return f"{dt.year}-{str(dt.month).zfill(2)}-{str(dt.day).zfill(2)}"