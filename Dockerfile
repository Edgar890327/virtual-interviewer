FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY static ./static

EXPOSE 8000

#CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "600"]
# ... (el resto de tu Dockerfile se queda igual)

# Añadimos los timeouts al final (ejemplo: 120 segundos)
#CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "600"]

