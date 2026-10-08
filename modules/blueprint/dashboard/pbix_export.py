"""Create a filtered PBIX through an installed, interactive Power BI Desktop.

Power BI does not expose a supported headless PBIX refresh/save API. This
local-desktop adapter therefore fails closed unless a Windows console session,
the Desktop executable, and the configured template are available.
"""

import json
import os
import shutil
import subprocess
import time
import zipfile
from collections import Counter
from pathlib import Path

import pandas as pd

from .pbi_export import export_pbi_dataset


TOPIC_PAGES = {
    "性別年齡分佈": "性別年齡分布表&圖",
    "年齡中位數": "年齡中位數表",
    "可分析個案與確診個案": "可分析個案與確診個案\u200b表",
}


def _power_bi_desktop_path():
    """Return an explicitly configured Desktop path or a known local install."""
    configured = os.getenv("PBI_DESKTOP_PATH")
    if configured:
        configured_path = Path(configured)
        if configured_path.is_file():
            return configured_path

    legacy_path = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe")
    if legacy_path.is_file():
        return legacy_path

    # Microsoft Store installs Desktop in an ACL-protected, versioned
    # WindowsApps folder. Ask Windows for the package location instead of
    # enumerating that folder, which regular user processes cannot list.
    try:
        package_location = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-AppxPackage -Name 'Microsoft.MicrosoftPowerBIDesktop' | Select-Object -First 1 -ExpandProperty InstallLocation)",
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        package_location = ""
    store_path = Path(package_location) / "bin" / "PBIDesktop.exe"
    return store_path if store_path.is_file() else legacy_path


class PbixExportError(RuntimeError):
    pass


def _until(action, *, step, timeout=90, interval=0.8):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            result = action()
            if result:
                return result
        except PbixExportError:
            raise
        except Exception as exc:
            last_error = exc
        time.sleep(interval)
    detail = f"（{last_error}）" if last_error else ""
    raise PbixExportError(f"Power BI Desktop 等候「{step}」逾時{detail}。")


def _windows(pid):
    from pywinauto import Desktop

    return [window for window in Desktop(backend="uia").windows() if window.process_id() == pid]


def _report_process_id(title):
    """Find the Desktop process actually hosting a newly opened report.

    The Microsoft Store build can use a small launcher process which exits
    after it hands the file to the real Desktop process, so Popen.pid is not
    always the process that owns the report window.
    """
    from pywinauto import Desktop

    for window in Desktop(backend="uia").windows():
        if title in window.window_text() and any(
            item.element_info.automation_id == "save" for item in window.descendants()
        ):
            return window.process_id()
    return None


def _main_window(pid, title):
    for window in _windows(pid):
        for item in window.descendants():
            if item.element_info.control_type == "Window" and item.window_text() == "無法開啟文件":
                details = [child.window_text() for child in item.descendants()
                           if child.element_info.control_type == "Text" and child.window_text()]
                raise PbixExportError("Power BI 無法開啟公版：" + "；".join(details[:4]))
        if title in window.window_text() and any(
            item.element_info.automation_id == "save" for item in window.descendants()
        ):
            return window
    return None


def _editor_window(pid):
    for window in _windows(pid):
        if any("檢視及修改此檔案中的參數" in item.window_text()
               for item in window.descendants() if item.element_info.control_type == "Button"):
            return window
    return None


def _parameter_dialog(pid):
    for window in _windows(pid):
        for item in window.descendants():
            if item.element_info.control_type == "Window" and item.window_text() == "管理參數":
                return item
    return None


def _invoke_button(window, title=None, automation_id=None):
    for item in window.descendants():
        if item.element_info.control_type != "Button":
            continue
        if title is not None and item.window_text() != title:
            continue
        if automation_id is not None and item.element_info.automation_id != automation_id:
            continue
        try:
            item.iface_invoke.Invoke()
            return
        except Exception:
            try:
                item.click_input()
                return
            except Exception:
                continue
    raise PbixExportError(f"Power BI Desktop 找不到可操作的按鈕：{title or automation_id}")


def _focus_main(pid, title):
    from pywinauto import Desktop

    for window in Desktop(backend="win32").windows():
        if window.process_id() == pid and title in window.window_text():
            window.set_focus()
            return
    raise PbixExportError("Power BI Desktop 主視窗無法取得焦點。")


