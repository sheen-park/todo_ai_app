# 백업/내보내기 기능 수동 회귀 테스트 케이스

## 목적

백업/내보내기 기능을 수정하거나 향후 복원/SQLite/Supabase 전환 작업을 할 때 기존 다운로드 기능과 데이터 안전 원칙이 깨지지 않았는지 확인하기 위한 수동 테스트 기준 문서다.  
자동 테스트가 아니라 사람이 앱 화면과 다운로드 파일을 직접 확인하는 수동 테스트 기준이다.  
데이터 손실 방지와 민감정보 제외 여부를 확인하기 위한 문서다.

---

## 공통 통과 기준

- 백업/내보내기 기능은 **읽기 전용**이어야 한다.
- 다운로드 실행 후 `todos.json` / `roles.json` 원본이 변경되지 않아야 한다.
- `API key`, `secrets.toml`, `.streamlit` 폴더는 어떤 백업에도 포함되면 안 된다.
- `ignored_role_tags.json`은 현재 구조에서 사용하지 않으므로 포함되면 안 된다.
- 파일명에는 `YYYYMMDD_HHMMSS` timestamp가 포함되어야 한다.
- 앱이 파일 없음 또는 빈 데이터 상황에서도 중단되지 않아야 한다.
- CSV는 Excel에서 한글이 깨지지 않아야 한다.
- Markdown은 사람이 읽을 수 있어야 한다.
- 통합 JSON은 `todos`와 `roles`만 포함해야 한다.

---

## 실패 패턴

| 패턴 | 설명 |
|---|---|
| 다운로드 버튼 클릭 시 앱 중단 | 예외 처리 누락 |
| 다운로드 후 원본 파일 변경 | `save_todos()` / `save_roles()` 호출 오류 |
| `secrets.toml` / API key 포함 | 포함 대상 범위 오류 |
| `ignored_role_tags.json` 포함 | 통합 백업 범위 오류 |
| CSV 한글 깨짐 | `utf-8-sig` 미적용 |
| Markdown이 읽기 어려운 구조 | 형식 오류 |
| 빈 데이터에서 traceback 발생 | 빈 목록 처리 누락 |
| 파일명에 timestamp 없음 | `build_backup_filename()` 미사용 |
| 복원 기능처럼 보이는 UI 노출 | 업로드 UI 혼입 |
| 백업 UI가 기본 화면을 과도하게 복잡하게 만듦 | expander 외부 노출 |

---

## 테스트 케이스

### TC-01 백업/내보내기 UI 표시

**조건**: 앱 실행 후 `💾 백업/내보내기` expander 확인

**기대**
- 기본 접힘 상태로 표시됨
- 복원 기능이 없다는 안내 문구 표시
- **JSON 백업** 영역과 **데이터 내보내기** 영역이 좌우로 구분되어 있음

**통과 기준**
- expander를 열기 전에는 메인 화면을 방해하지 않음

---

### TC-02 todos.json 다운로드

**조건**: `todos.json`이 존재하는 상태

**기대**
- `todos_backup_YYYYMMDD_HHMMSS.json` 형식 파일 다운로드
- 파일 내용이 현재 `todos.json`과 일치
- 원본 `todos.json`은 변경되지 않음

**통과 기준**
- 다운로드 파일을 원본과 diff 비교 시 동일함

---

### TC-03 roles.json 다운로드

**조건**: `roles.json`이 존재하는 상태

**기대**
- `roles_backup_YYYYMMDD_HHMMSS.json` 형식 파일 다운로드
- 파일 내용이 현재 `roles.json`과 일치
- 원본 `roles.json`은 변경되지 않음

**통과 기준**
- 다운로드 파일을 원본과 diff 비교 시 동일함

---

### TC-04 통합 JSON 백업

**조건**: todos와 roles가 로드된 상태

**기대**
- `todo_app_backup_YYYYMMDD_HHMMSS.json` 형식 파일 다운로드
- JSON 구조:
  ```json
  {
    "schema": "todo_ai_app_backup_v1",
    "generated_at": "...",
    "todos": [...],
    "roles": [...]
  }
  ```
- `secrets.toml`, API key, `ignored_role_tags.json`이 포함되지 않음
- 최상위 키가 `schema`, `generated_at`, `todos`, `roles` 4개만 존재함

**통과 기준**
- JSON 파일 열었을 때 위 구조 외 다른 키가 없음

---

### TC-05 CSV 내보내기

**조건**: todo 데이터가 있는 상태

**기대**
- `todo_export_YYYYMMDD_HHMMSS.csv` 형식 파일 다운로드
- Excel 또는 텍스트 편집기에서 한글이 깨지지 않음
- 포함 필드 (순서 포함):

  | 필드 |
  |---|
  | id |
  | title |
  | role_tag |
  | role_name |
  | created_date |
  | start_date |
  | due_date |
  | priority |
  | done |
  | memo |
  | created_at |
  | updated_at |

- 누락 필드는 빈 값으로 표시

**통과 기준**
- Excel에서 파일 열었을 때 열 이름과 한글 데이터가 정상 표시됨

