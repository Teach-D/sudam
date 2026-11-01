# KataGo 모델 파일 다운로드 (Windows)
# 사용: .\scripts\setup-katago.ps1
# 바이너리는 Docker 이미지 빌드 시 자동 설치됨

param(
    [switch]$SmallModel  # 소형 모델 사용 (~150MB 대신 ~800MB)
)

$ErrorActionPreference = "Stop"
$ModelsDir = Join-Path $PSScriptRoot "..\models"
New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

Write-Host "=== KataGo 모델 다운로드 ===" -ForegroundColor Cyan
Write-Host "저장 경로: $ModelsDir"

# ── 메인 모델 ──────────────────────────────────────────────────────────────
if ($SmallModel) {
    $ModelFile = Join-Path $ModelsDir "b18c384nbt-humanv0.bin.gz"
    $ModelUrl  = "https://github.com/lightvector/KataGo/releases/download/v1.14.0/b18c384nbt-humanv0.bin.gz"
    $ModelDesc = "Human SL 모델 (~150MB, 인간적인 기풍)"
} else {
    $ModelFile = Join-Path $ModelsDir "kata1-b28c512nbt-s9584861952-d4960414494.bin.gz"
    $ModelUrl  = "https://media.katagotraining.org/uploaded/networks/models/kata1/kata1-b28c512nbt-s9584861952-d4960414494.bin.gz"
    $ModelDesc = "풀 강도 모델 (~800MB, 프로 수준)"
}

if (Test-Path $ModelFile) {
    Write-Host "✓ 모델 이미 존재: $(Split-Path $ModelFile -Leaf)" -ForegroundColor Green
} else {
    Write-Host "다운로드 중: $ModelDesc"
    Write-Host "URL: $ModelUrl"
    Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile -UseBasicParsing
    Write-Host "✓ 모델 다운로드 완료" -ForegroundColor Green
}

# ── .env 자동 업데이트 ─────────────────────────────────────────────────────
$EnvFile = Join-Path $PSScriptRoot "..\\.env"
if (-not (Test-Path $EnvFile)) {
    Copy-Item (Join-Path $PSScriptRoot "..\.env.example") $EnvFile
}

$RelModelPath = "./models/$(Split-Path $ModelFile -Leaf)"
$EnvContent = Get-Content $EnvFile -Raw

if ($EnvContent -match "KATAGO_MODEL=") {
    $EnvContent = $EnvContent -replace "KATAGO_MODEL=.*", "KATAGO_MODEL=$RelModelPath"
} else {
    $EnvContent += "`nKATAGO_MODEL=$RelModelPath"
}

if ($EnvContent -match "KATAGO_MOCK=") {
    $EnvContent = $EnvContent -replace "KATAGO_MOCK=.*", "KATAGO_MOCK=false"
} else {
    $EnvContent += "`nKATAGO_MOCK=false"
}

Set-Content $EnvFile $EnvContent -NoNewline
Write-Host "✓ .env 업데이트 완료 (KATAGO_MODEL, KATAGO_MOCK=false)" -ForegroundColor Green

Write-Host ""
Write-Host "=== 완료 ===" -ForegroundColor Cyan
Write-Host "이제 다음 명령으로 서버를 재시작하세요:"
Write-Host "  docker compose up --build -d ai-service" -ForegroundColor Yellow
