# 데이터 안전성 수동 회귀 테스트 기준 문서

## 문서 목적

- JSON 기반 로컬 저장 구조의 데이터 안전성 회귀 테스트 기준 문서
- 자동 테스트가 아니라 사람이 파일 상태를 바꿔가며 앱 화면과 원본 파일 상태를 확인하는 수동 테스트 기준
- SQLite 전환 또는 복원 기능 추가 전 기존 JSON 안전 로딩이 깨지지 않았는지 확인하기 위한 기준

---

## 공통 통과 기준

- 앱이 JSON 읽기 실패로 중단되지 않아야 한다.
- `todos.json` / `roles.json` 원본 파일을 자동으로 덮어쓰면 안 된다.
- 파일 없음은 신규 사용자 상황으로 간주하고 앱이 실행되어야 한다.
- JSON 손상, 권한 오류, 타입 불일치 상황에서는 warning이 표시되어야 한다.
- traceback이나 exception repr이 사용자 화면에 그대로 노출되면 안 된다.
- 손상 파일을 경고 없이 조용히 빈 목록으로 대체하면 안 된다.
- 오류 상황에서도 백업/내보내기, 전체 보기, 오늘 할 일, 주간 보기 화면이 가능한 범위에서 열려야 한다.
- `save_todos()` / `save_roles()`는 명시적 저장 동작에서만 호출되어야 한다.

---

## 테스트 전 준비

테스트 전 현재 파일을 반드시 백업한다.

```powershell
copy .\todos.json .\todos.json.manual_backup
copy .\roles.json .\roles.json.manual_backup
```

테스트 후 원본 복원:

```powershell
copy .\todos.json.manual_backup .\todos.json
copy .\roles.json.manual_backup .\roles.json
```

### 주의 사항

- Git 추적 대상이 아닌 런타임 파일이므로 `git status`만으로 파일 복원 여부를 판단하지 않는다.
- 파일 수정 시간 확인 시 `Get-Item .\todos.json | Select-Object LastWriteTime` 을 사용할 수 있다.
- 테스트용 임시 파일(`.manual_backup`, `.bak`)은 Git에 `add`하지 않는다.

---

## 테스트 케이스

### TC-01. 정상 파일 로딩

| 항목 | 내용 |
|---|---|
| 조건 | `todos.json` 정상, `roles.json` 정상 |
| 기대 결과 | 앱 정상 실행, 오늘 할 일/주간/전체 보기/역할 분류 정상 표시 |
| 실패 조건 | 정상 파일임에도 warning이 표시됨 |

---

### TC-02. todos.json 파일 없음

**준비:**
```powershell
Rename-Item .\todos.json .\todos.json.bak
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | 앱이 중단되지 않음, todo 목록 빈 상태로 시작 |
| 확인 1 | `todos.json`이 자동 생성되지 않음 |
| 확인 2 | `roles.json`은 정상 로드됨 |
| 확인 3 | traceback 없음 |
| 실패 조건 | 앱 중단, 또는 `todos.json`이 자동 생성됨 |

**복원:**
```powershell
Rename-Item .\todos.json.bak .\todos.json
```

---

### TC-03. roles.json 파일 없음

**준비:**
```powershell
Rename-Item .\roles.json .\roles.json.bak
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | 앱이 중단되지 않음, roles 목록 빈 상태로 시작 |
| 확인 1 | `roles.json`이 자동 생성되지 않음 |
| 확인 2 | 기존 todo의 role_name 표시가 제한될 수 있으나 앱은 동작 |
| 확인 3 | traceback 없음 |
| 실패 조건 | 앱 중단, 또는 `roles.json`이 자동 생성됨 |

**복원:**
```powershell
Rename-Item .\roles.json.bak .\roles.json
```

---

### TC-04. todos.json JSON 손상

**준비:**
```powershell
copy .\todos.json .\todos.json.manual_backup
'{ broken json' | Set-Content .\todos.json -Encoding UTF8
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | 앱이 중단되지 않음 |
| 확인 1 | `todos.json`을 읽을 수 없다는 `st.warning()` 표시 |
| 확인 2 | 앱은 임시로 빈 todo 목록 사용 |
| 확인 3 | 손상된 `todos.json` 원본이 자동으로 덮어써지지 않음 |
| 확인 4 | traceback 없음 |
| 실패 조건 | 앱 중단, 또는 파일이 `[]`로 덮어써짐 |

**복원:**
```powershell
copy .\todos.json.manual_backup .\todos.json
```

---

### TC-05. roles.json JSON 손상

**준비:**
```powershell
copy .\roles.json .\roles.json.manual_backup
'{ broken json' | Set-Content .\roles.json -Encoding UTF8
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | 앱이 중단되지 않음 |
| 확인 1 | `roles.json`을 읽을 수 없다는 `st.warning()` 표시 |
| 확인 2 | 앱은 임시로 빈 role 목록 사용 |
| 확인 3 | 손상된 `roles.json` 원본이 자동으로 덮어써지지 않음 |
| 확인 4 | traceback 없음 |
| 실패 조건 | 앱 중단, 또는 파일이 `[]`로 덮어써짐 |

**복원:**
```powershell
copy .\roles.json.manual_backup .\roles.json
```

---

### TC-06. todos.json 타입 불일치

