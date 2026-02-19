from utils.files import read_file, write_to_file, erase_file
import os

def handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Función que maneja la entrada. Por defecto la función siempre devuelve True.

    Args:
        mensaje (str): mensaje inicial. 
        isResponseValid (function): función que verifica la validez de un input dado.

    Returns:
        boolean: True si el input es correcto, false en caso contrario.
    """
    respuesta = input(initial_message).strip()

    # Hasta que no se dé una respuesta válida no se puede salir del bucle
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    
    return respuesta

def tratar_existe_fichero():
    """
    Menú con opción de añadir contenido al fichero existente o sobreescribirlo.
    
    returns:
        boolean: True si sobreescribir archivo meter appids nuevos, False en caso contrario
    """

    mensaje = """El fichero de lista de appids ya existe:\n\n1. Añadir contenido al fichero existente
2. Sobreescribir fichero\n\nIntroduce elección: """

    respuesta = handle_input(mensaje, lambda x: x in {"1", "2"})
    return True if respuesta == "2" else False

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
        
        if not datos_existentes:
            datos_existentes = []
            print("Formato inesperado en archivo existente. Se crearán datos desde cero.")
        
        datos_totales = datos_existentes + datos_nuevos
    else:
        datos_totales = datos_nuevos
    
    return datos_totales

def _save_final_sesion(jsonl_file, gzip_final_file, minio = False):
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
    
    if _save_final_sesion(ruta_temp_jsonl, gzip_final_file, minio):
        nuevo_inicio = ultimo_idx_guardado + 1 
        if nuevo_inicio > juego_fin:
            print("¡Rango completado!")
            #actualizar_configuracion(ruta_config, juego_fin + 1, juego_fin)
        else:
            #actualizar_configuracion(ruta_config, nuevo_inicio, juego_fin)
            print(f"Archivo guardado: {gzip_final_file}")
    else:
        print("No se generaron datos nuevos o hubo un error en el guardado final")