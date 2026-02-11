# Steam Predictor

![](https://github.com/user-attachments/assets/d2471800-7fc6-4eb1-93bd-16a296e77c85)

## Descripción 
**Steam Predictor** es una consultoría automática online dirigida sobre todo a desarrolladores de videojuegos publicados en Steam. Nuestras herramientas incluyen **predictores de popularidad, estimadores de precio y análisis de reseñas**. De manera sencilla los desarrolladores podrán aceder a métricas con las que entender el impacto social de sus juegos, además de ayudar en otras tareas como estudio de mercado, análisis de redes sociales y recolección de opiniones. 

---

## Funcionalidades
### ¿Cómo funciona?


### Objetivos
- **Predictor de popularidad**: Usando como estimador de popularidad el número de reseñas que tiene un juego, predeciremos este valor usando sobre todo el impacto social (relevancia en RRSS), pero también otros parametros como los elementos de la página de Steam del juego.
- **Estimador de precios**: Predecir el precio de un juego en base a otros juegos similares y otros parámetros, pudiendo así clasificar por ejemplo juegos que pareciéndose en características a otros, se diferencien mucho en su precio. 
- **Análisis de reseñas**: Sintetizar el feedback de la comunidad para ayudar a los desarrolladores a detectar puntos fuertes y débiles de su juego. Además ayudará a usuarios a explorar el catálogo de Steam destacando los juegos con las características deseadas.

---

## Estructura del proyecto

```
SteamPredictor/
├── data/
│   └── [Drive de datos](https://drive.google.com/drive/folders/1BIC7hrgvBLbDqTDKP1Cg0qdcjAiJjNSI?usp=drive_link)
│   └── [Servidor de datos](https://minio.fdi.ucm.es/)
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

## Autores 
* Antón Vladislavov
* Jan Mercado
* Jorge Bertomeu
* Lucas Ospina
* Nicolás Gil
* Zhixian Zhou
