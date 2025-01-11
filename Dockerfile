# syntax=docker/dockerfile:1

# See https://docs.docker.com/go/dockerfile-reference/ for help

# Define python version
ARG PYTHON_VERSION=3.13.1
FROM python:${PYTHON_VERSION}-slim AS base

# Do not write pyc-files
ENV PYTHONDONTWRITEBYTECODE=1

# Do not buffer stdout and stderr
ENV PYTHONBUFFERED=1

WORKDIR /app


# Create a user to run the app with
# https://docs.docker.com/go/dockerfile-user-best-practices/

ARG UID
ARG GID

RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid ${UID} \
    appuser

# Download dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

# Copy program files to container
COPY . .

# Create datadirectory
RUN mkdir -p /app/db_data

RUN chmod -R a+r /app
RUN chown -R appuser:appuser /app
# RUN chown appuser:appuser /app/data

# RUN chmod 777 /app/data
# RUN chmod 777 /app/data/database.db

# Switch to appuser from root
USER appuser

# Expose port for the api
EXPOSE 8000

# Run application
# CMD python3 -m uvicorn api:app --host=0.0.0.0 --port=8000
# CMD python3 -m fastapi run
# CMD python3 -m http.server 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]


