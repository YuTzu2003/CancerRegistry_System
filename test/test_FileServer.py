from pathlib import Path
from typing import Optional, Tuple
import ctypes
from ctypes import wintypes
from getpass import getpass
import os
import shutil
import subprocess
import uuid

FILE_SERVER_SHARE = r"\\120.113.70.239\Drive"

class NETRESOURCEW(ctypes.Structure):
    _fields_ = [
        ("dwScope", wintypes.DWORD),
        ("dwType", wintypes.DWORD),
        ("dwDisplayType", wintypes.DWORD),
        ("dwUsage", wintypes.DWORD),
        ("lpLocalName", wintypes.LPWSTR),
        ("lpRemoteName", wintypes.LPWSTR),
        ("lpComment", wintypes.LPWSTR),
        ("lpProvider", wintypes.LPWSTR),
    ]


RESOURCETYPE_DISK = 1
NO_ERROR = 0
ERROR_SESSION_CREDENTIAL_CONFLICT = 1219


def load_windows_network_api():
    mpr = ctypes.WinDLL("mpr", use_last_error=True)
    mpr.WNetAddConnection2W.argtypes = [ctypes.POINTER(NETRESOURCEW),wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,]
    mpr.WNetAddConnection2W.restype = wintypes.DWORD
    mpr.WNetCancelConnection2W.argtypes = [wintypes.LPCWSTR,wintypes.DWORD,wintypes.BOOL,]
    mpr.WNetCancelConnection2W.restype = wintypes.DWORD
    return mpr

def select_file() -> Optional[Path]:
    ps_command = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dialog = New-Object System.Windows.Forms.OpenFileDialog; "
        "$dialog.Title = '選擇要上傳的檔案'; "
        "if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        "[Console]::Write($dialog.FileName) }"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", ps_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"無法開啟檔案選擇視窗：{details}")

    selected = result.stdout.strip()
    return Path(selected) if selected else None


def get_credentials() -> Optional[Tuple[str, str]]:
    username = input("File Server 帳號：").strip()
    if not username:
        return None

    password = getpass("File Server 密碼：")
    return (username, password) if password else None

def windows_error_message(error_code: int) -> str:
    known_errors = {
        5: "存取被拒，請檢查共享權限與 NTFS 權限。",
        53: "找不到網路路徑，請檢查 IP、網路及防火牆。",
        67: "找不到共享名稱，請檢查 Drive 是否為正確的共享名稱。",
        86: "密碼錯誤。請輸入 Windows 帳號密碼，不是登入 PIN 碼。",
        1219: (
            "Windows 已使用其他帳號連到同一台 File Server。"
            "請先在命令提示字元執行：net use * /delete，再重新測試。"
        ),
        1326: "帳號或密碼錯誤。帳號格式可使用 電腦名稱\\使用者名稱。",
    }
    if error_code in known_errors:
        return known_errors[error_code]
    system_message = ctypes.FormatError(error_code).strip()
    return system_message


def disconnect_file_server(mpr) -> None:
    mpr.WNetCancelConnection2W(FILE_SERVER_SHARE, 0, True)

def connect_file_server(mpr, username: str, password: str) -> None:
    resource = NETRESOURCEW()
    resource.dwType = RESOURCETYPE_DISK
    resource.lpRemoteName = FILE_SERVER_SHARE
    result = mpr.WNetAddConnection2W(ctypes.byref(resource),password,username,0,)
    if result == ERROR_SESSION_CREDENTIAL_CONFLICT:
        disconnect_file_server(mpr)
        result = mpr.WNetAddConnection2W(ctypes.byref(resource),password,username,0,)

    if result != NO_ERROR:
        details = windows_error_message(result)
        raise ConnectionError(f"連線失敗（錯誤 {result}）：{details}")


def upload_to_file_server(source_file: Path) -> Path:
    destination_folder = Path(FILE_SERVER_SHARE)
    if not destination_folder.is_dir():
        raise FileNotFoundError(f"無法開啟共享資料夾：{destination_folder}\n""請確認共享路徑、網路與資料夾權限。")

    destination_file = destination_folder / source_file.name
    temporary_file = destination_folder / f".upload_{uuid.uuid4().hex}.tmp"

    try:
        shutil.copyfile(source_file, temporary_file)
        source_size = source_file.stat().st_size
        uploaded_size = temporary_file.stat().st_size
        if uploaded_size != source_size:
            raise IOError(
                f"暫存檔大小不一致：來源 {source_size} bytes，"
                f"上傳 {uploaded_size} bytes。"
            )

        os.replace(temporary_file, destination_file)

        final_size = destination_file.stat().st_size
        if final_size != source_size:
            raise IOError(
                f"上傳驗證失敗：來源 {source_size} bytes，"
                f"目的地 {final_size} bytes。"
            )

        return destination_file

    except PermissionError as exc:
        raise PermissionError(
            "無法寫入或覆蓋檔案。請確認共享權限至少有「變更」，"
            "NTFS 權限至少有「修改」，並確認目的檔案沒有被 Excel 開啟。"
        ) from exc
    finally:
        if temporary_file.exists():
            try:
                temporary_file.unlink()
            except OSError:
                pass


def validate_settings() -> None:
    if "xxx" in FILE_SERVER_SHARE.lower():
        raise ValueError(
            "請先修改程式最上方的 FILE_SERVER_SHARE，"
            "把 xxx 換成 File Server 的實際 IP。"
        )
    if not FILE_SERVER_SHARE.startswith("\\\\"):
        raise ValueError(r'FILE_SERVER_SHARE 必須是 UNC 路徑，例如 \\192.168.x.x\Drive。')

def main() -> None:
    mpr = None
    connected = False

    try:
        validate_settings()
        source_file = select_file()
        if source_file is None:
            print("未輸入檔案路徑，已取消上傳。")
            return

        credentials = get_credentials()
        if credentials is None:
            print("未輸入帳號或密碼，已取消上傳。")
            return

        mpr = load_windows_network_api()
        username, password = credentials
        connect_file_server(mpr, username, password)
        connected = True

        destination_file = upload_to_file_server(source_file)
        print(f"上傳完成：{destination_file}")
        print("若目的地原本有同名檔案，已完成覆蓋。")

    except Exception as exc:
        print(f"上傳失敗：{exc}")
    finally:
        if connected and mpr is not None:
            disconnect_file_server(mpr)

if __name__ == "__main__":
    main()
