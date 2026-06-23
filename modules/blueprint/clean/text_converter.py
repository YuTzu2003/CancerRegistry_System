import pandas as pd
import os

def convert_txt_to_excel(input_path, output_path):
    delimiters = ['\t', ',', ';']
    encodings = ['utf-8', 'big5', 'utf-16', 'gbk']
    
    df = None
    for encoding in encodings:
        for sep in delimiters:
            try:
                df = pd.read_csv(input_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                if df.shape[1] > 1:
                    break
            except Exception:
                continue
        if df is not None and df.shape[1] > 1:
            break

    if df is not None and df.shape[1] > 1:
        if not output_path.lower().endswith('.xlsx'):
            output_path = os.path.splitext(output_path)[0] + '.xlsx'
        df.to_excel(output_path, index=False)
        print(f"File converted to Excel: {output_path}")
        return output_path
    else:
        with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = [f.readline() for _ in range(5)]
            for line in content:
                print(repr(line))
