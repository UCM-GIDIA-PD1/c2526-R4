"""
Modulo que proporciona funciones para extraer datos de Steam.
"""
from src_2.config import get_steam_api_key

from tqdm import tqdm

import time
import requests
from requests.exceptions import RequestException, JSONDecodeError

from datetime import datetime

def _parse_steam_date(date_str: str):
    """
    Convierte la fecha de texto de Steam a Unix timestamp.
    Maneja el formato '10 Oct, 2007'.
    """
    if not date_str or "Coming Soon" in date_str:
        return None
        
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    try:
        parts = date_str.replace(",", "").split()
        if len(parts) != 3:
            return None
            
        day = int(parts[0])
        month = months.get(parts[1])
        year = int(parts[2])
        
        if not month:
            return None
            
        dt = datetime(year, month, day)
        return int(dt.timestamp())
    except Exception:
        return None

def _request(session: requests.Session, url : str, params : dict | None, retries=3):
    for i in range(retries):
        try:
            response = session.get(url=url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except (RequestException, JSONDecodeError) as e:
            if i == retries - 1: raise e
            time.sleep(2 ** i)

# ----- Steam ----- #
def get_appid_list(session: requests.Session, appids_to_extract=1000000, last_appid=0):
    """
    Extrae una lista de AppIDs de Steam.

    Args:
        session: Sesión de requests.
        appids_to_extract: Cantidad máxima de IDs a obtener.
        last_appid: ID inicial para la búsqueda.

    Returns:
        list[str]: Lista de AppIDs extraídos.
    """

    API_KEY = get_steam_api_key()
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
    
    appid_list = []
    params = {"key": API_KEY, "last_appid": last_appid}

    with tqdm(total=appids_to_extract, desc="Extrayendo appids", unit="appids") as pbar:
        while appids_to_extract > 0:
            params["max_results"] = min(appids_to_extract, 50000)

            data = _request(session, url, params)
            resp_body = data.get("response", {})
            new_apps = resp_body.get("apps", [])

            if not new_apps:
                pbar.write("No se encontraron más aplicaciones.")
                break

            batch = [str(app["appid"]) for app in new_apps]
            appid_list.extend(batch)
            
            # Actualización de contadores
            num_extracted = len(batch)
            pbar.update(num_extracted)
            appids_to_extract -= num_extracted

            if not resp_body.get("have_more_results"):
                pbar.write("No hay más appids para extraer.")
                break

            params["last_appid"] = resp_body.get("last_appid")
            time.sleep(0.5)
            
    return appid_list

def test_get_appid_list():
    print("Test get_appid_list()--------------------")
    session = requests.Session()
    limit = 100

    try:
        result = get_appid_list(session, appids_to_extract=limit)
        
        assert isinstance(result, list), "El resultado debe ser una lista."
        assert isinstance(result[0], str), "Los elementos de la lista deben ser strings."
        
        print(f"Test exitoso: {result[:5]}...")
        
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.close()

def get_appdetails(session : requests.Session, appid : str):
    """
    Obtiene los detalles de una aplicación específica de Steam.

    Args:
        session: Sesión de requests.
        appid: ID de la aplicación.

    Returns:
        dict | None: Datos de la aplicación o None si no está disponible.
    """

    url = "https://store.steampowered.com/api/appdetails"
    params = {"appids": appid, "cc": "eur"}
    data = _request(session, url, params)

    if not data or not data.get(appid) or not data[appid].get("success"):
        return None
    
    return data[appid].get("data")

def test_get_appdetails():
    print("Test get_appdetails()--------------------")
    session = requests.Session()
    appid = "440"
    
    try:
        result = get_appdetails(session, appid)
        assert isinstance(result, dict), "El resultado debe ser un diccionario."
        print(f"Test exitoso: {result}")
        
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.close()

def get_reviews_first_month(session: requests.Session, appid: str, release_date: int):
    """
    Estima las reseñas positivas y negativas durante el primer mes tras el lanzamiento.

    Args:
        session: Sesión de requests.
        appid: ID de la aplicación.
        release_date: Fecha de lanzamiento (Unix timestamp).

    Returns:
        dict: Conteos estimados de reseñas positivas, negativas y totales.
    """
    url = f"https://store.steampowered.com/appreviewhistogram/" + appid
    data = _request(session, url, None)

    if not data or data.get("success") != 1:
        return {
            "positive_reviews_first_month": 0,
            "negative_reviews_first_month": 0,
            "total_reviews_first_month": 0
        }

    results = data.get("results", {})
    rollups = results.get("rollups", [])
    rollup_type = results.get("rollup_type", "week")

    SEC_DAY = 86400
    SEC_WEEK = 7 * SEC_DAY
    SEC_MONTH = 30 * SEC_DAY
    
    end_date = release_date + SEC_MONTH
    duration = SEC_MONTH if rollup_type == "month" else SEC_WEEK
    
    pos_total = 0.0
    neg_total = 0.0

    for rollup in rollups:
        rollup_start = rollup["date"]
        rollup_end = rollup_start + duration

        if rollup_start >= end_date:
            break

        if rollup_end <= release_date:
            continue

        overlap_start = max(rollup_start, release_date)
        overlap_end = min(rollup_end, end_date)
        overlap_duration = overlap_end - overlap_start

        if overlap_duration > 0:
            ratio = overlap_duration / duration
            pos_total += rollup["recommendations_up"] * ratio
            neg_total += rollup["recommendations_down"] * ratio

    return {
        "positive_reviews_first_month": int(pos_total),
        "negative_reviews_first_month": int(neg_total),
        "total_reviews_first_month": int(pos_total) + int(neg_total)
    }

def test_get_reviews_first_month():
    print("Test get_reviews_first_month()--------------------")
    # Para el juego Apex Legends, reseñas reales del primer mes (SteamDB): aprox 80K
    session = requests.Session()
    appid = "1172470"
    release_date = 1604530800
    try:
        result = get_reviews_first_month(session, appid, release_date)
        assert isinstance(result, dict), "El resultado debe ser un diccionario."
        print(f"Test exitoso: {result}")
        print(f"Total de reseñas predicho: {result['total_reviews_first_month']}, debería ser aproximadamente 80K para Apex Legends.")
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.close()

def get_reviews(session: requests.Session, appid: str, reviews_to_extract: int, 
                filter_type="recent", language="english", review_type="all"):
    """
    Extrae un número determinado de reseñas de Steam con filtros personalizables.
    Para más información sobre el comportamiento de los filtros, ver:
    https://github.com/Revadike/InternalSteamWebAPI/wiki/Get-App-Reviews
    Args:
        session: Sesión de requests.
        appid: ID de la aplicación.
        reviews_to_extract: Cantidad máxima de reseñas a obtener.
        filter_type: Criterio de ordenación ("all", "recent", "updated").
        language: Idioma de las reseñas (ej. "english", "spanish").
        review_type: Tipo de reseñas a filtrar ("all", "positive", "negative").

    Returns:
        list[dict]: Lista de diccionarios con los datos de las reseñas.
    """
    url = f"https://store.steampowered.com/appreviews/{appid}"
    extracted_reviews = []
    cursor = "*"
    
    with tqdm(total=reviews_to_extract, desc=f"Reviews {appid}", unit="reviews", leave=False) as pbar:
        while len(extracted_reviews) < reviews_to_extract:
            params = {
                "json": 1,
                "filter": filter_type,
                "language": language,
                "review_type": review_type,
                "num_per_page": 100,
                "cursor": cursor,
                "purchase_type": "all",
                "day_range": "all"
            }
            
            data = _request(session, url, params)
            
            if data.get("success") != 1:
                break

            batch = data.get("reviews", [])
            if not batch:
                break
                
            extracted_reviews.extend(batch)
            pbar.update(len(batch))
            
            new_cursor = data.get("cursor")
            if not new_cursor or new_cursor == cursor:
                break   
            
            cursor = new_cursor
            time.sleep(0.5)
            
    return extracted_reviews[:reviews_to_extract]

def test_get_reviews():
    print("Test get_reviews()--------------------")
    session = requests.Session()
    appid = "440"
    limit = 10
    
    try:
        result = get_reviews(session, appid, limit)
        
        assert isinstance(result, list), "El resultado debe ser una lista."
        assert isinstance(result[0], dict), "Cada reseña debe ser un diccionario."
        
        print(f"Test exitoso: {len(result)} reseñas obtenidas.")
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # test_get_appid_list()
    # test_get_appdetails()
    # test_get_reviews_first_month()
    test_get_reviews()
