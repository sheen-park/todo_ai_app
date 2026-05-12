# Project State

## Project Goal

- Colab 실습용 todo 앱을 넘어서 개인이 실제 사용할 수 있는 웹 기반 todo 앱을 단계적으로 개발한다.
- 1단계는 Streamlit + todos.json 기반 로컬 개인용 앱이다.
- 이후 SQLite, Supabase, 로그인/사용자별 데이터 분리로 확장할 수 있다.

---

## Current Tech Stack

| 항목 | 내용 |
|---|---|
| 언어 | Python |
| 프레임워크 | Streamlit |
| 라이브러리 | pandas |
| SDK | openai |
| 로컬 저장 | todos.json, roles.json |
| AI API (예정) | Mindlogic API Gateway / gpt-5.4-mini |

---

## Current File Structure

```
todo_ai_app/
├─ app.py                          # 단일 파일 앱 (전체 로직)
├─ requirements.txt                # streamlit, pandas, openai
├─ .gitignore
├─ todos.json                      # runtime, git ignored
├─ roles.json                      # runtime, git ignored
├─ .streamlit/
│  └─ secrets.toml.example         # SM_MINDLOGIC 키 예시
└─ docs/
   ├─ PROJECT_STATE.md
   ├─ DESIGN_DECISIONS.md
   └─ ROADMAP.md
```

> **todos.json**, **roles.json** 은 런타임 파일이며 `.gitignore`에 의해 Git 추적에서 제외된다.

---

## Implemented Features

### 할 일 관리
- 할 일 직접 입력
- 입력일, 시작일, 마감일, 우선순위(상/중/하), 완료 여부 필드
- 완료 checkbox 동기화 (오늘 할 일 ↔ 전체 보기)
- 개별 삭제 (아이콘 버튼)
- 완료 항목 일괄 삭제 (확인 checkbox 포함)

### 오늘 할 일
- 기준일(selected_date) 기반 오늘 할 일 필터
- 상태 계산: 완료 / 예정 / 진행 중 / 오늘 마감 / 지연
- 정렬 기준 선택: 분류 / 상태 / 우선순위

### 전체 보기
- 2단 레이아웃 (좌: 목록, 우: 보기 설정)
- 완료 포함 필터
- 우선순위 필터
- 상태 필터
- 역할/분류 표시 필터 (체크박스, 전체 체크/전체 해제 포함)

### 역할/분류 관리
- roles.json 기반 역할/분류 관리
- @태그 기반 분류 (등록된 태그만 분류로 인정)
- 미등록 @태그 발견 시 등록 여부 확인
- 등록하지 않고 저장하면 미분류 처리
- 역할 active on/off
- 역할 이름 변경
- 역할 삭제 (삭제 후 해당 @태그는 미분류로 자동 처리)
- 같은 태그 재등록 시 기존 제목의 @태그 자동 재분류

---

## Not Implemented Yet

- 할 일 수정 기능
- 할 일별 메모 기능
- 삭제 재확인 고도화
- 자연어 입력 파싱
- 복수 할 일 포함 자연어 처리
- AI 기반 세부 할 일 분해
- Mindlogic API 연동
- Google Calendar 읽기 연동
- Calendar + Todo 통합 표시
- 주간 단위 업무 plan 기능
- 캘린더 일정을 참고한 주간 todo 작성
- SQLite 전환
- Supabase 전환
- 로그인 및 사용자별 데이터 분리

---

## Current Development Status

- 1단계 MVP는 동작한다.
- 현재는 roles.json 기반 분류 구조와 UI 개선까지 진행되었다.
- 다음 주요 단계는 **할 일 수정 기능** 또는 **할 일별 메모 기능**이다.
- 자연어 파싱 전에 수정 기능과 메모 기능을 먼저 구현하는 것이 안전하다.

---

## Run Commands

Windows PowerShell 기준:

```powershell
cd c:\dev\todo_ai_app
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

---

## Manual Verification Checklist

- [ ] 할 일 추가 정상 동작
- [ ] @태그가 있는 할 일 추가 → 등록된 태그이면 분류 인정
- [ ] 미등록 @태그 발견 시 등록 여부 확인 UI 표시
- [ ] 등록하지 않고 저장 → 미분류 처리
- [ ] 완료 checkbox 체크 → 오늘 할 일과 전체 보기 동기화
- [ ] 개별 삭제 버튼 (🗑 아이콘) 동작
- [ ] 완료 항목 일괄 삭제: 확인 checkbox 미선택 시 경고, 선택 후 삭제
- [ ] 오늘 할 일 정렬 기준 radio (분류 / 상태 / 우선순위) 동작
- [ ] 전체 보기 2단 레이아웃 표시
- [ ] 전체 보기 우선순위 필터 / 상태 필터 / 완료 포함 필터 동작
- [ ] 전체 보기 분류 체크박스: active 역할 → 비활성 역할 → 미분류 순서
- [ ] 전체 체크 / 전체 해제 버튼 동작
- [ ] 역할 active on/off → 분류 필터 목록에 반영
- [ ] 역할 이름 변경 → 기존 할 일 role_name 자동 갱신
- [ ] 역할 삭제 → 기존 할 일 미분류 처리
- [ ] 같은 태그 재등록 → 기존 할 일 자동 재분류
