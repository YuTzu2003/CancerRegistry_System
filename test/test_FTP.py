import os
import subprocess
from ftplib import FTP, error_perm

FTP_HOST = "120.113.70.229"
FTP_PORT = 21212
FTP_USER = "willie"
FTP_PASSWORD = "nfu123@@@"
FTP_FOLDER = "Bilab_FTP/YuTzu/YLH_FILE/"

def connect_ftp():
    ftp = FTP()
    ftp.encoding = "utf-8"
    ftp.connect(FTP_HOST, FTP_PORT, timeout=10)
    ftp.login(FTP_USER, FTP_PASSWORD)
    ftp.set_pasv(True)
    print(ftp.getwelcome())
    return ftp


def upload_ftp():
    ps_cmd = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$f = New-Object System.Windows.Forms.OpenFileDialog; "
        "$f.Title = '請選擇要上傳的檔案'; "
        "if($f.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK){$f.FileName}"
    )

    result = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    file_path = result.stdout.strip()
    filename = os.path.basename(file_path)
    ftp = None

    try:
        ftp = connect_ftp()
        ftp.cwd(FTP_FOLDER)
        print(f"準備上傳檔案：{filename} 至 {FTP_FOLDER}")        
        with open(file_path, "rb") as file_obj:
            ftp.storbinary(f"STOR {filename}", file_obj) 
        print("檔案上傳成功！")

    except error_perm as exc:
        print("FTP 權限或帳號密碼錯誤：", exc)

    except TimeoutError:
        print("FTP 連線逾時，請確認 IP、Port 或防火牆設定")

    except OSError as exc:
        print("網路連線或檔案讀取失敗：", exc)

    except Exception as exc:
        print("FTP 測試失敗：", exc)

    finally:
        if ftp is not None:
            try:
                ftp.quit()
            except Exception:
                ftp.close()

if __name__ == "__main__":
    upload_ftp()