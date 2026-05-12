# Design Decisions

## 1. Storage Roadmap

저장 계층은 단계적으로 전환한다.

| 단계 | 저장 방식 | 상태 |
|---|---|---|
| 1 | todos.json + roles.json | ✅ 현재 |
| 2 | SQLite | 예정 |
| 3 | Supabase | 예정 |
| 4 | 로그인 및 사용자별 데이터 분리 | 예정 |

- 현재는 JSON 기반이지만 저장 계층 함수(`load_todos`, `save_todos`, `add_todo`, `update_todo_done`, `delete_todo`, `find_todo`)를 분리해 향후 전환 가능하게 설계했다.
- **todos.json** 은 할 일 데이터, **roles.json** 은 역할/분류 사전이다.
- 두 파일 모두 런타임 파일이므로 `.gitignore`에서 Git 추적을 제외한다.

---

## 2. Todo Data Principle

- `title`은 원본 데이터이다.
- `role_tag`, `role_name`은 `title`과 `roles.json`을 기준으로 계산되는 **파생 데이터**이다.
- `title` 안의 `@태그`는 삭제하지 않는다.
- 분류 삭제 후에도 `title`의 `@태그`는 유지된다.
- 향후 `notes` / `memo` 필드를 추가할 수 있다.

---

## 3. Role Tag Principle

핵심 원칙:

- **등록된 `@태그`만 역할/분류로 인정한다.**
- 등록되지 않은 `@태그`는 일반 문자로 처리한다.
- 등록하지 않고 저장한 `@태그`는 **미분류**로 처리한다.
- `"미등록 역할"` 상태는 사용하지 않는다.
- 같은 태그를 나중에 등록하면 기존 `title`에 남아 있는 `@태그`도 자동으로 분류된다.

---

## 4. Why `ignored_role_tags` Was Removed

> 중요한 설계 결정 — 복잡성 제거

- 초기에 미등록 태그를 `ignored_role_tags.json`으로 관리하는 방식을 검토했다.
- 비활성화, 분류 제외, 숨김, 복원, 목록 삭제가 겹치며 UX가 복잡해졌다.
- 개인용 todo 앱에서는 사용자가 감당해야 할 상태가 너무 많아졌다.
- 따라서 `ignored_role_tags` 구조를 제거하고, **"등록된 태그만 분류"** 라는 단순 원칙으로 정리했다.

---

## 5. Role Active vs Role Delete

| 구분 | 의미 | 데이터 영향 |
|---|---|---|
| `active=false` | 지금은 기본 필터 목록에서 숨기지만, 나중에 다시 사용할 수 있는 분류 | `roles.json`의 `active` 플래그만 변경 |
| 삭제 | `roles.json`에서 분류를 완전히 제거 | 해당 역할 항목 삭제, 기존 `@태그`는 `title`에 남지만 더 이상 분류로 인식하지 않음 |

---

## 6. Auto Reclassification

- 앱은 현재 `roles.json` 기준으로 매번 `role_tag`, `role_name`을 재계산한다(`enrich_todos_with_roles`).
- 따라서 분류 삭제, 재등록, 이름 변경이 화면에 **자동 반영**된다.
- 별도 reindex checkbox는 필요하지 않다고 판단했다.

---

## 7. UI Design Principle

- 전체 보기는 **좌측 목록 / 우측 보기 설정**으로 분리한다 (`st.columns([4, 1])`).
- **역할/분류관리의 `active`** 는 전역 설정이다 — `roles.json`에 저장된다.
- **전체 보기의 분류 checkbox** 는 현재 화면에서만 적용되는 보기 필터이다 — `roles.json`을 변경하지 않는다.
- 완료 항목 일괄 삭제는 확인 checkbox를 요구한다 (안전 장치).

---

## 8. Calendar and Weekly Planning Principle

향후 Calendar 연동 설계 원칙:

- Google Calendar는 처음에는 **읽기 전용**으로 연동한다.
- Calendar 일정과 Todo를 처음부터 양방향 동기화하지 않는다.
- 초기에는 Calendar를 참고 정보로 보여주고, Todo와 같은 날짜/주간 화면에서 **병렬 표시**한다.
- 주간 plan 기능은 캘린더 일정과 기존 todo를 참고하여 이번 주에 필요한 todo를 구성하는 방향으로 설계한다.
- Calendar 이벤트 자체를 바로 todo로 강제 변환하지 않고, **사용자가 확인 후 등록**하는 흐름이 안전하다.

---

## 9. AI Parsing Principle

향후 AI API 설계 원칙:

- 자연어 입력은 하나의 할 일이 아니라 **복수 할 일을 포함**할 수 있다.
- AI는 자연어에서 할 일, 시작일, 마감일, 우선순위, 역할태그를 추출한다.
- 단순 동작 중심이 아니라 **산출물 단계 중심**으로 분해한다.
- AI가 생성한 할 일은 바로 저장하지 않고, **사용자가 검토/수정 후 등록**할 수 있게 하는 것이 안전하다.
- AI는 세부 할 일을 제안할 수 있지만, 최종 등록은 사용자가 선택한다.
- **Mindlogic API Gateway**와 **gpt-5.4-mini**를 사용할 예정이다.

---

## 10. Next Development Priorities

| 순위 | 항목 |
|---|---|
| 1 | 할 일 수정 기능 |
| 2 | 할 일별 메모 기능 |
| 3 | 삭제 재확인 개선 |
| 4 | Mindlogic API 자연어 파싱 |
| 5 | AI 파싱 결과 검토/수정 흐름 |
| 6 | 주간 업무 plan 기능 |
| 7 | Google Calendar 읽기 연동 |
| 8 | Calendar + Todo 통합 주간 화면 |
| 9 | SQLite 전환 |
