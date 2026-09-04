FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Minimal runtime dependency (~200 KB instead of ~380 MB of compilers)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Cached dependencies layer: runs only when requirements.txt changes
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Project source code
COPY . /app/

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]