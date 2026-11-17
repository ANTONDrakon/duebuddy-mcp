FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py ./

# stdio-транспорт: сервер общается с MCP-клиентом через stdin/stdout.
ENTRYPOINT ["python", "/app/server.py"]