def _refresh_problem(window):
    for dialog in window.descendants():
        if dialog.element_info.control_type != "Window":
            continue
        if dialog.window_text() not in {"載入", "重新整理"}:
            continue
        messages = [item.window_text() for item in dialog.descendants()
                    if item.element_info.control_type == "Text" and item.window_text()]
        if any("錯誤" in message or "找不到" in message or "封鎖" in message for message in messages):
            return "；".join(messages[:6])
    return None


def _set_source(pid, title, excel_path):
    _invoke_button(_until(lambda: _main_window(pid, title), step="開啟公版", timeout=180), title="轉換資料")
    editor = _until(lambda: _editor_window(pid), step="開啟資料轉換", timeout=120)
    _invoke_button(editor, automation_id="ButtonManageParameters")

    def parameter_edit():
        dialog = _parameter_dialog(pid)
        if not dialog:
            return None
        edits = [item for item in dialog.descendants()
                 if item.element_info.control_type == "Edit" and item.window_text() == "目前的值"]
        return edits[0] if edits else None

    edit = _until(parameter_edit, step="開啟資料來源參數", timeout=45)
    edit.iface_value.SetValue(str(excel_path))
    if edit.iface_value.CurrentValue != str(excel_path):
        raise PbixExportError("Power BI Desktop 未接受篩選資料路徑。")
    dialog = _parameter_dialog(pid)
    _invoke_button(dialog, title="確定")
    _until(lambda: _parameter_dialog(pid) is None, step="套用資料來源參數", timeout=45)
    editor = _editor_window(pid)
    _invoke_button(editor, automation_id="ButtonCloseAndApplyQueryChanges")

    # The current Desktop's "關閉並套用" action both exits Power Query and
    # starts the model refresh.  Do not click a second "套用變更" button here:
    # recent Desktop builds no longer expose one on the report window.
    _focus_main(pid, title)
    refresh_started = time.monotonic()

    def load_complete():
        main = _main_window(pid, title)
        if not main:
            return False
        problem = _refresh_problem(main)
        if problem:
            raise PbixExportError(problem)
        return time.monotonic() - refresh_started >= 30 and not any(
            item.element_info.control_type == "Window" and item.window_text() == "載入"
            for item in main.descendants()
        )

    _until(load_complete, step="重新整理篩選資料", timeout=240)


def _keep_selected_pages(pid, title, pages):
    from pywinauto import keyboard

    main = _main_window(pid, title)
    tabs = [item.window_text() for item in main.descendants()
            if item.element_info.control_type == "TabItem"
            and item.window_text() in TOPIC_PAGES.values()]
    missing = pages.difference(tabs)
    if missing:
        raise PbixExportError(f"PBIX 公版缺少分析頁面：{'、'.join(sorted(missing))}")
    for page in tabs:
        if page in pages:
            continue
        _focus_main(pid, title)
        main = _main_window(pid, title)
        tab = next(item for item in main.descendants()
                   if item.element_info.control_type == "TabItem" and item.window_text() == page)
        tab.iface_selection_item.Select()
        tab.set_focus()
        keyboard.send_keys("+{F10}")
        menu = _until(lambda: next((item for item in _main_window(pid, title).descendants()
                                    if item.element_info.control_type == "MenuItem"
                                    and item.window_text() == "刪除"), None), step="開啟頁面刪除選單", timeout=30)
        menu.iface_invoke.Invoke()
        dialog = _until(lambda: next((item for item in _main_window(pid, title).descendants()
                                     if item.element_info.control_type == "Window"
                                     and item.window_text() == "刪除此頁面"), None), step="確認刪除報表頁面", timeout=30)
        _invoke_button(dialog, title="刪除")
        _until(lambda: not any(item.element_info.control_type == "TabItem" and item.window_text() == page
                               for item in _main_window(pid, title).descendants()), step="移除未選取的報表頁面", timeout=45)


