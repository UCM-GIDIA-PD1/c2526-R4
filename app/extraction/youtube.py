"""Módulo de extracción de datos de un juego mediante la API de Yotube Data v3

Dependencias:
    - API_KEY_YT: API key de Youtube (Obtenible desde Google Cloud Console)
"""

import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from utils.config import load_env_file

load_env_file()
API_KEY = os.environ.get("API_KEY_YT")

def get_video_data(game_name: str, release_date: str) -> list[dict]:
    """Dada un APPID y la fecha de salida de un juego realiza las busquedas en la API de Youtube para obtener los
    identificadores de un vídeo y luego obtiene las estadísticas de los 4 primeros vídeos.
    """
    print("Obtaining Youtube Data")
    youtube = build("youtube", "v3", developerKey=API_KEY)
    release_date = f"{release_date}T00:00:00Z"
    try:
        # Búsqueda IDs
        items = youtube.search().list(
            part="snippet",
            q=game_name,
            type="video",
            videoCategoryId="20",
            publishedBefore=release_date,
            maxResults=4,
            order="relevance",
        ).execute().get("items", [])

        if not items:
            print(f"No data found for {game_name}.")
            return []

        video_ids = [item["id"]["videoId"] for item in items]

        # Estadísticas de los vídeos
        videos_request = youtube.videos().list(
            part="statistics,snippet",
            id=",".join(video_ids),
        )
        videos_response = videos_request.execute()
        stats_list = []
        for item in videos_response['items']:
            stats_list.append({
                "id":               item["id"],
                "video_statistics": item["statistics"],
                "video_title":      item["snippet"]["title"],
                "channel":          item["snippet"]["channelTitle"],
            })

        return stats_list

    except HttpError as e:
        if e.resp.status == 403 and "quotaExceeded" in str(e.content):
            raise RuntimeError("YouTube API quota exceeded.") from e
        raise

if __name__ == "__main__":
    pass