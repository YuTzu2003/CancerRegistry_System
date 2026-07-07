import json
import logging
from modules.services.api import get_llm_client
from modules.services.db import get_conn

def get_chart_insight_logic(data):
    field_key = data.get("field_key", "")
    chart_data = data.get("data", {})
    fields = data.get("fields", [])
    
    definitions = []
    
    if fields:
        conn = get_conn()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(fields))
        query = f"""SELECT [中文欄位名稱], [define] FROM [Hospital_data].[dbo].[CancerRegistry_FieldMap] WHERE [中文欄位名稱] IN ({placeholders})"""
        cursor.execute(query, fields)
        rows = cursor.fetchall()
        for row in rows:
            col_name = row[0]
            col_def = row[1]
            if col_def and str(col_def).strip():
                definitions.append(f"- {col_name}: {str(col_def).strip()}")
        conn.close()

    if definitions:
        def_section = f"[Related Field Definitions]:\n" + "\n".join(definitions)
        analysis_instruction = "Please provide a formal data insight and analytical narrative based on the definitions and information provided above."
    else:
        def_section = ""
        analysis_instruction = "(No related field definitions are available; please interpret directly based on the data content.)\nPlease provide a formal data insight and analytical narrative based on the chart data above."

    prompt = f"""You are a professional medical and oncology data analysis expert. Please provide a rigorous and formal analysis based on the cancer registry statistical chart data provided below.
            [Chart Topic]: {field_key}
            {def_section}
            [Data Content]: {json.dumps(chart_data, ensure_ascii=False)}
            
            {analysis_instruction}
            The content should include trends shown by the data, population distribution characteristics, and their clinical or public health significance.
            Notes:
            1. Please provide the analysis content directly without any opening remarks or greetings.
            2. The tone must be professional and objective, suitable for inclusion in a formal cancer registry annual report or medical report.
            3. Do not include extraneous or irrelevant information. Keep it concise.
            4. Keep the explanation within 100 words."""
    #print(prompt)

    try:
        client, model_name = get_llm_client()
        response = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": "You are a professional cancer and medical data analysis expert. Please be sure to reply in Traditional Chinese."},
                {"role": "user", "content": prompt}
            ],temperature=0.3
        )
        insight = response.choices[0].message.content.strip("*-_#` \n\t")
        return {"success": True, "insight": insight}
    except Exception as e:
        logging.error(f"Error in AI analysis: {e}")
        return {"success": False, "error": str(e)}