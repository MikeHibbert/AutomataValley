FROM python:3.11-slim

WORKDIR /app

COPY valley/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY valley /app/valley

WORKDIR /app
CMD ["uvicorn", "valley.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
