import os
import sys
from modules.services.api import get_llm_client

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    client, model_name = get_llm_client()
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": "你好，請用一句話介紹你自己。"}],
        temperature=0.3)
    print(response.choices[0].message.content)
    
except Exception as e:
    print(e)