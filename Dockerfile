# Stage 1: Builder Stage
FROM python:3.11-slim AS builder

WORKDIR /mivro-server

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --target /dependencies

# Stage 2: Runner Stage
FROM python:3.11-slim AS runner

WORKDIR /mivro-server

COPY --from=builder /dependencies /usr/local/lib/python3.11/site-packages
COPY . .

EXPOSE 5000