def _validate_pbix(path, excel_path, expected_rows, selected_pages):
    from pbixray import PBIXRay

    model = PBIXRay(str(path))
    embedded = model.get_table("工作表1")
    actual_rows = len(embedded)
    if actual_rows != expected_rows:
        raise PbixExportError(f"PBIX 資料筆數不符：應為 {expected_rows}，實際為 {actual_rows}。")
    exported = pd.read_excel(excel_path)
    identity_columns = ["病歷號碼", "最初診斷日期", "原發部位", "組織型態"]
    if not all(column in embedded.columns and column in exported.columns for column in identity_columns):
        raise PbixExportError("PBIX 缺少個案驗證欄位，無法確認資料是否已重新整理。")

    def identities(frame):
        return Counter(
            tuple("" if pd.isna(value) else str(value).strip() for value in row)
            for row in frame[identity_columns].itertuples(index=False, name=None)
        )

    if identities(embedded) != identities(exported):
        raise PbixExportError("PBIX 的個案內容與目前篩選資料不一致，未提供下載。")
    with zipfile.ZipFile(path) as archive:
        # Desktop 2025 saves report definitions in a folder hierarchy rather
        # than the former Report/Layout file.
        if "Report/Layout" in archive.namelist():
            layout = json.loads(archive.read("Report/Layout").decode("utf-16-le"))
            actual_pages = {section["displayName"] for section in layout["sections"]}
        elif "Report/definition/pages/pages.json" in archive.namelist():
            pages = json.loads(archive.read("Report/definition/pages/pages.json").decode("utf-8"))
            actual_pages = {
                json.loads(
                    archive.read(f"Report/definition/pages/{page_id}/page.json").decode("utf-8")
                )["displayName"]
                for page_id in pages["pageOrder"]
            }
        else:
            raise PbixExportError("PBIX 格式不包含可驗證的報表頁面資訊。")
    if actual_pages != selected_pages:
        raise PbixExportError("PBIX 內的分析頁面與勾選主題不一致。")


def create_filtered_pbix(source_path, output_dir, *, cancers, year_start, year_end, behavior, topics):
    if os.name != "nt":
        raise PbixExportError("PBIX 產製目前只能在安裝 Power BI Desktop 的 Windows 電腦執行。")
    unknown = set(topics).difference(TOPIC_PAGES)
    if not topics or unknown:
        raise PbixExportError("目前 PBIX 公版只支援：" + "、".join(TOPIC_PAGES))
    selected_pages = {TOPIC_PAGES[topic] for topic in topics}
    template = Path(os.getenv("PBI_TEMPLATE_PATH", r"D:\PBIShare\powerbi_dataset.pbix"))
    desktop = _power_bi_desktop_path()
    if not template.is_file() or not desktop.is_file():
        raise PbixExportError("找不到 PBIX 公版或 Power BI Desktop，請檢查 PBI_TEMPLATE_PATH 與 PBI_DESKTOP_PATH。")

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    excel_path = output_dir / "powerbi_dataset.xlsx"
    pbix_path = output_dir / "annual_report.pbix"
    result = export_pbi_dataset(source_path, excel_path, cancers=cancers,
                                year_start=year_start, year_end=year_end, behavior=behavior)
    shutil.copy2(template, pbix_path)
    before = pbix_path.stat().st_mtime_ns
    # Keep Desktop visible while it refreshes the copy, so the user can see
    # that PBIX generation is in progress. It is closed after saving.
    launcher = subprocess.Popen([str(desktop), str(pbix_path)])
    desktop_pid = None
    try:
        title = pbix_path.stem
        desktop_pid = _until(lambda: _report_process_id(title), step="啟動 Power BI 公版", timeout=180)
        _set_source(desktop_pid, title, excel_path)
        _keep_selected_pages(desktop_pid, title, selected_pages)
        _invoke_button(_main_window(desktop_pid, title), automation_id="save")
        _until(lambda: pbix_path.stat().st_mtime_ns > before, step="儲存 PBIX", timeout=180)
        _validate_pbix(pbix_path, excel_path, result["rows"], selected_pages)
        return {**result, "pbix": str(pbix_path), "excel": str(excel_path)}
    finally:
        if launcher.poll() is None:
            launcher.terminate()
            try:
                launcher.wait(timeout=15)
            except subprocess.TimeoutExpired:
                launcher.kill()
        if desktop_pid:
            # This PID is the report process that was started for this output;
            # close it after saving so no hidden Desktop window is left behind.
            subprocess.run(["taskkill", "/PID", str(desktop_pid), "/T", "/F"],
                           capture_output=True, check=False)
