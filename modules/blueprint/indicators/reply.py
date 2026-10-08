"""LLM narrative prompts and response handling for monitoring indicators."""

from __future__ import annotations

import json
import logging
import re

from modules.services.llm_service import request_llm_chat


INDICATOR_STYLE_PROMPTS = {
    "balanced": """
            Use a calm, neutral, and objective cancer quality-monitoring style and follow
            these rules:
            1. Begin the entire narrative with one short introductory sentence containing
               the supplied diagnosis period, cancer name, and included_case_count, such as
               "2018至2024年共納入134例乳癌個案。" State this information only once.
            2. Write one concise sentence per indicator. Focus on the indicator name,
               monitoring percentage, numerator and denominator in the compact form
               "（分子/分母）", configured threshold, and threshold status.
            3. Do not routinely explain the positive or negative direction or the full
               selection_reason. Include a short reason only when it is necessary to
               understand what the indicator measures.
            4. Keep the tone neutral, natural, and readable. Avoid formal-report phrases,
               repetitive introductions, praise, criticism, recommendations, or causal
               inference.
            5. When year-by-year monitoring values are supplied, objectively describe the
               increase, decrease, or stability across years. If those values are absent,
               do not invent or imply a cross-year trend.
        """,
    "formal": """
            Use a formal cancer quality-monitoring report style and follow these rules:
            Begin the entire narrative with one introductory sentence stating that the
            analysis is based on cancer-registry database data for the supplied diagnosis
            period. Use a natural Traditional Chinese pattern such as
            "根據[診斷年度]年癌症登記資料庫分析，". State this information only once at the
            beginning of the entire narrative; do not repeat it for each indicator.
            After that introduction, write every indicator with the following fixed
            Traditional Chinese sentence structure. Preserve the wording and order as
            closely as possible; do not replace it with a looser summary:
            "指標「[indicator_name]」為[indicator_direction]，此指標[rewritten
            selection_reason]。統計結果為分子[numerator]例、分母[denominator]例，
            監測值[percentage]%，門檻值為[threshold]，判定為[threshold_status]。"
            Apply these additional requirements:
            1. Rewrite selection_reason into fluent, professional Traditional Chinese
               without changing its meaning and keep it within 50 Chinese characters.
            2. Numerator, denominator, percentage, threshold, and threshold status are all
               mandatory. Do not replace them with a general statement.
            3. Use the supplied indicator_direction exactly as 正向指標 or 負向指標.
            4. Prefer the fixed phrases "此指標" and "統計結果為". Do not change them to
               "其選取原因為", "監測結果顯示", or another alternative expression.
            5. When year-by-year monitoring values are supplied, append one formal sentence
               comparing whether the value increased, decreased, or remained stable. If
               those values are absent, do not invent or imply a cross-year trend.
        """,
    "concise": """
            Use a concise cancer quality-monitoring summary style and follow these rules:
            1. Do not write an introductory sentence or overall status counts; the system
               will add those automatically.
            2. Write exactly one compact fragment per indicator using this structure:
               "「[indicator_name]」[percentage]%（[numerator]/[denominator]，門檻
               [threshold]）". Join indicator fragments with Chinese semicolons and end the
               final fragment with a Chinese full stop.
            3. When percentage cannot be calculated, use:
               "「[indicator_name]」無法計算（[numerator]/[denominator]）".
            4. Do not state indicator direction, selection_reason, background, explanation,
               recommendation, praise, criticism, or a repeated threshold-status sentence.
            5. When year-by-year values are supplied, append only one brief overall trend
               clause. If those values are absent, do not invent or imply a trend.
        """,
}

def _clean_insight_text(value):
    text = re.sub(r"[*#`\n\t]+", "", str(value or "")).strip()
    return text.replace(r"\ge", ">=").replace(r"\le", "<=").replace(r"\neq", "!=").replace("$", "")


def _escape_invalid_json_backslashes(raw):
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", raw)


