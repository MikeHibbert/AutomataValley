FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY stt/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY stt /app/stt

WORKDIR /app
CMD ["uvicorn", "stt.app.main:app", "--host", "0.0.0.0", "--port", "8003"]
