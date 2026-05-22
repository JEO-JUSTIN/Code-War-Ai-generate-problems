FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    gcc \
    libc6-dev \
    openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 10000

CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]