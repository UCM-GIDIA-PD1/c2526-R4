from src_2.config import appid_list_path
from src_2.extract.steam_api import get_appid_list
from src_2.io_manager import write_to_file, read_file
from src_2.interface import handle_input
import requests

def _get_last_appid():
    if not appid_list_path.exists():
        return 0
    appid_list = read_file(appid_list_path)
    return appid_list[-1]

def get_requests_params():
    message = """Elige modo de ejecución:\n\n1. Elegir manualmente el los parámetros\n2. Extraer nuevos juegos\nIntroduce elección: """
    response = handle_input(message, lambda x: x in {"1", "2"})
    if response == "1": # Elegir manualmente el los parámetros
        n_appids = int(handle_input("Numero de appids a extraer: ", lambda x: x.isdigit()))
        last_appid = handle_input("Appid desde el que extraer: ", lambda x: x.isdigit())
    elif response == "2": # Extraer nuevos juegos
        n_appids = 200000 # Por ahora hay menos de 200000 juegos en Steam
        last_appid = _get_last_appid()
    return n_appids, last_appid

def main():
    session = requests.Session()
    appids_to_extract, last_appid = get_requests_params()
    appids = get_appid_list(session, appids_to_extract, last_appid)
    write_to_file(appids, appid_list_path)

if __name__ == "__main__":
    main()