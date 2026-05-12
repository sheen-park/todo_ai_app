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


def delete_role(tag: str) -> list[dict]:
    """roles.json에서 역할을 삭제하고 저장합니다."""
    tag = normalize_role_tag(tag)
    roles = load_roles()
    roles = [r for r in roles if r.get("tag") != tag]
    save_roles(roles)
    return roles


def build_role_filter_options(roles: list[dict]) -> list[str]:
    """roles 목록에서 역할 필터 선택지를 동적으로 생성합니다."""
    options = ["전체", "미분류"]
    for role in roles:
        if role.get("active") and role.get("name"):
            options.append(role["name"])
    options.append("비활성 역할")
    return options


# ---------------------------------------------------------------------------
# 역할 태그 추출 함수
# ---------------------------------------------------------------------------

def get_unregistered_tags_in_title(title: str, roles: list[dict]) -> list[str]:
    """제목의 @태그 중 roles에 등록되지 않은 태그만 반환합니다."""
    registered = {r["tag"] for r in roles}
    seen: list[str] = []
    for raw in re.findall(r"@([A-Za-z0-9_-]+)", title):
        tag = normalize_role_tag(raw)
        if tag and tag not in registered and tag not in seen:
            seen.append(tag)
    return seen


def extract_role_from_title(title: str, roles: list[dict]) -> tuple[str, str]:
    """제목에서 @태그를 순서대로 찾아 (role_tag, role_name)을 반환합니다.
    roles에 등록된 첫 번째 태그를 기준으로 판단합니다.
    등록된 태그가 없으면 ("", "미분류")를 반환합니다.
    미등록 @태그는 일반 문자로 취급합니다.
    """
    if not title:
        return "", "미분류"
    for raw in re.findall(r"@([A-Za-z0-9_-]+)", title):
        tag = normalize_role_tag(raw)
        if not tag:
            continue
        role = find_role_by_tag(roles, tag)
        if role:
            return tag, role["name"]
    return "", "미분류"


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
    """할 일 목록에 role_tag/role_name을 roles.json 기준으로 최신화합니다.
    등록된 @태그만 역할로 인정하며, 미등록 @태그만 있는 todo는 "미분류"가 됩니다.
    기존 todo에 memo 필드가 없으면 빈 문자열로 보정합니다.
    메모리만 변경하므로 todos.json은 자동 덮어쓰지 않습니다.
    """
    for item in todos:
        tag, name = extract_role_from_title(item.get("title", ""), roles)
        item["role_tag"] = tag
        item["role_name"] = name
        item.setdefault("memo", "")
    return todos


def save_todos(todos: list[dict]) -> None:
    """할 일 목록을 todos.json에 저장합니다."""
    try:
        with open(TODOS_FILE, "w", encoding="utf-8") as f:
            json.dump(todos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"저장 중 오류가 발생했습니다: {e}")


def add_todo(
    title: str,
    start_date: str,
    due_date: str,
    priority: str,
    roles: list[dict] | None = None,
) -> dict:
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
        "memo": "",
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


def update_todo(
    todo_id: str,
    title: str,
    start_date: str,
    due_date: str,
    priority: str,
    memo: str,
    roles: list[dict],
) -> tuple[bool, str]:
    """특정 할 일의 기본 필드를 수정하고 저장합니다.
    성공 시 (True, 메시지), 실패 시 (False, 오류 메시지)를 반환합니다.
    """
    title = title.strip()
    if not title:
        return False, "할 일 제목을 입력해 주세요."
    start = _parse_date(start_date)
    due = _parse_date(due_date)
    if start is None or due is None:
        return False, "날짜 형식이 올바르지 않습니다."
    if due < start:
        return False, "마감일은 시작일보다 이전일 수 없습니다."
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            todo["title"] = title
            todo["start_date"] = start_date
            todo["due_date"] = due_date
            todo["priority"] = priority
            todo["memo"] = memo if memo is not None else ""
            role_tag, role_name = extract_role_from_title(title, roles)
            todo["role_tag"] = role_tag
            todo["role_name"] = role_name
            todo["updated_at"] = datetime.now().isoformat()
            save_todos(todos)
            return True, "수정했습니다."
    return False, "해당 할 일을 찾을 수 없습니다."


