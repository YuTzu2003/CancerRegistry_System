# 癌症登記資料管理平台

以 Flask 與 SQL Server 建置的癌症登記資料處理、資料清洗與分析系統。

## 系統需求

- Python 3.12 以上
- [uv](https://docs.astral.sh/uv/)
- SQL Server 與 ODBC Driver 17 或 18
- 正式環境另需 IIS、IIS URL Rewrite 2.1 與 IIS ARR 3.0

## 本機開發

```powershell
git clone https://github.com/YuTzu2003/CancerRegistry_System.git
Set-Location CancerRegistry_System
uv sync
Copy-Item .env.example .env
```

設定 `.env` 的 `SQLALCHEMY_DATABASE_URI` 與 `SECRET_KEY` 後，以 Flask 開發模式啟動：

```powershell
uv run app.py
```

或使用不改寫 `.env` 的 debug 指令：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\start-development.ps1
```

## 正式部署

正式架構為：

```text
使用者 → IIS + ARR → Waitress → Flask → SQL Server
```

完整的 Windows IIS 架設、SQL Server 初始化、首次一鍵部署、後續更新、開機自啟、健康檢查、停止與 debug／production 模式切換，請參閱：[架設步驟](架設步驟.md)。

首次正式部署需以系統管理員 PowerShell 執行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\setup-and-deploy.ps1
```

後續程式更新不重跑 schema SQL：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\deploy\deploy-production.ps1
```

## 重要設定

- 資料庫由 `.env` 的 `SQLALCHEMY_DATABASE_URI` 決定；schema SQL 不固定資料庫名稱。
- 首次正式部署的目標必須是空白資料庫。
- `.env` 含有密鑰與資料庫連線資訊，禁止提交到 Git。
- 只有 IIS 已完成 HTTPS binding 時，才將 `SESSION_COOKIE_SECURE=true`。

## 主要目錄

| 目錄／檔案 | 說明 |
| --- | --- |
| `app.py` | Flask 與 Waitress 啟動入口 |
| `modules/` | 系統功能模組與 Blueprint |
| `static/` | CSS、JavaScript 與靜態資源 |
| `deploy/` | IIS、ARR、Waitress 與 SQL Server 部署腳本 |
| `deploy/database/CancerRegistry_System.sql` | 首次部署使用的 schema SQL |
| `架設步驟.md` | 完整 Windows 架設與維運手冊 |