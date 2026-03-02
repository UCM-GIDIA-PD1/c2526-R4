from src.utils.files import read_file, write_to_file, file_exists
from src.utils.config import config_file, appidlist_file, gamelist_file, youtube_scraping_file, steam_reviews_top100_file, steam_reviews_rest_file, get_appid_range
import os

def read_config(script_id, default_return = None):
    """
    Lee el archivo de configuración y devuelve la información del script requerido.
        
    Args:
        script_id (str): identificador del script que llama a la función
        default_return (default None): es devuelto en caso de que no exista la key del script en config_info

    Returns:
        dict: campo asociado a la key script_id en config_info
    """
    if os.path.exists(config_file):
        config_info = read_file(config_file)
        return config_info.get(script_id, default_return)
    
    return default_return

def update_config(script_id, info):
    """
    Actualiza el campo de la key script_id en config_info.
    
    Args:
        script_id (str): identificador del script que llama a la función
        info (dict): contiene la información a actualizar en el campo correspondiente de config_info
    
    """
    # El config siempre se escribe en local
    if file_exists(config_file):
        config_info = read_file(config_file, default_return={})
        config_info[script_id] = info
        write_to_file(config_info, config_file)
        return
    
    config_info = {script_id : info}
    write_to_file(config_info, config_file)

def handle_input(initial_message, isResponseValid = lambda x: True):
    """
    Función que maneja la entrada. Por defecto la función siempre devuelve True.

    Args:
        initial_mensagge (str): mensaje inicial. 
        isResponseValid (function): función que verifica la validez de un input dado.

    Returns:
        boolean: True si el input es correcto, false en caso contrario.
    """
    respuesta = input(initial_message).strip()

    # Hasta que no se dé una respuesta válida no se puede salir del bucle
    while not isResponseValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    
    return respuesta

def ask_overwrite_file(message):
    """
    Menú con opción de añadir contenido al fichero existente o sobreescribirlo.
    
    Args:
        message (str): mensaje que se muestra en el método handle_input 
        
    Returns:
        boolean: True si sobreescribir archivo meter appids nuevos, False en caso contrario
    """

    respuesta = handle_input(message, lambda x: x in {"1", "2"})
    return True if respuesta == "2" else False

def _get_session_info(script_id):
    """
    Comprueba si hay una sesión de extracción abierta leyendo el config y retorna los parámetros de la sesión
    si así lo quiere el usuario.

    Args:
        script_id (str): mensaje que se muestra en el método handle_input
        
    Returns:
        bool: True si se quiere usar la sesión y False en caso contrario.
        int: start_idx.
        int: curr_idx.
        int: end_idx.
            
    """
    # Parámetros de B
    gamelist_info = read_config(script_id)
    # Si existe sesión
    if gamelist_info is not None:
        message = f"Existe sesión de extracción [{gamelist_info.get('start_idx')}, {gamelist_info.get('end_idx')}] índice actual: {gamelist_info.get('curr_idx')}, quieres continuar con la sesión? [Y/N]: "
        response = handle_input(message, lambda x: x.lower() in {"y", "n", ""})
        # si quiere usar los parámetros de la sesión existente
        if response.lower() == "y" or response.lower() == "":
            # devuelve los parámetros de la sesión y un booleano que indica la decsión del usuario
            start_idx, curr_idx, end_idx = gamelist_info["start_idx"], gamelist_info["curr_idx"], gamelist_info["end_idx"]
            return True, start_idx, curr_idx, end_idx
    # Si no hay sesión devuelve valores dummy
    return False, -1, -1 ,-1

def _get_script_file(script_id):
    if script_id in ["B"]:
        return appidlist_file
    elif script_id in ["C1","E"]:
        return gamelist_file
    elif script_id in ["D"]:
        return [steam_reviews_top100_file, steam_reviews_rest_file]
    else:
        return youtube_scraping_file
    
def get_pending_games(script_id, minio = {"minio_write": False, "minio_read": False}):
    """
    Devuelve lista con la información pedida del fichero necesario para
    el script con id: script_id. Además se encarga de la gestión de la
    información en los ficheros.
    
    Args:
        script_id (str): identificador del script que llama a la función
    
    Returns:
        file_list[] (array): array que contiene la información pedida a través
        de las distintas opciones ofrecidas
        start_idx (int): posición inicial del rango seleccionado
        curr_idx (int): posición por la que continuar la extracción en el rango seleccionado
        end_idx (int): posición final del rango seleccionado
    """
    # leer la lista del archivo necesario para el script con id script_id
    file = _get_script_file(script_id)
    # Para manejar distintos ficheros
    if isinstance(file, list):
        file_list = []
        for f in file:
            data = read_file(f, minio)
            if data:
                file_list.extend(data)
    else:
        file_list = read_file(file, minio)
    # inicializar indices dummy
    start_idx, curr_idx, end_idx = -1, -1, -1
    # si no hay lista de juegos devolver una lista vacía
    if file_list is None:
        return [], start_idx, curr_idx, end_idx 

    continue_session, start_idx, curr_idx, end_idx = _get_session_info(script_id)
    # si se quiere usar información de sesión existente
    if continue_session:
        return file_list[curr_idx:end_idx+1], start_idx, curr_idx, end_idx
    
    # si no se quiere usar sesión existente o no hay sesión existente
    print("Configurando nueva sesión...\n")
    # muestra rangos disponibles de la lista
    list_size =  len(file_list)
    print(f"Tamaño lista de juegos: {list_size}")
    print(f"Rango de índices disponibles: [0, {list_size-1}]")

    message = """Opciones: \n\n1. Elegir rango manualmente\n2. Extraer rango correspondiente al identificador\n
Introduce elección: """
    option = handle_input(message, lambda x: x in {"1", "2"})

    if option == "1": # Elegir rango manualmente
        def _isValidStart(response):
            return response.isdigit() and int(response) >= 0 and int(response) < list_size
        message = f"Introduce índice inicial [0, {list_size-1}]: "
        start_idx = int(handle_input(message,_isValidStart))
        curr_idx = start_idx

        def _isValidEnd(response):
            return response.isdigit() and int(response) >= start_idx and int(response) < list_size
        message = f"Introduce índice final [{start_idx}, {list_size-1}]: "
        end_idx = int(handle_input(message,_isValidEnd))
        
    elif option == "2": # usar rango del identificador, si no hay identificador, se hace completo
        start_idx, curr_idx, end_idx = get_appid_range(list_size)
    
    return file_list[curr_idx:end_idx+1], start_idx, curr_idx, end_idx

def overwrite_confirmation():
    """
    Sirve para evitar que el usuario borre sin querer (sobrescribir) el fichero de información
    ya existente.
    
    Returns:
        bool: devuelve True en caso afirmativo (y) y False en caso contrario (n)
    """
    message = "¿Seguro que quieres eliminar la lista de juegos con su información [Y/N]?: "
    response = handle_input(message, lambda x: x.lower() in {"y", "n", ""})
    return True if response.lower() == "y" or response.lower() == "" else False
