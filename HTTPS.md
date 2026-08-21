# HTTPS 적용 가이드

운영 서버를 `http://`로 열어두면 **로그인 비밀번호와 접속 토큰이 평문으로**
네트워크를 지나갑니다. 실제로 중간자 프록시를 놓고 측정한 결과는 다음과 같습니다.

```
POST /auth/jwt/login HTTP/1.1
username=a@e.com&password=testpass123          ← 비밀번호가 그대로

GET /todos HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...  ← 토큰이 그대로
```

가로챈 토큰만으로 비밀번호 없이 계정에 접근됩니다. 그리고 JWT는 **암호화가 아니라
서명**이므로 페이로드는 키 없이 디코딩됩니다.

```json
{"sub": "1", "aud": ["fastapi-users:auth"], "exp": 1787885885}
```

`JWT_SECRET`은 *위조*를 막을 뿐 *엿보기*를 막지 못합니다. 토큰은 7일간 유효하고,
비밀번호를 바꿔도 이미 발급된 토큰은 무효화되지 않습니다(`JWT_SECRET`을 바꿔야 함).

노출되는 구간은 브라우저부터 서버까지 전부입니다 — 공용 WiFi, 사내 네트워크 장비,
ISP, 데이터센터 네트워크.

---

## 지금 당장 할 수 있는 조치: SSH 터널 (권장)

**도메인·인증서·비용·코드 변경이 전혀 없고, SSH가 구간을 암호화합니다.**
혼자 쓰는 개인 앱이라면 이것만으로 충분합니다.

서버에서 — 외부에 포트를 열지 말고 localhost에만 바인딩:

```bash
./run.sh 8000 127.0.0.1     # 0.0.0.0(전체 공개)이 아니라 127.0.0.1
```

내 노트북에서 — 터널을 연결한 뒤 로컬 주소로 접속:

```bash
ssh -N -L 8000:127.0.0.1:8000 oci-free
# 브라우저에서 http://localhost:8000 접속
```

이러면 인터넷에서 서버의 8000 포트에 아예 닿을 수 없고, 트래픽은 SSH 암호화 구간을
지나갑니다. 스캐너·무단 가입 시도도 함께 사라집니다.

한계: **터널을 연 기기에서만** 접속됩니다. 휴대폰에서 바로 쓰거나 다른 사람과
공유해야 한다면 아래 방식으로 가야 합니다.

---

## 방식별 비교

| 방식 | 도메인 | 비용 | 휴대폰에서 바로 | 특징 |
| --- | --- | --- | --- | --- |
| **SSH 터널** | 불필요 | 무료 | ✗ (앱 설치·설정 필요) | 즉시 적용. 포트를 닫아둘 수 있어 공격면이 가장 작다 |
| **Tailscale VPN** | 불필요 | 무료 | ○ (앱 설치 필요) | 포트 미개방. 기기마다 설치. 사설망 안에서만 접속 |
| **Caddy + Let's Encrypt** | 필요 | 도메인 값만 | ○ | 진짜 공개 HTTPS. 인증서 자동 발급·갱신 |
| **Cloudflare Tunnel** (Named) | 필요 | 무료 | ○ | 포트 미개방. 트래픽이 Cloudflare를 경유 |
| Cloudflare Quick Tunnel | 불필요 | 무료 | ○ | **재시작하면 URL이 바뀜.** 테스트 전용 — 아래 참고 |

앱 코드는 **어느 방식이든 수정할 필요가 없습니다.** 서버 앞단만 바뀝니다.

### Cloudflare Tunnel의 도메인 요건

두 종류가 있고, 도메인 요건이 다릅니다.

- **Named Tunnel** (운영용): 도메인이 필요하고, 소유만으로는 부족합니다.
  그 도메인의 **DNS를 Cloudflare로 옮겨(zone 등록)** 야 합니다. 다른 업체에서 산
  도메인을 그 업체 네임서버에 그대로 두고 쓸 수는 없습니다.
- **Quick Tunnel** (TryCloudflare): 도메인도 계정도 필요 없고 랜덤
  `*.trycloudflare.com` 주소를 받습니다. 다만 Cloudflare가 **"테스트·개발 전용"**
  이라고 명시하고, **가동시간(SLA)을 보장하지 않으며, 프로세스를 재시작하면 URL이
  바뀝니다.** 동시 요청 200개 제한과 SSE 미지원 제약도 있습니다(이 앱은 SSE를 쓰지
  않으므로 후자는 무관).

