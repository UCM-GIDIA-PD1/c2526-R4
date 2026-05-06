![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/status-En%20desarrollo-F39C12)
![UCM](https://img.shields.io/badge/UCM-Proyecto%20de%20Datos%20I-8E44AD)

# Steam Predictor

![](https://github.com/user-attachments/assets/d2471800-7fc6-4eb1-93bd-16a296e77c85)

## Índice
- [Descripción](#descripción)
- [Funcionalidades](#funcionalidades)
    * [Objetivos](#objetivos)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Uso del programa](#uso-del-programa)
    * [Iniciación de entorno y dependencias](#iniciación-de-entorno-y-dependencias)
    * [Configuraciones y dependencias](#configuraciones-y-dependencias)
    * [Dependencia: TOR](#dependencia-tor)
- [Instrucciones para ejecutar scripts](#instrucciones-para-ejecutar-scripts)
    * [Instrucciones de uso del menú](#instrucciones-de-uso-del-menú)
- [Resumen de resultados](#resumen-de-resultados)
- [Desplegar la web con uv run](#desplegar-la-web-con-uv-run)
- [Desplegar la web mediante el contenedor de Podman](#desplegar-la-web-mediante-el-contenedor-de-podman)
- [Autores](#autores)

## Descripción 
**Steam Predictor** es una consultoría automática online dirigida a desarrolladores y jugadores de videojuegos publicados en Steam. Nuestras herramientas incluyen **predictores de popularidad, estimadores de precio y análisis de reseñas**. De manera sencilla los desarrolladores podrán acceder a métricas con las que entender el impacto social de sus juegos, además de ayudar en otras tareas como estudio de mercado, análisis de redes sociales y recolección de opiniones.

---

## Funcionalidades
### Objetivos
- **Predictor de popularidad**: Usando como estimador de popularidad el número de reseñas que tiene un juego, predecimos este valor usando sobre todo el impacto social (relevancia en RRSS), pero también otros parametros como los elementos de la página de Steam del juego.
- **Estimador de precios**: Predecir el precio de un juego en base a otros juegos similares y otros parámetros, pudiendo así clasificar por ejemplo juegos que pareciéndose en características a otros, se diferencien mucho en su precio. 
- **Análisis de reseñas**: Sintetizar el feedback de la comunidad para ayudar a los desarrolladores a detectar puntos fuertes y débiles de su juego. Además ayudará a usuarios a explorar el catálogo de Steam destacando los juegos con las características deseadas. También predecir si una reseña es negativa o positiva.

---

## Estructura del proyecto

```txt
├── app/                        # Aplicación web
├── config_files/               # Configuraciones externas (TOR)
├── data/                       # Carpeta de datos (json, parquet)
├── models/                     # Carpeta de modelos (pkl)
├── src/                        # Carpeta final que contiene toda la lógica del proyecto
│   ├── A_Extraccion/
│   ├── B_Transformacion/
│   ├── C_Analisis/
│   ├── D_Modelos/
│   │   ├── Popularidad/
│   │   ├── Precios/
│   │   └── Reviews/
│   ├── E_pipeline/
│   ├── main.py                 # Fichero para ejecutar el menú
│   └── utils/                  # Funciones auxiliares
├── src_2/                      # Propuesta alternativa no oficial de algunos scripts del Pipeline
├── Containerfile               # Configuración del contenedor (Podman)
├── pyproject.toml              # Gestión de dependencias y proyecto (uv)
└── README.md
```

---
# Uso del programa
## Iniciación de entorno y dependencias
1. **Clonar el repositorio**:
``` shell
git clone https://github.com/UCM-GIDIA-PD1/c2526-R4.git
cd c2526-R4
```

## Configuraciones y dependencias
Las únicas dependencias esenciales son las variables de entorno, configurables de esta manera:

En Windows, ejecutar los siguientes comandos desde la terminal introduciendo tus claves:
```shell
setx STEAM_API_KEY clave_api
setx API_KEY_YT clave_api
setx WANDB_API_KEY clave_api
setx MINIO_ACCESS_KEY clave_de_acceso
setx MINIO_SECRET_KEY clave_secreta
setx PD1_ID identificador_grupo
```

En Linux o MacOS, hay que crear un archivo `.env` y añadir:
```bash
export PD1_ID=identificador_grupo
export STEAM_API_KEY=clave_api
export API_KEY_YT=clave_api
export WANDB_API_KEY=clave_api
export MINIO_ACCESS_KEY=clave_de_acceso
export MINIO_SECRET_KEY=clave_secreta
```

Además, para cualquier sistema operativo tendrás que añadir el `.env` con este formato si quieres correr el contenedor:
```bash
API_KEY_YT=clave_api
MINIO_ACCESS_KEY=clave_de_acceso
MINIO_SECRET_KEY=clave_secreta
```
> [!CAUTION]
> Si en vez de usar este formato en el `.env` lo escribes con `export ` el contenedor no funcionará. Puedes ponerlo de ambas formas en el mismo fichero para que funcione siempre.

Descripción de variables:
- La ``STEAM_API_KEY`` de [Steam](https://steamcommunity.com/dev/apikey) para extraer información de Steam.
- La ``API_KEY_YT`` de [YouTube](https://developers.google.com/youtube/v3/getting-started?hl=es-419) para extraer información de YouTube.
- La ``WANDB_API_KEY`` de [Weight & Biases](https://wandb.ai/site/) para monitorizar el entrenamiento de los modelos.
- Las ``MINIO_SECRET_KEY`` y ``MINIO_ACCESS_KEY``, claves secreta y de acceso del servidor de MinIO
- El ``PD1_ID`` que determina que integrante del grupo eres, útil para repartir el trabajo al extraer información. No es obligatorio.

### Dependencia: TOR
Únicamente para ejecutar el fichero C1 de extracción de datos hará falta configurar TOR.
Se necesita tener tanto una versión de Google Chrome reciente, como TOR bundle descargado de la [página oficial de TOR](https://www.torproject.org/download/tor/).
##### En Windows
Después de descargar TOR, ejecuta el archivo ``tor.exe`` que puedes encontrar dentro de la subcarpeta tor para que se creen los archivos por defecto para el correcto funcionamiento del mismo. Cuando el proceso de TOR llegue al 100%, ciérralo. Posteriormente, abre las variables de entorno del sistema y clica para abrir la variable PATH. Hecho eso, añade la carpeta de tor (la que tiene como hija al archivo tor.exe) como nueva variable de entorno.
##### Linux y MacOS
Se puede hacer la instalación usando la terminal:

- Mediante `apt` (distribuciones basadas en Debian):
```bash
sudo apt install tor
```

- Mediante `pacman` (distribuciones basadas en Arch):
```bash
sudo pacman -S tor
```

- Mediante `brew` (MacOS):
```bash
brew install tor
```

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
### Dependencia: ollama
Únicamente para ejecutar el fichero C2 de extracción de datos hará falta descargar ollama y el modelo gemma4.
Ollama es una herramienta para ejecutar modelos de IA generativa de forma local que utilizamos para saber si un video es o no es de un videojuego. Pasándo el título, el nombre del canal y otros parámetros gemma4 elige si usar o no usar el video para el entrenamiento.

Lo único que hay que hacer es descargar [ollama](https://ollama.com/download) y el modelo [gemma4](https://ollama.com/library/gemma4) o ejecutando:
```shell
ollama pull gemma4
```

---

## Instrucciones para ejecutar scripts
Todos los scripts del proyecto pueden ser ejecutados desde nuestro menú gráfico en la terminal. Para acceder al menú, desde la raíz del proyecto ejecuta:
```shell
uv run src/main.py
```

Desde el menú prodrás seleccionar cualquier fichero del proyecto para ejecutarlo: los de extracción de datos, transformación, entrenamiento de modelos y extracción de nuevos datos.
Además se puede seleccionar si usar los datos en local o los del servidor de [MinIO](https://minio.fdi.ucm.es/minio-console/login).

> [!IMPORTANT]
> El apartado de análisis no se puede ejecutar desde el menú ya que no son ficheros, son notebooks. Se pueden encontrar en la carpeta de análisis y no necesitan configuraciones extra para poder ejecutarse.

### Instrucciones de uso del menú
Al ejecutar el menú aparecerá una pestaña donde podrás elegir que acción querrás realizar, solo tendrás que escribir el número correspondiente para llegar al menú de selección de ese apartado:
- 1 ➜ Extracción

    Desde este menú podrás extraer todos los datos necesarios del proyecto. Para ejecutar modelos de los tres problemas del proyecto es necesario ejecutarlos todos.
- 2 ➜ Transformación

    Desde este menú podrás realizar las transformaciones necesarias para convertir los datos en crudo en los parquets necesarios para entrenar los modelos
- 3 ➜ Modelos

    Desde este menú podrás entrenar todos los modelos de nuestros tres problemas, además de ejecutar scripts de evaluación para obtener las métricas de todos ellos
- 4 ➜ Pipelines

    Desde este menú podrás ejecutar el pipeline para obtener nuevos datos, siempre que se hayan sacado inicialmente se podrán actualizar ejecutando el pipeline

Aun así, no es necesario ejecutarlo todo para poder seguir (ya que hay algunos ficheros que tardan varias horas), se pueden usar los datos de MinIO para ejecutar cualquiera de los scripts en todo momento. 

Desde estos submenús podrás elegir qué ficheros quieres ejecutar escribiendo en el chat el código (letra o letra y número) de los mismos. En el apartado de ficheros y dependencias aparecen todos los ficheros de salida que se pueden obtener ejecutando todos los scripts de esa sección, y un cuadro que se marcará si tienes ese fichero en local (o, habiendo seleccionado usar los datos de MinIO, si está disponible en minio). Además de las dependencias de los ficheros que has seleccionado para ejecutar, asegúrate de tener todas las casillas de dependencias marcadas antes de ejecutar los scripts. Una vez tengas seleccionado todo lo que quieres ejecutar escribe `RUN`. 

---

## Resumen de resultados
### Predictor de popularidad
El mejor modelo es MLP, con un MAE de 130 y RMSE de 1674. Estas métricas no son muy buena, siendo este el peor de nuestros modelos.
### Estimador de precios
El mejor modelo es el de kNN con un F1 de 0.6415, *accuracy* de 0.659, *precision* de 0.6527 y *recall* de 0.659, destacando que los precios mal predichos suelen ser de tan solo una categoría por encima o por debajo.
### Análisis de reseñas
En este apartado tenemos dos modelos, por una parte para saber si las reseñas son negativas o positivas tenemos un modelo de regresión logística con un balanced accuracy de 0.87 y F1 de 0.91. Por otra parte, para clasificar las reseñas por temáticas usamos un modelo de FASTopic al que no le hemos podido sacar métricas al no estar los datos etiquetados. Aun así este modelo parece funcionar bastante bien, dando siempre clasificaciones coherentes.

---

## Desplegar la web con uv run
Para desplegar la web, ejecuta este comando situado en la raíz del proyecto. Es importante estar conectado a la VPN de la UCM para la descarga de los datos y los modelos:

```shell
uv run uvicorn app.main:app --reload --port 8000
```

---

## Desplegar la web mediante el contenedor de Podman
Para poder desplegar la web es necesario tener instalado [podman](https://podman.io/) y tener el fichero .env con tus credenciales correctamente configurado como se especifica en el apartado de dependencias. Además de estar conectado a la VPN de la UCM.
1. **Iniciar Podman**:
``` shell
podman machine init
podman machine start
```
2. **Crear la imagen**:
``` shell
podman build -t steam-predictor .
```

2. **Iniciar contenedor**:
```shell
podman run -d -p 8000:8000 --name container --env-file .env steam-predictor
```

Accede a la web desde `http://localhost:8000`. 

> [!WARNING]
> Si estás en Windows puede que tu máquina Podman intente usar una IP interna aislada, para encontrarla:
> ```shell
> wsl -d podman-machine-default ip -4 a
> ```
Busca el bloque de red llamado eth0 y fíjate en la dirección que aparece al lado de inet. Podrás acceder a la web desde `http://<TU_IP>:8000`

---
## Autores 

| [<img src="https://github.com/nicgil23.png" width="100px;"/>](https://github.com/nicgil23) | [<img src="https://github.com/JanMercado51.png" width="100px;"/>](https://github.com/JanMercado51) | [<img src="https://github.com/jorgbert.png" width="100px;"/>](https://github.com/jorgbert) | [<img src="https://github.com/lucasosp.png" width="100px;"/>](https://github.com/lucasosp) | [<img src="https://github.com/anton-VK.png" width="100px;"/>](https://github.com/anton-VK) | [<img src="https://github.com/zhixianzucm.png" width="100px;"/>](https://github.com/zhixianzucm) |
| :-: | :-: | :-: | :-: | :-: | :-: |
| [Nicolás Gil](https://github.com/nicgil23) | [Jan Mercado](https://github.com/JanMercado51) | [Jorge Bertomeu](https://github.com/jorgbert) | [Lucas Ospina](https://github.com/lucasosp) | [Antón Vladislavov](https://github.com/anton-VK) | [Zhixian Zhou](https://github.com/zhixianzucm) |