**준비:**
```powershell
copy .\todos.json .\todos.json.manual_backup
'{"todos": []}' | Set-Content .\todos.json -Encoding UTF8
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | `st.warning()` 표시 |
| 확인 1 | 앱은 임시로 빈 todo 목록 사용 |
| 확인 2 | 원본 파일이 자동으로 덮어써지지 않음 |
| 확인 3 | traceback 없음 |
| 실패 조건 | warning 없이 조용히 빈 목록 대체, 또는 파일 덮어쓰기 |

**복원:**
```powershell
copy .\todos.json.manual_backup .\todos.json
```

---

### TC-07. roles.json 타입 불일치

**준비:**
```powershell
copy .\roles.json .\roles.json.manual_backup
'{"roles": []}' | Set-Content .\roles.json -Encoding UTF8
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | `st.warning()` 표시 |
| 확인 1 | 앱은 임시로 빈 role 목록 사용 |
| 확인 2 | 원본 파일이 자동으로 덮어써지지 않음 |
| 확인 3 | traceback 없음 |
| 실패 조건 | warning 없이 조용히 빈 목록 대체, 또는 파일 덮어쓰기 |

**복원:**
```powershell
copy .\roles.json.manual_backup .\roles.json
```

---

### TC-08. 빈 list 파일

**준비:**
```powershell
'[]' | Set-Content .\todos.json -Encoding UTF8
'[]' | Set-Content .\roles.json -Encoding UTF8
```

| 항목 | 내용 |
|---|---|
| 기대 결과 | warning 없이 정상 실행 |
| 확인 1 | todo / role이 비어 있는 정상 상태로 처리 |
| 확인 2 | 앱이 중단되지 않음 |
| 실패 조건 | 빈 `[]`임에도 warning 발생 또는 앱 중단 |

**복원:**
```powershell
copy .\todos.json.manual_backup .\todos.json
copy .\roles.json.manual_backup .\roles.json
```

---

### TC-09. 누락 필드가 있는 정상 list

**준비:**
- `todos.json`은 list지만 일부 todo에 `memo`, `role_name`, `updated_at` 등이 없음
- `roles.json`은 list지만 일부 role에 `active`가 없음

| 항목 | 내용 |
|---|---|
| 기대 결과 | 앱이 중단되지 않음 |
| 확인 1 | 기존 보정 로직이 정상 작동 (누락 필드 기본값 처리) |
| 확인 2 | 원본 파일이 load 단계에서 자동 저장되지 않음 |
| 확인 3 | traceback 없음 |
| 실패 조건 | 누락 필드로 인해 앱 중단, 또는 자동 저장 |

---

### TC-10. 원본 자동 덮어쓰기 금지

**조건:** TC-04 또는 TC-06 상황에서 앱 실행

| 항목 | 내용 |
|---|---|
| 확인 방법 | `Get-Item .\todos.json \| Select-Object LastWriteTime` 으로 수정 시간 비교 |
| 기대 결과 | 손상되거나 타입이 잘못된 파일 내용이 그대로 유지됨 |
| 확인 1 | 앱 실행만으로 파일이 `[]`로 바뀌지 않음 |
| 확인 2 | `save_todos()` / `save_roles()`가 load 실패 경로에서 호출되지 않음 |
| 실패 조건 | 앱 실행 후 파일 내용이 `[]`로 변경됨 |

---

### TC-11. 백업/내보내기 회귀

**조건:** 정상 파일 상태

| 확인 항목 | 기대 결과 |
|---|---|
| `todos.json` 다운로드 | 정상 |
| `roles.json` 다운로드 | 정상 |
| 통합 백업 JSON | 정상 |
| CSV 내보내기 | 정상 |
| Markdown 내보내기 | 정상 |
| 실패 조건 | 데이터 안전 처리 추가 후 백업/내보내기 기능이 깨짐 |

---

### TC-12. 기존 기능 회귀

| 확인 항목 | 기대 결과 |
|---|---|
| AI 자연어 입력 | 정상 |
| 오늘 할 일 | 정상 |
| 주간 보기 | 정상 |
| 전체 보기 | 정상 |
| 검색 | 정상 |
| 직접 입력 | 정상 |
| 완료 체크 | 정상 |
| 수정/삭제 | 정상 |
| 역할/분류 관리 | 정상 |

---

## 실패 패턴

| 실패 패턴 | 영향 |
|---|---|
| 손상된 JSON 때문에 앱이 중단됨 | TC-04, TC-05 실패 |
| 손상 파일이 자동으로 `[]`로 덮어써짐 | TC-10 실패 |
| 파일 없음 상황에서 앱이 중단됨 | TC-02, TC-03 실패 |
| 타입 불일치 상황에서 warning 없이 조용히 빈 목록으로 대체됨 | TC-06, TC-07 실패 |
| traceback이 사용자 화면에 노출됨 | TC-04~TC-07 실패 |
| `roles.json` 없음 상황에서 `roles.json`이 자동 생성됨 | TC-03 실패 |
| `load_todos()` / `load_roles()` 실패 경로에서 `save_*()` 호출됨 | TC-10 실패 |
| 정상 파일에서도 warning이 표시됨 | TC-01 실패 |
| 기존 기능이 데이터 안전 처리 이후 깨짐 | TC-12 실패 |

---

## 개발 원칙

- 데이터 손상 시 자동 복구하지 않는다.
- 자동 복구보다 원본 보존을 우선한다.
- 사용자가 오류를 인지할 수 있도록 warning을 표시한다.
- 파일 없음은 신규 사용자 상황으로 보고 과도한 warning을 피한다.
- 복원 기능은 별도 브랜치에서 다룬다.
- SQLite 전환 전에는 JSON 원본 보존과 백업 가능성을 최우선으로 둔다.
