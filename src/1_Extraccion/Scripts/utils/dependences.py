from .files import file_exists
from .config import appidlist_file, gamelist_file, youtube_scraping_file
import os

class appidlist_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {appidlist_file.name} (script A)"
    
    @staticmethod
    def check(minio):
        return file_exists(appidlist_file, minio)
    
class gamelist_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {gamelist_file.name} (script B)"
    
    @staticmethod
    def check(minio):
        return file_exists(gamelist_file, minio)

class youtube_scraping_file_dependence():
    @staticmethod
    def get_info():
        return f"Fichero {youtube_scraping_file.name} (script C1)"
    
    @staticmethod
    def check(minio):
        return file_exists(youtube_scraping_file, minio)
    
class steam_api_dependence():
    @staticmethod
    def get_info():
        return "API de Steam"
    
    @staticmethod
    def check(minio):
        API_KEY = os.environ.get("STEAM_API_KEY")
        if API_KEY is None:
            return False
        else:
            return True

class youtube_api_dependence():
    @staticmethod
    def get_info():
        return "API de YouTube"
    
    @staticmethod
    def check(minio):
        API_KEY = os.environ.get("API_KEY_YT")
        if API_KEY is None:
            return False
        else:
            return True
    
class minio_dependence():
    @staticmethod
    def get_info():
        return "Claves (de acceso y secreta) de MinIO"
    
    @staticmethod
    def check(minio):
        API_KEY1 = os.environ.get("MINIO_ACCESS_KEY")
        API_KEY2 = os.environ.get("MINIO_SECRET_KEY")
        if API_KEY1 is None or API_KEY2 is None:
            return False
        else:
            return True