즉 **매일 쓰는 앱을 도메인 없이 Cloudflare로 붙이는 것은 현실적이지 않습니다.**
주소가 계속 바뀌어 북마크가 불가능합니다. 도메인을 둘 생각이 없다면 Tailscale이나
SSH 터널을 쓰세요.

---

## Caddy 방식 (공개 HTTPS가 필요할 때)

사전 조건: 도메인 하나, 그 도메인의 A 레코드를 서버 공인 IP로 지정, OCI
보안 목록/방화벽에서 80·443 개방.

1. 앱은 localhost에만 띄운다 — `./run.sh 8000 127.0.0.1`
2. Caddy 설치 후 `/etc/caddy/Caddyfile`:

   ```
   todo.example.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```

3. `sudo systemctl reload caddy`

이 두 줄로 Let's Encrypt 인증서를 자동 발급하고 만료 전 자동 갱신합니다.
Nginx + certbot으로도 되지만 설정과 갱신 관리가 더 번거롭습니다.

주의: 80·443을 열면 자동 스캐너가 붙습니다. `REGISTER_CODE`를 반드시 설정하세요.

---

## Cloudflare Tunnel 방식 (현재 선택한 방식)

도메인: `cwworld.party` (Cloudflare Registrar 구입 → DNS가 이미 Cloudflare에 있어
zone 요건 충족). 목표: `https://todo.cwworld.party` → 서버의 `127.0.0.1:8000`.

**인바운드 포트를 하나도 열지 않습니다.** cloudflared가 서버에서 Cloudflare로
바깥쪽(outbound)으로 연결을 맺고, 그 통로로 요청이 들어옵니다. OCI 보안 목록에
80·443을 열 필요가 없고, 지금 열려 있는 8000은 오히려 닫아야 합니다.

### 1. 앱을 localhost에만 바인딩

```bash
# 서버에서 — 0.0.0.0(전체 공개)이 아니라 127.0.0.1
./run.sh 8000 127.0.0.1
```

터널은 서버 내부에서 접속하므로 외부 공개가 필요 없습니다.

### 2. cloudflared 설치

먼저 OS를 확인합니다 — `cat /etc/os-release`

Ubuntu·Debian 계열:

```bash
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg \
  | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main' \
  | sudo tee /etc/apt/sources.list.d/cloudflared.list
sudo apt-get update && sudo apt-get install -y cloudflared
```

Oracle Linux·RHEL 계열이면 `sudo yum install cloudflared` (같은 pkg.cloudflare.com
저장소를 등록한 뒤). 아키텍처(ARM/x86)는 패키지 관리자가 알아서 맞춥니다.

### 3. Cloudflare 계정 인증

```bash
cloudflared tunnel login
```

서버에는 브라우저가 없으므로 **URL이 터미널에 출력됩니다.** 그 URL을 내 노트북
브라우저에 붙여넣고 로그인한 뒤 **`cwworld.party`를 선택**하면 됩니다. 성공하면
서버의 `~/.cloudflared/cert.pem`이 생성됩니다.

### 4. 터널 생성

```bash
cloudflared tunnel create todo
```

출력된 **터널 UUID**를 적어두세요. 자격증명이
`~/.cloudflared/<UUID>.json`에 저장됩니다.

### 5. 설정 파일 작성

`~/.cloudflared/config.yml`:

```yaml
tunnel: <여기에-UUID>
credentials-file: /home/<사용자명>/.cloudflared/<UUID>.json

ingress:
  - hostname: todo.cwworld.party
    service: http://127.0.0.1:8000
  # 마지막 catch-all 규칙은 필수 — 다른 호스트로 들어온 요청은 404
  - service: http_status:404
```

### 6. DNS 레코드 연결

```bash
cloudflared tunnel route dns todo todo.cwworld.party
```

`todo.cwworld.party` → `<UUID>.cfargotunnel.com` CNAME이 자동으로 생성됩니다.
직접 DNS를 만질 필요가 없습니다.

### 7. 동작 확인 후 서비스로 등록

```bash
cloudflared tunnel run todo        # 먼저 포그라운드로 확인
```

내 노트북에서 `https://todo.cwworld.party` 접속 → 로그인 화면이 뜨면 성공입니다.
확인했으면 Ctrl+C로 끄고 부팅 시 자동 시작되도록 서비스로 등록합니다.

