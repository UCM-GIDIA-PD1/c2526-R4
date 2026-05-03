
from DrissionPage import ChromiumPage, ChromiumOptions
from random import choice, randint
from src_2.config import BROWSER_PATH, USER_AGENTS, COMMON_RESOLUTIONS, TOR_SOCKS_PROXY
from src_2.network.tor_manager import start_tor

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
    Busca vídeos de un juego en YouTube anteriores a una fecha específica.
    
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

if __name__ == "__main__":
    test_get_video_ids()