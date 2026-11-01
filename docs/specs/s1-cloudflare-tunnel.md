# S1-7: Cloudflare Tunnel 설정

## 목적
테스터가 인터넷에서 로컬 개발 서버에 접속할 수 있게 한다.

## 설치 (cloudflared)

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

# Windows (PowerShell)
winget install Cloudflare.cloudflared
```

## 임시 터널 (테스트용, 인증 불필요)

```bash
# web 서비스(3000)를 외부에 노출
cloudflared tunnel --url http://localhost:3000
```

출력 예시:
```
https://xxx-xxx-xxx.trycloudflare.com -> http://localhost:3000
```

이 URL을 테스터에게 공유한다.

## 영구 터널 (베타 운영용, S5)

1. Cloudflare 계정 로그인: `cloudflared login`
2. 터널 생성: `cloudflared tunnel create sudam`
3. `~/.cloudflared/config.yml` 설정:
   ```yaml
   tunnel: <tunnel-id>
   credentials-file: ~/.cloudflared/<tunnel-id>.json
   ingress:
     - hostname: sudam.example.com
       service: http://localhost:3000
     - service: http_status:404
   ```
4. 라우팅: `cloudflared tunnel route dns sudam sudam.example.com`
5. 실행: `cloudflared tunnel run sudam`

## Makefile 통합

```makefile
tunnel:
    cloudflared tunnel --url http://localhost:3000
```

`make dev` 실행 후 별도 터미널에서 `make tunnel` 실행.
