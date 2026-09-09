# Windows IIS 正式部署

## 開發模式

`.env` 使用：

```ini
APP_ENV=development
APP_DEBUG=true
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

啟動：

```powershell
uv run app.py
```

## 第一次正式部署

目標資料庫必須是空白 SQL Server 資料庫。將 `.env` 設為：

```ini
APP_ENV=production
APP_DEBUG=false
SECRET_KEY=至少32字元的隨機字串
SQLALCHEMY_DATABASE_URI=mssql+pyodbc://帳號:密碼@伺服器:1433/資料庫名稱?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
PUBLIC_HTTP_PORT=5000
BACKEND_BASE_PORT=51001
APP_WORKERS=1
```

以系統管理員身分執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\setup-and-deploy.ps1
```

此命令會先執行 `deploy/database/CancerRegistry_System.sql`，再設定 IIS、ARR、Windows 開機自啟、Firewall 與健康檢查。

## 後續更新

後續更新不重跑 schema：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\deploy-production.ps1
```

檢查服務：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\check-production.ps1
```

停止或移除自啟：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\stop-production.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\unregister-autostart.ps1
```

`SESSION_COOKIE_SECURE=true` 僅適用已設定 HTTPS 的 IIS binding；HTTP 環境請維持 `false`。
## Debug 快捷啟動

以下指令只在目前 PowerShell 工作階段使用 development 與 Flask debugger，不會改寫 `.env`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\start-development.ps1
```