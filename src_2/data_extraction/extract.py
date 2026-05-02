"""
Modulo que proporciona funciones para extraer datos para el proyecto.
"""
from src_2.config import get_steam_api_key, get_youtube_api_key

from tqdm import tqdm
import requests

# ----- Steam ----- #
def get_appid_list(appids_to_extract=1000000, last_appid=0):
    API_KEY = get_steam_api_key()
    url = "https://api.steampowered.com/IStoreService/GetAppList/v1/"
    
    appid_list = []
    session = requests.Session()
    params = {"key": API_KEY, "last_appid": last_appid}

    with tqdm(total=appids_to_extract, desc="Extrayendo appids", unit="appids") as pbar:
        while appids_to_extract > 0:
            params["max_results"] = min(appids_to_extract, 50000)
            
            response = session.get(url=url, params=params)
            response.raise_for_status()
            data = response.json()

            resp_body = data.get("response")
            if not resp_body or "apps" not in resp_body:
                pbar.write("No se recibieron más aplicaciones o formato inválido.")
                break

            new_apps = resp_body["apps"]
            appid_list.extend([str(app["appid"]) for app in new_apps])
            
            num_extracted = len(new_apps)
            pbar.update(num_extracted)
            appids_to_extract -= num_extracted

            if not resp_body.get("have_more_results") or num_extracted == 0:
                print("No hay más appids para extraer.")
                break
            
            params["last_appid"] = resp_body.get("last_appid")

    return appid_list

def _test_get_appid_list():
    appids = get_appid_list(appids_to_extract=10, last_appid=0)
    print(appids)

def get_appdetails(session : requests.Session, appid):
    url = "https://store.steampowered.com/api/appdetails"

    params = {"appids": appid, "cc": "eur"}
    response = session.get(url=url, params=params)
    response.raise_for_status()
    data = response.json()

    if data.get(appid) is None or not data[appid].get("success", False):
        raise Exception("Appdeatils request with no content", appid)
    return data.get(appid).get("data")

def _test_get_appdetails():
    session = requests.Session()
    appdetails = get_appdetails("440", session)
    print(appdetails)

def get_appreviewhistogram(session : requests.Session, appid):
    
    url = "https://store.steampowered.com/appreviewhistogram/" + appid
        
    params_info = {"l": "english"}
    
    response = session.get(url=url, params=params_info)
    response.raise_for_status()
    data = response.json()

    if data.get("success") == 0 or data.get("results") is None or data["results"].get("rollups") is None:
        raise Exception("Appreviewhistogram request with no content", appid)
    return data.get("results")

def _test_get_appreviewhistogram():
    session = requests.Session()
    appreviewhistogram = get_appreviewhistogram("440", session)
    print(appreviewhistogram)

def get_reviews_first_month(session : requests.Session, appid, release_date):
    url = "https://store.steampowered.com/appreviewhistogram/" + appid
    
    response = session.get(url)
    response.raise_for_status()
    data = response.json()

    results = data.get('results', {})
    rollups = results.get('rollups', [])
    rollup_type = results.get('rollup_type', 'week')

    UN_MES_SEGUNDOS = 30 * 24 * 60 * 60
    end_date = release_date + UN_MES_SEGUNDOS

    total_reviews_primer_mes = 0

    for rollup in rollups:
        r_start = rollup['date']
        reviews_en_rollup = rollup['recommendations_up'] + rollup['recommendations_down']

        if rollup_type == 'month':
            r_end = r_start + UN_MES_SEGUNDOS 
        elif rollup_type == 'week':
            r_end = r_start + (7 * 24 * 60 * 60)
        else:
            raise ValueError(f"Rollup type {rollup_type} not supported")

        if r_end <= release_date:
            continue

        if r_start >= end_date:
            break

        effective_start = max(r_start, release_date)

        overlap_end = min(r_end, end_date)

        if overlap_end > effective_start:
            effective_duration = r_end - effective_start 
            overlap_duration = overlap_end - effective_start 
            if effective_duration > 0:
                ratio = overlap_duration / effective_duration
                total_reviews_primer_mes += (reviews_en_rollup * ratio)

    return int(total_reviews_primer_mes)

def _test_get__reviews_first_month():
    session = requests.Session()
    reviews_first_month = get_reviews_first_month(session, "1623730", 1705622400)
    print(reviews_first_month)

def get_reviews(session: requests.Session, appid, reviews_to_extract):
    url = f"https://store.steampowered.com/appreviews/" + appid
    
    extracted_reviews = []
    cursor = '*'
    
    while len(extracted_reviews) < reviews_to_extract:
        batch_size = min(100, reviews_to_extract - len(extracted_reviews))
        params = {
            'json': 1,
            'filter': 'recent',
            'language': 'english',
            'num_per_page': batch_size,
            'cursor': cursor,
            'purchase_type': 'all'
        }
        
        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get('success') != 1:
            print(f"Error devuelto por la API de Steam. Success: {data.get('success')}")
            break

        reviews_batch = data.get('reviews', [])
        
        if not reviews_batch:
            break
            
        extracted_reviews.extend(reviews_batch)
        new_cursor = data.get('cursor')
        if not new_cursor or new_cursor == cursor:
            break   
        cursor = new_cursor
        
    return extracted_reviews[:reviews_to_extract]

def _test_get_reviews():
    session = requests.Session()
    reviews = get_reviews(session, "1623730", 1)
    print(reviews)


if __name__ == "__main__":
    _test_get_reviews()

