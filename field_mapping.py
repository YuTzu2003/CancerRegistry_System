import pandas as pd
from modules.db import get_conn

def field_mapping(target_col):
    conn = get_conn()
    query = """SELECT * FROM [Hospital_data].[dbo].[FieldName]"""
    df_mapping = pd.read_sql(query, conn)
    conn.close()

    alias_dict = {}
    output_field_list = []

    for _, row in df_mapping.iterrows():
        output_name = str(row[target_col]).strip() if pd.notna(row[target_col]) else ""

        if output_name and output_name not in output_field_list:
            output_field_list.append(output_name)

        aliases = [
            row['中文欄位名稱'], 
            row['英文欄位名稱'], 
            row['台大雲林欄位名稱'], 
            row['台大體系醫整庫欄位名稱'], 
            row['台灣癌症登記中心']
        ]

        for alias in aliases:
            if pd.notna(alias):
                clean_alias = str(alias).strip()
                if clean_alias:
                    alias_dict[clean_alias] = output_name

    return alias_dict, output_field_list

def process_data(excel_path, mapping_dict, AImodule_list, target_sheet=0):

    df_excel = pd.read_excel(excel_path, sheet_name=target_sheet)
    
    rename_map = {}
    for col in df_excel.columns:
        clean_col = str(col).strip()
        ai_name = mapping_dict.get(clean_col, "")
        if ai_name:
            rename_map[col] = ai_name
            
    df_transformed = df_excel[list(rename_map.keys())].copy()
    df_transformed.rename(columns=rename_map, inplace=True)
    for ai_name in AImodule_list:
        if ai_name not in df_transformed.columns:
            df_transformed[ai_name] = "" 
            
    df_final = df_transformed[AImodule_list]
    return df_final

if __name__ == "__main__": 
    data_path = "data/20260318測試.xlsx"  
    sheet_name = "測1.1" 
    target_column = "雲醫癌AI模組"

    alias_mapping, all_fields = field_mapping(target_column)
    df_output_data = process_data(data_path, alias_mapping, all_fields, target_sheet=sheet_name)
    
    rename_result_path = f"data/{target_column}_output.xlsx"
    df_output_data.to_excel(rename_result_path, index=False)