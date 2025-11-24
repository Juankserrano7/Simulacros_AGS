# Imagen base ligera con Python
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias del sistema necesarias para pandas/numpy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc git \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . /app

# Puerto por defecto de Streamlit
EXPOSE 8501

# Comando de inicio
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
