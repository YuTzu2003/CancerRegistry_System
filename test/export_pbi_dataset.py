"""Create a Power BI-ready annual-report Excel file without altering the source."""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.blueprint.dashboard.pbi_export import export_pbi_dataset


def main():
    parser = argparse.ArgumentParser(description="輸出含癌別與圖表輔助欄位的 PBI 年報資料")
    parser.add_argument("source", help="原始年報 Excel 路徑")
    parser.add_argument("output", help="PBI 專用 Excel 輸出路徑")
    args = parser.parse_args()

    result = export_pbi_dataset(args.source, args.output)
    print(f"完成：{result['rows']} 筆資料，{result['classified_rows']} 筆已分類癌別。")
    print(f"輸出檔：{result['output']}")


if __name__ == "__main__":
    main()
