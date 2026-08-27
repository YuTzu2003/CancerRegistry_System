## 癌症登記資料管理平台
是一個專為醫療機構設計的癌症登記資料管理系統，透過自動化的資料清洗、年報分析與版本控制，提升申報品質與效率。

---

### 1. 環境建置與安裝指南

請開啟終端機 (Terminal / PowerShell) 並執行以下指令：
```bash
git clone https://github.com/YuTzu2003/CancerRegistry_System.git
cd CancerRegistry_System

# 使用uv建立虛擬環境
uv sync
playwright install chromium
```

### 2. 資料庫還原配置
系統預設資料需透過還原備份檔來建立：
1. 開啟 **SQL Server Management Studio (SSMS)**。
2. 找到本專案資料夾下的 `data/Hospital_data.bak` 備份檔。
3. 確認登入的 SQL 使用者帳號擁有讀寫該資料庫的完整權限。

### 3. 環境變數設定 (`.env`)
請在專案根目錄下建立一個名為 `.env` 的純文字檔案，並填入以下系統設定（請依據您的實際MSSQL帳密與語言模型選擇進行修改）：

```env
# Flask設定
FLASK_PORT=5000

# SQL Server 資料庫連接設定
DB_SERVER=127.0.0.1
DB_PORT=1433
DB_NAME=Hospital_data
DB_USER=您的資料庫帳號 (例如: YLH)
DB_PASSWORD=您的資料庫密碼

# Ollama:
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_API_KEY=ollama
LLM_MODEL=gemma4:26b  # 替換為您實際下載的本地模型名稱

# OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=您的_OPENAI_API_KEY
# OPENAI_MODEL=gpt-4o-mini
```

### 4. 啟動系統
當上述環境變數與資料庫皆設定完成後，於終端機輸入以下指令啟動系統：

```bash
uv run app.py
```