"""
Extraer los nuevos datos bajo un prefijo específico.
Al final del proceso integrarlos con los datos anteriores.
    - Subir a MinIO con tag de versiones?
    - Metadatos de extracción: fecha, cantidad de registros, etc.?

1. Extraer los nuevos appids
2. Extraer información de steam (appdetails y appreviewhistogram)
3. Extraer información de las imágenes de Steam
4. Extraer reseñas de Steam (cuantas de cada juego?)
5. Extraer información de YouTube
6. Incorporar los nuevos datos a los anteriores

Problemas para el análisis del desempeño
- FASTopic
- Como hacemos para analizar el desempeño de los modelos con los nuevos datos?
- Previsión de problema: Para nuestra lista actual de appids hay muchísimos juegos filtrados por coming soon, con este método no los volvemos a incluir,
probablemente todos los appids nuevos sean coming soon, vamos a tener muy pocos datos nuevos.
- Nuestro pipeline actual tiene un problema fundamental y es que filtramos en la etapa de extracción, lo que hace que no podamos volver a incluir los 
juegos que antes estaban filtrados. Deberíamos extraer toda la información de todos los appids y luego filtrar en la etapa de transformación, así podríamos 
incluir los nuevos appids aunque sean coming soon.

Propuesta para cambiar el pipeline:
- Extraer TODA la información de los appids, sin filtrar nada
- No extraer todo Steam, creo que es suficiente hacer un random sampling de por ejemplo 40K appids. Ya en cada modelo ver de esos 40K cuantos se pueden usar
- Luego en la etapa de transformación, aplicar el filtro de coming soon y otros filtros

Secundario:
- Modificar integración con MinIO, de creo que solo files.py debería saber de MinIO
- Para escritura puede que se pueda diseñar interfaz para decidir qué ficheros locales sincronizar con MinIO
- Añadir un modelo más de reviews, BERT
- Diseñar un mejor sistema de nombres de ficheros
- Estamos usando clases para los modelos???

Ya en general, quitar complejidad innecesaria y un codigo más legible y sencillo 
"""

from src.A_Extraccion.utils_extraccion.steam_requests import get_appids
from src.A_Extraccion.B_informacion_juegos import _download_game_data
from src.utils.config import appidlist_file
from utils.files import read_file, write_to_file
from tqdm import tqdm
from time import sleep
from numpy.random import uniform
from requests import Session
# Extraer los nuevos de appids

def extract_new_appids():
    """
    Requisitos ((*)sujeto a cambios):
    - variable de entorno STEAM_API_KEY
    - * fichero appids_list.json.gz para saber el último appid extraído
    """
    appid_list = read_file(appidlist_file)        
    last_appid = appid_list[-1]
    new_appids = get_appids(last_appid=last_appid)
    # Actualizar el fichero de appids con los nuevos appids
    appid_list.extend(new_appids)
    write_to_file(appid_list, appidlist_file)
    return new_appids

# Extraer la información de Steam de los nuevos appids
def extract_steam_info(new_appids):
    # TODO: esta función es temporal, probablemente haya que modificarla para que se integre mejor con el pipeline
    # Manejo de sesiones
    # Filtrado de datos
    # Manejo de errores
    sesion = Session()
    with tqdm(new_appids, unit = "appids") as pbar:
            for appid in pbar:
                pbar.set_description(f"Procesando appid {appid}")
                try:
                    desc = _download_game_data(appid, sesion)
                    write_to_file(desc, "new_gamelist.jsonl.gz")
                except Exception as e:
                    pbar.write(str(e))
                finally:
                    curr_idx += 1
                    wait = uniform(1.7, 2.5)
                    sleep(wait)
    pass

# Extraer la información de las imágenes de Steam de los nuevos appids
def extract_steam_images(new_appids):
    pass

# Extraer las reseñas de Steam de los nuevos appids
def extract_steam_reviews(new_appids):
    pass

# Extraer la información de YouTube de los nuevos appids
def extract_youtube_info(new_appids):
    pass

# Integrar los nuevos datos con los anteriores
def integrate_new_data():
    pass