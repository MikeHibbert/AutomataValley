FROM python:3.11-slim

WORKDIR /app

COPY bridge/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY bridge /app/bridge

WORKDIR /app
CMD ["uvicorn", "bridge.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
