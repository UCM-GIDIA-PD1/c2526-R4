# El Containerfile es una lista de pasos que se ejecutan para crear la imagen del proyecto con la que posteriormente se puede ejecutar un contenedor.

# Pthon base
FROM python:3.13-slim 

# Copiar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Establecer el directorio de trabajo
WORKDIR /steam_predictor

# Copiar todo el código y ficheros de dependencias
COPY pyproject.toml README.md uv.lock ./
COPY app/pyproject.toml app/
COPY . .
RUN UV_INDEX_PYTORCH_CU118="https://download.pytorch.org/whl/cpu" uv sync --frozen --no-cache --no-group not_in_container

# Establecer puerto
EXPOSE 8000

# Añadir directorio de trabajo y entrar en app
ENV PYTHONPATH="/steam_predictor"
WORKDIR /steam_predictor/app

# Comando que se ejecuta al encender el contenedor (no al crear la imagen)
CMD ["/steam_predictor/.venv/bin/fastapi", "run", "main.py", "--port", "8000", "--host", "0.0.0.0"]