FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    gcc \
    libc6-dev \
    openjdk-17-jdk-headless \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY . .

RUN pip3 install --no-cache-dir -r requirements.txt

# Build frontend (if frontend folder exists)
RUN if [ -d "frontend" ]; then \
    cd frontend && npm install && npm run build ; \
    fi

RUN useradd -m -s /bin/bash runner
USER runner

EXPOSE 10000

CMD ["sh","-c","uvicorn app:app --host 0.0.0.0 --port ${PORT:-10000}"]