def _parse_chinese_insight(content):
    raw = str(content or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.IGNORECASE)
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        insight = _clean_insight_text(raw)
        if not insight:
            raise ValueError("AI response does not contain a Chinese narrative")
        return insight
    json_text = raw[start:end + 1]
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        if "Invalid \\escape" not in str(exc):
            raise
        payload = json.loads(_escape_invalid_json_backslashes(json_text))
    insight = _clean_insight_text(payload.get("zh-TW") or payload.get("zh") or payload.get("insight"))
    if not insight:
        raise ValueError("AI response is missing a Chinese narrative")
    return insight


_FORMAL_SCOPE_SENTENCE_RE = re.compile(
    r"根據\s*\d{4}\s*(?:年?\s*(?:至|到|[-–—~～])\s*\d{4})?\s*年?間?\s*"
    r"癌症(?:登記|登錄)資料庫(?:資料|數據)?(?:進行)?(?:分析|統計)?(?:結果)?(?:顯示)?\s*[，,：:]?\s*"
)


def _normalize_formal_scope_sentence(insight, year_start, year_end):
    """Keep the diagnosis-period/database scope statement once at the beginning."""
    start = str(year_start or "").strip()
    end = str(year_end or "").strip()
    if not start and not end:
        return insight

    period = start or end
    if start and end and start != end:
        period = f"{start}至{end}"

    body = _FORMAL_SCOPE_SENTENCE_RE.sub("", insight).strip(" ，,")
    return f"根據{period}年癌症登錄資料庫分析，{body}"


_BALANCED_SCOPE_SENTENCE_RE = re.compile(
    r"(?:根據\s*)?\d{4}\s*(?:年?\s*(?:至|到|[-–—~～])\s*\d{4})?\s*年?間?\s*"
    r"(?:癌症(?:登記|登錄)資料庫(?:資料|數據)?(?:分析)?\s*[，,]?\s*)?"
    r"(?:本次)?(?:共)?納入\s*\d+\s*例[^。「」；，]{0,20}個案[。；，]?\s*"
)


def _normalize_balanced_scope_sentence(insight, year_start, year_end, chart_data):
    """Create one short balanced-style scope sentence at the start of the narrative."""
    start = str(year_start or "").strip()
    end = str(year_end or "").strip()
    cancer = str(chart_data.get("cancer") or "").strip() if isinstance(chart_data, dict) else ""
    included = chart_data.get("included_case_count") if isinstance(chart_data, dict) else None
    if not (start or end) or included in (None, ""):
        return insight

    period = start or end
    if start and end and start != end:
        period = f"{start}至{end}"
    try:
        included_text = str(int(float(included)))
    except (TypeError, ValueError):
        included_text = str(included).strip()

    body = _BALANCED_SCOPE_SENTENCE_RE.sub("", insight)
    body = _FORMAL_SCOPE_SENTENCE_RE.sub("", body).strip(" ，,")
    return f"{period}年共納入{included_text}例{cancer}個案。{body}"


_CONCISE_SCOPE_SENTENCE_RE = re.compile(
    r"^\s*\d{4}\s*(?:年?\s*(?:至|到|[-–—~～])\s*\d{4})?\s*年?間?\s*"
    r"[^。]{0,30}監測摘要[：:]?[^。]*。\s*"
)


def _normalize_concise_scope_sentence(insight, year_start, year_end, chart_data):
    """Prepend one deterministic status-count summary for concise narratives."""
    indicators = chart_data.get("indicators") if isinstance(chart_data, dict) else None
    if not isinstance(indicators, list) or not indicators:
        return insight

    start = str(year_start or "").strip()
    end = str(year_end or "").strip()
    cancer = str(chart_data.get("cancer") or "").strip()
    period = start or end
    if start and end and start != end:
        period = f"{start}至{end}"

    counts = {"達標": 0, "未達標": 0, "無法計算": 0}
    for indicator in indicators:
        status = str(indicator.get("threshold_status") or "").strip() if isinstance(indicator, dict) else ""
        if status in {"達標", "未達標"}:
            counts[status] += 1
        else:
            counts["無法計算"] += 1

    body = _CONCISE_SCOPE_SENTENCE_RE.sub("", insight)
    body = _BALANCED_SCOPE_SENTENCE_RE.sub("", body)
    body = _FORMAL_SCOPE_SENTENCE_RE.sub("", body).strip(" ，,")
    scope = f"{period}年" if period else ""
    summary = (
        f"{scope}{cancer}監測摘要：共{len(indicators)}項指標，"
        f"達標{counts['達標']}項、未達標{counts['未達標']}項、"
        f"無法計算{counts['無法計算']}項。"
    )
    return f"{summary}{body}"


