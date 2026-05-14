# Tailscale 원격 접속 가이드

## 목적

- 집 밖이나 다른 네트워크에서도 개인 기기에서 todo 앱에 접속하기 위한 방법
- 공개 인터넷에 앱을 노출하지 않고 Tailscale 사설망(tailnet)을 통해 접속
- 데이터는 계속 호스트 PC의 `todos.json` / `roles.json`에 저장됨

---

## 기본 구조

| 역할 | 설명 |
|---|---|
| **호스트 PC** | todo 앱을 실행하는 PC, 데이터 파일이 저장됨 |
| **클라이언트 기기** | 노트북, 다른 PC, 태블릿 등 브라우저로 접속하는 기기 |

**전제 조건:**
- 두 기기가 같은 Tailscale 계정 또는 같은 tailnet에 있어야 한다.
- 호스트 PC가 켜져 있고 Streamlit 앱이 실행 중이어야 한다.

---

## 왜 Tailscale을 쓰는가

| 이유 | 설명 |
|---|---|
| 네트워크 무관 | 같은 Wi-Fi가 아니어도 개인 기기 간 접속 가능 |
| 포트포워딩 불필요 | 공유기 설정 없이 사용 가능 |
| 인터넷 비노출 | 공개 인터넷에 직접 노출하지 않음 |
| 개인용 적합 | 클라우드 배포 전 중간 단계로 적합 |

> 단, 호스트 PC가 꺼져 있으면 접속 불가.

---

## 설치 및 로그인

1. 호스트 PC와 클라이언트 기기에 Tailscale 설치
   - [https://tailscale.com/download](https://tailscale.com/download)
2. 두 기기 모두 **같은 계정**으로 로그인
3. Tailscale 앱 또는 admin console에서 두 기기가 같은 tailnet에 있는지 확인
4. 각 기기의 Tailscale IP 또는 MagicDNS 이름 확인

---

## 호스트 PC에서 앱 실행

```powershell
cd c:\dev\todo_ai_app
.\.venv\Scripts\Activate.ps1
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

| 옵션 | 설명 |
|---|---|
| `--server.address 0.0.0.0` | 로컬 및 Tailscale 네트워크 인터페이스 접속 허용 |
| `--server.port 8501` | 기본 포트 |

> 앱 실행 중인 터미널을 닫으면 접속도 종료된다.

---

## 클라이언트 기기에서 접속

### 방법 A — Tailscale IP 직접 접속 (권장)

```
http://100.x.y.z:8501
```

> `100.x.y.z`는 Tailscale 앱 또는 admin console에서 확인한 호스트 PC의 Tailscale IP.

### 방법 B — MagicDNS 이름 사용

```
http://호스트장치이름:8501
```

> MagicDNS 이름은 환경 설정에 따라 다를 수 있다.
> 접속이 안 되면 방법 A(IP 직접 접속)를 먼저 시도한다.

---

## tailscale serve / funnel 구분

| 명령 | 용도 | 이번 앱 사용 여부 |
|---|---|---|
| `tailscale serve` | tailnet 내부에서 로컬 서비스를 공유 | 선택 사항 |
| `tailscale funnel` | 로컬 서비스를 **공개 인터넷**에 노출 | **사용 금지** |

**1차 권장:** Tailscale IP 직접 접속 또는 tailnet 내부 접근만 사용.

> Funnel은 앱을 인터넷에 공개하는 성격이 있으므로, 인증/보안 구조가 갖춰지기 전에는 사용하지 않는다.

---

## 데이터 저장 주의사항

- 클라이언트 기기에서 todo를 추가해도 데이터는 **호스트 PC**의 `todos.json`에 저장된다.
- `roles.json`도 호스트 PC 기준으로 사용된다.
- 클라이언트 기기에는 데이터 파일이 저장되지 않는다.
- 호스트 PC를 바꾸면 기존 데이터가 보이지 않을 수 있다.
- 정기적으로 **백업/내보내기** 기능을 사용한다.

---

## API key 주의사항

- Mindlogic API key는 **호스트 PC**에만 필요하다.
- Streamlit secrets 또는 환경변수로 설정한다.
- 클라이언트 기기에는 API key를 둘 필요 없다.
- `.streamlit/secrets.toml`은 Git에 올리지 않는다.

---

## 보안 주의사항

- Tailscale 계정 보안이 중요하다 — **2단계 인증 사용 권장**.
- 신뢰하지 않는 기기를 tailnet에 추가하지 않는다.
- 앱을 공용 PC에서 열지 않는다.
- Funnel 또는 포트포워딩으로 앱을 공개 인터넷에 노출하지 않는다.
- 백업 파일에 API key가 포함되지 않는지 확인한다.

---

## 접속 안 될 때 점검 순서

1. 호스트 PC가 켜져 있는가?
2. 호스트 PC에서 Streamlit 앱이 실행 중인가?
3. 실행 명령에 `--server.address 0.0.0.0`이 포함되어 있는가?
4. 호스트 PC와 클라이언트 기기가 모두 Tailscale에 로그인되어 있는가?
5. 두 기기가 같은 tailnet에 있는가?
6. 호스트 PC의 Tailscale IP를 정확히 입력했는가?
7. 주소 끝에 `:8501` 포트를 붙였는가?
8. Windows 방화벽 또는 보안 프로그램이 Python/Streamlit 접속을 막고 있지 않은가?
9. 호스트 PC에서 `http://localhost:8501`이 열리는가?
10. Tailscale 앱에서 두 기기의 연결 상태가 정상인가?

---

## 권장 사용 시나리오

- 집 PC를 호스트로 두고 노트북에서 외부 접속
- 사무실 PC를 호스트로 두고 개인 노트북에서 접속
- 외부에서 iPad / 노트북으로 todo 확인 및 추가

> 단, 호스트 PC가 항상 켜져 있어야 한다.

---

## 권장하지 않는 사용 시나리오

- 공유기 포트포워딩으로 8501 포트를 인터넷에 공개
- `tailscale funnel`로 인증 없는 공개 URL 제공
- 여러 사용자가 동시에 편집하는 협업 도구로 사용
- 클라우드 배포 환경에서 `todos.json`을 영구 저장소처럼 사용

---

## 수동 검증 기준

| 검증 항목 | 기대 결과 |
|---|---|
| 호스트 PC 앱 실행 | 정상 실행 |
| 호스트 PC `localhost:8501` 접속 | 정상 표시 |
| 클라이언트 기기 `Tailscale IP:8501` 접속 | 정상 접속 |
| 클라이언트 기기에서 todo 추가 | 호스트 PC `todos.json`에 반영 |
| AI 자연어 입력 | 정상 동작 |
| 검색 / 주간 보기 / 백업 내보내기 | 정상 동작 |
| 클라이언트 기기 — API key 불필요 | 접속 정상 |
| 호스트 PC 앱 종료 | 클라이언트 접속 끊김 |
| Funnel / public URL | 사용하지 않음 확인 |

---

## 향후 확장 검토

- `run_network.ps1` 스크립트 추가 (0.0.0.0 바인딩 실행 단축)
- Tailscale 접속 테스트 문서 추가
- SQLite 전환 이후 장기 사용 안정화 검토
- 외부 DB 기반 클라우드 배포는 별도 브랜치에서 검토
