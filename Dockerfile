FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY duebuddy_mcp ./duebuddy_mcp

RUN pip install --no-cache-dir .

# stdio transport: the server talks to the MCP client over stdin/stdout.
ENTRYPOINT ["duebuddy-mcp"]
