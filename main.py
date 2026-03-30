import pandas as pd
from field_mapping import detect_system
from cancer_classify import cancer_classify, rule_table_classify
from clean import cleanValidate
from datetime import datetime

INPUT_FILE = 'data/20260318測試.xlsx' 
SHEET_NAME = '1150318虛擬V1(給虎科)'  
TARGET_SYSTEM = '雲醫癌AI模組'      
VALIDATE_OUTPUT = f"data/validate_result_{SHEET_NAME}.xlsx"
CANCER_OUTPUT = f"data/cancer_classified_{SHEET_NAME}.xlsx"
RULES_OUTPUT_DIR = f"data/output_rules_{SHEET_NAME}"
Auditor = "TEST"

df = pd.read_excel(INPUT_FILE, sheet_name=SHEET_NAME, dtype=str)
system_name, _ = detect_system(df.columns)
print(f"The data for {system_name}")

# 資料清洗
stats, alias_mapping, sorted_df, sorted_mask = cleanValidate(INPUT_FILE, SHEET_NAME, VALIDATE_OUTPUT)
total = stats['total']
errors = stats['errors']
accuracy_pct = stats['accuracy']*100 
missing = stats['missing']
format_err = stats['format']

print("================ Validate Report ================")
print(f"Records: {total}")
print(f"Error Count: {errors}")
print(f"Accuracy Rate: {accuracy_pct:.2f}%")
print(f"Error Breakdown: Missing {missing} fields / Format Errors {format_err} fields")
print("Auditor: {Auditor}")
print(f"Validate Date: {datetime.now()}")
print(f"Validate file to '{VALIDATE_OUTPUT}'")

# 待寫
