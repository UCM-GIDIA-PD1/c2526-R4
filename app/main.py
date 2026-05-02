"""
Archivo web de SteamPredictor.

Para levantar la página:
> uv run uvicorn app.main:app --reload --port 8000

Puerto: http://127.0.0.1:8000
"""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'false'
os.environ['KERAS_BACKEND'] = 'tensorflow'

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from pydantic import BaseModel
import pandas as pd
import nltk

from app.extraction.steam import get_appdetails, get_image_metadata, get_appreviewshistogram, get_reviews_text
from app.extraction.youtube import get_video_data
from app.transformation.prices import transform_for_prices, HISTORY_COLS as PRICE_HISTORY_COLS
from app.transformation.popularity import transform_for_popularity, HISTORY_COLS as POP_HISTORY_COLS
from app.transformation.reviews import clean_text, to_dataframe
from src.D_Modelos.Popularidad.mlp import MLPPopularity
from src.utils.config import GAME_FETCH_DATA_PATH, HISTORIC_GAMES_DATA_PATH, precios_knncompleteclusters_file, app_dir, popularidad_mlp_file, reviews_logistic_regression_optuna_file
from src.utils.files import read_file
from src.D_Modelos.Reviews.logistic_regression import predict_logistic_regression

# Dependencias para limpiar texto
nltk.download('stopwords')
nltk.download('wordnet')

PRICE_ORDER = [
    'Entre 0.01€ y 4.99€', 
    'Entre 5.00€ y 9.99€', 
    'Entre 10.00€ y 14.99€', 
    'Entre 15.00€ y 19.99€', 
    'Entre 20.00€ y 29.99€', 
    'Entre 30.00€ y 39.99€', 
    'Más de 40€'
]

# region classes

class PredictionRequest(BaseModel):
    """Datos de entrada para una predicción."""
    appid: int
    model_name: str = "default"

class PredictionReviewsRequest(BaseModel):
    """Datos de entrada para el problema de predecir la valoración de una review.
    """
    review : str

class PredictionResponse(BaseModel):
    """Resultado de una predicción."""
    value: float
    confidence: float
    model_used: str
    details: dict

class CustomGameRequest(BaseModel):
    name: str
    developer: str
    release_date: str
    genres: list[str]
    categories: list[str]
    languages_count: int = 1
    image: str | None = None
    youtube_videos: list[dict] = []

class YouTubeSearchRequest(BaseModel):
    name: str
    release_date: str

class PopularityResponse(BaseModel):
    """Resultado de la predicción del problema de popularidad
    """
    reviews : int

class PriceResponse(BaseModel):
    """Resultado de la predicción del problema de precios
    """
    price : str

class ReviewsTopicsResponse(BaseModel):
    """Resultado de la predicción del problema de puntos positivos y negativos"""
    topics : list

class ReviewsValueResponse(BaseModel):
    value : bool


class GameInfo(BaseModel):
    """Información básica de un juego. Usada para mostrar un juego en la página web y para luego obtener la información
    de dicho juego en cada modelo"""
    appid: int
    name: str
    banner_url: str
    release_date: str
    developer: str
    genres: list[str]
    price: float
    positive_reviews: int
    negative_reviews: int

# endregion

# region startup/shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    minio = {"minio_write": False, "minio_read": True}

    # Cargar modelos 
    print("Cargando modelo de popularidad")
    app.state.model_popularity = read_file(popularidad_mlp_file, minio)
    print("Cargando modelo de precios")
    app.state.model_price = read_file(precios_knncompleteclusters_file, minio)
    print("Cargando modelo de reviews(Simple)")
    app.state.model_reviews = read_file(reviews_logistic_regression_optuna_file, minio)

    # Cargar los datos históricos de developers y publishers
    print("Cargando datos históricos de juegos")
    app.state.historic_data = read_file(HISTORIC_GAMES_DATA_PATH, minio)

    # Cargar catálogo de juegos desde MinIO
    print("Cargando lista de juegos")
    app.state.games_df = read_file(GAME_FETCH_DATA_PATH, minio)

    print("SteamPredictor API iniciada")
    yield
    print("SteamPredictor API detenida")


