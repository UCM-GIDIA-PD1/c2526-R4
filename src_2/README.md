# Propuesta de arquitectura modular y pipeline incremental (v2)

Este directorio contiene una propuesta de rediseño para el motor de datos del proyecto. El sistema busca mejorar la escalabilidad y permitir un crecimiento incremental de los datos sin procesar información redundante.

## Estructura de módulos

*   **"network/"**: Gestión de infraestructura (TOR y rotación de IP).
*   **"extract/"**: Lógica de interacción con las APIs de Steam y YouTube.
*   **"transform/"**: Limpieza de datos y definición de esquemas fijos para las columnas de los parquets.
*   **"io_manager.py"**: Gestor centralizado de lectura y escritura de archivos (integrado con MinIO). La lectura prioriza local, y si falla intenta leer de MinIO. La escritura se hace en local porque se hacen muchas escrituras en json lines, se provee la función upload_file_to_minio() para subir archivos locales manteniendo la ruta relativa a la raíz del proyecto
*   **"session.py"**: Configuración de sesiones y reparto de carga de trabajo.

## Flujo de trabajo (Scripts)

La propuesta se organiza en los siguientes pasos secuenciales:

### Gestión de muestra
*   **"s01_appid_list_full.py"**: Actualiza la lista completa de AppIDs de la tienda de Steam (Censo).
*   **"s02_appid_list_sample.py"**: Genera una muestra aleatoria de juegos a partir del censo, teniendo en cuenta aquellos que ya se han procesado en el dataset final. Si este dataset crece demasiado de puede implementar un archivo de metadatos.

### Extracción 
*   **"s03_steam_details.py"**: Extrae detalles técnicos y estimación de reseñas del primer mes. Lee del sample de appids.
*   **"s04_steam_reviews.py"**: Extrae reseñas de Steam en inglés para los modelos de lenguaje (NLP). Lee del sample de appids.
*   **"s05_youtube_video_ids.py"**: Busca ids de vídeos en YouTube mediante scraping sobre la red TOR. Lee de un archivo del tipo steam_details*.jsonl.gz
*   **"s06_youtube_video_stats.py"**: Obtiene estadísticas de los vídeos encontrados a través de la API de Google. Lee de un archivo del tipo youtube_video_ids*.jsonl.gz
*   **"s07_image_features.py"**: Descarga los banners de los juegos y extrae vectores de características mediante redes neuronales. Lee de un archivo del tipo steam_details*.jsonl.gz

### Integración y transformación
*   **"s00_consolidate_raw.py"**: Script encargada de unir ficheros raw que provienen de la extracción de los distintos miembros del equipo. Ejemplo, une todos ficheros steam_details_*.jsonl.gz en steam_details.gz
*   **"s08_transform_reviews.py"**: Procesa y limpia las reseñas de texto para generar el archivo "reviews.parquet".
*   **"s09_transform_popularity.py"**: Une todas las fuentes y calcula métricas (EMA, YT Score) para generar "popularity.parquet".
*   **"s10_transform_prices.py"**: Filtra juegos de pago y genera el dataset de "prices.parquet".

### Pipeline
*   **"s11.extract_new_data.py"**: Ejecuta el flujo completo y gestiona el versionado de los datos, manteniendo un histórico ("_old"), la extracción actual ("_new") y el dataset unificado ("_final"). Este script no está diseñado para la extracción integrada con indentificadores. La lógica de extracción con identificadores es más compleja, pero los módulos y scripts proporcionan todas las herramientas para llevarla a cabo. Recomendación para testear este módulo: enerar un sample pequeño de datos (20) y extraer todos los datos. Si se quiere observar la capacidad incremental, ejecutar una segunda vez de la misma forma. En la carpeta processed quedará para cada problema tres parquets *_old, *_new y *_final (suma de los datos antiguos y los nuevos)

Comentario: este pipeline no está integrado con el proyecto. Es capaz de generar los parquets finales con las mismas columnas que las que se usan en los modelos. 