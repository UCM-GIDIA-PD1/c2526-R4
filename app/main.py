"""
Archivo web de SteamPredictor.

Para levantar la página:
> uv run fastapi dev

Puerto: http://127.0.0.1:8000
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi import Request
from pydantic import BaseModel
import random


# --------------------------------------------------------------------------
# Lifespan: se ejecuta al arrancar (startup) y al apagar (shutdown)
# --------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: cargar modelos en memoria
    # app.state.model_popularidad = load('models/popularidad/xgboost_model.pkl')
    # app.state.model_precio = load('models/precios/catboostClustered.pkl')
    # app.state.model_reviews = load('models/reviews/logistic_regression_optuna.pkl')
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
app.mount("/static", StaticFiles(directory="static", html=True), name="static")

# Plantillas Jinja2
templates = Jinja2Templates(directory="templates")


# --------------------------------------------------------------------------
# Modelos Pydantic
# --------------------------------------------------------------------------
class PredictionRequest(BaseModel):
    """Datos de entrada para una predicción."""
    appid: int
    model_name: str = "default"


class PredictionResponse(BaseModel):
    """Resultado de una predicción."""
    value: float
    confidence: float
    model_used: str
    details: dict


class GameInfo(BaseModel):
    """Información básica de un juego."""
    appid: int
    name: str
    banner_url: str
    release_date: str
    developer: str
    genres: list[str]
    price: float
    positive_reviews: int
    negative_reviews: int


# --------------------------------------------------------------------------
# Datos mock para desarrollo (se reemplazarán con datos reales)
# --------------------------------------------------------------------------
MOCK_GAMES = [
    GameInfo(appid=413150, name="Stardew Valley", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/413150/header.jpg", release_date="26 Feb, 2016", developer="ConcernedApe", genres=["RPG", "Simulation", "Farming"], price=13.99, positive_reviews=523847, negative_reviews=5891),
    GameInfo(appid=1245620, name="Elden Ring", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1245620/header.jpg", release_date="25 Feb, 2022", developer="FromSoftware Inc.", genres=["Action", "RPG", "Open World"], price=49.99, positive_reviews=412893, negative_reviews=62341),
    GameInfo(appid=1091500, name="Cyberpunk 2077", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1091500/header.jpg", release_date="10 Dec, 2020", developer="CD PROJEKT RED", genres=["RPG", "Open World", "Action"], price=29.99, positive_reviews=498234, negative_reviews=119823),
    GameInfo(appid=892970, name="Valheim", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/892970/header.jpg", release_date="2 Feb, 2021", developer="Iron Gate AB", genres=["Survival", "Open World", "Co-op"], price=19.99, positive_reviews=345123, negative_reviews=23456),
    GameInfo(appid=1174180, name="Red Dead Redemption 2", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1174180/header.jpg", release_date="5 Dec, 2019", developer="Rockstar Games", genres=["Action", "Adventure", "Open World"], price=39.99, positive_reviews=389234, negative_reviews=67891),
    GameInfo(appid=105600, name="Terraria", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/105600/header.jpg", release_date="16 May, 2011", developer="Re-Logic", genres=["Action", "Adventure", "Sandbox"], price=9.99, positive_reviews=967123, negative_reviews=12345),
    GameInfo(appid=570, name="Dota 2", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/570/header.jpg", release_date="9 Jul, 2013", developer="Valve", genres=["MOBA", "Strategy", "Free to Play"], price=0.00, positive_reviews=1823456, negative_reviews=345678),
    GameInfo(appid=730, name="Counter-Strike 2", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/730/header.jpg", release_date="21 Aug, 2012", developer="Valve", genres=["FPS", "Shooter", "Competitive"], price=0.00, positive_reviews=7234567, negative_reviews=1234567),
    GameInfo(appid=1086940, name="Baldur's Gate 3", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/1086940/header.jpg", release_date="3 Aug, 2023", developer="Larian Studios", genres=["RPG", "Strategy", "Adventure"], price=59.99, positive_reviews=512345, negative_reviews=15234),
    GameInfo(appid=367520, name="Hollow Knight", banner_url="https://shared.cloudflare.steamstatic.com/store_item_assets/steam/apps/367520/header.jpg", release_date="24 Feb, 2017", developer="Team Cherry", genres=["Metroidvania", "Action", "Indie"], price=14.99, positive_reviews=289345, negative_reviews=4567),
]


def _generate_mock_history(base_value: float, months: int = 12) -> list[dict]:
    """Genera datos históricos mock para gráficas."""
    history = []
    current = base_value
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                   "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    for i in range(months):
        variation = random.uniform(-0.15, 0.15) * current
        current = max(0.01, current + variation)
        history.append({"month": month_names[i % 12], "value": round(current, 2)})
    return history


# --------------------------------------------------------------------------
# Página principal
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request, name="index.html")


# --------------------------------------------------------------------------
# API REST — Endpoints JSON (el frontend los llama con fetch())
# --------------------------------------------------------------------------

@app.get("/api/search")
def search_games(q: str = ""):
    """Buscar juegos por nombre."""
    if not q:
        return [g.model_dump() for g in MOCK_GAMES]
    query = q.lower()
    return [g.model_dump() for g in MOCK_GAMES if query in g.name.lower()]


@app.get("/api/game/{appid}")
def get_game(appid: int):
    """Obtener detalles de un juego."""
    for g in MOCK_GAMES:
        if g.appid == appid:
            return g.model_dump()
    return JSONResponse(status_code=404, content={"error": "Juego no encontrado"})


@app.get("/api/trending")
def get_trending():
    """Juegos trending con predicción de tendencia."""
    trending = []
    for g in MOCK_GAMES:
        trending.append({
            **g.model_dump(),
            "trend": random.choice(["up", "down"]),
            "change_percent": round(random.uniform(1, 25), 1),
        })
    return trending


@app.post("/api/predict/popularidad", response_model=PredictionResponse)
def predict_popularidad(req: PredictionRequest):
    """Predicción de popularidad (stub)."""
    base = random.uniform(50000, 500000)
    return PredictionResponse(
        value=round(base),
        confidence=round(random.uniform(0.72, 0.95), 2),
        model_used="XGBoost (Log)",
        details={
            "metric": "estimated_owners",
            "unit": "jugadores",
            "history": _generate_mock_history(base),
            "feature_importance": {
                "reviews_count": 0.34, "price": 0.21,
                "genres": 0.18, "developer_reputation": 0.15, "release_year": 0.12,
            },
        },
    )


@app.post("/api/predict/precio", response_model=PredictionResponse)
def predict_precio(req: PredictionRequest):
    """Predicción de precio (stub)."""
    base = round(random.uniform(4.99, 59.99), 2)
    return PredictionResponse(
        value=base,
        confidence=round(random.uniform(0.65, 0.92), 2),
        model_used="CatBoost Clustered",
        details={
            "metric": "predicted_price",
            "unit": "€",
            "history": _generate_mock_history(base),
            "price_range": {"min": round(base * 0.7, 2), "max": round(base * 1.3, 2)},
        },
    )


@app.post("/api/predict/reviews", response_model=PredictionResponse)
def predict_reviews(req: PredictionRequest):
    """Predicción de sentimiento de reseñas (stub)."""
    ratio = round(random.uniform(0.55, 0.96), 2)
    return PredictionResponse(
        value=ratio,
        confidence=round(random.uniform(0.70, 0.93), 2),
        model_used="Logistic Regression (Optuna)",
        details={
            "metric": "positive_ratio",
            "unit": "ratio",
            "sentiment_distribution": {
                "very_positive": round(random.uniform(0.2, 0.5), 2),
                "positive": round(random.uniform(0.1, 0.3), 2),
                "mixed": round(random.uniform(0.05, 0.15), 2),
                "negative": round(random.uniform(0.02, 0.1), 2),
                "very_negative": round(random.uniform(0.01, 0.05), 2),
            },
            "history": _generate_mock_history(ratio * 100),
        },
    )