```bash
sudo cloudflared --config /home/<사용자명>/.cloudflared/config.yml service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

**설정 파일을 하나로 합쳐두세요 ★**

`service install`은 설정을 `/etc/cloudflared/config.yml`로 복사하고, systemd는
**그 파일만** 읽습니다. 이후 홈 디렉터리의 `~/.cloudflared/config.yml`을 고쳐도
아무 일도 일어나지 않습니다. 실제로 이 때문에 호스트를 추가했는데 404가 나는 일을
겪었습니다.

`/etc/cloudflared/config.yml`을 유일한 기준으로 삼고 홈 쪽을 심볼릭 링크로 바꾸면
재발하지 않습니다. CLI 검증 명령도 같은 파일을 읽게 됩니다.

```bash
mv ~/.cloudflared/config.yml ~/.cloudflared/config.yml.bak
ln -s /etc/cloudflared/config.yml ~/.cloudflared/config.yml

# 실제로 어느 파일이 실행되는지 확인
systemctl cat cloudflared | grep ExecStart
```

### 8. 8000 포트를 닫는다 ★

이 단계를 빼면 HTTPS를 붙여도 **평문 HTTP 경로가 그대로 남습니다.**
OCI 콘솔의 보안 목록(Security List / NSG)에서 8000 인그레스 규칙을 삭제하고,
서버 방화벽에서도 막습니다.

```bash
# 열려 있는지 확인 — 내 노트북에서
curl -m 5 http://<서버공인IP>:8000/     # 연결이 안 돼야 정상
```

앱을 `127.0.0.1`로 띄웠다면(1단계) 애초에 외부에서 닿지 않습니다.

### 호스트 추가하기 (한 터널로 여러 서비스)

터널 하나가 여러 호스트를 처리합니다. **터널을 새로 만들거나 cloudflared를 하나 더
띄울 필요가 없습니다.** `config.yml`에 규칙만 추가하면 됩니다.

예: `weight.cwworld.party` → `127.0.0.1:8077`

**1) `~/.cloudflared/config.yml`에 규칙 추가 — catch-all보다 위에**

```yaml
tunnel: <UUID>
credentials-file: /home/<사용자명>/.cloudflared/<UUID>.json

ingress:
  - hostname: todo.cwworld.party
    service: http://127.0.0.1:8000
  - hostname: weight.cwworld.party      # ← 추가
    service: http://127.0.0.1:8077
  - service: http_status:404            # ← catch-all은 언제나 맨 마지막
```

cloudflared는 규칙을 **위에서 아래로** 훑어 처음 맞는 것을 씁니다. 새 규칙을
catch-all 아래에 두면 404가 먼저 걸려서 **영원히 도달하지 않습니다.**

`service:`의 스킴은 **로컬 앱이 실제로 말하는 프로토콜**입니다. uvicorn을 그냥
띄웠다면 `http://`입니다. 공식 문서 예시에 `https://`가 보이는 것은 그쪽 예시의
로컬 앱이 TLS를 쓰기 때문이며, 그대로 복사하면 502가 납니다.

**2) 설정 검증 — 재시작 전에 확인**

```bash
cloudflared tunnel ingress validate                        # 문법 검사
cloudflared tunnel ingress rule https://weight.cwworld.party   # 어느 규칙에 걸리는지
```

두 번째 명령이 `http://127.0.0.1:8077`로 가는 규칙을 가리켜야 정상입니다.
`http_status:404`를 가리키면 규칙 순서가 잘못된 것입니다.

> **주의:** 이 명령은 사용자 계정으로 실행되어 `~/.cloudflared/config.yml`을 읽습니다.
> systemd가 읽는 `/etc/cloudflared/config.yml`과 다르면, **이 검증은 통과하는데
> 실제 서비스는 404를 내는** 상황이 생깁니다. 출력 첫 줄의 `Using rules from ...`이
> 어느 경로인지 꼭 확인하세요. 위 7단계의 심볼릭 링크를 적용해 두면 이 문제가
> 사라집니다.

**3) DNS 레코드 생성**

```bash
cloudflared tunnel route dns todo weight.cwworld.party
```

터널 이름(`todo`)은 그대로 씁니다. 호스트마다 터널을 만드는 게 아닙니다.

**4) 재시작**

```bash
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
```

무중단이 필요하면 공식 문서는 replica를 띄워 교체하는 방식을 권하지만, 개인용이라면
몇 초 끊기는 재시작으로 충분합니다.

**5) 확인, 그리고 8077 닫기**

```bash
curl -I https://weight.cwworld.party        # 200
curl -m 5 http://<서버공인IP>:8077/          # 실패해야 정상
```

