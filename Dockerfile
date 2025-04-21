# Stage 1: Builder Stage
FROM python:3.11-slim AS builder

ARG APP_HOME=/mivro-server
# ARG BUILD_ENVIRONMENT="production"

WORKDIR $APP_HOME

# ENV BUILD_ENVIRONMENT=$BUILD_ENVIRONMENT

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /dependencies

# Stage 2: Runner Stage
FROM python:3.11-slim AS runner

WORKDIR $APP_HOME

COPY --from=builder /dependencies /usr/local/lib/python3.11/site-packages
COPY . .

EXPOSE 5000
