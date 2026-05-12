# Roadmap

## Phase 1: Local Streamlit Todo App

> **현재 진행 중**

**목표:** 로컬에서 개인이 실제 사용할 수 있는 기본 todo 앱 완성

| 기능 | 상태 |
|---|---|
| todos.json 저장 | ✅ 완료 |
| roles.json 분류 관리 | ✅ 완료 |
| 할 일 직접 입력 | ✅ 완료 |
| 오늘 할 일 (기준일 기반) | ✅ 완료 |
| 상태 계산 (완료/예정/진행 중/오늘 마감/지연) | ✅ 완료 |
| 전체 보기 2단 레이아웃 | ✅ 완료 |
| 완료 관리 (checkbox, 일괄 삭제) | ✅ 완료 |
| 분류 표시 필터 (체크박스, 전체 체크/해제) | ✅ 완료 |
| 오늘 할 일 정렬 기준 (분류/상태/우선순위) | ✅ 완료 |
| UI 개선 (아이콘 버튼, 2단 레이아웃) | ✅ 완료 |
| 할 일 수정 기능 | ⏳ 예정 |
| 할 일별 메모 기능 | ⏳ 예정 |
| 삭제 재확인 개선 | ⏳ 예정 |

---

## Phase 2: Editing and Memo Layer

**목표:** 할 일을 생성한 이후에도 수정하고 메모를 남길 수 있는 구조 완성

- 할 일 수정 (제목, 날짜, 우선순위)
- 할 일별 메모 (자유 텍스트, `notes` 필드 추가)
- 할 일 상세 보기 (별도 화면 또는 expander)
- 삭제 재확인 개선

> 자연어 파싱 전에 수정 기능과 메모 기능을 먼저 구현하는 것이 안전하다.
> 수정 UI가 없으면 AI 파싱 결과를 검토/수정하는 흐름을 만들 수 없다.

---

## Phase 3: AI Natural Language Parsing

**목표:** 자연어 입력으로 복수 할 일을 생성하는 흐름 구현

- Mindlogic API Gateway 연동
- gpt-5.4-mini 사용
- 자연어 입력에서 복수 할 일 추출 (제목, 시작일, 마감일, 우선순위, 역할태그)
- 단순 동작 중심이 아닌 산출물 단계 중심 분해
- AI 세부 할 일 제안 기능
- AI 생성 결과를 바로 저장하지 않고 **사용자가 검토/수정 후 등록**하는 흐름

---

## Phase 4: Weekly Planning

**목표:** 주간 단위 업무 계획 화면 구현

- 주간 단위 업무 plan 화면
- 이번 주 할 일 자동 정리
- 캘린더 일정과 기존 todo를 참고한 주간 todo 제안
- 주간 리뷰 (지난 주 완료/미완료 집계)
- 다음 주 계획 작성 흐름

---

## Phase 5: Google Calendar Read Integration

**목표:** Google Calendar를 읽기 전용으로 연동하여 일정과 todo를 같이 표시

- Google Calendar API 읽기 전용 연동
- 일간/주간 화면에서 Calendar 일정과 todo 병렬 표시
- Calendar 이벤트를 참고하여 todo 등록 제안 (사용자가 선택 후 등록)
- 초기에는 Calendar write / 양방향 sync 하지 않음

---

## Phase 6: Local Production Storage

**목표:** JSON 파일에서 SQLite로 전환하여 개인 실사용 안정성 강화

- todos.json → SQLite `todos` 테이블
- roles.json → SQLite `roles` 테이블 (또는 유지)
- 저장 계층 함수(`load_todos`, `save_todos` 등)만 교체
- 기존 JSON 데이터 마이그레이션 스크립트 작성

---

## Phase 7: Cloud and Multi-user

**목표:** 클라우드 배포 및 다중 사용자 지원

- SQLite → Supabase 전환
- 로그인 기능 (Supabase Auth 또는 Streamlit 자체 인증)
- 사용자별 데이터 분리 (`user_id` 필드 추가)
- 배포형 웹앱 구조로 확장

---

## Development Principles

- 한 번에 너무 많은 기능을 구현하지 않는다.
- 작은 단위로 구현하고 검증 후 커밋한다.
- AI 파싱 결과는 바로 저장하지 않고 사용자가 검토하게 한다.
- Calendar는 처음에 읽기 전용으로만 붙인다.
- 저장 구조 전환 전까지는 `app.py` 단일 파일 중심을 유지한다.
