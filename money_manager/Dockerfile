ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base-python:3.12-alpine3.20
FROM ${BUILD_FROM}

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py core.py ./
COPY templates ./templates
COPY static ./static

ENV MONEY_MANAGER_DB=/config/money_manager.db
EXPOSE 8099
CMD ["python", "app.py"]
