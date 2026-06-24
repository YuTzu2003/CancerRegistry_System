import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def get_llm_client():
    provider = os.environ.get("LLM_PROVIDER")
    
    if provider and provider.lower() == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        model = os.environ.get("OPENAI_MODEL")
        client = OpenAI(api_key=api_key)
        return client, model
    else:
        base_url = os.environ.get("LLM_BASE_URL")
        api_key = os.environ.get("LLM_API_KEY")
        model = os.environ.get("LLM_MODEL")
        client = OpenAI(base_url=base_url, api_key=api_key)
        return client, model