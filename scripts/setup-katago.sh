#!/usr/bin/env bash
# KataGo 바이너리 및 네트워크 파일 다운로드
# 사용: bash scripts/setup-katago.sh
# 또는: make models

set -euo pipefail

MODELS_DIR="$(cd "$(dirname "$0")/.." && pwd)/models"
mkdir -p "$MODELS_DIR"

KATAGO_VERSION="v1.14.1"
OS="$(uname -s)"

echo "=== KataGo $KATAGO_VERSION 설정 ==="
echo "다운로드 경로: $MODELS_DIR"

# ── 1. KataGo 바이너리 ─────────────────────────────────────────────────────

KATAGO_BIN="$MODELS_DIR/katago"

if [[ -f "$KATAGO_BIN" ]]; then
    echo "✓ KataGo 바이너리 이미 존재: $KATAGO_BIN"
else
    case "$OS" in
        Linux)
            URL="https://github.com/lightvector/KataGo/releases/download/${KATAGO_VERSION}/katago-${KATAGO_VERSION}-opencl-linux-x86_64.zip"
            ;;
        Darwin)
            URL="https://github.com/lightvector/KataGo/releases/download/${KATAGO_VERSION}/katago-${KATAGO_VERSION}-opencl-macos-arm64.zip"
            ;;
        MINGW*|MSYS*|CYGWIN*)
            echo "Windows: PowerShell 스크립트를 사용하세요: scripts/setup-katago.ps1"
            exit 1
            ;;
        *)
            echo "지원하지 않는 OS: $OS"
            exit 1
            ;;
    esac

    echo "다운로드 중: $URL"
    curl -L "$URL" -o "$MODELS_DIR/katago.zip"
    unzip -o "$MODELS_DIR/katago.zip" -d "$MODELS_DIR"
    chmod +x "$KATAGO_BIN" 2>/dev/null || true
    rm -f "$MODELS_DIR/katago.zip"
    echo "✓ KataGo 바이너리 설치됨"
fi

# ── 2. 일반 네트워크 (강한 기보 학습) ─────────────────────────────────────

GENERAL_MODEL="$MODELS_DIR/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz"
GENERAL_URL="https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz"

if [[ -f "$GENERAL_MODEL" ]]; then
    echo "✓ 일반 네트워크 이미 존재"
else
    echo "일반 네트워크 다운로드 중 (~1GB)..."
    curl -L "$GENERAL_URL" -o "$GENERAL_MODEL" --progress-bar
    echo "✓ 일반 네트워크 설치됨"
fi

# ── 3. Human SL 네트워크 (인간 기보 학습) ─────────────────────────────────

HUMAN_MODEL="$MODELS_DIR/b18c384nbt-humanv0.bin.gz"
HUMAN_URL="https://github.com/lightvector/KataGo/releases/download/v1.14.0/b18c384nbt-humanv0.bin.gz"

if [[ -f "$HUMAN_MODEL" ]]; then
    echo "✓ Human SL 네트워크 이미 존재"
else
    echo "Human SL 네트워크 다운로드 중 (~150MB)..."
    curl -L "$HUMAN_URL" -o "$HUMAN_MODEL" --progress-bar
    echo "✓ Human SL 네트워크 설치됨"
fi

# ── 4. KataGo 설정 파일 ────────────────────────────────────────────────────

CONFIG_FILE="$MODELS_DIR/katago_gtp.cfg"

if [[ ! -f "$CONFIG_FILE" ]]; then
    cat > "$CONFIG_FILE" << 'EOF'
# KataGo GTP 설정 — CPU 기반 (GPU 없는 환경용)
numSearchThreads = 4
maxVisits = 800
ponderingEnabled = false

# 로그
logFile = models/katago.log
logAllGTPCommunication = false

# 분석용 설정
reportAnalysisWinratesAs = SIDETOMOVE
EOF
    echo "✓ KataGo 설정 파일 생성됨"
fi

echo ""
echo "=== 설치 완료 ==="
echo "테스트: make test-engine"
echo "또는: models/katago gtp -model $GENERAL_MODEL -config $CONFIG_FILE"
