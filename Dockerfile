FROM python:3.10-slim

ARG APP_VERSION="v0.0" 
ENV APP_VERSION=${APP_VERSION}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir spotipy && \
    pip install --no-cache-dir git+https://gitlab.com/RemixDev/deezer-py.git && \
    pip install --no-cache-dir git+https://gitlab.com/RemixDev/deemix-py.git

COPY . .

RUN echo "${APP_VERSION}" > /app/version.txt

RUN mkdir -p /config /music /downloads && chmod -R 777 /config /music /downloads

CMD ["python", "run.py"]