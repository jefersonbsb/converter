FROM python:3.12.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install LibreOffice + OCR + common fonts
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libreoffice \
    libreoffice-writer \
    tesseract-ocr \
    tesseract-ocr-por \
    fonts-dejavu \
    fonts-liberation \
    && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create and set the working directory
WORKDIR /app

# Copy dependency file and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY . .

# Run as non-root
RUN useradd -m -u 10001 appuser && \
    mkdir -p /tmp/file-converter-api && \
    chown -R appuser:appuser /app /tmp/file-converter-api
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3004/', timeout=3)" || exit 1

# Expose the port the API will run on
EXPOSE 3004

# Run the application with uvicorn (trust reverse proxy / Cloudflare forwarded headers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3004", "--proxy-headers", "--forwarded-allow-ips", "*"]
