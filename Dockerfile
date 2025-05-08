FROM python:3.10-slim

# Instalar Chromium y dependencias mínimas
RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Variables de entorno para Selenium
ENV GOOGLE_CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
