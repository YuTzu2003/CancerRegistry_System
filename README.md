本專案是一個專為醫療機構設計的癌症登記資料管理系統。透過自動化的資料清洗流程，協助癌症登記人員（Cancer Registrar）提升資料申報的品質與效率。

---

## 目前功能

1.  **資料清洗模組**：自動偵測原始 CSV/Excel 資料中的格式錯誤、邏輯衝突，並根據癌症登記手冊進行標準化轉換。
2.  **申報紀錄與審核**：完整紀錄每次資料清洗的歷程，支援結果匯出與歷史申報檔案管理。
3.  **虛擬資料生成**：支援產生符合格式規範的測試資料，用於系統測試。
4.  **使用者權限管理**：區分管理者與一般使用者權限，確保資料存取安全。

---

## 環境建置與執行流程

### 1. 環境準備
請確保電腦已安裝：
-   Python3.12 或更高版本
-   [uv](https://github.com/astral-sh/uv)
-   SQL Server

### 2. 下載專案與環境初始化
```bash
git clone https://github.com/YuTzu2003/CancerRegistry_System.git
cd CancerRegistry_System

uv venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate # Linux/Mac
uv sync
```

### 3. 資料庫配置
還原資料庫：請在 SQL Server 中還原 `data/Hospital_data.bak` 備份檔。


### 4. 執行應用程式
```bash
uv run app.py
```
啟動後，平台網址 `http://127.0.0.1:5000`。

---

## 備註
-   如需調整資料庫連接字串，請至 `modules/db.py` 進行修改。
-   資料清洗邏輯在 `modules/clean_pipeline/` 目錄下。