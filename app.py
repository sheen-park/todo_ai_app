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
import re
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
ROLES_FILE = BASE_DIR / "roles.json"

# ---------------------------------------------------------------------------
# 역할 저장 계층
# ---------------------------------------------------------------------------

_DEFAULT_ROLES_RAW: list[tuple[str, str]] = [
    ("kca", "KCA협회 센터장"),
    ("sw", "SW중심대학"),
    ("coaching", "코칭/상담"),
    ("lecture", "강의"),
    ("personal", "개인"),
]


def get_default_roles() -> list[dict]:
    """기본 역할 목록을 반환합니다."""
    now = datetime.now().isoformat()
    return [
        {"tag": tag, "name": name, "active": True, "created_at": now, "updated_at": now}
        for tag, name in _DEFAULT_ROLES_RAW
    ]


def load_roles() -> list[dict]:
    """roles.json에서 역할 목록을 불러옵니다.
    파일이 없으면 기본 역할 목록을 생성해 저장하고 반환합니다.
    """
    if not ROLES_FILE.exists():
        defaults = get_default_roles()
        save_roles(defaults)
        return defaults
    try:
        with open(ROLES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            st.warning("roles.json 형식이 올바르지 않아 기본 역할을 사용합니다.")
            return get_default_roles()
        now = datetime.now().isoformat()
        for item in data:
            item.setdefault("tag", "")
            item["tag"] = normalize_role_tag(item["tag"])
            item.setdefault("name", item["tag"])
            item.setdefault("active", True)
            item.setdefault("created_at", now)
            item.setdefault("updated_at", now)
        return data
    except json.JSONDecodeError:
        st.warning("roles.json 파일이 손상되었습니다. 기본 역할을 사용합니다.")
        return get_default_roles()
    except Exception as e:
        st.warning(f"roles.json을 읽는 중 오류가 발생했습니다: {e}")
        return get_default_roles()


def save_roles(roles: list[dict]) -> None:
    """역할 목록을 roles.json에 저장합니다."""
    try:
        with open(ROLES_FILE, "w", encoding="utf-8") as f:
            json.dump(roles, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"roles.json 저장 중 오류가 발생했습니다: {e}")


def normalize_role_tag(tag: str) -> str:
    """앞의 @ 제거, 소문자 변환, 허용 문자(영문/숫자/언더스코어/하이픈)만 유지."""
    tag = tag.strip().lstrip("@").lower()
    tag = re.sub(r"[^a-z0-9_-]", "", tag)
    return tag


def find_role_by_tag(roles: list[dict], tag: str) -> dict | None:
    """tag 기준으로 role dict를 반환합니다. 없으면 None."""
    tag = normalize_role_tag(tag)
    for role in roles:
        if role.get("tag") == tag:
            return role
    return None


def add_role(tag: str, name: str, active: bool = True) -> list[dict]:
    """roles.json에 새 역할을 추가하거나 기존 역할을 업데이트합니다."""
    tag = normalize_role_tag(tag)
    roles = load_roles()
    now = datetime.now().isoformat()
    existing = find_role_by_tag(roles, tag)
    if existing:
        existing["name"] = name
        existing["active"] = active
        existing["updated_at"] = now
    else:
        roles.append({"tag": tag, "name": name, "active": active,
                      "created_at": now, "updated_at": now})
    save_roles(roles)
    return roles


def update_role_active(tag: str, active: bool) -> list[dict]:
    """active 값을 변경하고 저장합니다."""
    tag = normalize_role_tag(tag)
    roles = load_roles()
    for role in roles:
        if role.get("tag") == tag:
            role["active"] = active
            role["updated_at"] = datetime.now().isoformat()
            break
    save_roles(roles)
    return roles


def update_role_name(tag: str, name: str) -> list[dict]:
    """role name을 변경하고 저장합니다."""
    tag = normalize_role_tag(tag)
    roles = load_roles()
    for role in roles:
        if role.get("tag") == tag:
            role["name"] = name
            role["updated_at"] = datetime.now().isoformat()
            break
    save_roles(roles)
    return roles


def build_role_filter_options(roles: list[dict]) -> list[str]:
    """roles 목록에서 역할 필터 선택지를 동적으로 생성합니다."""
    options = ["전체", "미분류"]
    for role in roles:
        if role.get("active") and role.get("name"):
            options.append(role["name"])
    options.append("미등록 역할")
    options.append("비활성 역할")
    return options


# ---------------------------------------------------------------------------
# 역할 태그 추출 함수
# ---------------------------------------------------------------------------

def extract_role_from_title(title: str, roles: list[dict]) -> tuple[str, str]:
    """제목에서 첫 번째 @태그를 추출하여 (role_tag, role_name)을 반환합니다.
    태그가 없으면 ("", "미분류")를 반환합니다.
    roles에 없는 태그는 (tag, "미등록 역할")을 반환합니다.
    """
    if not title:
        return "", "미분류"
    match = re.search(r"@([A-Za-z0-9_-]+)", title)
    if not match:
        return "", "미분류"
    tag = match.group(1).lower()
    role = find_role_by_tag(roles, tag)
    if role:
        return tag, role["name"]
    return tag, "미등록 역할"


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


def enrich_todos_with_roles(todos: list[dict], roles: list[dict]) -> list[dict]:
    """할 일 목록에 role_tag/role_name을 roles.json 기준으로 정상화(보정)합니다.
    메모리만 변경하므로 todos.json은 자동 덮어쓰지 않습니다.
    """
    for item in todos:
        tag, name = extract_role_from_title(item.get("title", ""), roles)
        item["role_tag"] = tag
        item["role_name"] = name
    return todos


def save_todos(todos: list[dict]) -> None:
    """할 일 목록을 todos.json에 저장합니다."""
    try:
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {e}")


def add_todo(title: str, start_date: str, due_date: str, priority: str,
             roles: list[dict] | None = None) -> dict:
    """새 할 일을 생성하고 저장합니다.
    # 향후 user_id 추가 가능
    """
    if roles is None:
        roles = load_roles()
    now = datetime.now().isoformat()
    today = date.today().isoformat()
    role_tag, role_name = extract_role_from_title(title, roles)
    new_todo = {
        "id": str(uuid.uuid4()),
        "title": title,
        "created_date": today,
        "start_date": start_date,
        "due_date": due_date,
        "priority": priority,
        "role_tag": role_tag,
        "role_name": role_name,
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

def get_done_checkbox_key(scope: str, todo: dict) -> str:
    """done 값과 updated_at을 포함한 동적 checkbox key를 생성합니다.
    done 또는 updated_at이 바뀌면 key도 달라져 Streamlit이 stale session_state를 재사용하지 않습니다.
    """
    todo_id = todo.get("id", "")
    done_token = "1" if bool(todo.get("done", False)) else "0"
    updated_token = (
        str(todo.get("updated_at", ""))
        .replace(":", "")
        .replace(".", "")
        .replace("-", "")
        .replace("T", "")
    )
    return f"{scope}_done_{todo_id}_{done_token}_{updated_token}"


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
            "역할": todo.get("role_name", "미분류"),
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

def render_input_form(roles: list[dict]) -> None:
    """할 일 직접 입력 폼을 렌더링합니다."""
    st.subheader("✏️ 할 일 추가")
    active_tags = ", ".join(
        f"@{r['tag']}" for r in roles if r.get("active")
    )
    st.caption(f"제목에 역할 태그를 붙이면 역할별로 분류됩니다. 예: {active_tags}")
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
                roles=roles,
            )
            st.success("저장되었습니다!")
            st.rerun()


def render_today_view(todos: list[dict], selected_date: date, roles: list[dict]) -> None:
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
        todo_id = todo["id"]
        current_done = bool(todo.get("done", False))
        checkbox_key = get_done_checkbox_key("today", todo)
        col1, col2 = st.columns([0.08, 0.92])
        with col1:
            new_done = st.checkbox(
                label="완료",
                value=current_done,
                key=checkbox_key,
                label_visibility="collapsed",
            )
        with col2:
            role_label = todo.get("role_name", "미분류")
            st.markdown(
                f"{icon} **{todo['title']}**  \n"
                f"[{role_label}] 시작: {todo.get('start_date','')} | 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')}"
            )
        if new_done != current_done:
            update_todo_done(todo_id, new_done)
            st.rerun()


def render_all_view(selected_date: date, roles: list[dict]) -> None:
    """전체 보기 섹션을 렌더링합니다.
    항상 최신 데이터를 직접 불러와 필터링에 반영합니다.
    """
    st.subheader("📂 전체 보기")

    todos = load_todos()
    todos = enrich_todos_with_roles(todos, roles)

    role_filter_options = build_role_filter_options(roles)

    col1, col2, col3, col4 = st.columns(4)
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
    with col4:
        role_filter = st.selectbox(
            "역할 필터",
            role_filter_options,
            key="role_filter",
        )

    inactive_role_names = {
        r["name"] for r in roles if not r.get("active") and r.get("name")
    }

    filtered = []
    for todo in todos:
        status = compute_status(todo, selected_date)
        todo_role_name = todo.get("role_name", "미분류")
        todo_role_tag = todo.get("role_tag", "")

        if not show_done and todo.get("done"):
            continue
        if priority_filter != "전체" and todo.get("priority") != priority_filter:
            continue
        if status_filter != "전체" and status != status_filter:
            continue
        if role_filter != "전체":
            if role_filter == "미분류":
                if todo_role_tag != "":
                    continue
            elif role_filter == "미등록 역할":
                if todo_role_name != "미등록 역할":
                    continue
            elif role_filter == "비활성 역할":
                if todo_role_name not in inactive_role_names:
                    continue
            else:
                if todo_role_name != role_filter:
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
        todo_id = todo["id"]
        current_done = bool(todo.get("done", False))
        checkbox_key = get_done_checkbox_key("all", todo)
        c1, c2, c3 = st.columns([0.05, 0.85, 0.10])
        with c1:
            new_done = st.checkbox(
                label="완료",
                value=current_done,
                key=checkbox_key,
                label_visibility="collapsed",
            )
        with c2:
            role_label = todo.get("role_name", "미분류")
            st.markdown(
                f"{icon} **{todo['title']}**  \n"
                f"[{role_label}] 시작: {todo.get('start_date','')} | 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')} | 상태: {status}"
            )
        with c3:
            if st.button("🗑️ 삭제", key=f"del_{todo_id}"):
                delete_todo(todo_id)
                st.rerun()
        if new_done != current_done:
            update_todo_done(todo_id, new_done)
            st.rerun()

    st.caption(f"총 {len(filtered_sorted)}개 항목")


def render_role_manager(roles: list[dict], todos: list[dict]) -> None:
    """역할/분류 관리 expander를 렌더링합니다."""
    with st.expander("⚙️ 역할/분류 관리", expanded=False):

        # ── 현재 역할 목록 ──────────────────────────────────────────────
        st.markdown("**현재 역할 목록**")
        if roles:
            header_cols = st.columns([0.2, 0.45, 0.2, 0.15])
            header_cols[0].markdown("**태그**")
            header_cols[1].markdown("**역할명**")
            header_cols[2].markdown("**사용 여부**")
            for role in roles:
                tag = role.get("tag", "")
                name = role.get("name", "")
                active = bool(role.get("active", True))
                c_tag, c_name, c_active, _ = st.columns([0.2, 0.45, 0.2, 0.15])
                c_tag.markdown(f"`@{tag}`")
                c_name.markdown(name)
                new_active = c_active.checkbox(
                    "활성",
                    value=active,
                    key=f"role_active_{tag}",
                    label_visibility="collapsed",
                )
                if new_active != active:
                    update_role_active(tag, new_active)
                    st.rerun()
        else:
            st.info("등록된 역할이 없습니다.")

        st.divider()

        # ── 새 역할 등록 ────────────────────────────────────────────────
        st.markdown("**새 역할 등록**")
        with st.form("add_role_form", clear_on_submit=True):
            rc1, rc2 = st.columns([0.35, 0.65])
            with rc1:
                new_tag_input = st.text_input("태그 (예: family)", key="new_role_tag_input")
            with rc2:
                new_name_input = st.text_input("역할명 (예: 가족)", key="new_role_name_input")
            role_submitted = st.form_submit_button("등록")

        if role_submitted:
            norm_tag = normalize_role_tag(new_tag_input)
            if not norm_tag:
                st.warning("태그를 입력해 주세요. (@없이 영문/숫자만)")
            elif not new_name_input.strip():
                st.warning("역할명을 입력해 주세요.")
            elif find_role_by_tag(roles, norm_tag) is not None:
                st.warning(f"이미 등록된 태그입니다: @{norm_tag}")
            else:
                add_role(norm_tag, new_name_input.strip())
                st.success(f"@{norm_tag} ({new_name_input.strip()}) 등록 완료!")
                st.rerun()

        st.divider()

        # ── 미등록 역할 후보 ────────────────────────────────────────────
        unregistered_tags = sorted({
            t.get("role_tag", "")
            for t in todos
            if t.get("role_name") == "미등록 역할" and t.get("role_tag", "")
        })
        if unregistered_tags:
            st.markdown("**미등록 역할 후보**")
            for u_tag in unregistered_tags:
                uc1, uc2, uc3 = st.columns([0.25, 0.50, 0.25])
                uc1.markdown(f"`@{u_tag}`")
                u_name = uc2.text_input(
                    "역할명",
                    key=f"unreg_name_{u_tag}",
                    label_visibility="collapsed",
                    placeholder="역할명 입력",
                )
                if uc3.button("등록", key=f"unreg_btn_{u_tag}"):
                    if not u_name.strip():
                        st.warning(f"@{u_tag}의 역할명을 입력해 주세요.")
                    else:
                        add_role(u_tag, u_name.strip())
                        st.success(f"@{u_tag} ({u_name.strip()}) 등록 완료!")
                        st.rerun()


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

    roles = load_roles()
    todos = load_todos()
    todos = enrich_todos_with_roles(todos, roles)

    st.divider()

    # 상단: 오늘 할 일(좌) + 입력 폼(우)
    left_col, right_col = st.columns([0.6, 0.4])
    with left_col:
        render_today_view(todos, selected_date, roles)
    with right_col:
        render_input_form(roles)

    st.divider()

    # 하단: 전체 보기
    render_all_view(selected_date, roles)

    st.divider()

    # 역할/분류 관리
    render_role_manager(roles, todos)


if __name__ == "__main__":
    main()
