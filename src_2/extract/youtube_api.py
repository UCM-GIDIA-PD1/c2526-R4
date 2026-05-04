
from DrissionPage import ChromiumPage, ChromiumOptions
from googleapiclient.discovery import build
from random import choice, randint
from src_2.config import BROWSER_PATH, USER_AGENTS, COMMON_RESOLUTIONS, TOR_SOCKS_PROXY, get_youtube_api_key
from src_2.network.tor_manager import start_tor
from datetime import datetime

def _parse_steam_date(date_str: str):
    """
    Convierte la fecha de texto de Steam al formato 'YYYY-MM-DD'.
    Maneja el formato '10 Oct, 2007'.
    """
    if not date_str or "Coming Soon" in date_str or "To be announced" in date_str:
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
        
        return dt.strftime("%Y-%m-%d")
        
    except Exception:
        return None
    
# --- SECCIÓN 1: SCRAPING (DrissionPage + TOR) ---
def new_configured_chromium_page():
    """
    Configura y devuelve una nueva instancia de ChromiumPage con proxy TOR.
    """
    co = ChromiumOptions()
    
    co.set_browser_path(BROWSER_PATH)
    co.set_user_agent(choice(USER_AGENTS))
    co.set_argument(f'--proxy-server={TOR_SOCKS_PROXY}')
    co.set_argument('--password-store=basic')
    
    ancho, alto_base = choice(COMMON_RESOLUTIONS)
    alto = alto_base + randint(-20, 0)
    co.set_argument(f"--window-size={ancho},{alto}")

    return ChromiumPage(co)

def get_video_ids(session: ChromiumPage, game_name: str, date: str):
    """
    Busca IDs de vídeos en YouTube filtrando por nombre de juego y fecha.
    Importante: la sesión que recibe debe estar configurada con TOR.\n
    start_tor()\n 
    session = new_configured_chromium_page()
    Args:
        session: Sesión de ChromiumPage.
        game_name: Nombre del juego.
        date: Fecha límite de búsqueda (YYYY-MM-DD).

    Returns:
        list[dict]: Lista de IDs de vídeos encontrados.
    """

    query = f"%22{game_name.replace(" ", "+")}%22+Steam+game+before:{date}"
    url = f"https://www.youtube.com/results?search_query={query}&sp=CAM%253D"

    session.get(url)
    
    try:
        results_container = session.ele("tag:ytd-two-column-search-results-renderer")
        video_elements = results_container.eles("tag:ytd-video-renderer")
        video_ids = []
        
        for v in video_elements:
            href = v.ele("#thumbnail").attr("href")
            if href and "watch?v=" in href and "shorts" not in href:
                video_id = href.split("v=")[1].split("&")[0]
                video_ids.append({"id": video_id})
        return video_ids
    except Exception:
        return []
    
def test_get_video_ids():
    print("Test get_video_ids()--------------------")
    game_name = "Apex Legends"
    release_date = "2020-11-05"
    
    try:
        start_tor() 
        session = new_configured_chromium_page()
        video_ids = get_video_ids(session, game_name, release_date)
        assert isinstance(video_ids, list), "El resultado debe ser una lista."
        print(f"Test exitoso: {video_ids}")
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.quit()

# --- SECCIÓN 2: API (Google API Client) ---
def get_youtube_service():
    """Inicializa el cliente oficial de la API de YouTube."""
    return build('youtube', 'v3', developerKey=get_youtube_api_key())

def request_youtube_stats(service, video_id_list):
    """
    Obtiene estadísticas y metadatos de una lista de vídeos mediante la API de YouTube.

    Args:
        service: Objeto de servicio de la API de Google.
        video_id_list: Lista de diccionarios que contienen los IDs de los vídeos.

    Returns:
        list[dict]: Lista de diccionarios con estadísticas, título y canal de cada vídeo.
    """
    if not video_id_list:
        return []
    
    ids_string = ','.join([v.get('id') for v in video_id_list if v.get('id')])
    if not ids_string:
        return []

    response = service.videos().list(part="statistics,snippet", id=ids_string).execute()

    stats = []
    for item in response.get('items', []):
        stats.append({
            'id': item['id'],
            'video_statistics': item.get('statistics', {}),
            'video_title': item['snippet'].get('title', ""),
            'channel': item['snippet'].get('channelTitle')
        })

    return stats

def process_game_youtube_data(app_data, service):
    """
    Orquesta la obtención de estadísticas de YouTube para un juego específico.

    Args:
        app_data: Diccionario con la información del juego y los IDs de los vídeos.
        service: Cliente de la API de YouTube.

    Returns:
        dict: Diccionario con el appid, nombre y la lista de estadísticas obtenidas.
    """

    video_ids = app_data.get("video_ids", [])
    
    result = {
        'appid': app_data.get('appid'),
        'video_statistics': []
    }

    if video_ids:
        result['video_statistics'] = request_youtube_stats(service, video_ids)
        
    return result

def test_process_game_youtube_data():
    print("Test process_game_youtube_data()--------------------")
    app_data = {"appid": "1172470", "name": "Apex Legends", "video_statistics": []}
    try:
        start_tor()
        session = new_configured_chromium_page()
        video_ids = get_video_ids(session, "Apex Legends", "2020-11-05")
        app_data["video_statistics"] = video_ids
        service = get_youtube_service()
        result = process_game_youtube_data(app_data, service)
        assert isinstance(result, dict), "El resultado debe ser un diccionario."
        print(f"Test exitoso: {result}")
    except Exception as e:
        print(f"Test fallido: {e}")
    finally:
        session.quit()
        service.close()

# Límite de requests api de Steam
REQUEST_LIMIT = 10000

if __name__ == "__main__":
    print(_parse_steam_date("10 Oct, 2007"))