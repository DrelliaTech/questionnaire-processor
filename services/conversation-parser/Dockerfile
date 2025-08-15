FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml poetry.lock* ./
COPY src/ ./src/

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy shared packages
COPY ../../shared/models /app/drellia_models
COPY ../../shared/database /app/drellia_database
COPY ../../shared/utils /app/drellia_utils

# Run the service
CMD ["python", "src/main.py"]