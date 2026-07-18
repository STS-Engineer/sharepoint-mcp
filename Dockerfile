FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .
ENV HOST=0.0.0.0 PORT=8000 MCP_TRANSPORT=streamable-http
EXPOSE 8000
CMD ["python", "server.py"]