---

### TC-06 Markdown 내보내기

**조건**: todo 데이터가 있는 상태

**기대**
- `todo_export_YYYYMMDD_HHMMSS.md` 형식 파일 다운로드
- 파일 첫 줄이 `# Todo Export`로 시작
- `generated_at` 시각 포함
- 미완료 항목이 `## 미완료 항목` 섹션에 먼저 표시
- 완료 항목이 `## 완료 항목` 섹션에 나중에 표시
- `memo`가 있는 항목은 `- 메모: ...` 줄 포함
- `memo`가 없는 항목은 메모 줄 생략

**통과 기준**
- Markdown 뷰어 또는 텍스트 편집기에서 구조가 명확히 읽힘

---

### TC-07 빈 todo 데이터

**조건**: `todos`가 빈 목록인 상태

**기대**
- CSV 내보내기 — 헤더만 있는 파일 생성, 앱 중단 없음
- Markdown 내보내기 — `(없음)` 표시로 정상 생성, 앱 중단 없음
- 오류 traceback이 화면에 노출되지 않음

**통과 기준**
- 버튼 클릭 후 앱이 정상 상태를 유지함

---

### TC-08 roles.json 없음

**조건**: `roles.json`이 없는 상태 (임시 제거 또는 파일 미존재)

**기대**
- `roles.json` 다운로드 버튼 영역에 안내 메시지(`roles.json 파일이 없습니다.`) 표시
- 앱이 중단되지 않음
- 통합 백업은 `load_roles()` 결과(빈 목록)로 안전하게 생성
- 원본 파일을 새로 만들거나 수정하지 않음

**통과 기준**
- `read_file_bytes_if_exists()` 반환 `None` 시 안내 분기 정상 동작

---

### TC-09 todos.json 없음

**조건**: `todos.json`이 없는 상태 (임시 제거 또는 파일 미존재)

**기대**
- `todos.json` 다운로드 버튼 영역에 안내 메시지(`todos.json 파일이 없습니다.`) 표시
- 앱이 중단되지 않음
- CSV / Markdown은 `load_todos()` 결과 기준으로 안전하게 처리
- 원본 파일을 새로 만들거나 수정하지 않음

**통과 기준**
- `read_file_bytes_if_exists()` 반환 `None` 시 안내 분기 정상 동작

---

### TC-10 원본 불변성 확인

**조건**: 백업/내보내기 버튼을 모두 한 번씩 실행

**기대**
- `git status --short`에 `todos.json` / `roles.json` 변경이 나타나지 않음
- 파일 수정 시간이 불필요하게 바뀌지 않음
- `save_todos()` / `save_roles()` 가 호출되지 않아야 함

**검증 명령**
```bash
git status --short
```

**통과 기준**
- `M todos.json` 또는 `M roles.json` 항목이 나타나지 않음

---

### TC-11 민감정보 제외

**조건**: `.streamlit/secrets.toml`이 존재하는 환경

**기대**
- 어떤 다운로드 파일에도 `SM_MINDLOGIC`, API key, `secrets.toml` 내용이 포함되지 않음
- 통합 백업 JSON에도 secrets 관련 키가 없음

**통과 기준**
- 다운로드 파일을 텍스트 편집기에서 열었을 때 API key 문자열이 검색되지 않음

---

### TC-12 다운로드 파일명

**조건**: 여러 다운로드 버튼 순차 실행

**기대**
- 각 파일명에 `YYYYMMDD_HHMMSS` timestamp 포함
- 파일 확장자가 올바름:
  - JSON 백업: `.json`
  - CSV 내보내기: `.csv`
  - Markdown 내보내기: `.md`
- 동일 실행 시점의 파일명 timestamp가 일관되거나 충돌 없이 생성됨

**통과 기준**
- 다운로드 파일명 5개 모두 timestamp가 포함된 형식임

---

### TC-13 기존 기능 회귀

백업/내보내기 추가 이후 다음 기존 기능들이 정상 동작하는지 확인한다.

| 기능 | 확인 항목 |
|---|---|
| AI 자연어 입력 | 파싱 후보 정상 표시 및 적용 |
| 오늘 할 일 | 기준일 기준 todo 정상 표시 |
| 주간 보기 | 이번 주/다음 주 분류 및 진행률 정상 |
| 전체 보기 | 필터/정렬/상세/수정/삭제 정상 |
| 직접 입력 | 저장 후 목록에 즉시 반영 |
| 역할/분류 관리 | 역할 추가/삭제 정상 |
| 완료 체크, 수정, 삭제 | 상태 변경 및 재렌더 정상 |

---

## 개발 원칙

- 백업/내보내기는 **읽기 전용** 기능이다.
- 복원 기능은 별도 브랜치에서 다룬다.
- 저장 구조를 변경하지 않는다.
- API key나 secrets 파일은 절대 포함하지 않는다.
- JSON 기반 저장을 SQLite/Supabase로 전환하더라도 내보내기 기능의 사용자 경험은 유지한다.
- 다운로드 기능은 앱 사용성을 방해하지 않도록 expander 안에 둔다.
