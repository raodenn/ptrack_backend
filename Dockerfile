FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# Install minimal runtime dependencies + curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependency cache layer: only rebuilds when requirements.txt changes
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app/

COPY entrypoint.sh /entrypoint.sh

# Set up non-root user and grant execution rights
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser \
    && sed -i 's/\r$//' /entrypoint.sh \
    && chmod 755 /entrypoint.sh \
    && chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["gunicorn", "ptrack_configuration.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]