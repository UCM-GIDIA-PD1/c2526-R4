from utils.files import read_file, write_to_file, erase_file
from utils.config import config_file
import os

def read_config(script_id, default_return = None):
    """
    Devuelve parámetros para Script A
    
    :return info_A (dict): Keys: 'last_appid', 'size'
    :return None: si no encuentra información o se produce error de lectura
    """
    if os.path.exists(config_file):
        config_info = read_file(config_file)
        return config_info.get(script_id, default_return)
    
    return default_return

def update_config(script_id, info):
    """
    Actualiza config con la información de A
    
    :param info (dict): diccionario con la nueva informacion para script A
    :return None:
    """
    if os.path.exists(config_file):
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

def tratar_existe_fichero(mensaje):
    """
    Menú con opción de añadir contenido al fichero existente o sobreescribirlo.
    
    returns:
        boolean: True si sobreescribir archivo meter appids nuevos, False en caso contrario
    """

    respuesta = handle_input(mensaje, lambda x: x in {"1", "2"})
    return True if respuesta == "2" else False