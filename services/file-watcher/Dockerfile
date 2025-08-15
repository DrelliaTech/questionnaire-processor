FROM public.ecr.aws/lambda/python:3.11

# Copy requirements
COPY pyproject.toml poetry.lock* ./
COPY src/ ./src/

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy shared packages
COPY ../../shared/models /opt/python/drellia_models
COPY ../../shared/utils /opt/python/drellia_utils

# Set the CMD to your handler
CMD ["src.handler.lambda_handler"]