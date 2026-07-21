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

INSIGHT_LANGUAGES = ("zh-TW", "en")


def _clean_insight_text(value):
    text = re.sub(r'[*#`\n\t]+', '', str(value or '')).strip()
    return text.replace(r'\ge', '>=').replace(r'\le', '<=').replace(r'\neq', '!=').replace('$', '')


def _parse_bilingual_insights(content):
    raw = str(content or '').strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*|\s*```$', '', raw, flags=re.IGNORECASE)
    start, end = raw.find('{'), raw.rfind('}')
    if start < 0 or end <= start:
        raise ValueError('AI response does not contain bilingual JSON')
    payload = json.loads(raw[start:end + 1])
    insights = {language: _clean_insight_text(payload.get(language)) for language in INSIGHT_LANGUAGES}
    if not all(insights.values()):
        raise ValueError('AI response is missing a Chinese or English narrative')
    return insights

def get_chart_insight_logic(data):
    field_key = data.get("field_key", "")
    chart_data = data.get("data", {})
    fields = data.get("fields", [])
    mode_ai = data.get("mode_ai", "balanced")
    insight_language = data.get("language", "zh-TW")
    if insight_language not in INSIGHT_LANGUAGES:
        insight_language = "zh-TW"
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
    style_instruction = STYLE_PROMPTS.get(mode_ai, STYLE_PROMPTS["balanced"])
    prompt = f"""
                You are a professional medical and oncology data analysis expert.
                Produce matching Traditional Chinese and English narratives from the same
                cancer-registry chart data. Both versions must contain exactly the same
                facts, numbers, percentages, trends, level of certainty, and conclusions.
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
                6. Keep each language version within 130 words.
                7. When regenerating, vary sentence structure and presentation order while
                   preserving every number, percentage, trend, and conclusion supported by the data.
                8. Use Traditional Chinese for zh-TW and professional medical English for en.
                9. Return valid JSON only, without markdown or explanatory text, using exactly:
                   {{"zh-TW":"中文分析敘述","en":"English analysis narrative"}}
        """

    try:
        client, model_name = get_llm_client()
        response = client.chat.completions.create(
            model=model_name, 
            messages=[
                {"role": "system", "content": "You are a professional cancer-registry data analyst. Return valid bilingual JSON only."},
                {"role": "user", "content": prompt}
            ],temperature=0.5
        )
        content = response.choices[0].message.content
        insights = _parse_bilingual_insights(content)
        return {"success": True, "insight": insights[insight_language], "insights": insights}
    
    except Exception as e:
        logging.error(f"Error in AI analysis: {e}")
        return {"success": False, "error": str(e)}


def get_compare_insight_logic(data):
    analysis_item = str(data.get("analysis_item", "")).strip()
    comparison_direction = str(data.get("comparison_direction", "")).strip()
    selected_conditions = data.get("selected_conditions", {})
    baseline_data = data.get("baseline", {})
    comparison_data = data.get("comparison", {})
    total_difference = data.get("total_difference", {})
    mode_ai = data.get("mode_ai", "balanced")

    if not analysis_item or not isinstance(baseline_data, dict) or not isinstance(comparison_data, dict):
        return {"success": False, "error": "比較分析資料不完整"}

    style_instruction = STYLE_PROMPTS.get(mode_ai, STYLE_PROMPTS["balanced"])
    histology_no_data_instruction = ""
    if analysis_item == "組織型態":
        histology_no_data_instruction = """
                [Histology No-Data Rule]
                This rule overrides any general requirement to compare both datasets.
                Evaluate the baseline and comparison histology datasets separately. Keep a
                normal factual narrative for every side that contains valid histology data.
                For a side whose histology data is empty or has zero cases, use only that
                side's no_data_reason to explain the absence of data. If its reason is that
                the records do not meet the case-classification criteria, state that no
                eligible cases are available for that side. When only one side has data,
                describe that side's distribution but do not claim a difference, trend, or
                comparison against the side with no data. If both sides have no data, report
                their reasons only. Never generate clinical explanations or unsupported
                inferences for a side with no eligible cases.
            """
    prompt = f"""
                You are a professional medical and oncology data comparison expert.
                Compare the baseline and comparison cancer registry datasets below.
                [Analysis Item]{analysis_item}
                [Comparison Direction]{comparison_direction}
                [Selected Conditions]{json.dumps(selected_conditions, ensure_ascii=False)}
                [Baseline Data]{json.dumps(baseline_data, ensure_ascii=False)}
                [Comparison Data]{json.dumps(comparison_data, ensure_ascii=False)}
                [Calculated Differences]{json.dumps(total_difference, ensure_ascii=False)}
                [Writing Style]{style_instruction}

                [Comparison Requirements]
                1. State the principal difference between the comparison and baseline data.
                2. Describe the most important distribution or trend differences supported by both datasets.
                3. Use the baseline as the reference and keep the comparison direction consistent.
                4. Mention zero counts or missing values when they materially limit comparison.

                Notes:
                1. Reply without an opening remark or greeting.
                2. Base every conclusion strictly on the two supplied datasets.
                3. Do not infer unsupported causes or clinical outcomes.
                4. Do not confuse absolute differences with percentage differences.
                5. Keep the response within 160 words.
                {histology_no_data_instruction}
            """

    try:
        client, model_name = get_llm_client()
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are a professional cancer registry data comparison expert. Reply in Traditional Chinese."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        content = response.choices[0].message.content
        insight = re.sub(r'[*#`\n\t]+', '', content).strip()
        insight = insight.replace(r'\ge', '>=').replace(r'\le', '<=').replace(r'\neq', '!=').replace('$', '')
        return {"success": True, "insight": insight}
    except Exception as e:
        logging.error(f"Error in AI comparison analysis: {e}")
        return {"success": False, "error": str(e)}
