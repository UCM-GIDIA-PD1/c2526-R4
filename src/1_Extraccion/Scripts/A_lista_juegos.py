import os
from utils.config import appidlist_file_path, appidlist_info_path
from utils.files import read_file, write_to_file
from utils.steam_requests import get_appids


"""
Script que itera sobre la API de Steam y devuelve un JSON comprimido con n juegos y sus APPID.

Requisitos:
- Módulo 'requests'.
- Tener API de steam.

Información extra:
- max_results tiene por defecto 10000 juegos, pero se puede ajustar hasta 50000.
- Usamos el parámetro last_appid para indicar el último juego que se extrajo.

Entrada:
- Ninguna.

Salida:
- Los datos se almacenan en la el directorio indicado.
"""

def _handle_input(initial_message, _isValid = lambda x: True):
    respuesta = input(initial_message).strip()
    while not _isValid(respuesta):
        respuesta = input("Opción no válida, prueba de nuevo: ").strip()
    return respuesta

def _tratar_existe_fichero():
    """Devuelve booleano, si sobreescribir archivo meter appids nuevos"""

    mensaje = """El fichero de lista de appids ya existe:
    1. Añadir contenido al fichero existente
    2. Sobreescribir fichero
Introduce elección: """

    def _isValid(respuesta):
        valid_inputs ={"1", "2"}
        return respuesta in valid_inputs

    respuesta = _handle_input(mensaje, _isValid)
    
    return True if respuesta == "2" else False
    
def _parametros_de_request():
    mensaje = """Elige modo de ejecución:
    1. Elegir manualmente el los parámetros
    2. Extraer nuevos juegos
Introduce elección: """
    def _isValid(respuesta):
        valid_inputs ={"1", "2"}
        return respuesta in valid_inputs
    
    respuesta = _handle_input(mensaje, _isValid)
    n_appids = 0
    last_appid = 0

    def _isValid(respuesta):
        return respuesta.isdigit()
    
    if respuesta == "1":
        mensaje = "Número de appids a extraer: "
        
        n_appids = int(_handle_input(mensaje, _isValid))
        mensaje = "Appid desde el que hay que extraer: "
        last_appid = int(_handle_input(mensaje, _isValid))
    elif respuesta == "2":
        mensaje = "Número de appids nuevos a extraer: "
        n_appids = int(_handle_input(mensaje, _isValid))
        info = read_file(appidlist_info_path)
        if info is None:
            appid_list = read_file(appidlist_file_path)
            last_appid = appid_list[-1]
        else:
            last_appid = info["last_appid"]

    return int(n_appids), str(last_appid)


def A_lista_juegos():
    """
    Obtiene la lista completa de appids de los juegos de Steam

    Args:
        minio (bool): Activar para descargar los datos al servidor de MinIO en vez de en local
    
    Returns:
        None
    """
    data = []
    seen = set()
    if os.path.exists(appidlist_file_path):
        overwrite_file = _tratar_existe_fichero()
        if not overwrite_file:
            old_data = read_file(appidlist_file_path)
            data.extend(old_data)
            seen = set(data)

    n_appids, last_appid = _parametros_de_request()
    new_data = get_appids(n_appids, last_appid)
    for appid in new_data:
        if appid not in seen:
            data.append(appid)
            seen.add(appid)          
    
    write_to_file(data, appidlist_file_path)
    list_info = {"last_appid": data[-1]}
    write_to_file(list_info, appidlist_info_path)
    

if __name__ == "__main__":
    A_lista_juegos()
    