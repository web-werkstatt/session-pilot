FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5055

ENV PYTHONUNBUFFERED=1

CMD ["python3", "app.py"]
