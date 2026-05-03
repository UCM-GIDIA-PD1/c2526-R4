from src_2.config import appid_list_path
from src_2.extract.steam_api import get_appid_list
from src_2.io_manager import write_to_file
import requests

def main():
    session = requests.Session()
    appids = get_appid_list(session)
    write_to_file(appids, appid_list_path)

if __name__ == "__main__":
    main()