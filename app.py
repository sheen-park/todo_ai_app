# =============================================================================
# 개인용 AI 할 일 관리 앱 - 1단계: todos.json 로컬 저장
#
# Storage Roadmap:
# 1. todos.json - current minimal local storage
# 2. SQLite - local personal production-like storage
# 3. Supabase - cloud database
# 4. Auth + user_id - multi-user data separation
# =============================================================================

import json
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
TODOS_FILE = BASE_DIR / "todos.json"

# ---------------------------------------------------------------------------
# 저장 계층 함수
# 이 함수들만 todos.json 파일을 직접 읽거나 씁니다.
# 향후 SQLite로 전환할 때는 이 함수들의 내부 구현만 교체합니다.
# ---------------------------------------------------------------------------

def load_todos() -> list[dict]:
    """todos.json에서 할 일 목록을 불러옵니다.
    파일이 없으면 빈 리스트를 반환합니다.
    JSON 파싱 오류 시 빈 리스트를 반환하고 경고를 표시합니다.
    """
    if not TODOS_FILE.exists():
        return []
    try:
        with open(TODOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            st.warning("todos.json 형식이 올바르지 않아 초기화합니다.")
            return []
        return data
    except json.JSONDecodeError:
        st.warning("todos.json 파일이 손상되었습니다. 빈 목록으로 시작합니다.")
        return []
    except Exception as e:
        st.warning(f"todos.json을 읽는 중 오류가 발생했습니다: {e}")
        return []


def save_todos(todos: list[dict]) -> None:
    """할 일 목록을 todos.json에 저장합니다."""
    try:
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {e}")


def add_todo(title: str, start_date: str, due_date: str, priority: str) -> dict:
    """새 할 일을 생성하고 저장합니다.
    # 향후 user_id 추가 가능
    """
    now = datetime.now().isoformat()
    today = date.today().isoformat()
    new_todo = {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_date": today,
        "start_date": start_date,
        "due_date": due_date,
        "priority": priority,
        "done": False,
        "created_at": now,
        "updated_at": now,
    }
    todos = load_todos()
    todos.append(new_todo)
    save_todos(todos)
    return new_todo


def update_todo_done(todo_id: str, done: bool) -> None:
    """특정 할 일의 완료 여부를 변경하고 저장합니다. updated_at을 갱신합니다."""
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["done"] = done
            todo["updated_at"] = datetime.now().isoformat()
            break
    save_todos(todos)


def delete_todo(todo_id: str) -> None:
    """특정 할 일을 삭제하고 저장합니다."""
    todos = load_todos()
    todos = [t for t in todos if t["id"] != todo_id]
    save_todos(todos)


def find_todo(todos: list[dict], todo_id: str) -> dict | None:
    """todo_id로 특정 할 일을 찾아 반환합니다. 없으면 None을 반환합니다."""
    for todo in todos:
        if todo["id"] == todo_id:
            return todo
    return None


# ---------------------------------------------------------------------------
# 상태 계산 함수
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> date | None:
    """날짜 문자열을 date 객체로 변환합니다. 실패 시 None을 반환합니다."""
    try:
        return date.fromisoformat(date_str)
    except Exception:
        return None


def compute_status(todo: dict, selected_date: date) -> str:
    """기준일(selected_date)을 기준으로 할 일의 상태를 계산합니다.
    완료된 항목은 항상 "완료"를 반환합니다.
    """
    if todo.get("done"):
        return "완료"

    start = _parse_date(todo.get("start_date", ""))
    due = _parse_date(todo.get("due_date", ""))

    if start is None or due is None:
        return "날짜 오류"

    if selected_date < start:
        return "예정"
    elif selected_date == due:
        return "오늘 마감"
    elif selected_date < due:
        return "진행 중"
    else:
        return "지연"


# ---------------------------------------------------------------------------
# UI 헬퍼 함수
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"상": 0, "중": 1, "하": 2}
STATUS_COLOR = {
    "완료": "✅",
    "예정": "🔵",
    "진행 중": "🟢",
    "오늘 마감": "🟠",
    "지연": "🔴",
    "날짜 오류": "⚠️",
}


