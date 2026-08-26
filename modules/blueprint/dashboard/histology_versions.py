import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

VERSION_DIR = Path(__file__).resolve().parents[3] / "tasks" / "histcode_version"

def _safe_user_id(user_id):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id))

def _staging_path(user_id):
    return VERSION_DIR / f"staging_{_safe_user_id(user_id)}.jsonl"

def _commit_path(commit_id):
    return VERSION_DIR / f"{commit_id}.jsonl"

def _read_jsonl(path):
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as source:
        return [json.loads(line) for line in source if line.strip()]

def append_staging_change(user_id, base_commit_id, histcode_id, action, before, after):
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "base_commit_id": str(base_commit_id) if base_commit_id else None,
        "histcode_id": histcode_id,
        "action": action,
        "before": before or {},
        "after": after or {},
    }
    with _staging_path(user_id).open("a", encoding="utf-8", newline="\n") as target:
        target.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def record_staging_change(cursor, user_id, histcode_id, action, before=None, after=None):
    changes = staging_changes(user_id)
    base_commit_id = changes[0]["base_commit_id"] if changes else latest_commit_id(cursor)
    append_staging_change(user_id, base_commit_id, histcode_id, action, before, after)


def staging_changes(user_id):
    return _read_jsonl(_staging_path(user_id))


def staging_count(user_id):
    return len(_read_jsonl(_staging_path(user_id)))


def has_any_staging_changes():
    return any(_read_jsonl(path) for path in VERSION_DIR.glob("staging_*.jsonl"))


def latest_commit_id(cursor):
    cursor.execute("SELECT TOP 1 current_commit.CommitId FROM dbo.HistologyCodeCommits AS current_commit WHERE NOT EXISTS (SELECT 1 FROM dbo.HistologyCodeCommits AS child_commit WHERE child_commit.ParentCommitId = current_commit.CommitId) ORDER BY current_commit.CreatedAt DESC")
    row = cursor.fetchone()
    return row[0] if row else None

def ensure_initial_commit(cursor, user_id, user_name):
    cursor.execute("SELECT COUNT(*) FROM dbo.HistologyCodeCommits")
    if cursor.fetchone()[0]:
        return None
    commit_id = uuid4()
    cursor.execute("INSERT INTO dbo.HistologyCodeCommits (CommitId, ParentCommitId, CreatedByUserID, CreatedByName, Action, ChangeCount, RevertUntil) VALUES (?, NULL, ?, ?, 'Commit', 0, DATEADD(DAY, 10, SYSDATETIME()))",str(commit_id), user_id, user_name,)
    return commit_id


def create_empty_commit_file(commit_id):
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    _commit_path(commit_id).touch(exist_ok=False)


def commit_ids_equal(left, right):
    return left is not None and right is not None and UUID(str(left)) == UUID(str(right))


def mapping_values_match(columns, actual, expected):
    return all(("" if actual.get(column) is None else str(actual.get(column)))== ("" if expected.get(column) is None else str(expected.get(column)))
        for column in columns)


def normalize_change(record, columns):
    if "HistCodeId" in record:
        return record
    change = {"HistCodeId": record["histcode_id"], "Action": record["action"]}
    for column in columns:
        change[f"Before{column}"] = record.get("before", {}).get(column)
        change[f"After{column}"] = record.get("after", {}).get(column)
    return change


def save_staging_commit(cursor, user_id, user_name):
    changes = staging_changes(user_id)
    if not changes:
        raise ValueError("目前沒有尚未儲存的變更。")
    base_commit_id = changes[0]["base_commit_id"]
    parent_commit_id = latest_commit_id(cursor)
    if base_commit_id is not None or parent_commit_id is not None:
        if not commit_ids_equal(base_commit_id, parent_commit_id):
            raise ValueError("版本衝突：其他使用者已提交較新的版本。")
    commit_id = uuid4()
    cursor.execute("INSERT INTO dbo.HistologyCodeCommits (CommitId, ParentCommitId, CreatedByUserID, CreatedByName, Action, ChangeCount, RevertUntil) VALUES (?, ?, ?, ?, 'Commit', ?, DATEADD(DAY, 10, SYSDATETIME()))",str(commit_id), parent_commit_id, user_id, user_name, len(changes),)
    return commit_id, changes


def finalize_staging_commit(user_id, commit_id):
    source = _staging_path(user_id)
    target = _commit_path(commit_id)
    if target.exists():
        raise FileExistsError(f"版本檔案已存在：{target.name}")
    os.replace(source, target)


def commit_changes(commit_id):
    return _read_jsonl(_commit_path(commit_id))