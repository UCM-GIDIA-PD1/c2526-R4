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

```txt
├── config_files/
│   └── torrc
├── .gitignore
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
├── src/
│   ├── A_Extraccion/
│   ├── B_Transformacion/
│   ├── C_Analisis/
│   ├── D_Modelos/
│   ├── main.py
│   └── utils/
└── uv.lock
```

---
## Uso del programa
### Introducción
1. **Clonar el repositorio**:
``` shell
git clone https://github.com/UCM-GIDIA-PD1/c2526-R4.git
cd c2526-R4
```

2. **Ejecutar el menú**. La primera vez tardará un poco al tener que sincronizar el [entorno virtual UV](https://docs.astral.sh/uv/):
```shell
uv run src/main.py
```

Desde el menú prodrás seleccionar cualquier fichero del proyecto para ejecutarlo: los de extracción de datos, transformación y entrenamiento de modelos.
Además se puede seleccionar si usar los datos en local o los del servidor de [MinIO](https://minio.fdi.ucm.es/minio-console/login).

Además, el apartado de análisis no se puede ejecutar desde el menú ya que no son ficheros sino notebooks. Estos ficheros se pueden encontrar en la carpeta de análisis y no necesitan configuraciones extra para poder ejecutarse.
---
## Configuraciones y dependencias
Deberás tener ciertas variables de entorno, configurables de esta manera:

En Windows:
```shell
setx STEAM_API_KEY clave_api
setx API_KEY_YT clave_api
setx WANDB_API_KEY clave_api
setx MINIO_ACCESS_KEY clave_de_acceso
setx MINIO_SECRET_KEY clave_secreta
setx PD1_ID identificador_grupo
```

En Linux o MacOS hay que crear un archivo `.env` y añadir:
```bash
export STEAM_API_KEY=clave_api
export API_KEY_YT=clave_api
export WANDB_API_KEY=clave_api
export MINIO_ACCESS_KEY=clave_de_acceso
export MINIO_SECRET_KEY=clave_secreta
export PD1_ID=identificador_grupo
```

Definición de variables:
- La ``STEAM_API_KEY`` de [Steam](https://steamcommunity.com/dev/apikey) para extraer información de Steam.
- La ``API_KEY_YT`` de [YouTube](https://developers.google.com/youtube/v3/getting-started?hl=es-419) para extraer información de YouTube.
- La ``WANDB_API_KEY`` de [Weight & Biases](https://wandb.ai/site/) para monitorizar el entrenamiento de los modelos.
- Las ``MINIO_SECRET_KEY`` y ``MINIO_ACCESS_KEY``, claves secreta y de acceso del servidor de MinIO
- El ``PD1_ID`` que determina que integrante del grupo eres, útil para repartir el trabajo al extraer información. No es obligatorio.

### Dependencia: TOR
Para Scrapear YouTube necesitamos tener tanto una versión de Google Chrome reciente, como TOR bundle descargado de la [página oficial de TOR](https://www.torproject.org/download/tor/).
##### En Windows
Después de descargar TOR, ejecutad el archivo ``tor.exe`` que podéis encontrar dentro de la subcarpeta tor para que se creen los archivos por defecto para el correcto funcionamiento del mismo. Cuando el proceso de TOR llegue al 100%, cerradlo. Posteriormente, abrid las variables de entorno del sistema y clicad para abrir la variable PATH. Hecho eso, añadid la carpeta de tor (la que tiene como hija al archivo tor.exe) como nueva variable de entorno. El script C1 usará como configuración de TOR el archivo `torrc` que podéis encontrar en el repositorio, que sirve para que funcione correctamente la rotación de IP.
##### Linux
Algunas distros de linux ejecutan un proceso en segundo plano de TOR al iniciar. Si el script C1 diese error al cambiar de IP, se deben ejecutar los siguientes comandos en consola:

Para detener el proceso:
```bash
sudo pkill -f tor
```

Para detener el proceso actual y deshabilitar el servicio permanentemente:
```bash
sudo systemctl stop tor
sudo systemctl disable tor
```

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