def build_display_df(todos: list[dict], selected_date: date) -> pd.DataFrame:
    """표시용 DataFrame을 생성합니다."""
    rows = []
    for todo in todos:
        status = compute_status(todo, selected_date)
        rows.append({
            "id": todo["id"],
            "상태": STATUS_COLOR.get(status, "") + " " + status,
            "할 일": todo.get("title", ""),
            "시작일": todo.get("start_date", ""),
            "마감일": todo.get("due_date", ""),
            "우선순위": todo.get("priority", ""),
            "완료": todo.get("done", False),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 섹션 렌더링 함수
# ---------------------------------------------------------------------------

def render_input_form() -> None:
    """할 일 직접 입력 폼을 렌더링합니다."""
    st.subheader("✏️ 할 일 추가")
    with st.form("add_todo_form", clear_on_submit=True):
        title = st.text_input("할 일 제목 *")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("시작일", value=date.today())
        with col2:
            due_date = st.date_input("마감일", value=date.today())
        priority = st.selectbox("우선순위", ["상", "중", "하"])
        submitted = st.form_submit_button("저장")

    if submitted:
        if not title.strip():
            st.warning("할 일 제목을 입력해 주세요.")
        elif due_date < start_date:
            st.warning("마감일은 시작일보다 빠를 수 없습니다.")
        else:
            add_todo(
                title=title.strip(),
                start_date=start_date.isoformat(),
                due_date=due_date.isoformat(),
                priority=priority,
            )
            st.success("저장되었습니다!")
            st.rerun()


def render_today_view(todos: list[dict], selected_date: date) -> None:
    """오늘 할 일 보기 섹션을 렌더링합니다."""
    st.subheader("📋 오늘 할 일")

    today_todos = []
    for todo in todos:
        if todo.get("done"):
            continue
        start = _parse_date(todo.get("start_date", ""))
        if start is None:
            continue
        if start <= selected_date:
            status = compute_status(todo, selected_date)
            if status != "예정":
                today_todos.append(todo)

    if not today_todos:
        st.info("오늘 할 일이 없습니다.")
        return

    today_todos_sorted = sorted(
        today_todos,
        key=lambda t: (
            PRIORITY_ORDER.get(t.get("priority", "하"), 2),
            t.get("due_date", ""),
        ),
    )

    for todo in today_todos_sorted:
        status = compute_status(todo, selected_date)
        icon = STATUS_COLOR.get(status, "")
        col1, col2 = st.columns([0.08, 0.92])
        with col1:
            current_done = bool(todo.get("done", False))
            new_done = st.checkbox(
                label="완료",
                value=current_done,
                key=f"today_done_{todo['id']}",
                label_visibility="collapsed",
            )
        with col2:
            st.markdown(
                f"{icon} **{todo['title']}**  \n"
                f"시작: {todo.get('start_date','')} | 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')}"
            )
        if new_done != current_done:
            update_todo_done(todo["id"], new_done)
            st.rerun()


def render_all_view(selected_date: date) -> None:
    """전체 보기 섹션을 렌더링합니다.
    항상 최신 데이터를 직접 불러와 필터링에 반영합니다.
    """
    st.subheader("📂 전체 보기")

    todos = load_todos()

    col1, col2, col3 = st.columns(3)
    with col1:
        show_done = st.checkbox("완료 항목 포함", value=True)
    with col2:
        priority_filter = st.selectbox(
            "우선순위 필터",
            ["전체", "상", "중", "하"],
            key="priority_filter",
        )
    with col3:
        status_filter = st.selectbox(
            "상태 필터",
            ["전체", "예정", "진행 중", "오늘 마감", "지연", "완료"],
            key="status_filter",
        )

    filtered = []
    for todo in todos:
        status = compute_status(todo, selected_date)

        if not show_done and todo.get("done"):
            continue
        if priority_filter != "전체" and todo.get("priority") != priority_filter:
            continue
        if status_filter != "전체" and status != status_filter:
            continue
        filtered.append(todo)

    if not filtered:
        st.info("표시할 항목이 없습니다.")
        return

    filtered_sorted = sorted(
        filtered,
        key=lambda t: (
            PRIORITY_ORDER.get(t.get("priority", "하"), 2),
            t.get("due_date", ""),
        ),
    )

    for todo in filtered_sorted:
        status = compute_status(todo, selected_date)
        icon = STATUS_COLOR.get(status, "")
        c1, c2, c3 = st.columns([0.05, 0.85, 0.10])
        with c1:
            current_done = bool(todo.get("done", False))
            new_done = st.checkbox(
                label="완료",
                value=current_done,
                key=f"all_done_{todo['id']}",
                label_visibility="collapsed",
            )
        with c2:
            st.markdown(
                f"{icon} **{todo['title']}**  \n"
                f"시작: {todo.get('start_date','')} | 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')} | 상태: {status}"
            )
        with c3:
            if st.button("🗑️ 삭제", key=f"del_{todo['id']}"):
                delete_todo(todo["id"])
                st.rerun()
        if new_done != current_done:
            update_todo_done(todo["id"], new_done)
            st.rerun()

    st.caption(f"총 {len(filtered_sorted)}개 항목")


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="개인용 AI 할 일 관리 앱", layout="wide")
    st.title("🧠 개인용 AI 할 일 관리 앱")

    # 기준일 선택
    selected_date: date = st.date_input(
        "📅 기준일",
        value=date.today(),
        key="selected_date",
    )

    todos = load_todos()

    st.divider()

    # 상단: 오늘 할 일(좌) + 입력 폼(우)
    left_col, right_col = st.columns([0.6, 0.4])
    with left_col:
        render_today_view(todos, selected_date)
    with right_col:
        render_input_form()

    st.divider()

    # 하단: 전체 보기
    render_all_view(selected_date)


if __name__ == "__main__":
    main()
