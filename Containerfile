FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
# Default uploads directory inside the container (can be overridden at runtime)
ENV UPLOAD_DIR=/uploads

WORKDIR /app

# Install runtime dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

# Add an entrypoint that ensures the upload directory exists
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create a non-root user for running the app and ensure upload dir exists
RUN groupadd -g 1000 appuser || true \
 && useradd -m -u 1000 -g appuser appuser || true \
 && mkdir -p "$UPLOAD_DIR" \
 && chown -R appuser:appuser "$UPLOAD_DIR" || true

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python3 -c "import urllib.request, sys; import urllib.error; url='http://127.0.0.1:5000/';\
try: resp = urllib.request.urlopen(url, timeout=5); sys.exit(0 if getattr(resp, 'status', 200) == 200 else 1)\
except Exception: sys.exit(1)"

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "web_app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]
