import json
import os
import re
from pathlib import Path
from uuid import UUID, uuid4

VERSION_DIR = Path(__file__).resolve().parents[3] / "tasks" / "versions"
VERSION_NAMES = {"histology_code": "histology", "national": "national"}


def version_path(data_type, user_id=None, commit_id=None):
    name = VERSION_NAMES[data_type]
    directory = VERSION_DIR / name
    if commit_id:
        return directory / f"{name}_{commit_id}.jsonl"
    safe_user_id = re.sub(r"[^A-Za-z0-9_.-]", "_", str(user_id))
    return directory / f"{name}_staging_{safe_user_id}.jsonl"


def version_changes(data_type, user_id=None, commit_id=None):
    source = version_path(data_type, user_id, commit_id)
    if not source.exists():
        return []
    with source.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def latest_commit_id(cursor, data_type):
    cursor.execute(
        "SELECT TOP 1 current_commit.CommitId FROM dbo.BranchCommits AS current_commit "
        "WHERE current_commit.DataType = ? AND NOT EXISTS ("
        "SELECT 1 FROM dbo.BranchCommits AS child_commit "
        "WHERE child_commit.DataType = ? AND child_commit.ParentCommitId = current_commit.CommitId) "
        "ORDER BY current_commit.CreatedAt DESC",
        data_type,
        data_type,
    )
    row = cursor.fetchone()
    return row[0] if row else None


def record_change(cursor, data_type, user_id, record_id, action, before=None, after=None, dataset=None):
    staged = version_changes(data_type, user_id)
    source = version_path(data_type, user_id)
    source.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "base_commit_id": staged[0]["base_commit_id"] if staged else str(latest_commit_id(cursor, data_type) or "") or None,
        "record_id": record_id,
        "action": action,
        "before": before or {},
        "after": after or {},
    }
    if dataset:
        record["dataset"] = dataset
    with source.open("a", encoding="utf-8", newline="\n") as file:
        file.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


def ensure_initial_commit(cursor, data_type, user_id, user_name):
    cursor.execute(
        "UPDATE dbo.BranchCommits SET Info = N'建立初始版本' "
        "WHERE DataType = ? AND ParentCommitId IS NULL AND (Info IS NULL OR LTRIM(RTRIM(Info)) = '')",
        data_type,
    )
    cursor.execute("SELECT COUNT(*) FROM dbo.BranchCommits WHERE DataType = ?", data_type)
    if cursor.fetchone()[0]:
        return None
    commit_id = uuid4()
    cursor.execute(
        "INSERT INTO dbo.BranchCommits "
        "(CommitId, ParentCommitId, CreatedByUserID, CreatedByName, Info, DataType, Action, ChangeCount, RevertUntil) "
        "VALUES (?, NULL, ?, ?, N'建立初始版本', ?, 'Commit', 0, DATEADD(DAY, 10, SYSDATETIME()))",
        str(commit_id), user_id, user_name, data_type,
    )
    return commit_id


def save_staging_commit(cursor, data_type, user_id, user_name, info, staged=None):
    info = info.strip()
    if not info:
        raise ValueError("請輸入本次更新內容。")
    if len(info) > 100:
        raise ValueError("本次更新內容不可超過 100 字。")
    staged = staged if staged is not None else version_changes(data_type, user_id)
    if not staged:
        raise ValueError("沒有可儲存的變更。")
    parent_commit_id = latest_commit_id(cursor, data_type)
    if staged[0]["base_commit_id"] or parent_commit_id:
        if not commit_ids_equal(staged[0]["base_commit_id"], parent_commit_id):
            raise ValueError("目前版本已變更，請重新整理後再儲存。")
    commit_id = uuid4()
    cursor.execute(
        "INSERT INTO dbo.BranchCommits "
        "(CommitId, ParentCommitId, CreatedByUserID, CreatedByName, Info, DataType, Action, ChangeCount, RevertUntil) "
        "VALUES (?, ?, ?, ?, ?, ?, 'Commit', ?, DATEADD(DAY, 10, SYSDATETIME()))",
        str(commit_id), parent_commit_id, user_id, user_name, info, data_type, len(staged),
    )
    return commit_id, staged


def finalize_staging_commit(data_type, user_id, commit_id):
    source = version_path(data_type, user_id)
    target = version_path(data_type, commit_id=commit_id)
    if target.exists():
        raise FileExistsError(f"版本檔案已存在：{target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source, target)


def replace_staging_changes(data_type, user_id, changes):
    source = version_path(data_type, user_id)
    with source.open("w", encoding="utf-8", newline="\n") as file:
        for change in changes:
            file.write(json.dumps(change, ensure_ascii=False, default=str) + "\n")


def discard_staging_changes(data_type, user_id):
    source = version_path(data_type, user_id)
    if source.exists():
        source.unlink()


def create_empty_commit_file(data_type, commit_id):
    target = version_path(data_type, commit_id=commit_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch(exist_ok=False)


def has_any_staging_changes(data_type):
    directory = VERSION_DIR / VERSION_NAMES[data_type]
    return any(path.stat().st_size for path in directory.glob(f"{VERSION_NAMES[data_type]}_staging_*.jsonl")) if directory.exists() else False


def commit_ids_equal(left, right):
    return left is not None and right is not None and UUID(str(left)) == UUID(str(right))


def commit_changes(data_type, commit_id):
    return version_changes(data_type, commit_id=commit_id)


def reverse_commits(cursor, data_type, target_id):
    commits = []
    current_id = latest_commit_id(cursor, data_type)
    while current_id and not commit_ids_equal(current_id, target_id):
        cursor.execute(
            "SELECT ParentCommitId FROM dbo.BranchCommits WHERE CommitId = ? AND DataType = ?",
            current_id,
            data_type,
        )
        parent = cursor.fetchone()
        if not parent:
            break
        commits.append(current_id)
        current_id = parent[0]
    return commits if commit_ids_equal(current_id, target_id) else None
