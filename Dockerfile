FROM python:3.11-slim
WORKDIR /app
RUN pip install uv
COPY pyproject.toml uv.lock ./
RUN uv pip install --system .
COPY src ./src
COPY config ./config
COPY data ./data
EXPOSE 8001
CMD ["uv", "run", "src/servers/research_server.py"]
