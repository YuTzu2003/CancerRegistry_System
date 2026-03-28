import pandas as pd
import os
from field_mapping import detect_system
from cancer_classify import cancer_classify, rule_table_classify
from clean import cleanValidate

INPUT_FILE = 'data/20260318測試.xlsx' 
SHEET_NAME = '1150318虛擬V1(給虎科)'  
TARGET_SYSTEM = '雲醫癌AI模組'      
VALIDATE_OUTPUT = f"data/validate_result_{SHEET_NAME}.xlsx"
CANCER_OUTPUT = f"data/cancer_classified_{SHEET_NAME}.xlsx"
RULES_OUTPUT_DIR = f"data/output_rules_{SHEET_NAME}"

df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, dtype=str)
system_name, _ = detect_system(df.columns)
print(f"The data for {system_name}")

# 資料清洗
error_count, alias_mapping = cleanValidate(INPUT_FILE, SHEET_NAME, VALIDATE_OUTPUT)
print(f"error count: {error_count}")
print(f"save file: {VALIDATE_OUTPUT}")

# 待寫