# Crear la aplicación web
app = FastAPI(
    title="SteamPredictor API",
    description="Predicción de métricas de juegos de Steam",
    version="1.0.0",
    lifespan=lifespan,
)

# Ficheros estáticos
app.mount("/static", StaticFiles(directory= app_dir() / "static"), name="static")

# Plantillas Jinja2
templates = Jinja2Templates(directory= app_dir() / "templates")

#endregion

# region search

def _df_rows_to_list(df, offset: int = 0, limit: int = 20) -> dict:
    """Convierte las filas especificadas del DataFrame a una particion paginada con id, name, img."""
    total = len(df)
    subset = df.iloc[offset:offset+limit][["id", "name", "img"]].copy()
    
    # Asegurar que no hay NaNs en campos críticos antes de enviarlos como JSON
    subset["id"] = subset["id"].fillna(0).astype(int)
    subset["name"] = subset["name"].fillna("Unknown")
    subset["img"] = subset["img"].fillna("")
    
    subset.rename(columns={"id": "appid", "img": "banner_url"}, inplace=True)
    return {
        "games": subset.to_dict("records"),
        "has_more": offset + limit < total
    }

# Página principal
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, name="index.html")

# API REST
@app.get("/api/search")
def search_games(q: str = "", page: int = 1, limit: int = 40, sort: str = "desc", genre: str = "", prices: str = ""):
    """Buscar juegos por nombre, género y rango de precio."""
    try:
        offset = (page - 1) * limit
        df = app.state.games_df
        
        # Filtrado por búsqueda
        if q:
            query = q.lower()
            name_mask = df["name"].astype(str).str.lower().str.contains(query, na=False)
            id_mask = df["id"].astype(str).str.contains(query, na=False)
            df = df[name_mask | id_mask]
            
        # Filtrado por género
        if genre and genre != "all":
            selected_genres = [g.strip().lower() for g in genre.split(",")]
            def has_genre(row_genres):
                if isinstance(row_genres, list):
                    rg_lower = [g.lower() for g in row_genres]
                    return any(g in rg_lower for g in selected_genres)
                if isinstance(row_genres, str):
                    rg_lower = row_genres.lower()
                    return any(g in rg_lower for g in selected_genres)
                return False
            df = df[df["genres"].apply(has_genre)]
        else:
            # Excluir contenido sexual y desnudez por defecto
            excluded_genres = ["sexual content", "nudity"]
            def has_excluded(row_genres):
                if isinstance(row_genres, list):
                    rg_lower = [g.lower() for g in row_genres]
                    return any(g in rg_lower for g in excluded_genres)
                if isinstance(row_genres, str):
                    rg_lower = row_genres.lower()
                    return any(g in rg_lower for g in excluded_genres)
                return False
            df = df[~df["genres"].apply(has_excluded)]
            
        # Filtrado por precio
        if prices and prices != "all":
            import operator
            from functools import reduce
            price_ranges = []
            for p_range in prices.split(","):
                try:
                    p_min, p_max = map(float, p_range.split("_"))
                    price_ranges.append((p_min, p_max))
                except ValueError:
                    continue
            
            if price_ranges:
                price_masks = []
                for p_min, p_max in price_ranges:
                    if p_max >= 0:
                        mask = (df["price_overview"] >= p_min) & (df["price_overview"] <= p_max)
                    else:
                        mask = df["price_overview"] >= p_min
                    price_masks.append(mask)
                
                final_mask = reduce(operator.or_, price_masks)
                df = df[final_mask]
        
        # Ordenación
        if sort == "asc":
            df = df.iloc[::-1] # Asumimos que el DF ya viene ordenado por popularidad/desc
            
        return _df_rows_to_list(df, offset=offset, limit=limit)
    except Exception as e:
        print(f"Error en /api/search: {e}")
        return {"games": [], "has_more": False}

