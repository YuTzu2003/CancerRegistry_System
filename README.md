## 資料自動偵測錯誤並清洗

環境建置
```bash
uv venv
.venv\Scripts\activate
uv sync
```

欄位名稱轉換
```bash
Restore Hospital_data.bak
uv run field_mapping.py
```

資料清洗
```bash
uv run mian.py
```