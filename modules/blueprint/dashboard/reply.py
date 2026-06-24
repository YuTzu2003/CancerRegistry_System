import modules.blueprint.dashboard.definition.fmt_115 as fmt_115
from modules.services.api import get_llm_client

def get_chart_insight_logic(data):
    field_key = data.get("field_key", "")
    chart_data = data.get("data", {})
    description = ""
    definition = ""

    if fmt_115 and hasattr(fmt_115, 'RULES') and field_key in fmt_115.RULES:
        rule = fmt_115.RULES[field_key]
        description = rule.get("description", "")
        definition = rule.get("definition", "")

    desc_str = f"[Field Description]: {description}\n" if description else ""
    def_str = f"[Code Definition]:\n{definition}\n" if definition else ""

    prompt = f"""You are a professional and rigorous medical data analyst. Please provide a concise analysis of about 50 to 100 words for the following chart data, pointing out population characteristics and trends.
                [Analysis Field]: {field_key}{desc_str}{def_str}
                [Statistical Results]:{chart_data}
                Based on the above description and definition, provide a professional conclusion. Please provide the analysis content directly without any introductory greetings or small talk."""
    print(prompt)

    try:
        client, model_name = get_llm_client()
        response = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": "You are a professional data analysis expert. Please always respond in Traditional Chinese."},
                {"role": "user", "content": prompt}
            ],temperature=0.3)
        
        insight = response.choices[0].message.content
        return {"success": True, "insight": insight}
    except Exception as e:
        return {"success": False, "error": str(e)}