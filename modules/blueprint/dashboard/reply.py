import re
import json
import logging
from modules.services.api import get_llm_client
from modules.services.db import get_conn

STYLE_PROMPTS = {
    "balanced": """
            Use a calm, neutral, and objective analytical style.
            Clearly describe the main statistical trends and population distribution.
            Avoid overly strong conclusions or speculative statements.
            Use language suitable for general medical data interpretation.
            """,

    "formal": """
            Use a rigorous, formal, and professional oncology reporting style.
            The content must be suitable for inclusion in a cancer registry annual report
            or formal medical report. Use precise medical, epidemiological, and statistical
            terminology. Avoid conversational expressions and subjective judgments.
            """,

    "concise": """
            Use a concise medical summary style.
            Focus only on the most important statistical trend, population characteristic,
            and clinical or public health significance.
            Avoid repeating values or providing unnecessary background information.
            """
}

def get_chart_insight_logic(data):
    field_key = data.get("field_key", "")
    chart_data = data.get("data", {})
    fields = data.get("fields", [])
    mode_ai = data.get("mode_ai", "balanced")
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
    else:
        def_section = ""
    style_instruction = STYLE_PROMPTS.get(mode_ai, STYLE_PROMPTS["balanced"])

    prompt = f"""
                You are a professional medical and oncology data analysis expert.
                Please provide a rigorous analysis based strictly on the cancer registry
                statistical chart data provided below.
                [Chart Topic]{field_key}
                [Definition]{def_section}
                [Data Content]{json.dumps(chart_data, ensure_ascii=False)}
                [Writing Style]{style_instruction}

                [Analysis Requirements]
                The content should include:
                1. The principal trends shown by the data.
                2. Important population distribution characteristics.
                3. Relevant clinical, epidemiological, or public health significance.

                Notes:
                1. Provide the analysis directly without opening remarks or greetings.
                2. Base all conclusions strictly on the supplied data.
                3. Do not infer causes that cannot be supported by the data.
                4. Do not include irrelevant background information.
                5. Keep the response within 100 words.
            """

    try:
        client, model_name = get_llm_client()
        response = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": "You are a professional cancer and medical data analysis expert. Please be sure to reply in Traditional Chinese."},
                {"role": "user", "content": prompt}
            ],temperature=0.3
        )
        content = response.choices[0].message.content
        insight = re.sub(r'[*#`\n\t]+', '', content).strip()
        insight = (insight.replace(r'\ge', '>=').replace(r'\le', '<=').replace(r'\neq', '!=').replace('$', ''))
        return {"success": True, "insight": insight}
    
    except Exception as e:
        logging.error(f"Error in AI analysis: {e}")
        return {"success": False, "error": str(e)}