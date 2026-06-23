files = [
    'modules/services/dashboard.py',
    'modules/blueprint/dashboard/__init__.py'
]

for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('_load_user_favorites', 'load_user_favorites')
    
    with open(file, 'w', encoding='utf-8') as f:
        f.write(content)
