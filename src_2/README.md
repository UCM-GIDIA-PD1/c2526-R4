# Propuesta de arquitectura modular y pipeline incremental (v2)

Este directorio contiene una propuesta de rediseño para el pipeline ETL del proyecto. El sistema busca mejorar la escalabilidad y permitir un crecimiento incremental de los datos sin procesar información redundante.

## Estructura de módulos

*   **`network/`**: Gestión de infraestructura (TOR y rotación de IP).
*   **`extract/`**: Lógica de interacción con las APIs de Steam y YouTube.
*   **`transform/`**: Limpieza de datos y definición de esquemas fijos para las columnas de los archivos Parquet.
*   **`io_manager.py`**: Gestor centralizado de lectura y escritura de archivos (integrado con MinIO). La lectura prioriza el almacenamiento local y, si el archivo no existe, intenta leer de MinIO. La escritura se realiza en local para optimizar el rendimiento en procesos de *JSON lines*. Se provee la función `upload_file_to_minio()` para subir archivos locales manteniendo la ruta relativa a la raíz del proyecto.
*   **`session.py`**: Configuración de sesiones y reparto de carga de trabajo.

## Flujo de trabajo (Scripts)

La propuesta se organiza en los siguientes pasos secuenciales:

### Gestión de muestra
*   **`s01_appid_list_full.py`**: Actualiza la lista completa de AppIDs de la tienda de Steam (Censo).
*   **`s02_appid_list_sample.py`**: Genera una muestra aleatoria de juegos a partir del censo, omitiendo aquellos que ya han sido procesados en el dataset final. Si el dataset crece demasiado, el sistema permite implementar un archivo de metadatos para cada parquet

### Extracción 
*   **`s03_steam_details.py`**: Extrae detalles técnicos y estimación de reseñas del primer mes. Lee de la muestra de AppIDs generada en el paso anterior.
*   **`s04_steam_reviews.py`**: Extrae reseñas de Steam en inglés para los modelos de lenguaje (NLP). Lee de la muestra de AppIDs.
*   **`s05_youtube_video_ids.py`**: Busca IDs de vídeos en YouTube mediante *scraping* sobre la red TOR. Lee de los archivos de detalles de Steam (`steam_details*.jsonl.gz`).
*   **`s06_youtube_video_stats.py`**: Obtiene estadísticas oficiales de los vídeos encontrados a través de la API de Google. Lee de los archivos de IDs de YouTube (`youtube_video_ids*.jsonl.gz`).
*   **`s07_image_features.py`**: Descarga los banners de los juegos y extrae vectores de características mediante redes neuronales (ResNet, ConvNeXt, CLIP). Lee de los archivos de detalles de Steam.

### Integración y transformación
*   **`s00_join_extraction_files.py`**: Script encargado de unir los ficheros *raw* provenientes de la extracción distribuida del equipo. Por ejemplo, unifica todos los `steam_details_*.jsonl.gz` en un único `steam_details.jsonl.gz`.
*   **`s08_transform_reviews.py`**: Procesa y limpia las reseñas de texto para generar el archivo `reviews.parquet`.
*   **`s09_transform_popularity.py`**: Une todas las fuentes y calcula métricas para generar `popularity.parquet`.
*   **`s10_transform_prices.py`**: Filtra juegos de pago y genera el dataset de `prices.parquet`.

### Pipeline Principal
*   **`s11_extract_new_data.py`**: Ejecuta el flujo completo y gestiona el versionado automático de los datos. Mantiene un histórico (`_old`), la extracción actual (`_new`) y el dataset unificado (`_final`). 

> **Nota sobre la ejecución:** Este script (`s11`) está diseñado para una ejecución secuencial simple. Aunque los módulos proporcionan herramientas para la extracción distribuida con identificadores (`PD1_ID`).
> 
> **Recomendación para testeo:** Generar una muestra pequeña (ej. 20 juegos) y ejecutar el pipeline. Para observar la capacidad incremental, ejecutar una segunda vez; en la carpeta `processed` se generarán tres archivos por cada problema (`_old`, `_new` y `_final`), donde este último es la suma deduplicada de los datos antiguos y los nuevos.

---

**Comentario final:** Este pipeline no está integrada oficialmente con el proyecto, pero es capaz de generar los parquets finales con las mismas columnas que las utilizadas en los modelos oficiales.