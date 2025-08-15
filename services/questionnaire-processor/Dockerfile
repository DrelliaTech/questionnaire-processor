FROM public.ecr.aws/lambda/python:3.11

# Install system dependencies
RUN yum install -y gcc postgresql-devel && yum clean all

# Copy requirements
COPY pyproject.toml poetry.lock* ./
COPY src/ ./src/

# Install poetry and dependencies
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Copy shared packages
COPY ../../shared/models /opt/python/drellia_models
COPY ../../shared/database /opt/python/drellia_database
COPY ../../shared/utils /opt/python/drellia_utils

# Set the CMD to your handler
CMD ["src.main.lambda_handler"]