def _quote_indicator_names(insight, chart_data):
    """Wrap every supplied indicator name in Traditional Chinese corner brackets."""
    indicators = chart_data.get("indicators") if isinstance(chart_data, dict) else None
    if not isinstance(indicators, list):
        return insight

    names = sorted(
        {
            str(indicator.get("indicator_name") or "").strip()
            for indicator in indicators
            if isinstance(indicator, dict) and str(indicator.get("indicator_name") or "").strip()
        },
        key=len,
        reverse=True,
    )
    for name in names:
        for opening, closing in (("「", "」"), ("『", "』"), ("“", "”"), ('"', '"')):
            insight = insight.replace(f"{opening}{name}{closing}", name)
    if not names:
        return insight
    name_pattern = re.compile("|".join(re.escape(name) for name in names))
    return name_pattern.sub(lambda match: f"「{match.group(0)}」", insight)


def get_indicator_insight_logic(data):
    field_key = str(data.get("field_key") or "監測指標分析")
    chart_data = data.get("data") if isinstance(data.get("data"), dict) else {}
    mode_ai = str(data.get("mode_ai") or "balanced")
    year_start = str(data.get("year_start") or "")
    year_end = str(data.get("year_end") or "")
    selected_year_range = f"{year_start}-{year_end}" if year_start and year_end else year_start or year_end or "Not specified"
    style_instruction = INDICATOR_STYLE_PROMPTS.get(mode_ai, INDICATOR_STYLE_PROMPTS["balanced"])

    prompt = f"""
                You are a professional cancer quality-monitoring data analyst.
                Produce one Traditional Chinese narrative from the supplied
                monitoring-indicator data.
                [Monitoring Topic]{field_key}
                [Diagnosis Period]{selected_year_range}
                [Indicator Data]{json.dumps(chart_data, ensure_ascii=False)}
                [Writing Style]{style_instruction}

                [Required Interpretation]
                1. Enclose every supplied indicator_name in Traditional Chinese corner
                   brackets exactly like "「指標名稱」" whenever it appears in the narrative.
                2. Report each supplied numerator, denominator, percentage, configured
                   threshold, and threshold status accurately.
                3. Clearly distinguish an unconfigured threshold from a failed threshold.
                4. Do not invent causes, clinical effectiveness, benchmarks, recommendations,
                   or cross-year trends not supported by the supplied data.
                5. Use professional Traditional Chinese only. Do not produce an English
                   translation or any English narrative.
                6. Return valid JSON only, without markdown or explanatory text, using exactly:
                   {{"zh-TW":"中文分析敘述"}}
        """

    try:
        content = request_llm_chat(
            [
                {
                    "role": "system",
                    "content": "You are a professional cancer quality-monitoring analyst. Return one Traditional Chinese narrative as valid JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )
        insight = _parse_chinese_insight(content)
        insight = _quote_indicator_names(insight, chart_data)
        if mode_ai == "formal":
            insight = _normalize_formal_scope_sentence(insight, year_start, year_end)
        elif mode_ai == "balanced":
            insight = _normalize_balanced_scope_sentence(insight, year_start, year_end, chart_data)
        elif mode_ai == "concise":
            insight = _normalize_concise_scope_sentence(insight, year_start, year_end, chart_data)
        return {"success": True, "insight": insight, "insights": {"zh-TW": insight}}
    except Exception as exc:
        logging.error("Error in monitoring-indicator AI analysis: %s", exc)
        return {"success": False, "error": str(exc)}
