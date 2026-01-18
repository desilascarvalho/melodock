FROM python:3.10-slim

# --- RECEBE O NÚMERO DO SCRIPT EXTERNO ---
# Se não vier nada, usa 0 como padrão
ARG BUILD_NUM=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1. Instalação e Limpeza
COPY requirements.txt .

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    build-essential && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir --force-reinstall https://github.com/yt-dlp/yt-dlp/archive/master.zip && \
    apt-get purge -y --auto-remove git build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 2. Copia o código
COPY . .

# 3. GERA A VERSÃO SEQUENCIAL
# O resultado será algo como: v3.0.15
RUN echo "v3.0.${BUILD_NUM}" > /app/version.txt

# 4. Inicialização
CMD ["python", "run.py"]