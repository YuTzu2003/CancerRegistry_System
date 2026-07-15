import re
import json
import logging
from modules.services.api import get_llm_client
from modules.services.db import get_conn

STYLE_PROMPTS = {
    "balanced": """
            Use a calm, neutral, and objective medical-statistical reporting style.
            Clearly describe the main trends, population distribution characteristics,
            and important differences shown in the chart. Where supported by the data,
            identify differences by year, sex, age, or stage. Avoid over-interpretation
            and causal claims that cannot be supported by the data. Use natural,
            professional language suitable for internal medical data analysis and reporting.
            """,

    "formal": """
            Use a formal cancer registry annual-report style.
            The writing must be rigorous, objective, and precise, and suitable for direct
            inclusion in a cancer registry annual report or formal medical report.
            Prioritize the reporting year, case count, principal distribution, and key
            comparisons. When supported by the chart, describe differences from national
            data, the previous year, or other population groups. Use formal medical,
            epidemiological, and statistical terminology. Avoid conversational language,
            subjective commentary, exaggerated conclusions, and speculation about causes.
            Structure the narrative by first summarizing the overall findings, then covering
            relevant age, sex, stage, histology, or treatment distributions.
            """,

    "concise": """
            Use a concise and direct medical summary style.
            Retain only the most important statistical trends, population characteristics,
            and practical significance shown in the chart. Avoid repeated values,
            background exposition, and secondary details. Keep sentences short and clear
            while maintaining a professional and objective tone.
            """
}

def get_chart_insight_logic(data):
    field_key = data.get("field_key", "")
    chart_data = data.get("data", {})
    fields = data.get("fields", [])
    mode_ai = data.get("mode_ai", "balanced")
    year_start = data.get("year_start", "")
    year_end = data.get("year_end", "")
    selected_year_range = f"{year_start}-{year_end}" if year_start and year_end else year_start or year_end or "Not specified"
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
    style_instruction = STYLE_PROMPTS.get(mode_ai)

    prompt = f"""
                You are a professional medical and oncology data analysis expert.
                Please provide a rigorous analysis based strictly on the cancer registry
                statistical chart data provided below.
                [Chart Topic]{field_key}
                [Definition]{def_section}
                [Selected Year Range]{selected_year_range}
                [Data Content]{json.dumps(chart_data, ensure_ascii=False)}
                [Writing Style]{style_instruction}

                [Analysis Requirements]
                The content should include:
                1. The principal trends shown by the data.
                2. Important population distribution characteristics.
                3. Relevant clinical, epidemiological.

                Notes:
                1. without opening remarks or greetings.
                2. Base all conclusions strictly on the supplied data.
                3. Do not infer causes that cannot be supported by the data.
                4. Do not include irrelevant background information.
                5. Treat the selected year range as the scope of the analysis.
                6. Keep the response within 130 words.
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
