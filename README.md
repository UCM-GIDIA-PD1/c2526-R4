# Steam Predictor

![](https://github.com/user-attachments/assets/d2471800-7fc6-4eb1-93bd-16a296e77c85)

## Descripción 
**Steam Predictor** es una consultoría automática online dirigida sobre todo a desarrolladores de videojuegos publicados en Steam. Nuestras herramientas incluyen **predictores de popularidad, estimadores de precio y análisis de reseñas**. De manera sencilla los desarrolladores podrán aceder a métricas con las que entender el impacto social de sus juegos, además de ayudar en otras tareas como estudio de mercado, análisis de redes sociales y recolección de opiniones. 

---

## Funcionalidades
### Objetivos
- **Predictor de popularidad**: Usando como estimador de popularidad el número de reseñas que tiene un juego, predeciremos este valor usando sobre todo el impacto social (relevancia en RRSS), pero también otros parametros como los elementos de la página de Steam del juego.
- **Estimador de precios**: Predecir el precio de un juego en base a otros juegos similares y otros parámetros, pudiendo así clasificar por ejemplo juegos que pareciéndose en características a otros, se diferencien mucho en su precio. 
- **Análisis de reseñas**: Sintetizar el feedback de la comunidad para ayudar a los desarrolladores a detectar puntos fuertes y débiles de su juego. Además ayudará a usuarios a explorar el catálogo de Steam destacando los juegos con las características deseadas.

---

## Estructura del proyecto

```
SteamPredictor/
├── config/                                       # Archivos de configuración
│   └── torrc
├── src/
│   ├── 1_Extraccion/                             # Captura de datos
│   │   ├── Scripts/
│   │   │   ├── A_lista_juegos.py
│   │   │   ├── B_informacion_juegos.py
│   │   │   ├── C1_informacion_youtube_busqueda.py
│   │   │   ├── C2_informacion_youtube_video.py
│   │   │   ├── D_informacion_resenyas.py
│   │   │   ├── E_metadatos_imagenes.py
│   │   │   └── Z_funciones.py
│   │   └── main.py                               
│   └── 2_Analisis/                               # Estudio de distribución de datos
│       └── Analisis_distribucion_popularidad.py  
├── .gitignore
├── .python-version
├── README.md
├── pyproject.toml
└── uv.lock
```

---

## Inicialización del entorno de trabajo
### Introducción
1. **Clonar el repositorio**:
``` shell
git clone https://github.com/UCM-GIDIA-PD1/c2526-R4.git
cd c2526-R4
```

2. **Sincronizar las librerías y versión de Python** de manera automática con el [entorno virtual UV](https://docs.astral.sh/uv/), el cual deberemos tener descargado con anterioridad. Ejecuta el siguiente comando para sincronizar el entorno:
``` shell
uv sync
```
Este entorno virtual funciona gracias a los archivos ``pyproject.tolm`` y ``uv.lock``, que se encuentran dentro del repositorio. Teniendo esto instalado ya puedes ejecutar *scripts* desde nuestro menú ejecutando:
```shell
uv run src/1_Extraccion/main.py
```

3. **Obtener los datos**. Para ello, existen dos opciones:
	1. Descargar los datos directamente desde el servidor de [MinIO](https://minio.fdi.ucm.es/minio-console/login).
	2. Extraer los datos de forma manual, explicado posteriormente.
### Extracción de datos
Se debe tener en cuenta que la extracción manual de los datos tarda un tiempo largo, por lo que se recomienda descargar o usar los datos directamente del servidor de *MinIO*.

Si se desea extraer la información en grupo de 6 personas, se debe crear una variable del sistema nueva llamada `PD1_ID`, que tendrá un valor de entre 1 y 6. Si no se crea esta variable se extraerá la información de manera completa. 
En Windows ejecutamos:
```shell
setx PD1_ID identificador_grupo
```
En Linux hay que crear un archivo .env y añadir:
```bash
export PD1_ID=identificador_grupo
```

#### Dependencias
Para realizar la extracción de la lista de juegos de Steam así como de las estadísticas individuales de los vídeos *scrapeados*, necesitamos antes conseguir acceso a varias APIs, a las que se adjuntan documentación del proceso de obtención:
- La ``STEAM_API_KEY`` de [Steam](https://steamcommunity.com/dev/apikey).
- La ``API_KEY_YT`` de [YouTube](https://developers.google.com/youtube/v3/getting-started?hl=es-419).

Además, si queremos guardar los datos en el servidor de la FDI de MinIO necesitaremos:
- Clave de acceso del servidor de MinIO
- Clave secreta del servidor de MinIO

Una vez conseguidas, vamos a incluirlas como variables del sistema para que el código las detecte:
En Windows:
```shell
setx STEAM_API_KEY clave_api
setx API_KEY_YT clave_api
setx MINIO_ACCESS_KEY clave_de_acceso
setx MINIO_SECRET_KEY clave_secreta
```
En Linux hay que crear un archivo .env y añadir:
```bash
export STEAM_API_KEY=clave_api
export API_KEY_YT=clave_api
export MINIO_ACCESS_KEY=clave_de_acceso
export MINIO_SECRET_KEY=clave_secreta
```

Además para poder conectarse a MinIO hay que descargarse el [mc.exe](https://dl.min.io/client/mc/release/windows-amd64/mc.exe) y meterlo en la raiz del proyecto.

Para Scrapear YouTube necesitamos tener tanto una versión de Google Chrome reciente, como TOR bundle descargado de la [página oficial de TOR](https://www.torproject.org/download/tor/).

En **Windows**:
Después de descargar TOR, ejecutad el archivo ``tor.exe`` que podéis encontrar dentro de la subcarpeta tor para que se creen los archivos por defecto para el correcto funcionamiento del mismo. Cuando el proceso de TOR llegue al 100%, cerradlo. Posteriormente, abrid las variables de entorno del sistema y clicad en la variable PATH. Hecho eso, añadid la carpeta de TOR como nueva variable de entorno. El script C1 usará como configuración de TOR el archivo `torrc` que podéis encontrar en el repositorio, no hace falta hacer nada con él, pero sirve para que funcione correctamente la rotación de IP.

En **Linux**:
- Mediante `apt` (gran parte de distros):
```bash
sudo apt install tor
```
- Mediante `pacman` (Arch):
```bash
sudo pacman -S tor
```

En **MacOS**:
- Mediante `brew`:
```bash
brew install tor
```

---

## Autores 
* Antón Vladislavov
* Jan Mercado
* Jorge Bertomeu
* Lucas Ospina
* Nicolás Gil
* Zhixian Zhou