def count_completed_todos(todos: list[dict]) -> int:
    """done == True인 항목 수를 반환합니다."""
    return sum(1 for t in todos if bool(t.get("done", False)))


def delete_completed_todos() -> int:
    """todos.json에서 done == True인 항목을 모두 삭제하고 삭제 개수를 반환합니다."""
    todos = load_todos()
    remaining = [t for t in todos if not bool(t.get("done", False))]
    deleted_count = len(todos) - len(remaining)
    if deleted_count > 0:
        save_todos(remaining)
    return deleted_count


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
STATUS_ORDER = {"지연": 0, "오늘 마감": 1, "진행 중": 2, "예정": 3, "완료": 4, "날짜 오류": 5}


def summarize_memo(memo: str, max_len: int = 80) -> str:
    """메모를 한 줄 요약 문자열로 반환합니다. 줄바꿈은 공백으로 치환하며 max_len 초과 시 '...'을 붙입니다."""
    text = " ".join(str(memo or "").split())
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def sort_todos_for_today(
    todos: list[dict], selected_date: date, sort_mode: str
) -> list[dict]:
    """오늘 할 일 목록을 sort_mode에 따라 정렬합니다."""
    def _key(t: dict):
        status = compute_status(t, selected_date)
        s_ord = STATUS_ORDER.get(status, 9)
        p_ord = PRIORITY_ORDER.get(t.get("priority", "하"), 2)
        due = t.get("due_date", "")
        role = t.get("role_name") or "\uffff"  # 미분류를 마지막으로
        if sort_mode == "분류":
            # 미분류(role_tag=='')는 맨 뒤
            is_unclassified = 0 if t.get("role_tag") else 1
            return (is_unclassified, role, s_ord, p_ord, due)
        elif sort_mode == "상태":
            return (s_ord, p_ord, due, role)
        else:  # 우선순위
            return (p_ord, s_ord, due, role)
    return sorted(todos, key=_key)


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
    """할 일 직접 입력 폼을 렌더링합니다.

    미등록 @태그 처리:
    - 제목에 미등록 @태그가 발견되면 등록 여부를 묻는 phase 2로 전환합니다.
    - 등록하지 않고 저장하면 해당 todo는 미분류로 저장됩니다.
    """
    st.subheader("✏️ 할 일 추가")
    active_tags = ", ".join(
        f"@{r['tag']}" for r in roles if r.get("active")
    )
    st.caption(f"제목에 역할 태그를 붙이면 역할별로 분류됩니다. 예: {active_tags}")

    pending = st.session_state.get("_pending_todo", None)

    # ── Phase 2: 미등록 태그 발견 → 역할명 입력 및 active 설정 ──────────
    if pending:
        p_title = pending["title"]
        p_start = pending["start_date"]
        p_due = pending["due_date"]
        p_priority = pending["priority"]
        unreg_tags = pending["unregistered_tags"]  # list[str]
        is_leading = pending.get("is_leading", False)

        st.warning("미등록 @태그가 발견되었습니다. 역할명을 입력하면 등록됩니다.")
        st.caption("같은 @태그가 기존 할 일 제목에 남아 있다면, 등록 후 자동으로 같은 분류로 인식됩니다.")
        if is_leading:
            st.caption("제목 앞의 @태그는 분류 의도가 강해 보입니다. 등록을 권장합니다.")
        st.caption("'등록 후 사용함'을 끄고 등록하면 비활성 역할로 저장되며, 비활성 역할 필터에서 확인할 수 있습니다.")
        st.markdown(f"할 일: **{p_title}**")

        with st.form("pending_tag_form"):
            tag_names: dict[str, str] = {}
            tag_active: dict[str, bool] = {}
            for utag in unreg_tags:
                st.markdown(f"`@{utag}`")
                c_name, c_chk = st.columns([0.65, 0.35])
                tag_names[utag] = c_name.text_input(
                    "역할명",
                    placeholder=f"@{utag} 역할명",
                    key=f"pending_name_{utag}",
                    label_visibility="collapsed",
                )
                tag_active[utag] = c_chk.checkbox(
                    "등록 후 사용함",
                    value=True,
                    key=f"pending_active_{utag}",
                )

            cb1, cb2, cb3 = st.columns([0.42, 0.35, 0.23])
            with cb1:
                do_register_save = st.form_submit_button("입력한 역할 등록 후 저장", type="primary")
            with cb2:
                do_save_only = st.form_submit_button("등록하지 않고 저장")
            with cb3:
                do_cancel = st.form_submit_button("취소")

        if do_cancel:
            st.session_state.pop("_pending_todo", None)
            st.rerun()

        if do_save_only:
            add_todo(
                title=p_title,
                start_date=p_start,
                due_date=p_due,
                priority=p_priority,
                roles=roles,
            )
            st.session_state.pop("_pending_todo", None)
            st.success("저장되었습니다. 미등록 태그는 미분류로 처리됩니다.")
            st.rerun()

        if do_register_save:
            # 역할명이 입력된 태그만 등록 대상
            to_register = [t for t in unreg_tags if tag_names.get(t, "").strip()]
            if not to_register:
                st.warning("등록할 역할명을 하나 이상 입력해 주세요. 역할 등록 없이 저장하려면 [등록하지 않고 저장]을 눌러 주세요.")
            else:
                current_roles = roles
                for t in to_register:
                    current_roles = add_role(t, tag_names[t].strip(), active=tag_active[t])
                add_todo(
                    title=p_title,
                    start_date=p_start,
                    due_date=p_due,
                    priority=p_priority,
                    roles=current_roles,
                )
                st.session_state.pop("_pending_todo", None)
                registered_str = ", ".join(f"@{t}" for t in to_register)
                st.success(f"저장되었습니다. 등록된 태그: {registered_str}")
                st.rerun()
        return

    # ── Phase 1: 일반 입력 form ───────────────────────────────────────────
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
        title_stripped = title.strip()
        if not title_stripped:
            st.warning("할 일 제목을 입력해 주세요.")
        elif due_date < start_date:
            st.warning("마감일은 시작일보다 빠를 수 없습니다.")
        else:
            unreg = get_unregistered_tags_in_title(title_stripped, roles)
            if unreg:
                is_leading = title_stripped.startswith("@")
                st.session_state["_pending_todo"] = {
                    "title": title_stripped,
                    "start_date": start_date.isoformat(),
                    "due_date": due_date.isoformat(),
                    "priority": priority,
                    "unregistered_tags": unreg,
                    "is_leading": is_leading,
                }
                st.rerun()
            else:
                add_todo(
                    title=title_stripped,
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

    sort_col, memo_col = st.columns([3, 1])
    with sort_col:
        sort_mode = st.radio(
            "정렬 기준",
            ["분류", "상태", "우선순위"],
            horizontal=True,
            key="today_sort_mode",
            label_visibility="collapsed",
        )
    with memo_col:
        show_today_memo = st.checkbox(
            "메모 표시",
            value=False,
            key="today_show_memo",
        )

    today_todos_sorted = sort_todos_for_today(today_todos, selected_date, sort_mode)

    for todo in today_todos_sorted:
        status = compute_status(todo, selected_date)
        icon = STATUS_COLOR.get(status, "")
        todo_id = todo["id"]
        current_done = bool(todo.get("done", False))
        checkbox_key = get_done_checkbox_key("today", todo)
        col1, col2 = st.columns([0.06, 0.94])
        with col1:
            new_done = st.checkbox(
                label="완료",
                value=current_done,
                key=checkbox_key,
                label_visibility="collapsed",
            )
        with col2:
            role_label = todo.get("role_name", "미분류")
            _today_memo = str(todo.get("memo", "") or "")
            memo_flag = " 📝" if _today_memo.strip() and not show_today_memo else ""
            memo_line = f"  \n📝 {summarize_memo(_today_memo)}" if show_today_memo and _today_memo.strip() else ""
            st.markdown(
                f"{icon}{memo_flag} **{todo['title']}**  \n"
                f"[{role_label}] 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')}"
                f"{memo_line}"
            )
        if new_done != current_done:
            update_todo_done(todo_id, new_done)
            st.rerun()


def render_all_view(todos: list[dict], selected_date: date, roles: list[dict]) -> None:
    """전체 보기 섹션을 렌더링합니다.
    main()에서 enrich된 todos를 받아 필터링에 반영합니다.
    좌측: todo 목록 / 우측: 보기 설정 + 분류 체크박스 + 완료 항목 일괄 삭제
    """
    st.subheader("📂 전체 보기")

    active_roles = [r for r in roles if r.get("active") and r.get("name")]
    inactive_role_names = {
        r["name"] for r in roles if not r.get("active") and r.get("name")
    }

    left_col, right_col = st.columns([4, 1])

    # ── 우측 패널: 보기 설정 ───────────────────────────────────────────
    with right_col:
        st.markdown("**보기 설정**")

        show_done = st.checkbox("완료 항목 포함", value=True, key="all_show_done")
        priority_filter = st.selectbox(
            "우선순위",
            ["전체", "상", "중", "하"],
            key="priority_filter",
        )
        status_filter = st.selectbox(
            "상태",
            ["전체", "예정", "진행 중", "오늘 마감", "지연", "완료"],
            key="status_filter",
        )

        st.markdown("**분류 표시**")

        # 전체 체크 / 전체 해제 버튼 (checkbox 렌더링 전에 배치)
        _vis_keys = (
            [f"vis_role_{r['tag']}" for r in active_roles]
            + (["vis_inactive"] if inactive_role_names else [])
            + ["vis_unclassified"]
        )
        _sel_col, _clr_col = st.columns(2)
        if _sel_col.button("전체 체크", key="role_vis_select_all"):
            for _k in _vis_keys:
                st.session_state[_k] = True
            st.rerun()
        if _clr_col.button("전체 해제", key="role_vis_clear_all"):
            for _k in _vis_keys:
                st.session_state[_k] = False
            st.rerun()

        # 분류별 체크박스: active 역할 → 비활성 역할 → 미분류 순
        # (view filter — roles.json active 변경 없음)
        role_vis: dict[str, bool] = {}
        for role in active_roles:
            rname = role["name"]
            safe_key = f"vis_role_{role['tag']}"
            role_vis[rname] = st.checkbox(rname, value=True, key=safe_key)
        if inactive_role_names:
            role_vis["__inactive__"] = st.checkbox(
                "비활성 역할", value=True, key="vis_inactive"
            )
        role_vis["미분류"] = st.checkbox("미분류", value=True, key="vis_unclassified")

        st.divider()

        # ── 완료 항목 일괄 삭제 ────────────────────────────────────────
        st.markdown("**완료 항목 정리**")
        completed_count = count_completed_todos(todos)
        if completed_count == 0:
            st.caption("완료 항목이 없습니다.")
        else:
            st.caption(f"완료 항목: {completed_count}개")
            confirm_delete = st.checkbox(
                f"완료 항목 {completed_count}개 삭제를 확인합니다.",
                value=False,
                key="confirm_bulk_delete",
            )
            if st.button("완료 항목 일괄 삭제", key="bulk_delete_btn"):
                if not confirm_delete:
                    st.warning("삭제를 확인하려면 위 체크박스를 선택해 주세요.")
                else:
                    deleted = delete_completed_todos()
                    st.success(f"완료 항목 {deleted}개를 삭제했습니다.")
                    st.rerun()

    # ── 좌측 패널: todo 목록 ──────────────────────────────────────────
    with left_col:
        # 1) 완료 포함 여부
        filtered = [t for t in todos if show_done or not t.get("done")]

        # 2) 우선순위 필터
        if priority_filter != "전체":
            filtered = [t for t in filtered if t.get("priority") == priority_filter]

        # 3) 상태 필터
        if status_filter != "전체":
            filtered = [
                t for t in filtered
                if compute_status(t, selected_date) == status_filter
            ]

        # 4) 분류 체크박스 필터
        def _role_visible(todo: dict) -> bool:
            todo_role_tag = todo.get("role_tag", "")
            todo_role_name = todo.get("role_name", "미분류")
            if not todo_role_tag:
                return role_vis.get("미분류", True)
            if todo_role_name in inactive_role_names:
                return role_vis.get("__inactive__", True)
            return role_vis.get(todo_role_name, True)

        filtered = [t for t in filtered if _role_visible(t)]

        if not filtered:
            st.info("표시할 항목이 없습니다.")
        else:
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
                is_editing = st.session_state.get("editing_todo_id") == todo_id

                c1, c2, action_col = st.columns([0.05, 0.84, 0.11])
                with c1:
                    new_done = st.checkbox(
                        label="완료",
                        value=current_done,
                        key=checkbox_key,
                        label_visibility="collapsed",
                    )
                with c2:
                    role_label = todo.get("role_name", "미분류")
                    _memo = str(todo.get("memo", "") or "")
                    _memo_line = f"  \n📝 {summarize_memo(_memo)}" if _memo.strip() else ""
                    st.markdown(
                        f"{icon} **{todo['title']}**  \n"
                        f"[{role_label}] 시작: {todo.get('start_date','')} | 마감: {todo.get('due_date','')} | 우선순위: {todo.get('priority','')} | 상태: {status}"
                        f"{_memo_line}"
                    )
                with action_col:
                    edit_col, del_col = st.columns(2)
                    with edit_col:
                        if st.button("✏️", key=f"edit_btn_{todo_id}", help="수정"):
                            st.session_state["editing_todo_id"] = todo_id
                            st.rerun()
                    with del_col:
                        if st.button("🗑", key=f"del_{todo_id}", help="삭제"):
                            if st.session_state.get("editing_todo_id") == todo_id:
                                st.session_state.pop("editing_todo_id", None)
                            delete_todo(todo_id)
                            st.rerun()
                if new_done != current_done:
                    update_todo_done(todo_id, new_done)
                    st.rerun()

                if is_editing:
                    _start_default = _parse_date(todo.get("start_date", "")) or date.today()
                    _due_default = _parse_date(todo.get("due_date", "")) or date.today()
                    with st.form(key=f"edit_form_{todo_id}"):
                        new_title = st.text_input(
                            "할 일 제목",
                            value=todo.get("title", ""),
                            key=f"edit_title_{todo_id}",
                        )
                        col_s, col_d, col_p = st.columns(3)
                        with col_s:
                            new_start = st.date_input(
                                "시작일",
                                value=_start_default,
                                key=f"edit_start_{todo_id}",
                            )
                        with col_d:
                            new_due = st.date_input(
                                "마감일",
                                value=_due_default,
                                key=f"edit_due_{todo_id}",
                            )
                        with col_p:
                            _pri_options = ["상", "중", "하"]
                            _pri_idx = _pri_options.index(todo.get("priority", "중")) if todo.get("priority", "중") in _pri_options else 1
                            new_priority = st.selectbox(
                                "우선순위",
                                _pri_options,
                                index=_pri_idx,
                                key=f"edit_priority_{todo_id}",
                            )
                        new_memo = st.text_area(
                            "메모",
                            value=todo.get("memo", ""),
                            key=f"edit_memo_{todo_id}",
                            height=100,
                        )
                        btn_col1, btn_col2, btn_spacer = st.columns([1, 1, 5])
                        with btn_col1:
                            save_clicked = st.form_submit_button("저장")
                        with btn_col2:
                            cancel_clicked = st.form_submit_button("취소")

                    if cancel_clicked:
                        st.session_state.pop("editing_todo_id", None)
                        st.rerun()
                    if save_clicked:
                        ok, msg = update_todo(
                            todo_id=todo_id,
                            title=new_title,
                            start_date=new_start.isoformat(),
                            due_date=new_due.isoformat(),
                            priority=new_priority,
                            memo=new_memo,
                            roles=roles,
                        )
                        if ok:
                            st.session_state.pop("editing_todo_id", None)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.warning(msg)

            st.caption(f"총 {len(filtered_sorted)}개 항목")


def _render_role_rows(role_list: list[dict]) -> None:
    """역할 목록 행들을 렌더링합니다 (헤더 + 역할명 편집 + 삭제 포함)."""
    header_cols = st.columns([0.18, 0.22, 0.28, 0.13, 0.10, 0.09])
    header_cols[0].markdown("**태그**")
    header_cols[1].markdown("**현재 역할명**")
    header_cols[2].markdown("**새 역할명**")
    header_cols[3].markdown("**사용 여부**")
    for role in role_list:
        tag = role.get("tag", "")
        name = role.get("name", "")
        active = bool(role.get("active", True))
        c_tag, c_name, c_rename, c_active, c_rename_btn, c_del = st.columns(
            [0.18, 0.22, 0.28, 0.13, 0.10, 0.09]
        )
        c_tag.markdown(f"`@{tag}`")
        c_name.markdown(name)
        new_name_val = c_rename.text_input(
            "새 역할명",
            key=f"role_rename_{tag}",
            label_visibility="collapsed",
            placeholder="변경할 이름",
        )
        new_active = c_active.checkbox(
            "활성",
            value=active,
            key=f"role_active_{tag}",
            label_visibility="collapsed",
        )
        if c_rename_btn.button("변경", key=f"role_rename_btn_{tag}"):
            if not new_name_val.strip():
                st.warning(f"@{tag}의 새 역할명을 입력해 주세요.")
            elif new_name_val.strip() == name:
                st.info(f"@{tag}의 역할명이 이미 '{name}'입니다.")
            else:
                update_role_name(tag, new_name_val.strip())
                st.rerun()
        if c_del.button("삭제", key=f"role_del_{tag}"):
            delete_role(tag)
            st.rerun()
        if new_active != active:
            update_role_active(tag, new_active)
            st.rerun()


def render_role_manager(roles: list[dict]) -> None:
    """역할/분류 관리 expander를 렌더링합니다."""
    with st.expander("⚙️ 역할/분류 관리", expanded=False):
        st.caption(
            "분류는 제목에 남아 있는 @태그와 현재 roles.json을 기준으로 자동 계산됩니다. "
            "분류를 삭제하면 해당 @태그는 일반 문자로 처리되고, "
            "같은 태그를 다시 등록하면 기존 할 일도 자동으로 다시 분류됩니다."
        )

        active_roles = [r for r in roles if r.get("active")]
        inactive_roles = [r for r in roles if not r.get("active")]

        # ── 활성 역할 목록 ─────────────────────────────────────────────
        st.markdown("**활성 역할**")
        if active_roles:
            _render_role_rows(active_roles)
        else:
            st.info("활성 역할이 없습니다.")

        # ── 비활성 역할 목록 ──────────────────────────────────────────
        if inactive_roles:
            with st.expander(f"비활성 역할 ({len(inactive_roles)}개)", expanded=False):
                _render_role_rows(inactive_roles)

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
    render_all_view(todos, selected_date, roles)

    st.divider()

    # 역할/분류 관리
    render_role_manager(roles)


if __name__ == "__main__":
    main()
