FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY csos_mcp ./csos_mcp

EXPOSE 8001

CMD ["uvicorn", "csos_mcp.server:app", "--host", "0.0.0.0", "--port", "8001"]
