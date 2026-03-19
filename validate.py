import pandas as pd
import re
from datetime import datetime

# 驗證
def validate_cell(val, rule):
    if pd.isna(val):
        val = ""
    val = str(val).strip()

    if 'SV' in rule:
        if isinstance(rule['SV'], list) and val in rule['SV']:
            return True
        elif val == rule['SV']:
            return True

    if 'length' in rule and len(val) != rule['length']:
        return False
    
    if 'digit' in rule and rule['digit'] and not val.isdigit():
        return False
    
    if 'max_length' in rule and len(val) > rule['max_length']:
        return False
    
    if 'regex' in rule and not re.match(rule['regex'], val):
        return False

    if 'choices' in rule and val not in rule['choices']:
        return False
    
    if 'is_date' in rule:
        try:
            datetime.strptime(val, rule['is_date'])
        except ValueError:
            return False
        
    if 'range' in rule:
        try:
            num_val = int(val)
            min_val, max_val = rule['range']
            if not (min_val <= num_val <= max_val):
                return False
        except ValueError:
            return False
        
    return True