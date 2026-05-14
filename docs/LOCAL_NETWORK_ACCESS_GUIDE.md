# 로컬 네트워크 접속 가이드

## 목적

- 개인용 todo 앱을 같은 네트워크의 다른 PC에서 접속하는 방법 정리
- 클라우드 배포가 아니라 로컬 PC를 호스트로 쓰는 방식
- 데이터는 호스트 PC의 `todos.json` / `roles.json`에 저장됨

---

## 기본 구조

| 역할 | 설명 |
|---|---|
| **호스트 PC** | 앱을 실행하는 PC, 데이터 파일이 저장됨 |
| **클라이언트 PC** | 브라우저로 접속하는 다른 PC |

**전제 조건:** 두 PC가 같은 Wi-Fi 또는 같은 공유기 내부망에 있어야 한다.

> 회사/학교 네트워크에서는 장비 간 접속이 차단될 수 있다.

---

## 1단계 — 호스트 PC에서 앱 실행

```powershell
cd c:\dev\todo_ai_app
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

| 옵션 | 설명 |
|---|---|
| `--server.address 0.0.0.0` | 같은 네트워크의 다른 장치 접속 허용 |
| `--server.port 8501` | 기본 포트 (변경 가능) |

> 앱 실행 중인 터미널을 닫으면 접속도 종료된다.

---

## 2단계 — 호스트 PC IP 확인

```powershell
ipconfig
```

확인 항목:
- **무선 LAN 어댑터 Wi-Fi** 또는 **이더넷 어댑터**의 **IPv4 주소**

출력 예:
```
무선 LAN 어댑터 Wi-Fi:
   IPv4 주소 . . . . . . . . . . . : 192.168.0.25
```

---

## 3단계 — 다른 PC에서 접속

클라이언트 PC의 브라우저 주소창에 입력:

```
http://192.168.0.25:8501
```

> `192.168.0.25` 부분을 실제 호스트 PC IP로 변경한다.

---

## Windows 방화벽 확인

처음 실행 시 Python 또는 Streamlit 네트워크 접근 허용 창이 나올 수 있다.
**개인 네트워크** 허용을 선택한다. 공용 네트워크는 신중하게 판단한다.

### 방화벽 포트 허용 (필요 시, PowerShell 관리자 권한)

```powershell
New-NetFirewallRule -DisplayName "Streamlit 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

### 문제 발생 시 확인

- Windows Defender 방화벽에서 Python 허용 여부 확인
- 포트 8501 인바운드 허용 여부 확인
- 같은 네트워크인지 확인
- VPN / 보안 프로그램이 차단하지 않는지 확인

---

## 접속 안 될 때 점검 순서

1. 호스트 PC에서 앱이 실행 중인가?
2. 실행 명령에 `--server.address 0.0.0.0`이 포함되었는가?
3. 호스트 PC IP를 정확히 입력했는가?
4. 포트 `:8501`을 붙였는가?
5. 두 PC가 같은 네트워크에 있는가?
6. Windows 방화벽에서 허용했는가?
7. 회사/학교 네트워크에서 장치 간 접속이 차단된 것은 아닌가?

---

## 데이터 저장 주의사항

- 다른 PC에서 접속해 todo를 추가해도 데이터는 **호스트 PC**의 `todos.json`에 저장된다.
- `roles.json`도 호스트 PC 기준으로 사용된다.
- 클라이언트 PC에는 데이터 파일이 저장되지 않는다.
- 호스트 PC를 바꾸면 기존 데이터가 보이지 않을 수 있다.
- 정기적으로 **백업/내보내기** 기능을 사용한다.

---

## API key 주의사항

- Mindlogic API key는 **호스트 PC**의 Streamlit secrets 또는 환경변수에 있어야 한다.
- 클라이언트 PC에는 API key가 필요 없다.
- `.streamlit/secrets.toml`은 Git에 올리지 않는다.

### secrets.toml 위치 예

```
c:\dev\todo_ai_app\.streamlit\secrets.toml
```

---

## 보안 주의사항

- 이 방식은 **같은 네트워크 내부 접속**용이다.
- 공유기 포트포워딩으로 인터넷에 직접 노출하지 않는다.
- 외부 접속이 필요하면 Tailscale 같은 개인 VPN 방식을 검토한다.
- 공용 Wi-Fi에서는 사용하지 않는 것이 안전하다.

---

## 종료 방법

호스트 PC 터미널에서:

```
Ctrl + C
```

> 앱이 종료되면 다른 PC 접속도 끊긴다.

---

## 수동 검증 기준

| 검증 항목 | 기대 결과 |
|---|---|
| 호스트 PC 앱 실행 | 정상 실행 |
| 호스트 PC `localhost:8501` 접속 | 정상 표시 |
| 클라이언트 PC `호스트IP:8501` 접속 | 정상 접속 |
| 클라이언트 PC에서 todo 추가 | 호스트 PC `todos.json`에 반영 |
| 백업/내보내기 기능 | 정상 동작 |
| AI 자연어 입력 | 정상 동작 |
| 앱 종료 후 클라이언트 접속 | 접속 끊김 확인 |
