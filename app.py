# =============================================================================
# 개인용 AI 할 일 관리 앱 - 1단계: todos.json 로컬 저장
#
# Storage Roadmap:
# 1. todos.json - current minimal local storage
# 2. SQLite - local personal production-like storage
# 3. Supabase - cloud database
# 4. Auth + user_id - multi-user data separation
# =============================================================================

import html as html_lib
import json
import os
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from openai import OpenAI

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
    memo: str = "",
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
        "memo": memo if memo is not None else "",
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
# 주간 계획 helper 함수
# ---------------------------------------------------------------------------

def get_week_range(base_date: date) -> tuple[date, date]:
    """base_date가 속한 주의 월요일~일요일을 반환합니다."""
    week_start = base_date - timedelta(days=base_date.weekday())
    week_end = week_start + timedelta(days=6)
    return week_start, week_end


def get_next_week_range(base_date: date) -> tuple[date, date]:
    """base_date가 속한 다음 주의 월요일~일요일을 반환합니다."""
    week_start, week_end = get_week_range(base_date)
    return week_start + timedelta(days=7), week_end + timedelta(days=7)


def date_ranges_overlap(start1: date, end1: date, start2: date, end2: date) -> bool:
    """두 날짜 구간이 하루라도 겹치면 True를 반환합니다."""
    if start1 > end1 or start2 > end2:
        return False
    return start1 <= end2 and start2 <= end1


def classify_todo_for_week(todo: dict, week_start: date, week_end: date) -> str:
    """todo 하나를 주간 기준으로 분류합니다.

    반환값: '완료' | '날짜 오류' | '지연' | '이번 주 마감' | '이번 주 진행' | '해당 없음'
    '이번 주 마감'은 '이번 주 진행'보다 우선합니다.
    """
    if todo.get("done"):
        return "완료"

    start = _parse_date(todo.get("start_date", ""))
    due = _parse_date(todo.get("due_date", ""))

    if start is None or due is None:
        return "날짜 오류"

    if due < week_start:
        return "지연"
    if week_start <= due <= week_end:
        return "이번 주 마감"
    if start <= week_end and due >= week_start:
        return "이번 주 진행"
    return "해당 없음"


def filter_todos_for_week(
    todos: list[dict],
    week_start: date,
    week_end: date,
    include_done: bool = False,
) -> dict[str, list[dict]]:
    """todo 목록을 주간 그룹별로 분류해서 반환합니다.

    반환 키: '지연', '이번 주 마감', '이번 주 진행', '완료', '날짜 오류'
    '해당 없음' 항목은 포함하지 않습니다.
    include_done=False이면 완료 항목을 제외합니다.
    각 그룹은 due_date → priority(상/중/하) → title 순으로 정렬됩니다.
    """
    groups: dict[str, list[dict]] = {
        "지연": [],
        "이번 주 마감": [],
        "이번 주 진행": [],
        "완료": [],
        "날짜 오류": [],
    }

    for todo in todos:
        label = classify_todo_for_week(todo, week_start, week_end)
        if label == "해당 없음":
            continue
        if label == "완료" and not include_done:
            continue
        groups[label].append(todo)

    def _sort_key(t: dict):
        due = t.get("due_date", "9999-12-31")
        pri = PRIORITY_ORDER.get(t.get("priority", "하"), 2)
        return (due, pri, t.get("title", ""))

    for label in groups:
        groups[label].sort(key=_sort_key)

    return groups


def get_priority_icon(priority: str) -> str:
    """주간 보기 전용 우선순위 아이콘을 반환합니다."""
    return {"상": "\u203c\ufe0f", "중": "\u2757"}.get(priority, "")


def get_current_week_items(
    todos: list[dict],
    week_start: date,
    week_end: date,
) -> tuple[list[dict], list[dict]]:
    """이번 주 진행률 계산 대상(weekly_total)과 미완료 실행 리스트(weekly_active)를 반환합니다.

    weekly_total: 완료 여부와 관계없이 이번 주 실행 대상
      - 완료 todo 중 날짜 범위가 이번 주와 겹치는 것
      - 미완료 todo 중 due_date < week_start (지난 주까지 마감이었지만 미완료)
      - 미완료 todo 중 이번 주 기간과 날짜가 겹치는 것
    weekly_active: weekly_total 중 done == False
    """

    def _sort_key(t: dict):
        pri = PRIORITY_ORDER.get(t.get("priority", "하"), 2)
        due = t.get("due_date", "9999-12-31")
        return (pri, due, t.get("title", ""))

    weekly_total: list[dict] = []
    for todo in todos:
        start = _parse_date(todo.get("start_date", ""))
        due = _parse_date(todo.get("due_date", ""))
        if start is None or due is None:
            continue
        done = bool(todo.get("done"))
        if done:
            if date_ranges_overlap(start, due, week_start, week_end):
                weekly_total.append(todo)
        else:
            if due < week_start or date_ranges_overlap(start, due, week_start, week_end):
                weekly_total.append(todo)

    weekly_active = [t for t in weekly_total if not t.get("done")]
    weekly_active.sort(key=_sort_key)
    return weekly_total, weekly_active


def get_next_week_items(
    todos: list[dict],
    next_start: date,
    next_end: date,
) -> list[dict]:
    """다음 주 기간과 겹치는 미완료 todo만 반환합니다. 지연 항목은 포함하지 않습니다."""

    def _sort_key(t: dict):
        pri = PRIORITY_ORDER.get(t.get("priority", "하"), 2)
        due = t.get("due_date", "9999-12-31")
        return (pri, due, t.get("title", ""))

    result: list[dict] = []
    for todo in todos:
        if todo.get("done"):
            continue
        start = _parse_date(todo.get("start_date", ""))
        due = _parse_date(todo.get("due_date", ""))
        if start is None or due is None:
            continue
        if due < next_start:
            continue
        if date_ranges_overlap(start, due, next_start, next_end):
            result.append(todo)
    result.sort(key=_sort_key)
    return result


# ---------------------------------------------------------------------------
# 백업/내보내기 helper 함수
# ---------------------------------------------------------------------------

