FROM python:3.12-slim

# KataGo eigenavx2 의존성: libzip5 + libssl1.1 (Debian 13에 없는 OpenSSL 1.1)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl unzip libzip5 && \
    rm -rf /var/lib/apt/lists/*

# libssl 1.1 — KataGo eigen 바이너리가 요구. Debian 11(Bullseye) 보안 아카이브에서 설치
RUN curl -fsSL "http://deb.debian.org/debian/pool/main/o/openssl/libssl1.1_1.1.1w-0%2Bdeb11u1_amd64.deb" \
        -o /tmp/libssl1.1.deb && \
    dpkg -i /tmp/libssl1.1.deb && \
    rm /tmp/libssl1.1.deb

# KataGo CPU-only (eigenavx2) 바이너리 설치 — v1.15.0+: Human SL 네트워크 지원
RUN curl -fsSL "https://github.com/lightvector/KataGo/releases/download/v1.15.0/katago-v1.15.0-eigenavx2-linux-x64.zip" \
        -o /tmp/katago.zip && \
    unzip /tmp/katago.zip -d /tmp/katago_dir && \
    find /tmp/katago_dir -name "katago" -type f -exec install -m755 {} /usr/local/bin/katago \; && \
    rm -rf /tmp/katago.zip /tmp/katago_dir

RUN pip install uv

WORKDIR /app

COPY packages/go-core /packages/go-core
COPY packages/analysis /packages/analysis
COPY packages/engine-pool /packages/engine-pool
COPY packages/verifier /packages/verifier

COPY apps/ai-service/. .
RUN sed -i 's|path = "../../packages/|path = "/packages/|g' pyproject.toml && \
    uv pip install --system -e ".[dev]"

EXPOSE 8000
CMD ["uvicorn", "ai_service.app:app", "--host", "0.0.0.0", "--port", "8000"]
