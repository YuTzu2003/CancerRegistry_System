import re

def _natural_sort_key_original(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]

def _natural_sort_key_new(s):
    def convert(text, is_match):
        if is_match:
            return tuple(int(x) for x in text.split('.'))
        return text.lower()
    parts = re.split(r'(\d+(?:\.\d+)*)', str(s))
    return [convert(text, i % 2 == 1) for i, text in enumerate(parts)]

def test_sort(name, cases, expected_new):
    print(f"--- Test: {name} ---")
    print(f"Input: {cases}")
    
    original_sorted = sorted(cases, key=_natural_sort_key_original)
    new_sorted = sorted(cases, key=_natural_sort_key_new)
    
    print(f"Original result: {original_sorted}")
    print(f"New result:      {new_sorted}")
    print(f"Expected (New):  {expected_new}")
    
    success = new_sorted == expected_new
    print(f"Match Expected:  {success}")
    return success

# Test Cases
test_cases = [
    ("Hierarchical Numbers", 
     ['2.3.1YYY', '2.3.2YYY', '2.3XXX', '2.4ZZZ'], 
     ['2.3XXX', '2.3.1YYY', '2.3.2YYY', '2.4ZZZ']),
    
    ("Hierarchical Numbers with multi-digit decimals", 
     ['7.10其他', '7.2其他', '7.1其他'], 
     ['7.1其他', '7.2其他', '7.10其他']),
    
    ("Numbers and Letters", 
     ['100', '20', 'A', '1'], 
     ['1', '20', '100', 'A']),
    
    ("Prefix Hierarchical", 
     ['1.2.3.4', '1.2.3'], 
     ['1.2.3', '1.2.3.4']),
]

all_passed = True
for name, cases, expected in test_cases:
    if not test_sort(name, cases, expected):
        all_passed = False

print("\n--- Edge Cases ---")
edge_cases = ['', 'abc', '123', '1.2.', '.1.2', '2..3', ' ', '0.1.0']
for ec in edge_cases:
    try:
        key = _natural_sort_key_new(ec)
        print(f"'{ec}' -> {key}")
    except Exception as e:
        print(f"'{ec}' FAILED: {e}")
        all_passed = False

if all_passed:
    print("\nVerification Complete: New implementation works as expected.")
else:
    print("\nVerification Failed: Issues found.")