def get_timestamp_for_filename() -> str:
    """현재 시각을 파일명에 안전한 YYYYMMDD_HHMMSS 문자열로 반환합니다."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_file_bytes_if_exists(path: Path) -> bytes | None:
    """파일이 있으면 bytes로 읽어 반환합니다. 없거나 오류 시 None을 반환합니다."""
    try:
        if path.exists():
            return path.read_bytes()
    except Exception:
        pass
    return None


def build_backup_filename(prefix: str, extension: str, timestamp: str | None = None) -> str:
    """백업/내보내기용 파일명을 생성합니다.

    예: build_backup_filename("todos_backup", "json") → todos_backup_20260514_153000.json
    extension에 점이 있어도 없어도 처리합니다.
    """
    ts = timestamp or get_timestamp_for_filename()
    ext = extension.lstrip(".")
    return f"{prefix}_{ts}.{ext}"


def todos_to_csv_bytes(todos: list[dict]) -> bytes:
    """todo 목록을 CSV bytes(UTF-8 with BOM)로 변환합니다."""
    fields = [
        "id", "title", "role_tag", "role_name",
        "created_date", "start_date", "due_date",
        "priority", "done", "memo", "created_at", "updated_at",
    ]
    rows = []
    for todo in todos:
        rows.append({f: todo.get(f, "") for f in fields})
    df = pd.DataFrame(rows, columns=fields)
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def todos_to_markdown(todos: list[dict]) -> str:
    """todo 목록을 Markdown 문자열로 변환합니다.

    미완료 항목 먼저, 완료 항목 나중에 표시합니다.
    """
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    undone = [t for t in todos if not t.get("done")]
    done = [t for t in todos if t.get("done")]

    def _item_md(todo: dict) -> str:
        priority = todo.get("priority", "")
        title = todo.get("title", "")
        role_name = todo.get("role_name") or "미분류"
        start_str = format_date_kr_short(todo.get("start_date", ""))
        due_str = format_date_kr_short(todo.get("due_date", ""))
        memo = str(todo.get("memo", "") or "").strip()
        lines = [
            f"- [{priority}] {title}",
            f"  - 분류: {role_name}",
            f"  - 기간: {start_str} ~ {due_str}",
        ]
        if memo:
            lines.append(f"  - 메모: {memo}")
        return "\n".join(lines)

    parts = [
        "# Todo Export",
        f"generated_at: {generated_at}",
        "",
        f"## 미완료 항목 ({len(undone)}개)",
        "",
    ]
    if undone:
        parts.extend(_item_md(t) for t in undone)
    else:
        parts.append("(없음)")

    parts += [
        "",
        f"## 완료 항목 ({len(done)}개)",
        "",
    ]
    if done:
        parts.extend(_item_md(t) for t in done)
    else:
        parts.append("(없음)")

    return "\n".join(parts)


def todos_to_markdown_bytes(todos: list[dict]) -> bytes:
    """todos_to_markdown()을 UTF-8 bytes로 인코딩해서 반환합니다."""
    return todos_to_markdown(todos).encode("utf-8")


def build_combined_backup_json_bytes(todos: list[dict], roles: list[dict]) -> bytes:
    """todos와 roles를 하나의 JSON bundle로 묶어 UTF-8 bytes로 반환합니다.

    구조:
    {
      "schema": "todo_ai_app_backup_v1",
      "generated_at": "...",
      "todos": [...],
      "roles": [...]
    }
    secrets.toml, API key, ignored_role_tags.json은 포함하지 않습니다.
    """
    payload = {
        "schema": "todo_ai_app_backup_v1",
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "todos": todos,
        "roles": roles,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


# ---------------------------------------------------------------------------
# 검색 helper 함수
# ---------------------------------------------------------------------------

def normalize_search_text(value: object) -> str:
    """검색 비교용 문자열로 정규화합니다."""
    if value is None:
        return ""
    text = str(value).strip().lower()
    return re.sub(r"\s+", " ", text)


def get_todo_search_text(todo: dict) -> str:
    """todo의 검색 대상 필드를 하나의 문자열로 결합합니다."""
    role_tag_raw = str(todo.get("role_tag") or "").strip()
    role_tag_plain = role_tag_raw.lstrip("@")
    role_tag_at = f"@{role_tag_plain}" if role_tag_plain else ""

    parts = [
        todo.get("title"),
        todo.get("memo"),
        role_tag_plain,
        role_tag_at,
        todo.get("role_name"),
        todo.get("priority"),
    ]
    joined = " ".join(str(p) if p is not None else "" for p in parts)
    return normalize_search_text(joined)


def todo_matches_search(todo: dict, query: str) -> bool:
    """단일 todo가 검색어와 매칭되는지 반환합니다."""
    normalized_query = normalize_search_text(query)
    if not normalized_query:
        return True

    haystack = get_todo_search_text(todo)
    # 고급 문법(OR/정규식 등)은 1차에서 의도적으로 지원하지 않습니다.
    terms = [term for term in normalized_query.split(" ") if term]
    return all(term in haystack for term in terms)


def filter_todos_by_search(todos: list[dict], query: str) -> list[dict]:
    """검색어로 todo 리스트를 필터링해 새 리스트로 반환합니다."""
    if not normalize_search_text(query):
        return list(todos)
    return [todo for todo in todos if todo_matches_search(todo, query)]


def count_search_results(todos: list[dict], query: str) -> int:
    """검색 결과 개수를 반환합니다."""
    return len(filter_todos_by_search(todos, query))


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


def escape_html(value: object) -> str:
    """HTML 특수문자를 이스케이프합니다."""
    return html_lib.escape(str(value or ""))


_MEMO_BANNED_PHRASES = [
    "기준일",
    "파싱",
    "단일 완성 단계",
    "AI가",
    "추정",
    "배분함",
    "전체 기간",
    "출력",
    "사용자 명시",
    "초안 이후",
    "단계로 배분",
]


def sanitize_ai_memo(memo: object) -> str:
    """AI 생성 memo에서 시스템 설명 문장을 제거합니다."""
    text = str(memo or "").strip()
    if not text:
        return ""
    import re as _re
    sentences = _re.split(r"(?<=[.!?。])\ *", text)
    kept = [s for s in sentences if s.strip() and not any(p in s for p in _MEMO_BANNED_PHRASES)]
    result = " ".join(kept).strip()
    # 구두점 없이 단일 구 형태인 경우도 처리
    if not kept:
        if any(p in text for p in _MEMO_BANNED_PHRASES):
            return ""
        return text
    return result


def inject_compact_todo_css() -> None:
    """todo 목록용 compact CSS를 페이지에 주입합니다."""
    st.markdown(
        """
        <style>
        .todo-title {
            font-size: 0.97rem;
            line-height: 1.35;
            font-weight: 650;
        }
        .todo-meta {
            font-size: 0.80rem;
            line-height: 1.25;
            color: #6b7280;
            margin-top: 0.08rem;
        }
        .todo-memo {
            font-size: 0.78rem;
            line-height: 1.25;
            color: #9ca3af;
            margin-top: 0.1rem;
        }
        .todo-block {
            margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# AI 자연어 파싱 헬퍼
# ---------------------------------------------------------------------------

_MINDLOGIC_BASE_URL = "https://factchat-cloud.mindlogic.ai/v1/gateway"
_MINDLOGIC_MODEL = "gpt-5.4-mini"


def get_mindlogic_api_key() -> str:
    """Mindlogic API 키를 반환합니다. secrets → 환경변수 순으로 탐색합니다."""
    try:
        key = st.secrets.get("SM_MINDLOGIC", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.environ.get("SM_MINDLOGIC", "").strip()


def get_mindlogic_client() -> OpenAI | None:
    """Mindlogic OpenAI 호환 클라이언트를 반환합니다. 키가 없으면 None을 반환합니다."""
    key = get_mindlogic_api_key()
    if not key:
        return None
    return OpenAI(api_key=key, base_url=_MINDLOGIC_BASE_URL)


def build_ai_parse_prompt(
    raw_text: str,
    base_date: date,
    roles: list[dict],
    decompose: bool = True,
) -> str:
    """한국어 자연어 todo 파싱 전용 프롬프트를 생성합니다."""
    role_info = ", ".join(
        f"@{r['tag']}({r['name']})" for r in roles if r.get("tag")
    ) or "없음"
    decompose_instruction = (
        "decompose=true: 산출물 단계가 명확하면 2~4개 후보로 분해합니다."
        if decompose
        else (
            "decompose=false: 반드시 JSON array 안에 1개 객체만 반환합니다. "
            "초안/검토/수정/최종안 같은 세부 단계는 title로 분해하지 않습니다. "
            "title은 전체 업무명 하나로 만들고, 세부 단계는 memo에 요약합니다. "
            "예: {{\"title\": \"[AAA보고서] 작성 @kca\", \"start_date\": \"...\", \"due_date\": \"...\", "
            "\"priority\": \"상\", \"memo\": \"초안 작성, 검토 및 수정, 최종안 작성까지 포함한 통합 업무.\"}}"
        )
    )
    return f"""당신은 한국어 자연어 문장에서 할 일 목록을 추출하는 전문가입니다.

기준일: {base_date.isoformat()}
등록된 역할 태그 목록 (참고용): {role_info}
분해 모드: {decompose_instruction}

[분해 사고 절차 - 출력 전에 내부적으로 수행하되, 최종 출력에는 reasoning을 포함하지 않습니다]
1. 이 업무의 최종 목표가 무엇인가? (무엇이 완료된 상태인가?)
2. 핵심 산출물 또는 완료 조건은 무엇인가?
3. 그 목표에 도달하기 위해 실제로 필요한 중간 단계와 의존관계를 추론한다.
4. 이 업무는 단순 할 일인가, 아니면 복합 프로젝트인가?
   - 단순 할 일이면 억지로 분해하지 않는다. 1개 후보로 충분하다.
   - 복합 프로젝트이고 기간이 2주 이상이면 보통 3~5개 후보가 적절하다.
   - 후보 수를 채우기 위해 추상적인 title을 만들지 않는다. 3개가 모두 추상적이면 4~5개의 구체 단계로 다시 나눈다.
5. 분해 축을 1~2개 선택해 title을 만든다 (모든 축을 다 쓰지 않는다):
   - 이해관계자 흐름: 모집·접수·안내·참여자 관리·외부 협력자 조율
   - 운영 흐름: 기획·준비·실행·현장 운영·후속 처리
   - 산출물 흐름: 자료 수집·초안·검토·최종본·제출 (문서 산출물일 때만)
   - 의사결정 흐름: 후보 조사·비교·결정·구매/예약·확인
   - 평가/심사 흐름: 기준 수립·평가자 섭외·평가표 준비·결과 정리
   - 커뮤니케이션 흐름: 공지·홍보·안내·리마인드·결과 공유
   - 자원 흐름: 장소·인력·예산·물품 (해당 업무에서 자원이 핵심일 때만)
6. 사용자가 명시한 날짜·우선순위·@태그를 각 후보에 반영한다.
7. 출력 전 title 품질 자기검토 (최종 출력에는 포함하지 않는다):
   - 이 title을 보고 바로 다음 행동을 할 수 있는가?
   - "무엇을" 처리하는지 명확한가? (구체 대상이 title에 드러나는가?)
   - "준비", "점검", "정리", "관리", "운영" 같은 단어가 있다면 앞에 구체 대상이 있는가?
   - "운영 요소", "진행안", "관련 사항", "필요 내용"처럼 범위가 모호한 표현이 있으면 더 구체적인 실행 단위로 바꾼다.
   - title에 서로 다른 대상이 3개 이상 묶여 있지는 않은가? ("자료·장비·장소" 같은 형태)
   - 후보끼리 역할이 겹치면 합치거나 다른 단계로 교체한다.
   - 너무 넓은 title은 2개로 나누는 것이 더 나은가?
   - 너무 좁은 title은 인접 title과 묶어도 자연스러운가?
   - 해당 업무를 실제로 수행하는 사람이 봤을 때 바로 행동할 수 있는 title인지 최종 확인한다.

[분해 품질 기준 - 반드시 준수]
- 각 title은 독립적으로 실행 가능한 할 일이어야 합니다.
- 후보 간 title이 단어만 조금 다른 반복이면 실패입니다.
- 일반 템플릿을 그대로 붙인 느낌이면 실패입니다.
- 해당 업무를 실제로 아는 사람이 봤을 때 자연스러운 단계여야 합니다.
- 새로운 업무 유형이 나오면 기존 예시를 복사하지 말고, 그 업무를 완수하기 위해 실제로 필요한 단계들을 생성합니다.

[실행 가능한 title 기준]
각 title은 다음 세 요소 중 최소 2개 이상을 포함해야 합니다:
1. 구체 대상: 강사, 참석자, 참가팀, 심사위원, 심사표, 안내문, 신청폼, 강의자료, 장비, 숙소, 항공, 방문지, 원고, 목차, 체크리스트 등
2. 실행 행위: 섭외, 확정, 작성, 수합, 발송, 예약, 확인, 점검, 접수, 안내, 검토, 정리 등
3. 결과물 또는 완료 상태: 명단, 체크리스트, 안내문, 신청폼, 심사표, 운영 시나리오, 최종본, 예약 확인, 발송 완료 등

나쁜 title 특징 (이런 결과가 나오면 자기검토를 다시 수행한다):
- "준비/정리/점검/관리/운영"만 있고 구체 대상이 약함
- 서로 다른 성격의 대상 3개 이상을 한 title에 묶음 → "자료·장비·장소 준비"
- "사후 정리"처럼 무엇을 정리하는지 불명확
- "운영 요소 점검", "관련 사항 정리", "진행안 최종 정리"처럼 모호한 표현
- title을 보고 바로 어떤 행동을 해야 할지 떠오르지 않음

더 나은 title 예:
- "교내 창업경진대회 심사위원 섭외 및 심사표 작성" (구체 대상 + 실행 행위)
- "교내 창업경진대회 본선 당일 운영 시나리오 작성" (결과물 명시)
- "학과 AI 특강 참석자 신청 명단 정리" (구체 대상 + 결과물)
- "학과 AI 특강 강의자료 수합 및 장비 점검" (자연스럽게 묶이는 2가지)

[compound title 제한]
- 하나의 title에는 핵심 실행 초점이 하나여야 합니다.
- "A·B·C 준비"처럼 서로 다른 대상 3개 이상을 한꺼번에 묶지 않습니다.
- 서로 다른 담당·행동·시점이 필요한 항목은 별도 todo로 나눕니다.
- 허용: "강의자료 수합 및 장비 점검", "홍보문 작성 및 발송", "방문지·식당 리스트 정리"
- 금지: "자료·장비·장소 준비", "모집·심사·운영 준비", "참가자·심사위원·준비물 관리"
- 후보 수를 줄이기 위해 title을 추상적으로 만들지 않습니다. title이 너무 넓어지면 4~6개까지 허용합니다.

[실행 행위 동사 선택]
title 끝부분은 실제 행동을 나타내는 표현으로 마무리합니다.
권장: 작성, 확정, 섭외, 수합, 발송, 접수, 안내, 예약 확인, 명단 정리, 체크리스트 작성, 운영 시나리오 작성, 결과 정리, 후속 안내
주의: 준비, 정리, 점검, 관리, 운영 — 이 단어 자체는 허용하지만 반드시 구체 대상이 앞에 있어야 합니다.
  나쁨: "특강 준비", "사후 정리", "운영 점검"
  좋음: "특강 강의장 장비 점검", "특강 참석자 명단 정리", "특강 만족도 조사 결과 정리"

[단계명 선택 기준]
- "초안 / 검토 및 수정 / 최종안" 구조는 문서·보고서·강의안·제안서처럼 문서 산출물이 목표인 경우에만 사용합니다.
- 문서 산출물이 목표가 아닌 업무(여행, 행사, 경진대회, 특강 운영 등)에는 그 업무를 실제로 진행하는 단계명을 사용합니다.
- "계획 초안", "계획 검토", "계획 최종안"처럼 계획 자체를 문서로 취급하지 않습니다.
- 단순 동작("시작", "검토", "제출")만으로 title을 만들지 않습니다. 업무 대상을 포함한 구체적 단계명을 사용합니다.

[title 작성 규칙]
- 각 후보 title은 서로 구분되는 실행 단계명을 포함합니다.
- 단계 차이를 memo에만 숨기지 말고 title에 드러냅니다.
- 원문에 @태그가 있으면 등록 여부와 관계없이 모든 후보 title 맨 마지막에 유지합니다.
- @태그는 title의 맨 마지막에만 둡니다. 앞에 두지 않습니다.
- 새 @태그를 임의로 만들지 않습니다. 원문에 없는 @태그는 추가하지 않습니다.
- 원문에 [프로젝트명] 형태가 있으면 모든 후보 title에서 그대로 유지합니다.

[날짜 배분 규칙]
여러 단계로 분해할 때 각 후보의 날짜는 반드시 순차적으로 다르게 배분합니다.
모든 후보에 동일한 start_date/due_date를 넣는 것은 잘못된 출력입니다.

적용 우선순위:
1. 사용자가 특정 단계의 날짜를 명시한 경우 → 그 날짜를 그대로 사용합니다.
2. 사용자가 소요 기간을 명시한 경우 → 그 기간을 반영합니다.
3. 전체 시작일·마감일만 있는 경우 → 전체 기간을 단계 수에 맞게 비례 배분합니다.
   - 각 단계는 최소 1일 이상, 이전 단계 due_date 다음 날을 다음 단계 start_date로 씁니다.
4. 마감일만 있는 경우 → 기준일({base_date.isoformat()})을 시작일로 사용합니다.
5. 기간이 너무 짧으면 후보 수를 줄입니다.

날짜 조건:
- start_date <= due_date (각 후보)
- 후보 간 날짜가 순차적으로 이어집니다 (겹치지 않음)
- 마지막 후보의 due_date = 전체 최종 마감일
- 모든 날짜는 YYYY-MM-DD 형식

[명시 행동 보존 원칙]
- 사용자가 "A하고 B해야 한다", "A 후 B", "A 정리하고 B 제출"처럼 여러 행동을 명시하면, 핵심 행동들이 title에 반영되어야 합니다.
- 단순히 마지막 행동만 남기지 않습니다.
- 자연스럽게 묶을 수 있으면 하나의 title에 묶어도 됩니다.
예:
  나쁨: "법인카드 사용 내역 정리" + "법인카드 증빙 제출"
  좋음: "법인카드 사용 내역 확인 및 정리" + "법인카드 증빙자료 수합 및 제출"

[최종 행위 보강 원칙]
- 제출, 발송, 신청, 보고, 업로드, 등록 같은 최종 행위가 나오면, 그 전에 필요한 자료 수합·확인·작성·정리 단계를 title에 반영합니다.
- 최종 행위만 단독 title로 만들면 실행 가능성이 낮습니다.
- 단순 업무라면 "수합 및 제출"처럼 하나로 묶어도 됩니다.
예: 증빙 제출 → 증빙자료 수합 및 제출 / 안내 발송 → 안내문 작성 및 발송 / 명단 제출 → 명단 확인 및 제출

[과분해 방지]
- 간단한 행정 업무는 보통 2~3개 후보면 충분합니다.
- 사용자가 명시한 행동이 2개뿐인데 억지로 5개 이상 만들지 않습니다.
- 사용자가 여러 단계를 명시한 경우에만 그에 맞게 나눕니다.

[기타 규칙]
- 상대 날짜("다음주 월요일", "이달 말")는 기준일({base_date.isoformat()}) 기준 YYYY-MM-DD로 변환합니다.
- 날짜가 불명확하면 기준일을 사용합니다.
- 우선순위: "매우 중요"/"급함" → "상", 단서 없으면 "중", 낮으면 "하".
- role_tag, role_name 필드는 출력하지 않습니다.
- memo에는 사용자가 실제 업무 수행에 참고할 내용만 적습니다. 날짜 해석 근거·파싱 방식·AI 설명·"추정" 같은 문구는 쓰지 않습니다. 참고사항이 없으면 memo는 ""로 둡니다.
- "작성 시작", "작업 시작"만 있는 항목은 별도 할 일로 만들지 않습니다.

[출력 예시 1 - 여행 계획]
입력: "이번달 말 제주도 가족여행 계획짜기 @family"
기준일 2026-05-13, 마감 2026-05-31:
[
  {{"title": "제주도 가족여행 일정 후보 정리 @family", "start_date": "2026-05-13", "due_date": "2026-05-17", "priority": "중", "memo": ""}},
  {{"title": "제주도 가족여행 교통·숙소 확인 @family", "start_date": "2026-05-18", "due_date": "2026-05-22", "priority": "중", "memo": ""}},
  {{"title": "제주도 가족여행 방문지·식당 리스트 정리 @family", "start_date": "2026-05-23", "due_date": "2026-05-27", "priority": "중", "memo": ""}},
  {{"title": "제주도 가족여행 준비물 및 예약 최종 확인 @family", "start_date": "2026-05-28", "due_date": "2026-05-31", "priority": "중", "memo": ""}}
]
(나쁜 예: "계획 초안 / 계획 검토 및 수정 / 계획 최종안" — 계획은 문서 산출물이 아님)

[출력 예시 2 - 문서 산출물]
입력: "AAA 보고서를 5월 15일까지. 초안 만들고 검토 후 최종본. @kca"
[
  {{"title": "AAA 보고서 초안 @kca", "start_date": "2026-05-01", "due_date": "2026-05-08", "priority": "중", "memo": ""}},
  {{"title": "AAA 보고서 검토 및 수정 @kca", "start_date": "2026-05-09", "due_date": "2026-05-12", "priority": "중", "memo": ""}},
  {{"title": "AAA 보고서 최종본 @kca", "start_date": "2026-05-13", "due_date": "2026-05-15", "priority": "중", "memo": ""}}
]

[출력 예시 3 - 강의안 (문서 산출물 포함)]
입력: "이번주까지 질문의기술 B2B과정 강의안 작성완료. 상. @how로 분류"
decompose=true:
[
  {{"title": "질문의기술 B2B과정 강의 목차 구성 @how", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "질문의기술 B2B과정 강의자료 작성 @how", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "질문의기술 B2B과정 최종 점검 @how", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}}
]
decompose=false:
[
  {{"title": "질문의기술 B2B과정 강의안 작성 @how", "start_date": "...", "due_date": "...", "priority": "상", "memo": "강의 목차 구성, 강의자료 작성, 최종 점검 포함."}}
]

[출력 예시 4 - 특강 운영 준비 (실행 가능한 title)]
입력: "다음달 학과 AI 특강 운영 준비. 중요도 상. @sw"
좋은 출력 (구체 대상 + 실행 행위 포함):
[
  {{"title": "학과 AI 특강 강사 일정 확정 @sw", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "학과 AI 특강 홍보문 작성 및 발송 @sw", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "학과 AI 특강 참석자 신청 명단 정리 @sw", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "학과 AI 특강 강의자료 수합 및 장비 점검 @sw", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}},
  {{"title": "학과 AI 특강 당일 운영 체크리스트 작성 @sw", "start_date": "...", "due_date": "...", "priority": "상", "memo": ""}}
]
나쁜 출력 (추상적·과도하게 묶임 — 절대 금지):
[
  {{"title": "학과 AI 특강 자료·장비·장소 준비 @sw", ...}},
  {{"title": "학과 AI 특강 당일 운영 및 사후 정리 @sw", ...}},
  {{"title": "학과 AI 특강 운영 요소 점검 @sw", ...}}
]

[출력 예시 5 - 행사/경진대회 운영 준비 (구체 실행 단위)]
입력: "1달 뒤 진행할 교내 창업경진대회 진행 준비를 해야해. @sw 중요도 상."
기준일 2026-05-13, 마감 약 2026-06-13:
올바른 출력 (이해관계자 흐름 + 평가/심사 흐름 선택):
[
  {{"title": "교내 창업경진대회 모집 공고 및 접수 양식 준비 @sw", "start_date": "2026-05-13", "due_date": "2026-05-20", "priority": "상", "memo": ""}},
  {{"title": "교내 창업경진대회 심사위원 섭외 및 심사표 작성 @sw", "start_date": "2026-05-21", "due_date": "2026-05-28", "priority": "상", "memo": ""}},
  {{"title": "교내 창업경진대회 참가팀 접수 확인 및 안내 @sw", "start_date": "2026-05-29", "due_date": "2026-06-05", "priority": "상", "memo": ""}},
  {{"title": "교내 창업경진대회 본선 당일 운영 시나리오 작성 @sw", "start_date": "2026-06-06", "due_date": "2026-06-10", "priority": "상", "memo": ""}},
  {{"title": "교내 창업경진대회 결과 발표 및 수상자 후속 안내 @sw", "start_date": "2026-06-11", "due_date": "2026-06-13", "priority": "상", "memo": ""}}
]
나쁜 출력 (추상적 — 절대 금지):
[
  {{"title": "교내 창업경진대회 진행 준비 일정 확정 @sw", ...}},
  {{"title": "교내 창업경진대회 운영 요소 점검 @sw", ...}},
  {{"title": "교내 창업경진대회 진행안 최종 정리 @sw", ...}}
]

[출력 예시 5 - 사용자 명시 날짜 우선]
입력: "[AAA보고서] 다음주 월요일 시작해서 다음주 토요일까지 초안, 그다음주 토요일까지 최종안. @kca 중요해"
[
  {{"title": "[AAA보고서] 초안 @kca", "start_date": "<다음주 월요일>", "due_date": "<다음주 토요일>", "priority": "상", "memo": ""}},
  {{"title": "[AAA보고서] 최종안 @kca", "start_date": "<다음주 일요일>", "due_date": "<그다음주 토요일>", "priority": "상", "memo": ""}}
]

[출력 형식]
반드시 JSON array만 출력합니다. 설명·markdown·code fence를 포함하지 않습니다.
[
  {{
    "title": "string",
    "start_date": "YYYY-MM-DD",
    "due_date": "YYYY-MM-DD",
    "priority": "상|중|하",
    "memo": "string"
  }}
]

[입력 문장]
{raw_text}"""


def extract_json_array_from_text(text: str) -> list[dict]:
    """모델 응답 텍스트에서 JSON array를 안정적으로 파싱합니다."""
    text = text.strip()
    try:
        result = json.loads(text)
        if not isinstance(result, list):
            raise ValueError("응답이 JSON array가 아닙니다.")
        return result
    except json.JSONDecodeError:
        pass
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("응답에서 JSON array를 찾을 수 없습니다.")
    try:
        result = json.loads(text[start:end + 1])
        if not isinstance(result, list):
            raise ValueError("응답이 JSON array가 아닙니다.")
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파싱 실패: {e}") from e


def normalize_ai_todo_candidates(
    items: list[dict], base_date: date, raw_text: str = ""
) -> tuple[list[dict], list[str]]:
    """AI 결과를 앱 내부 후보 형식으로 보정합니다.
    반환: (유효한 candidates list, warnings list)
    """
    candidates: list[dict] = []
    warnings: list[str] = []
    valid_priorities = {"상", "중", "하"}

    for i, item in enumerate(items):
        label = f"후보 {i + 1}"
        title = str(item.get("title", "")).strip()
        if not title:
            warnings.append(f"{label}: 제목이 비어 있어 제외됩니다.")
            continue

        priority = str(item.get("priority", "중")).strip()
        if priority not in valid_priorities:
            warnings.append(f"{label} '{title}': 우선순위 '{priority}'를 '중'으로 보정합니다.")
            priority = "중"

        start_str = str(item.get("start_date", "") or "")
        due_str = str(item.get("due_date", "") or "")
        start = _parse_date(start_str)
        due = _parse_date(due_str)

        if start is None:
            warnings.append(f"{label} '{title}': 시작일 '{start_str}'이 올바르지 않아 기준일로 보정합니다.")
            start = base_date
            start_str = base_date.isoformat()
        if due is None:
            warnings.append(f"{label} '{title}': 마감일 '{due_str}'이 올바르지 않아 기준일로 보정합니다.")
            due = base_date
            due_str = base_date.isoformat()
        if due < start:
            warnings.append(f"{label} '{title}': 마감일이 시작일보다 이르므로 시작일로 맞춥니다.")
            due = start
            due_str = start_str

        memo = sanitize_ai_memo(item.get("memo", ""))

        candidates.append({
            "title": title,
            "start_date": start_str,
            "due_date": due_str,
            "priority": priority,
            "memo": memo,
        })

    # 여러 후보가 모두 동일한 날짜이면 경고
    if len(candidates) > 1:
        dates_set = {(c["start_date"], c["due_date"]) for c in candidates}
        if len(dates_set) == 1:
            warnings.append(
                "⚠️ 모든 후보의 시작일·마감일이 동일합니다. "
                "단계별 날짜가 제대로 배분되지 않았을 수 있습니다. "
                "후보를 직접 확인하고 필요하면 날짜를 수정해 주세요."
            )

    # 여행/행사형 업무가 문서형 패턴(초안/검토/최종안)으로 분해된 경우 경고
    _TRAVEL_EVENT_KW = {"여행", "가족여행", "출장", "여행계획", "모임", "행사", "파티", "회식", "세미나", "발표회"}
    _DOC_STAGE_KW = {"초안", "검토 및 수정", "최종안", "최종본"}
    _raw_has_travel = any(kw in raw_text for kw in _TRAVEL_EVENT_KW)
    _titles = [c.get("title", "") for c in candidates]
    _doc_stage_count = sum(
        1 for t in _titles if any(kw in t for kw in _DOC_STAGE_KW)
    )
    if _raw_has_travel and len(candidates) > 1 and _doc_stage_count >= 2:
        warnings.append(
            "⚠️ 여행/행사형 업무가 문서형 단계(초안/검토/최종안)로 분해된 것으로 보입니다. "
            "후보 제목을 확인해 주세요."
        )

    return candidates, warnings


def parse_todos_with_ai(
    raw_text: str,
    base_date: date,
    roles: list[dict],
    decompose: bool = True,
) -> tuple[list[dict], list[str], str]:
    """Mindlogic API를 호출해 자연어를 todo 후보로 파싱합니다.
    반환: (candidates, warnings, raw_response_text)
    """
    client = get_mindlogic_client()
    if client is None:
        raise RuntimeError("API 키가 설정되어 있지 않습니다. SM_MINDLOGIC 키를 확인해 주세요.")

    prompt = build_ai_parse_prompt(raw_text, base_date, roles, decompose=decompose)
    response = client.chat.completions.create(
        model=_MINDLOGIC_MODEL,
        messages=[
            {"role": "system", "content": "당신은 할 일 파싱 전문가입니다. JSON array만 출력합니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    raw_text_response = response.choices[0].message.content or ""
    items = extract_json_array_from_text(raw_text_response)
    candidates, warnings = normalize_ai_todo_candidates(items, base_date, raw_text=raw_text)
    if not decompose and len(candidates) > 1:
        single = collapse_candidates_to_single(raw_text, candidates, base_date)
        candidates = [single]
        warnings.append("분해 옵션이 꺼져 있어 여러 후보를 하나의 할 일로 합쳤습니다.")
    return candidates, warnings, raw_text_response


def format_date_kr_short(d) -> str:
    """date 또는 YYYY-MM-DD 문자열을 'M/D(요일)' 형식으로 반환합니다.
    변환 실패 시 원문 문자열을 반환합니다.
    """
    _KR_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
    if isinstance(d, str):
        original = d
        d = _parse_date(d)
        if d is None:
            return original
    try:
        return f"{d.month}/{d.day}({_KR_WEEKDAY[d.weekday()]})"
    except Exception:
        return str(d)


_STAGE_WORDS = re.compile(
    r"(초안|검토\s*및\s*수정|검토|수정|최종안|최종본|수정본|완성본|완성|작성)\s*$",
    re.UNICODE,
)
_AT_TAG_RE = re.compile(r"@\w+")
_BRACKET_RE = re.compile(r"^\[([^\]]+)\]")


def collapse_candidates_to_single(
    raw_text: str,
    candidates: list[dict],
    base_date: date,
) -> dict:
    """여러 candidates를 하나의 단일 candidate로 합칩니다. decompose=False 시 사용합니다."""
    priority_order = {"상": 0, "중": 1, "하": 2}

    # start_date: 가장 이른 날짜
    start_dates = [_parse_date(c["start_date"]) for c in candidates if _parse_date(c["start_date"])]
    best_start = min(start_dates) if start_dates else base_date

    # due_date: 가장 늦은 날짜
    due_dates = [_parse_date(c["due_date"]) for c in candidates if _parse_date(c["due_date"])]
    best_due = max(due_dates) if due_dates else best_start

    # priority: 가장 높은 우선순위
    priorities = [c.get("priority", "중") for c in candidates]
    best_priority = min(priorities, key=lambda p: priority_order.get(p, 1))

    # @태그: 후보 title들 또는 raw_text에서 추출 (중복 제거, 첫 번째 사용)
    all_tags: list[str] = []
    for c in candidates:
        all_tags.extend(_AT_TAG_RE.findall(c.get("title", "")))
    if not all_tags:
        all_tags.extend(_AT_TAG_RE.findall(raw_text))
    tag_suffix = f" {all_tags[0]}" if all_tags else ""

    # [프로젝트명] 추출
    bracket_match = _BRACKET_RE.match(raw_text.strip())
    bracket_prefix = f"[{bracket_match.group(1)}] " if bracket_match else ""

    # title 생성
    if bracket_prefix:
        base_title = f"{bracket_prefix}작성{tag_suffix}"
    else:
        # 후보 title에서 @태그와 단계어 제거 후 공통 prefix 추출
        cleaned = []
        for c in candidates:
            t = c.get("title", "")
            t = _AT_TAG_RE.sub("", t).strip()
            t = _STAGE_WORDS.sub("", t).strip()
            if t:
                cleaned.append(t)
        if cleaned:
            # 공통 prefix: 첫 번째 cleaned를 기준으로 모든 것과 공통인 부분
            common = cleaned[0]
            for other in cleaned[1:]:
                # 단어 단위로 공통 prefix 찾기
                words_a = common.split()
                words_b = other.split()
                common_words = []
                for wa, wb in zip(words_a, words_b):
                    if wa == wb:
                        common_words.append(wa)
                    else:
                        break
                common = " ".join(common_words)
            common = common.strip()
            if common:
                base_title = f"{common} 작성{tag_suffix}"
            else:
                # 첫 후보 기반
                first_clean = cleaned[0] if cleaned else "할 일"
                base_title = f"{first_clean} 작성{tag_suffix}" if first_clean else f"할 일 정리{tag_suffix}"
        else:
            base_title = f"할 일 정리{tag_suffix}"

    # memo: 세부 단계 요약
    stage_parts = []
    for c in candidates:
        t = c.get("title", "")
        t_clean = _AT_TAG_RE.sub("", t).strip()
        s = format_date_kr_short(c.get("start_date", ""))
        d = format_date_kr_short(c.get("due_date", ""))
        stage_parts.append(f"{t_clean}({s}~{d})")
    memo_text = "세부 단계: " + ", ".join(stage_parts) if stage_parts else ""

    return {
        "title": base_title,
        "start_date": best_start.isoformat(),
        "due_date": best_due.isoformat(),
        "priority": best_priority,
        "memo": memo_text,
    }


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

@st.dialog("📋 할 일 상세")
def _show_todo_detail_dialog(todo: dict, selected_date: date) -> None:
    """할 일 상세 팝업 (조회 전용)."""
    status = compute_status(todo, selected_date)
    done_str = "✅ 완료" if todo.get("done") else "⬜ 미완료"
    st.markdown(f"### {escape_html(todo.get('title', ''))}", unsafe_allow_html=False)
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**분류** {todo.get('role_name', '미분류')}")
        st.markdown(f"**시작일** {format_date_kr_short(todo.get('start_date', '-'))}")
        st.markdown(f"**마감일** {format_date_kr_short(todo.get('due_date', '-'))}")
    with col_b:
        st.markdown(f"**우선순위** {todo.get('priority', '-')}")
        st.markdown(f"**상태** {status}")
        st.markdown(f"**완료** {done_str}")
    memo = str(todo.get("memo", "") or "")
    if memo.strip():
        st.divider()
        st.markdown("**메모**")
        st.markdown(memo)


def _open_detail(todo: dict, selected_date: date, key: str) -> None:
    """상세 팝업 열기 버튼 helper (st.dialog 트리거)."""
    if st.button("🔍", key=key, help="상세 보기"):
        _show_todo_detail_dialog(todo, selected_date)


def _ai_save_payloads(
    payloads: list[dict],
    roles: list[dict],
    selected_date: date,
) -> None:
    """AI 후보 payload 목록을 add_todo()로 저장하고 session_state를 정리합니다."""
    import streamlit as _st
    saved_count = 0
    for p in payloads:
        s = _parse_date(p["start_date"]) or selected_date
        d = _parse_date(p["due_date"]) or selected_date
        add_todo(
            title=p["title"],
            start_date=s.isoformat(),
            due_date=d.isoformat(),
            priority=p["priority"],
            roles=roles,
            memo=p.get("memo", ""),
        )
        saved_count += 1
    _st.session_state.pop("_ai_pending_todos", None)
    _st.session_state.pop("_ai_last_raw_response", None)
    _st.session_state.pop("_ai_parse_warnings", None)
    _st.session_state.pop("_ai_pending_apply_todos", None)
    _st.session_state.pop("_ai_pending_unregistered_tags", None)
    if saved_count:
        _st.success(f"{saved_count}개 저장되었습니다.")
    _st.rerun()


def render_ai_parse_section(selected_date: date, roles: list[dict]) -> None:
    """AI 자연어 입력 섹션을 렌더링합니다."""
    with st.expander("🤖 AI 자연어 입력", expanded=True):
        if not get_mindlogic_api_key():
            st.warning("SM_MINDLOGIC API 키가 설정되지 않았습니다.")

        raw_input = st.text_area(
            "자연어로 할 일 입력",
            key="ai_parse_input",
            height=110,
            placeholder="예: 이번주까지 질문의기술 B2B과정 강의안 작성 완료. 상. @how로 분류",
            label_visibility="collapsed",
        )

        decompose = st.checkbox(
            "여러 할 일로 분해",
            value=True,
            key="ai_decompose",
            help="체크 시 산출물 단계별로 분해, 해제 시 하나의 할 일로 정리",
        )

        if st.button("AI로 정리", key="ai_parse_btn"):
            if not raw_input.strip():
                st.warning("입력 내용을 작성해 주세요.")
            elif not get_mindlogic_api_key():
                st.warning("API 키가 없어 AI 파싱을 실행할 수 없습니다.")
            else:
                with st.spinner("AI가 할 일 후보를 생성 중입니다..."):
                    try:
                        candidates, parse_warnings, raw_resp = parse_todos_with_ai(
                            raw_input.strip(), selected_date, roles, decompose=decompose
                        )
                        st.session_state["_ai_pending_todos"] = candidates
                        st.session_state["_ai_last_raw_response"] = raw_resp
                        st.session_state["_ai_parse_warnings"] = parse_warnings
                    except RuntimeError as e:
                        st.warning(str(e))
                    except ValueError as e:
                        st.error(f"JSON 파싱 오류: {e}")
                        raw_resp = st.session_state.get("_ai_last_raw_response", "")
                        if raw_resp:
                            with st.expander("AI 원본 응답 확인", expanded=False):
                                st.text(raw_resp[:1000])
                    except Exception as e:
                        st.error(f"AI 호출 중 오류가 발생했습니다: {e}")

        # ── 보정 경고 표시 ─────────────────────────────────────────────
        parse_warnings = st.session_state.get("_ai_parse_warnings", [])
        if parse_warnings:
            for w in parse_warnings:
                st.warning(w)

        # ── 후보 미리보기: st.data_editor 표 ──────────────────────────
        candidates = st.session_state.get("_ai_pending_todos")
        if not candidates:
            return

        st.caption(f"{len(candidates)}개 후보 — 필요한 항목만 선택해 적용하세요.")

        df_rows = []
        for cand in candidates:
            df_rows.append({
                "선택": True,
                "할 일": cand["title"],
                "시작일": format_date_kr_short(cand["start_date"]),
                "마감일": format_date_kr_short(cand["due_date"]),
                "우선순위": cand["priority"],
                "메모": cand.get("memo", ""),
            })

        display_df = pd.DataFrame(df_rows)
        editor_height = min(220, 80 + len(display_df) * 36)
        edited_df = st.data_editor(
            display_df,
            column_config={
                "선택": st.column_config.CheckboxColumn("선택", default=True),
                "할 일": st.column_config.TextColumn("할 일", width="large"),
                "시작일": st.column_config.TextColumn("시작일", disabled=True),
                "마감일": st.column_config.TextColumn("마감일", disabled=True),
                "우선순위": st.column_config.SelectboxColumn(
                    "우선순위", options=["상", "중", "하"]
                ),
                "메모": st.column_config.TextColumn("메모", width="medium"),
            },
            hide_index=True,
            height=editor_height,
            width="stretch",
            key="ai_candidate_editor",
        )

        # ── 미등록 @태그 등록 UI (pending 상태일 때) ──────────────────
        ai_pending_payloads = st.session_state.get("_ai_pending_apply_todos")
        ai_pending_unreg = st.session_state.get("_ai_pending_unregistered_tags")

        if ai_pending_payloads is not None and ai_pending_unreg is not None:
            st.warning("미등록 @태그가 있습니다. 역할명을 입력하면 등록 후 적용됩니다.")
            ai_tag_names: dict[str, str] = {}
            ai_tag_active: dict[str, bool] = {}
            with st.form("ai_pending_tag_form"):
                for utag in ai_pending_unreg:
                    st.markdown(f"`@{utag}`")
                    _nc, _ac = st.columns([0.65, 0.35])
                    ai_tag_names[utag] = _nc.text_input(
                        "역할명",
                        placeholder=f"@{utag} 역할명",
                        key=f"ai_pending_name_{utag}",
                    )
                    ai_tag_active[utag] = _ac.checkbox(
                        "사용함",
                        value=True,
                        key=f"ai_pending_active_{utag}",
                    )
                _b1, _b2, _b3 = st.columns(3)
                do_register_apply = _b1.form_submit_button("등록 후 적용")
                do_skip_apply = _b2.form_submit_button("등록하지 않고 적용")
                do_ai_tag_cancel = _b3.form_submit_button("취소")

            if do_ai_tag_cancel:
                st.session_state.pop("_ai_pending_apply_todos", None)
                st.session_state.pop("_ai_pending_unregistered_tags", None)
                st.rerun()

            if do_register_apply:
                missing = [u for u in ai_pending_unreg if not ai_tag_names.get(u, "").strip()]
                if missing:
                    st.warning(f"역할명을 입력해 주세요: {', '.join(f'@{u}' for u in missing)}")
                else:
                    current_roles = roles
                    for utag in ai_pending_unreg:
                        current_roles = add_role(utag, ai_tag_names[utag].strip(), active=ai_tag_active[utag])
                    _ai_save_payloads(ai_pending_payloads, current_roles, selected_date)

            if do_skip_apply:
                _ai_save_payloads(ai_pending_payloads, roles, selected_date)

            return

        # ── 적용 / 취소 버튼 ──────────────────────────────────────────
        btn_apply, btn_cancel = st.columns([1, 1])

        with btn_apply:
            if st.button("적용", key="ai_save_btn"):
                # 선택된 후보 payload 수집
                apply_payloads = []
                skipped = []
                for idx, row in edited_df.iterrows():
                    if not row["선택"]:
                        continue
                    t = str(row["할 일"]).strip()
                    if not t:
                        skipped.append(f"후보 {idx + 1}: 제목이 비어 있어 건너뜁니다.")
                        continue
                    orig = candidates[idx]
                    s = _parse_date(orig["start_date"]) or selected_date
                    d = _parse_date(orig["due_date"]) or selected_date
                    if d < s:
                        skipped.append(f"'{t}': 마감일이 시작일보다 이릅니다. 건너뜁니다.")
                        continue
                    apply_payloads.append({
                        "title": t,
                        "start_date": s.isoformat(),
                        "due_date": d.isoformat(),
                        "priority": str(row["우선순위"]),
                        "memo": str(row["메모"]),
                    })
                for msg in skipped:
                    st.warning(msg)
                if not apply_payloads:
                    if not skipped:
                        st.warning("선택된 후보가 없습니다.")
                else:
                    # 미등록 @태그 수집
                    unreg_set: set[str] = set()
                    for p in apply_payloads:
                        unreg_set.update(get_unregistered_tags_in_title(p["title"], roles))
                    if unreg_set:
                        st.session_state["_ai_pending_apply_todos"] = apply_payloads
                        st.session_state["_ai_pending_unregistered_tags"] = sorted(unreg_set)
                        st.rerun()
                    else:
                        _ai_save_payloads(apply_payloads, roles, selected_date)

        with btn_cancel:
            if st.button("취소", key="ai_clear_btn"):
                st.session_state.pop("_ai_pending_todos", None)
                st.session_state.pop("_ai_last_raw_response", None)
                st.session_state.pop("_ai_parse_warnings", None)
                st.rerun()


def render_input_form(roles: list[dict], show_header: bool = True) -> None:
    """할 일 직접 입력 폼을 렌더링합니다.

    미등록 @태그 처리:
    - 제목에 미등록 @태그가 발견되면 등록 여부를 묻는 phase 2로 전환합니다.
    - 등록하지 않고 저장하면 해당 todo는 미분류로 저장됩니다.
    """
    if show_header:
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


def render_weekly_plan_view(todos: list[dict], selected_date: date, roles: list[dict]) -> None:
    """주간 보기 섹션을 렌더링합니다. 실행 목록 + 진행률 요약."""
    with st.expander("🗓 주간 보기", expanded=False):
        range_mode = st.radio(
            "주간 보기 범위",
            ["이번 주", "다음 주"],
            horizontal=True,
            key="weekly_view_range_mode",
            label_visibility="collapsed",
        )

        if range_mode == "이번 주":
            week_start, week_end = get_week_range(selected_date)
            st.caption(
                f"이번 주: {format_date_kr_short(week_start)} ~ {format_date_kr_short(week_end)}"
            )
            weekly_total, weekly_active = get_current_week_items(todos, week_start, week_end)
            total_count = len(weekly_total)
            done_count = total_count - len(weekly_active)

            if total_count == 0:
                st.info("이번 주 할 일이 없습니다.")
                return
            if len(weekly_active) == 0:
                st.success("이번 주 할 일을 모두 완료했습니다. 🎉")
                return

            st.markdown(f"**진행률 {done_count}/{total_count}**")
            display_items = weekly_active

        else:
            next_start, next_end = get_next_week_range(selected_date)
            st.caption(
                f"다음 주: {format_date_kr_short(next_start)} ~ {format_date_kr_short(next_end)}"
            )
            display_items = get_next_week_items(todos, next_start, next_end)

            if not display_items:
                st.info("다음 주에 진행 예정인 할 일이 없습니다.")
                return

            st.markdown(f"**다음 주 진행 예정 {len(display_items)}개**")

        for todo in display_items:
            safe_title = escape_html(todo.get("title", ""))
            icon = get_priority_icon(todo.get("priority", ""))
            memo_icon = " 📝" if str(todo.get("memo") or "").strip() else ""
            suffix = f" {icon}" if icon else ""
            due_display = format_date_kr_short(todo.get("due_date", ""))
            due_part = f" · {escape_html(due_display)}" if due_display else ""
            st.markdown(f"- {safe_title}{due_part}{suffix}{memo_icon}", unsafe_allow_html=True)


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
        col1, col2, col3 = st.columns([0.05, 0.88, 0.07])
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
            memo_html = (
                f'<div class="todo-memo">📝 {escape_html(summarize_memo(_today_memo, max_len=40))}</div>'
                if show_today_memo and _today_memo.strip()
                else ""
            )
            st.markdown(
                f'<div class="todo-block">'
                f'<div class="todo-title">{escape_html(icon)}{escape_html(memo_flag)} {escape_html(todo["title"])}</div>'
                f'<div class="todo-meta">[{escape_html(role_label)}] 마감: {escape_html(format_date_kr_short(todo.get("due_date","")))} | 우선순위: {escape_html(todo.get("priority",""))}</div>'
                f'{memo_html}'
                f'</div>',
                unsafe_allow_html=True,
            )
        with col3:
            _open_detail(todo, selected_date, key=f"detail_today_{todo_id}")
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
        show_done = st.checkbox("완료 포함", value=True, key="all_show_done")

        sort_mode = st.radio(
            "정렬",
            ["마감일", "주제"],
            horizontal=True,
            key="all_sort_mode",
            label_visibility="collapsed",
        )

        _PRI_OPTS = [("전체", "전", "전체"), ("상", "상", "우선순위 상"), ("중", "중", "우선순위 중"), ("하", "하", "우선순위 하")]
        if "priority_filter" not in st.session_state:
            st.session_state["priority_filter"] = "전체"
        _pcols = st.columns(4)
        for _pc, (_pval, _plbl, _phelp) in zip(_pcols, _PRI_OPTS):
            _psel = st.session_state["priority_filter"] == _pval
            if _pc.button(
                _plbl,
                key=f"pf_btn_{_pval}",
                help=_phelp,
                type="primary" if _psel else "secondary",
                width="stretch",
            ):
                st.session_state["priority_filter"] = _pval
                st.rerun()
        priority_filter = st.session_state["priority_filter"]

        _STATUS_ROWS = [
            [("전체", "📋"), ("진행 중", "🟢"), ("오늘 마감", "🟠")],
            [("지연", "🔴"), ("예정", "🔵"), ("완료", "✅")],
        ]
        if "status_filter" not in st.session_state:
            st.session_state["status_filter"] = "전체"
        for _row_idx, _row in enumerate(_STATUS_ROWS):
            _scols = st.columns(3)
            for _sc, (_val, _icon) in zip(_scols, _row):
                _selected = st.session_state["status_filter"] == _val
                if _sc.button(
                    _icon,
                    key=f"sf_btn_{_row_idx}_{_val}",
                    help=_val,
                    type="primary" if _selected else "secondary",
                    width="stretch",
                ):
                    st.session_state["status_filter"] = _val
                    st.rerun()
        status_filter = st.session_state["status_filter"]

        st.divider()
        st.caption("분류")

        # 전체 체크 / 전체 해제 버튼
        _vis_keys = (
            [f"vis_role_{r['tag']}" for r in active_roles]
            + (["vis_inactive"] if inactive_role_names else [])
            + ["vis_unclassified"]
        )
        _sel_col, _clr_col = st.columns(2)
        if _sel_col.button("전체", key="role_vis_select_all"):
            for _k in _vis_keys:
                st.session_state[_k] = True
            st.rerun()
        if _clr_col.button("해제", key="role_vis_clear_all"):
            for _k in _vis_keys:
                st.session_state[_k] = False
            st.rerun()

        # 분류별 체크박스: 1열 배치, help 제거, session_state 선설정
        role_vis: dict[str, bool] = {}
        _role_opts: list[dict] = []
        for _r in active_roles:
            _role_opts.append({
                "key": f"vis_role_{_r['tag']}",
                "label": f"@{_r['tag']}",
                "vis_key": _r["name"],
            })
        if inactive_role_names:
            _role_opts.append({
                "key": "vis_inactive",
                "label": "비활성",
                "vis_key": "__inactive__",
            })
        _role_opts.append({
            "key": "vis_unclassified",
            "label": "미분류",
            "vis_key": "미분류",
        })

        for _opt in _role_opts:
            if _opt["key"] not in st.session_state:
                st.session_state[_opt["key"]] = True
            _checked = st.checkbox(
                _opt["label"],
                key=_opt["key"],
            )
            role_vis[_opt["vis_key"]] = _checked

        st.divider()

        # ── 완료 항목 일괄 삭제 ────────────────────────────────────────
        completed_count = count_completed_todos(todos)
        if completed_count == 0:
            st.caption("완료 항목 없음")
        else:
            st.caption(f"완료 {completed_count}개")
            confirm_delete = st.checkbox(
                f"{completed_count}개 삭제 확인",
                value=False,
                key="confirm_bulk_delete",
            )
            if st.button("완료 일괄 삭제", key="bulk_delete_btn"):
                if not confirm_delete:
                    st.warning("위 체크박스를 선택해 주세요.")
                else:
                    deleted = delete_completed_todos()
                    st.success(f"{deleted}개 삭제했습니다.")
                    st.rerun()

    # ── 좌측 패널: todo 목록 ──────────────────────────────────────────
    with left_col:
        # 1) 완료 포함 여부 — status_filter가 "완료"이면 완료 항목만 강제 표시
        if status_filter == "완료":
            filtered = [t for t in todos if t.get("done")]
        else:
            filtered = [t for t in todos if show_done or not t.get("done")]

        # 2) 우선순위 필터
        if priority_filter != "전체":
            filtered = [t for t in filtered if t.get("priority") == priority_filter]

        # 3) 상태 필터 (완료는 위에서 처리)
        if status_filter not in ("전체", "완료"):
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

        def _clean_title_for_sort(title: str) -> str:
            import re as _re
            return _re.sub(r"@\w+", "", title).strip().lower()

        if not filtered:
            st.info("표시할 항목이 없습니다.")
        else:
            if sort_mode == "주제":
                filtered_sorted = sorted(
                    filtered,
                    key=lambda t: (
                        _clean_title_for_sort(t.get("title", "")),
                        t.get("due_date", ""),
                        PRIORITY_ORDER.get(t.get("priority", "하"), 2),
                    ),
                )
            else:  # 마감일
                filtered_sorted = sorted(
                    filtered,
                    key=lambda t: (
                        t.get("due_date", ""),
                        PRIORITY_ORDER.get(t.get("priority", "하"), 2),
                        _clean_title_for_sort(t.get("title", "")),
                    ),
                )

            for todo in filtered_sorted:
                status = compute_status(todo, selected_date)
                icon = STATUS_COLOR.get(status, "")
                todo_id = todo["id"]
                current_done = bool(todo.get("done", False))
                checkbox_key = get_done_checkbox_key("all", todo)
                is_editing = st.session_state.get("editing_todo_id") == todo_id

                c1, c2, action_col = st.columns([0.04, 0.82, 0.14])
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
                    _memo_html = (
                        f'<div class="todo-memo">📝 {escape_html(summarize_memo(_memo, max_len=40))}</div>'
                        if _memo.strip() else ""
                    )
                    st.markdown(
                        f'<div class="todo-block">'
                        f'<div class="todo-title">{escape_html(icon)} {escape_html(todo["title"])}</div>'
                        f'<div class="todo-meta">[{escape_html(role_label)}] 마감: {escape_html(format_date_kr_short(todo.get("due_date","")))} | {escape_html(todo.get("priority",""))} | {escape_html(status)}</div>'
                        f'{_memo_html}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                with action_col:
                    a1, a2, a3 = st.columns(3)
                    with a1:
                        _open_detail(todo, selected_date, key=f"detail_all_{todo_id}")
                    with a2:
                        if st.button("✏️", key=f"edit_btn_{todo_id}", help="수정"):
                            st.session_state["editing_todo_id"] = todo_id
                            st.rerun()
                    with a3:
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
# 백업/내보내기 UI
# ---------------------------------------------------------------------------

def render_backup_export_section(todos: list[dict], roles: list[dict]) -> None:
    """백업/내보내기 expander를 렌더링합니다. 읽기 전용 다운로드만 제공합니다."""
    with st.expander("💾 백업/내보내기", expanded=False):
        st.caption("⚠️ 이 기능은 다운로드 전용입니다. 복원 기능은 지원하지 않습니다.")

        ts = get_timestamp_for_filename()

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**JSON 백업**")

            # todos.json 다운로드
            todos_bytes = read_file_bytes_if_exists(TODOS_FILE)
            if todos_bytes is not None:
                st.download_button(
                    label="📥 todos.json 다운로드",
                    data=todos_bytes,
                    file_name=build_backup_filename("todos_backup", "json", ts),
                    mime="application/json",
                    key="dl_todos_json",
                )
            else:
                st.info("todos.json 파일이 없습니다.")

            # roles.json 다운로드
            roles_bytes = read_file_bytes_if_exists(ROLES_FILE)
            if roles_bytes is not None:
                st.download_button(
                    label="📥 roles.json 다운로드",
                    data=roles_bytes,
                    file_name=build_backup_filename("roles_backup", "json", ts),
                    mime="application/json",
                    key="dl_roles_json",
                )
            else:
                st.info("roles.json 파일이 없습니다.")

            # 통합 JSON 백업
            st.download_button(
                label="📥 통합 백업 (bundle.json) 다운로드",
                data=build_combined_backup_json_bytes(todos, roles),
                file_name=build_backup_filename("todo_app_backup", "json", ts),
                mime="application/json",
                key="dl_combined_json",
            )

        with col2:
            st.markdown("**데이터 내보내기**")

            # CSV 내보내기
            st.download_button(
                label="📥 CSV 내보내기",
                data=todos_to_csv_bytes(todos),
                file_name=build_backup_filename("todo_export", "csv", ts),
                mime="text/csv",
                key="dl_csv",
            )

            # Markdown 내보내기
            st.download_button(
                label="📥 Markdown 내보내기",
                data=todos_to_markdown_bytes(todos),
                file_name=build_backup_filename("todo_export", "md", ts),
                mime="text/markdown",
                key="dl_md",
            )


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(page_title="개인용 AI 할 일 관리 앱", layout="wide")
    st.title("🧠 개인용 AI 할 일 관리 앱")
    inject_compact_todo_css()

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
        render_ai_parse_section(selected_date, roles)
        with st.expander("✏️ 직접 입력", expanded=False):
            render_input_form(roles, show_header=False)

    st.divider()

    # 주간 보기
    render_weekly_plan_view(todos, selected_date, roles)

    st.divider()

    # 하단: 전체 보기
    render_all_view(todos, selected_date, roles)

    st.divider()

    # 역할/분류 관리
    render_role_manager(roles)

    # 백업/내보내기
    render_backup_export_section(todos, roles)


if __name__ == "__main__":
    main()