@app.get("/api/game/{appid}")
def get_game(appid: int):
    """Obtener detalles de un juego."""
    try:
        df = app.state.games_df
        # Tolerancia a tipos: convertir la columna a numérico para asegurar el match
        match = df[pd.to_numeric(df["id"], errors='coerce') == appid]
        if match.empty:
            return JSONResponse(status_code=404, content={"error": "Juego no encontrado"})
        
        row_dict = match.iloc[0].fillna("").to_dict()
        
        # Asegurar compatibilidad de nombres de clave esperados por el frontend
        row_dict["appid"] = int(row_dict.get("id", appid))
        row_dict["banner_url"] = row_dict.get("img", "")
        
        # En caso de que se llamen positive/negative en lugar de positive_reviews/negative_reviews
        row_dict["positive_reviews"] = int(row_dict.get("positive", 0) or row_dict.get("positive_reviews", 0) or 0)
        row_dict["negative_reviews"] = int(row_dict.get("negative", 0) or row_dict.get("negative_reviews", 0) or 0)
        
        # Mapeos de datos del Parquet
        row_dict["developer"] = str(row_dict.get("developers", "Unknown"))
        row_dict["total_reviews_at_launch"] = int(row_dict.get("total_reviews", 0) or 0)

        # Obtener posibles descuentos en tiempo real de Steam para el price_overview
        try:
            steam_info = get_appdetails(str(appid))
            row_dict["discount"] = steam_info.get("price_overview", {}).get("final_formatted", "Unknown")
            row_dict["discount_percent"] = steam_info.get("price_overview", {}).get("discount_percent", 0)
        except Exception as e:
            print(f"No se pudo obtener price_overview de Steam para {appid}: {e}")
            row_dict["discount"] = "Unknown"
            row_dict["discount_percent"] = 0

        row_dict["release_date"] = str(row_dict.get("release_date", "Unknown"))
        
        genres_data = row_dict.get("genres", "")
        if isinstance(genres_data, str) and genres_data:
            row_dict["genres"] = [g.strip() for g in genres_data.split(",")]
        elif not isinstance(genres_data, list):
            row_dict["genres"] = ["Aventura"] # Default si está vacío
            
        return row_dict
    except Exception as e:
        print(f"Error en /api/game/{appid}: {e}")
        return JSONResponse(status_code=500, content={"error": "Error interno del servidor"})

@app.get("/api/trending")
def get_trending(page: int = 1, limit: int = 40, sort: str = "desc", genre: str = "", prices: str = ""):
    """Todos los juegos del catálogo con filtros."""
    return search_games(q="", page=page, limit=limit, sort=sort, genre=genre, prices=prices)

@app.get("/api/filter-options")
def get_filter_options():
    """Obtener lista de géneros únicos y opciones de precio."""
    try:
        df = app.state.games_df
        
        # Extraer géneros
        all_genres = set()
        for g_list in df["genres"]:
            if isinstance(g_list, list):
                all_genres.update(g_list)
            elif isinstance(g_list, str):
                # Limpiar si es string tipo "['A','B']" o "A, B"
                cleaned = g_list.replace("[", "").replace("]", "").replace("'", "").split(",")
                all_genres.update([c.strip() for c in cleaned if c.strip()])
        
        sorted_genres = sorted(list(all_genres))
        
        # Opciones de precio específicas
        price_options = [
            {"label": "Todos", "min": 0, "max": -1},
            {"label": "Gratis", "min": 0, "max": 0},
            {"label": "0.01 - 5€", "min": 0.01, "max": 5},
            {"label": "5.01 - 10€", "min": 5.01, "max": 10},
            {"label": "10.01 - 15€", "min": 10.01, "max": 15},
            {"label": "15.01 - 20€", "min": 15.01, "max": 20},
            {"label": "20.01 - 30€", "min": 20.01, "max": 30},
            {"label": "30.01 - 40€", "min": 30.01, "max": 40},
            {"label": "> 40€", "min": 40.01, "max": -1}
        ]
        
        # Extraer edades
        all_ages = set()
        if "required_age" in df.columns:
            all_ages.update(df["required_age"].unique())
        elif "required_age" in df.iloc[0].index if not df.empty else False: # fallback
            all_ages.update(df["required_age"].unique())
        else:
            # Fallback a valores comunes si no está la columna
            all_ages = {0, 3, 7, 12, 16, 18}
        
        sorted_ages = sorted([int(a) for a in all_ages if pd.notna(a)])
        
        return {
            "genres": sorted_genres,
            "prices": price_options,
            "ages": sorted_ages,
            "max_languages": 74
        }
    except Exception as e:
        print(f"Error en /api/filter-options: {e}")
        return {"genres": [], "prices": [], "ages": [0, 3, 7, 12, 16, 18], "max_languages": 74}