8077 서비스도 `127.0.0.1`에만 바인딩하고 OCI 보안 목록에서 8077 인그레스 규칙을
삭제하세요. 안 그러면 그 서비스는 여전히 평문 HTTP로 열려 있습니다.

### 안 될 때 — 상태 코드로 원인 좁히기

브라우저나 curl로 받은 응답 코드가 어디가 문제인지 알려줍니다.

```bash
curl -sS -D - -o /dev/null https://weight.cwworld.party
```

| 응답 | 의미 | 확인할 곳 |
| --- | --- | --- |
| **404** (본문 없음, `content-type` 없음) | 요청이 cloudflared까지 도달했지만 **catch-all에 걸림.** 해당 hostname 규칙이 실행 중인 설정에 없다 | `systemctl cat cloudflared`로 실제 설정 경로 확인 → 그 파일에 규칙이 있는지, catch-all보다 위에 있는지 |
| **502 / 503** | 규칙은 맞았지만 **로컬 서비스에 못 닿음** | 서버에서 `curl -I http://127.0.0.1:<포트>/`, `ss -tlnp`로 리스닝 확인. `service:`의 포트·스킴(`http` vs `https`) 확인 |
| **1033 / 530** (Cloudflare 오류 페이지) | 터널이 연결돼 있지 않거나 DNS가 터널을 가리키지 않음 | `systemctl is-active cloudflared`, `cloudflared tunnel route dns` 재실행 |
| **DNS 해석 실패** | CNAME이 없음 | `dig +short <호스트> A` → Cloudflare IP가 나와야 정상 |

404와 502를 구분하는 게 핵심입니다. **404는 설정(라우팅) 문제, 502는 원본 서비스 문제**입니다.

앱의 404와 cloudflared의 404를 구분하려면 본문을 보세요. cloudflared의
`http_status:404`는 **본문이 비어 있고 `content-type` 헤더가 없습니다.**

### 확인 체크리스트

```bash
curl -I https://todo.cwworld.party            # 200, HTTPS
curl -m 5 http://<서버공인IP>:8000/            # 실패해야 정상
sudo systemctl is-active cloudflared          # active
```

### 주의할 점

- 이제 로그인 화면이 인터넷에 공개됩니다. **`REGISTER_CODE`를 반드시 설정**하세요
  (`.env`). 자동 스캐너가 회원가입을 시도합니다.
- 앱 자체도 재시작에 살아남아야 합니다. `run.sh`를 nohup·tmux로 띄워두었다면
  서버 재부팅 시 죽습니다. cloudflared만 systemd로 올려도 앱이 없으면 502가 뜨니,
  앱도 systemd 유닛으로 만드는 편이 안전합니다.
- 더 잠그고 싶다면 **Cloudflare Access**(Zero Trust)를 앞단에 걸어 이메일 인증을
  거친 사람만 도달하게 할 수 있습니다. 그러면 로그인 화면 자체가 외부에 노출되지
  않습니다. 소규모는 무료입니다.
- 트래픽이 Cloudflare를 경유합니다. 브라우저↔Cloudflare 구간은 HTTPS,
  Cloudflare↔서버 구간은 터널로 암호화됩니다.

---

## Tailscale 방식 (도메인 없이, 여러 기기에서)

1. 서버와 각 기기에 Tailscale 설치 후 같은 계정으로 로그인
2. 앱은 `./run.sh 8000 127.0.0.1` 또는 Tailscale 인터페이스에만 바인딩
3. 기기에서 `http://<서버의-tailscale-이름>:8000` 접속

사설망 안이라 구간이 암호화되고, 공개 포트가 없습니다. `tailscale serve`를 쓰면
사설망 안에서 진짜 `https://`도 붙일 수 있습니다.

---

## 토큰이 유출된 것 같을 때

`JWT_SECRET`을 바꾸면 **발급된 모든 토큰이 즉시 무효**가 됩니다. 계정과 데이터는
그대로이고, 모두 다시 로그인하면 됩니다.

```bash
openssl rand -base64 32     # 새 값을 .env의 JWT_SECRET에 넣고
./run.sh                    # 재시작
```

---

## 그때까지 지켜야 할 것

- 다른 서비스에서 쓰는 비밀번호를 재사용하지 마세요. 평문으로 지나갑니다.
- 공용 WiFi(카페·공항·호텔)에서는 로그인하지 마세요. 가장 흔한 유출 경로입니다.
- `REGISTER_CODE`를 반드시 설정해 두세요. 무단 가입을 막습니다.
- 가능하면 `./run.sh 8000 127.0.0.1` + SSH 터널로 운영하세요.
