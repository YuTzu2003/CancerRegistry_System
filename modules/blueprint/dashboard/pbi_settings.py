"""Persistent, administrator-managed settings for Power BI publication."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SETTINGS_PATH = PROJECT_ROOT / "tasks" / "data" / "config" / "powerbi_publish.json"


def get_pbi_publish_settings():
    """Return the one configured Power BI publication target, if any."""
    if not SETTINGS_PATH.is_file():
        return {}
    try:
        with SETTINGS_PATH.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_pbi_publish_path():
    return str(get_pbi_publish_settings().get("publish_path") or "").strip()


def _verify_destination(path):
    """Verify the Flask account can create and replace files in this folder."""
    destination = Path(path)
    if destination.suffix.lower() != ".xlsx":
        raise ValueError("Power BI 發布檔案必須是 .xlsx 格式")
    parent = destination.parent
    try:
        os.stat(parent)
    except FileNotFoundError as exc:
        raise ValueError("找不到 Power BI 發布資料夾，請確認 UNC 路徑") from exc
    except PermissionError as exc:
        raise ValueError("沒有存取 Power BI 發布資料夾的權限") from exc
    except OSError as exc:
        raise ValueError(f"無法存取 Power BI 發布資料夾：{exc}") from exc
    if not os.path.isdir(parent):
        raise ValueError("Power BI 發布位置必須是資料夾內的 .xlsx 檔案")

    first = second = None
    try:
        first = tempfile.NamedTemporaryFile(
            mode="wb", prefix=".pbi_permission_", suffix=".tmp", dir=parent, delete=False
        )
        first.close()
        second = tempfile.NamedTemporaryFile(
            mode="wb", prefix=".pbi_permission_", suffix=".tmp", dir=parent, delete=False
        )
        second.close()
        os.replace(first.name, second.name)
        first = None
    except OSError as exc:
        raise ValueError(f"無法寫入此資料夾：{exc}") from exc
    finally:
        for temporary in (first, second):
            if temporary:
                try:
                    os.unlink(temporary.name)
                except OSError:
                    pass
        if second and os.path.exists(second.name):
            try:
                os.unlink(second.name)
            except OSError:
                pass


def save_pbi_publish_path(path, updated_by):
    path = str(path or "").strip()
    if not path:
        raise ValueError("請輸入 Power BI 發布檔案路徑")

    _verify_destination(path)
    settings = {
        "publish_path": path,
        "updated_by": str(updated_by or ""),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = SETTINGS_PATH.with_name(f".{SETTINGS_PATH.name}.tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(settings, handle, ensure_ascii=False, indent=2)
    os.replace(temporary, SETTINGS_PATH)
    return settings