# endregion

#region predictions
@app.post("/api/predict/popularidad", response_model=PopularityResponse)
def predict_popularidad(req: PredictionRequest):
    """Predicción de popularidad (stub)."""
    print('Predicting popularity')
    appid = str(req.appid)
    data = get_appdetails(appid)
    release_date = data['release_date']
    data['appreviewshistogram'] = get_appreviewshistogram(appid, release_date)
    print(data)

    header_url = data['header_url']
    brillo, v_clip = get_image_metadata(header_url)
    print(brillo)
    print(v_clip, len(v_clip))

    name = data['name']
    print(name, release_date)
    yt_data = get_video_data(name, release_date)
    print(yt_data)

    # El transformador espera un dict con la clave "video_statistics"
    yt_stats = {"video_statistics": yt_data}
    
    row = transform_for_popularity(data, appid, app.state.historic_data, v_clip, brillo, data['appreviewshistogram'], yt_stats)
    
    # Instanciamos el modelo para usar su lógica de preprocesamiento
    dummy_model = MLPPopularity(minio={"minio_write": False, "minio_read": False})
    config = {"avoid_multicol": False}
    df_prep = dummy_model._preprocess_data(row, config)
    if "recomendaciones_totales" in df_prep.columns:
        df_prep = df_prep.drop(columns=["recomendaciones_totales"])
    
    # Extraemos el modelo del diccionario
    model = app.state.model_popularity.get('model') if isinstance(app.state.model_popularity, dict) else app.state.model_popularity
    prediction = model.predict(df_prep)
    print('Prediction',prediction)

    reviews_pred = int(round(float(prediction[0])))
    return PopularityResponse(reviews=reviews_pred)


@app.post("/api/predict/precio", response_model=PriceResponse)
def predict_precio(req: PredictionRequest):
    """Predicción de precio (stub)."""
    print('Predicting prices')
    appid = str(req.appid)
    data = get_appdetails(appid)
    print(data)

    header_url = data['header_url']
    brillo, v_clip = get_image_metadata(header_url)
    print(brillo)
    print(v_clip, len(v_clip))

    print("Transforming data to dataFrame")
    row = transform_for_prices(data, appid, app.state.historic_data, v_clip, brillo )
    print(row)
    print(row.columns)

    prediction = app.state.model_price.predict(row)

    idx = int(round(float(prediction[0])))
    idx = max(0, min(idx, len(PRICE_ORDER) - 1))
    range_label = PRICE_ORDER[idx]

    print('Predicción', range_label, prediction)
    return PriceResponse(price=range_label)

@app.post("/api/predict/reviews/topics", response_model=ReviewsTopicsResponse)
def predict_reviews(req: PredictionRequest):
    """Predicción de sentimiento de reseñas (stub)."""
    appid = str(req.appid)
    reviews_list = get_reviews_text(appid)
    print(reviews_list)
    print(len(reviews_list))

    reviews_df = to_dataframe(reviews_list)

    #TODO: llamar al modelo y predecir
    return ReviewsTopicsResponse(['Nebullet Party', 'GymFlex'])

@app.post("/api/predict/reviews", response_model=ReviewsValueResponse)
def predict_review_value(req : PredictionReviewsRequest):
    """Predice si una reseña es positiva (True) o negativa (False)"""
    text = clean_text(req.review)
    row = pd.DataFrame(
        {
            'is_positive' : 'dummy',
            'text' : [text] # Aseguramos que sea una lista para evitar errores de longitud
        })

    prediction = predict_logistic_regression(app.state.model_reviews, row, None )
    return ReviewsValueResponse( value=bool(prediction[0]))

