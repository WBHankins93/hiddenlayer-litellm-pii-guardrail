FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config ./config
COPY src ./src

ENV PYTHONPATH=/app
ENV PORT=4000

EXPOSE 4000

CMD ["litellm", "--config", "config/litellm.config.yaml", "--host", "0.0.0.0", "--port", "4000"]