"""Build the hospital-approved benchmark summary from report tables."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .models import ReportTable


@dataclass(frozen=True)
class SummaryItem:
    cancer: str
    stages: str


_ORDER = (
    "大腸癌",
    "直腸癌",
    "子宮頸癌",
    "子宮體癌",
    "卵巢癌",
    "乳癌",
    "肺腺癌",
    "肺鱗癌",
    "小細胞肺癌",
    "食道癌",
    "肝癌",
    "鼻咽癌",
    "口腔癌",
    "下咽癌",
    "喉癌",
    "p16(-) 口咽癌",
    "攝護腺癌",
)

_CHINESE_NUMBER = {
    "0": "零",
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
    "9": "九",
    "10": "十",
}


def _compact(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value or ""))


def _summary_cancer(table: ReportTable) -> str | None:
    cancer = _compact(table.cancer).lower()
    staging = _compact(table.staging_system).lower()
    if "大腸癌-all" in cancer or "大腸癌all" in cancer:
        return None
    if "大腸癌-結腸癌" in cancer or cancer == "結腸癌":
        return "大腸癌"
    if "大腸癌-直腸癌" in cancer or cancer == "直腸癌":
        return "直腸癌"
    if "子宮頸癌" in cancer:
        return "子宮頸癌"
    if "子宮體癌" in cancer:
        return "子宮體癌"
    if "卵巢癌" in cancer:
        return "卵巢癌"
    if "乳癌" in cancer:
        return "乳癌"
    if "非小細胞癌-all" in cancer or "非小細胞癌all" in cancer:
        return None
    if "腺癌" in cancer and "肺" in cancer:
        return "肺腺癌"
    if ("鱗狀" in cancer or "鱗癌" in cancer) and "肺" in cancer:
        return "肺鱗癌"
    if "小細胞" in cancer and "肺" in cancer:
        return "小細胞肺癌"
    if "食道癌" in cancer:
        return "食道癌"
    if "肝癌" in cancer:
        return "肝癌" if staging == "bclc" else None
    if "鼻咽癌" in cancer:
        return "鼻咽癌"
    if "口腔癌" in cancer:
        return "口腔癌"
    if "下咽癌" in cancer:
        return "下咽癌"
    if cancer == "喉癌" or cancer.endswith("-喉癌"):
        return "喉癌"
    if "口咽癌" in cancer and ("p16-" in cancer or "p16(-)" in cancer):
        return "p16(-) 口咽癌"
    if "攝護腺癌" in cancer or "前列腺癌" in cancer:
        return "攝護腺癌"
    return None


def _stage_token(stage: str) -> str | None:
    value = _compact(stage)
    if value.startswith("不分期別") or value in {"全期", "全期*"}:
        return "full"
    match = re.fullmatch(r"第?([0-9]+|[一二三四五六七八九十]+)([A-D]?)(M[01])?期", value, re.I)
    if match:
        number, suffix, metastasis = match.groups()
        return f"{number.upper()}|{suffix.upper()}|{(metastasis or '').upper()}"
    match = re.fullmatch(r"第?([A-D])期", value, re.I)
    if match:
        return f"bclc|{match.group(1).upper()}"
    return None


def _token_sort_key(token: str) -> tuple[int, str, str]:
    if token == "full":
        return (99, "", "")
    if token.startswith("bclc|"):
        return (50, token, "")
    number, suffix, metastasis = token.split("|")
    arabic = next((key for key, value in _CHINESE_NUMBER.items() if value == number), number)
    try:
        numeric = int(arabic)
    except ValueError:
        numeric = 40
    return (numeric, suffix, metastasis)


def _stage_label(token: str) -> str:
    if token == "full":
        return "全期 *"
    if token.startswith("bclc|"):
        return f"BCLC-{token.split('|', 1)[1]}"
    number, suffix, metastasis = token.split("|")
    number_label = _CHINESE_NUMBER.get(number, number)
    if suffix:
        base = f"第 {number}{suffix} 期"
    else:
        base = f"第{number_label}期"
    return f"{base} {metastasis}" if metastasis else base


def _format_stage_group(cancer: str, tokens: set[str]) -> str:
    ordered = sorted(tokens, key=_token_sort_key)
    if cancer in {"口腔癌", "下咽癌"}:
        grouped: list[str] = []
        used: set[str] = set()
        by_base: dict[tuple[str, str], list[str]] = {}
        for token in ordered:
            if token == "full" or token.startswith("bclc|"):
                continue
            number, suffix, metastasis = token.split("|")
            by_base.setdefault((number, suffix), []).append(metastasis)
        for token in ordered:
            if token in used:
                continue
            if token == "full" or token.startswith("bclc|"):
                grouped.append(_stage_label(token))
                used.add(token)
                continue
            number, suffix, _ = token.split("|")
            related = [
                item for item in ordered
                if item != "full" and not item.startswith("bclc|")
                and item.split("|")[:2] == [number, suffix]
            ]
            used.update(related)
            base = _stage_label(f"{number}|{suffix}|")
            metastases = [item.split("|")[2] for item in related if item.split("|")[2]]
            grouped.append(f"{base}（{'、'.join(metastases)}）" if metastases else base)
        return "、".join(grouped)
    labels = [_stage_label(token) for token in ordered]
    if len(labels) == 2 and cancer in {"大腸癌", "食道癌", "肺腺癌"}:
        return "及".join(labels)
    return "、".join(labels)


def build_benchmark_summary(tables: tuple[ReportTable, ...]) -> tuple[SummaryItem, ...]:
    """Return stages where the primary hospital outperforms medical centers."""
    grouped: dict[str, dict[str, set[str]]] = {}
    for table in tables:
        cancer = _summary_cancer(table)
        if cancer is None:
            continue
        staging = _compact(table.staging_system).upper() or "AJCC"
        for row in table.rows:
            primary = table.hospital_value(row, table.primary_hospital_key).estimate
            benchmark = row.medical_center
            if not primary.available or not benchmark.available or primary.rate <= benchmark.rate:
                continue
            token = _stage_token(row.stage)
            if token is not None:
                grouped.setdefault(cancer, {}).setdefault(staging, set()).add(token)

    items: list[SummaryItem] = []
    for cancer in _ORDER:
        systems = grouped.get(cancer)
        if not systems:
            continue
        if cancer in {"子宮體癌", "卵巢癌"}:
            parts = []
            for system in ("AJCC", "FIGO"):
                if not systems.get(system):
                    continue
                stage_text = _format_stage_group(cancer, systems[system])
                if cancer == "卵巢癌" and system == "AJCC" and len(systems[system]) == 2:
                    stage_text = stage_text.replace("、", "及", 1)
                parts.append(f"{system} {stage_text}")
            stages = "；".join(parts)
        else:
            tokens = set().union(*systems.values())
            stages = _format_stage_group(cancer, tokens)
        if stages:
            items.append(SummaryItem(cancer, stages))
    return tuple(items)
