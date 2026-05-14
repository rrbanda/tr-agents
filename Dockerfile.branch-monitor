FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml config.yaml README.md ./
COPY shared/ shared/
COPY agents/ agents/

RUN pip install --no-cache-dir . && \
    chmod -R a+w /usr/local/lib/python3.12/site-packages/google/adk/cli/browser/assets/config/ 2>/dev/null || true

EXPOSE 8000

ENV PYTHONPATH=/app

CMD ["adk", "web", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--a2a", \
     "--session_service_uri", "memory://", \
     "--log_level", "info", \
     "/app/agents"]
