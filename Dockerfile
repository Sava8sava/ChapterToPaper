FROM python:3.14-slim 

# Evita que o Python gere arquivos .pyc e buffers de log
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app 

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gcc \
    python3-dev \
    libxml2-dev \
    libxslt-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt 

RUN playwright install --with-deps firefox 

COPY . .

VOLUME ["/app/downloads","/app/config"] 

ENTRYPOINT ["python", "main.py"]
