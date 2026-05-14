# 배포/접속 구조 1차 범위 문서

## 현재 앱 상태

- Streamlit 기반 로컬 웹앱
- Python 실행 환경 필요 (`streamlit run app.py`)
- `todos.json` / `roles.json` 로컬 파일 저장
- Mindlogic API key는 Streamlit secrets 또는 환경변수 사용
- GitHub 저장소에 코드 반영 완료
- 현재는 로컬 PC에서 실행하는 단일 PC 구조

---

## 접속 방식 후보

### A. 로컬 PC 직접 실행

```
streamlit run app.py
```

| 항목 | 내용 |
|---|---|
| 복잡도 | 가장 단순 |
| 데이터 위치 | 해당 PC에만 저장 |
| 적합 대상 | 개인 단일 PC 사용 |
| 제약 | 해당 PC에서만 접속 가능 |

---

### B. 같은 네트워크 내 다른 PC 접속

```
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

| 항목 | 내용 |
|---|---|
| 접속 URL | `http://호스트PC_IP:8501` |
| 유효 범위 | 같은 Wi-Fi / 공유기 안 |
| 데이터 위치 | 호스트 PC에 저장 |
| 추가 작업 | Windows 방화벽 포트 허용 필요 |

IP 확인 명령:
```powershell
ipconfig
```

접속 URL 예:
```
http://192.168.0.25:8501
```

---

### C. Tailscale 같은 개인 VPN 접속

| 항목 | 내용 |
|---|---|
| 접속 범위 | 외부 네트워크에서도 호스트 PC에 안전하게 접속 |
| 인터넷 노출 | 공개 인터넷에 앱을 노출하지 않음 |
| 데이터 위치 | 호스트 PC에 저장 |
| 적합 대상 | 개인용 실사용 중간 단계 |
| 여러 기기 | 여러 기기에서 접속 가능 |

---

### D. Streamlit Community Cloud / Render / Railway / Hugging Face Spaces

| 항목 | 내용 |
|---|---|
| 접속 범위 | 인터넷 어디서나 접속 가능 |
| JSON 저장 | 재배포/재시작 시 파일 유실 위험 |
| 추가 요건 | 외부 DB 또는 persistent storage 필요 |
| API key | 플랫폼별 secrets 관리 필요 |
| 전제 조건 | SQLite / Supabase 전환 후 검토 |

---

## 1차 권장 방향

| 단계 | 방법 | 이유 |
|---|---|---|
| 1차 | 로컬 PC 실행 + 같은 네트워크 접속 테스트 | 가장 단순, 현재 JSON 구조에 안전 |
| 2차 | Tailscale 접속 테스트 | 공개 노출 없이 외부 접속 가능 |
| 3차 | SQLite 또는 Supabase 전환 후 배포형 웹앱 검토 | JSON 저장 한계 해소 후 진행 |

### 이유

- 현재 JSON 저장 구조는 서버 재시작/배포 환경에 취약하다.
- 먼저 개인 PC를 호스트로 두고 실제 사용성을 검증하는 것이 안전하다.
- 외부 공개 배포는 인증/데이터 저장/보안 문제가 커진다.

---

## 1차 구현 범위

| 항목 | 설명 |
|---|---|
| 로컬 네트워크 접속 방법 | `--server.address 0.0.0.0` 실행 및 IP 확인 |
| Windows 방화벽 포트 허용 | 8501 포트 인바운드 허용 절차 |
| Tailscale 사용 가능성 검토 | 개인 VPN 설정 가이드 |
| Streamlit 실행 명령 정리 | 로컬 / 네트워크 접속용 명령 |
| API key 설정 방법 | `secrets.toml` 또는 환경변수 사용법 |
| 데이터 저장 위치와 백업 주의사항 | 호스트 PC 기준 백업 안내 |

---

## 1차 제외 범위

| 제외 항목 | 이유 |
|---|---|
| 실제 클라우드 배포 | JSON 저장 구조 미비 |
| 사용자 로그인 기능 | 별도 구현 필요 |
| 다중 사용자 권한 관리 | 단일 사용자 앱 |
| HTTPS / 도메인 설정 | 클라우드 배포 이후 검토 |
| Docker 설정 | 복잡도 증가 |
| SQLite / Supabase 전환 | 별도 브랜치 |
| 자동 실행 서비스 등록 | OS별 설정 복잡 |
| Google Calendar 연동 | 기능 확장 범위 |

---

## 보안 원칙

- API key는 Git에 올리지 않는다.
- `.streamlit/secrets.toml`은 Git 추적 제외 상태를 유지한다.
- 앱을 공개 인터넷에 인증 없이 노출하지 않는다.
- 같은 네트워크 접속도 신뢰 가능한 네트워크에서만 사용한다.
- Tailscale 또는 VPN 없는 포트포워딩은 1차 권장하지 않는다.
- 백업/내보내기 파일에는 secrets가 포함되지 않아야 한다.

### `.gitignore` 확인 항목

```
.streamlit/secrets.toml
*.env
.env
```

---

## 데이터 원칙

- `todos.json` / `roles.json`은 호스트 PC에 저장된다.
- 다른 PC에서 접속해도 데이터는 호스트 PC 파일을 사용한다.
- 클라우드 배포 전에는 JSON 저장 방식의 한계를 인식해야 한다.
- 실제 장기 사용 전 백업/내보내기를 정기적으로 수행한다.
- 외부 배포 단계에서는 SQLite persistent volume 또는 Supabase 같은 외부 DB 검토가 필요하다.

---

## 실행 명령 예시

### 로컬 실행

```bash
streamlit run app.py
```

### 같은 네트워크 접속용 실행

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

### 호스트 PC IP 확인

```powershell
ipconfig
```

### 접속 URL 예

```
http://192.168.0.25:8501
```

### Windows 방화벽 포트 허용 (PowerShell 관리자 권한)

```powershell
New-NetFirewallRule -DisplayName "Streamlit 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```

---

## 수동 검증 기준

| 검증 항목 | 기대 결과 |
|---|---|
| 로컬에서 앱 실행 | 정상 실행 |
| 같은 네트워크 다른 PC 접속 | 정상 접속 및 표시 |
| Windows 방화벽 허용 후 접속 | 정상 접속 |
| 다른 PC에서 todo 추가 | 호스트 PC `todos.json`에 반영 |
| API key 없이 실행 | 앱이 중단되지 않고 안내 표시 |
| 백업/내보내기 기능 | 정상 동작 |
| Git에 `secrets.toml` 미포함 | `git status` / `git log` 확인 |

---

## 구현 단계

| 커밋 | 내용 |
|---|---|
| 커밋 1 | 배포/접속 scope 문서 추가 (`docs/DEPLOYMENT_ACCESS_SCOPE.md`) |
| 커밋 2 | 로컬 네트워크 실행 가이드 문서 추가 |
| 커밋 3 | Tailscale 사용 가이드 문서 추가 |
| 커밋 4 | 배포형 웹앱 전환 검토 문서 추가 |
| 이후 | Docker / DB 전환 별도 브랜치 |

---

## 개발 원칙

- 배포보다 데이터 안정성을 우선한다.
- 공개 배포보다 개인 안전 접속을 먼저 검증한다.
- 새 기능 구현보다 실제 사용 경로를 먼저 확정한다.
- `app.py` 수정은 필요한 경우에만 별도 커밋으로 진행한다.
