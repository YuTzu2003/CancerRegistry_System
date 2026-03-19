import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from rules import RULES
from validate import validate_cell

input_file = 'data.xlsx'
output_file = f"validate_{input_file}"

df = pd.read_excel(input_file, dtype=str)

# 錯誤紀錄
error_mask = pd.DataFrame(False, index=df.index, columns=df.columns)
for ch_name, rule in RULES.items():
    en_field = rule.get('field')
    if en_field and en_field in df.columns:
        error_mask[en_field] = df[en_field].apply(lambda x: not validate_cell(x, rule))


# 將錯誤資料排到最上面
df['_has_error'] = error_mask.any(axis=1)
sorted_df = df.sort_values(by='_has_error', ascending=False, kind='mergesort')
sorted_mask = error_mask.loc[sorted_df.index]
sorted_df = sorted_df.drop(columns=['_has_error'])
sorted_df.to_excel(output_file, index=False, engine='openpyxl')


# 錯誤標記
wb = load_workbook(output_file)
ws = wb.active
fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
for r_idx in range(len(sorted_df)):
    for c_idx in range(len(sorted_df.columns)):
        if sorted_mask.iloc[r_idx, c_idx]:
    
            ws.cell(row=r_idx + 2, column=c_idx + 1).fill = fill

wb.save(output_file)
error_count = error_mask.any(axis=1).sum()

print(f"error count: {error_count}")
print(f"save file:{output_file}")