# endregion

@app.post("/api/youtube/search")
def youtube_search(req: YouTubeSearchRequest):
    """Busca vídeos en YouTube antes de la fecha de publicación."""
    try:
        results = get_video_data(req.name, req.release_date)
        return results
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/api/predict/custom")
async def predict_custom_game(req: CustomGameRequest):
    """
    Predicción real de precio y popularidad para un juego personalizado.
    Utiliza los vídeos seleccionados por el usuario para las estadísticas de YouTube.
    """
    try:
        # 1. Preparar géneros y categorías
        mapped_genres = [{"description": g} for g in req.genres]
        mapped_categories = [{"description": c} for c in req.categories]
        
        # 2. Crear objeto 'data' similar al de Steam API
        custom_data = {
            "name": req.name,
            "developers": [req.developer],
            "publishers": [req.developer],
            "genres": mapped_genres,
            "categories": mapped_categories,
            "release_date": req.release_date, # String directo para pd.to_datetime
            "supported_languages": ["English"] * req.languages_count, # Lista para len()
            "header_url": "",
            "short_description": ' '*100,
            "img": req.image
        }

        # 3. Datos Multimedia
        brillo, v_clip = get_image_metadata(custom_data['img'])
        # Usar los vídeos de YouTube seleccionados por el usuario
        yt_data = req.youtube_videos
        
        app_reviews = {"rollups": {"recommendations_up": 0, "recommendations_down": 0}}
        
        # 4. Transformación para Popularidad
        # Envolvemos yt_data para el transformador
        yt_stats = {"video_statistics": yt_data}
        
        row_pop = transform_for_popularity(
            custom_data, "0", app.state.historic_data, 
            v_clip, brillo, app_reviews, yt_stats
        )

        # Inyectar historial real si el desarrollador existe en la base de datos
        try:
            dev_name = req.developer.lower().strip()
            h_df = app.state.historic_data
            dev_col = 'developers' if 'developers' in h_df.columns else 'developer' if 'developer' in h_df.columns else None
            if dev_col:
                match_dev = h_df[h_df[dev_col].astype(str).str.lower().str.contains(dev_name, na=False)]
                if not match_dev.empty:
                    latest_stats = match_dev.iloc[-1]
                    for col in POP_HISTORY_COLS:
                        if col in latest_stats:
                            row_pop.loc[0, col] = latest_stats[col]
        except Exception as e:
            print(f"Error in history injection (Pop): {e}")
        
        # Preprocesamiento específico del modelo MLP
        dummy_model = MLPPopularity(minio={"minio_write": False, "minio_read": False})
        df_prep = dummy_model._preprocess_data(row_pop, {"avoid_multicol": False})
        if "recomendaciones_totales" in df_prep.columns:
            df_prep = df_prep.drop(columns=["recomendaciones_totales"])
            
        model_pop = app.state.model_popularity.get('model') if isinstance(app.state.model_popularity, dict) else app.state.model_popularity
        pop_pred = model_pop.predict(df_prep)
        popularity = int(round(float(pop_pred[0])))

        # 5. Transformación para Precio
        row_price = transform_for_prices(
            custom_data, "0", app.state.historic_data, v_clip, brillo
        )

        # Inyectar historial real para precio
        try:
            if dev_col:
                match_dev = h_df[h_df[dev_col].astype(str).str.lower().str.contains(dev_name, na=False)]
                if not match_dev.empty:
                    latest_stats = match_dev.iloc[-1]
                    for col in PRICE_HISTORY_COLS:
                        if col in latest_stats:
                            row_price.loc[0, col] = latest_stats[col]
        except Exception as e:
            print(f"Error in history injection (Price): {e}")

        price_pred = app.state.model_price.predict(row_price)
        
        idx = int(round(float(price_pred[0])))
        idx = max(0, min(idx, len(PRICE_ORDER) - 1))
        price_label = PRICE_ORDER[idx]
        
        return {
            "price": price_label,
            "popularity": popularity
        }
    except Exception as e:
        print(f"Error en predicción custom: {e}")
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"Error en la predicción: {str(e)}"})