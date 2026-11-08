"""Recalculate observed survival for the 108–112 feedback cohort."""

from collections import Counter, defaultdict
from math import isfinite, prod

from openpyxl import load_workbook

WEIGHTS = {
    "Oral cavity": ("口腔癌", (17.3, 32.6, 29.7, 13.0, 7.4)),
    "Oropharynx": ("口咽癌", (14.5, 36.6, 30.9, 12.4, 5.6)),
    "Hypopharynx": ("下咽癌", (10.3, 34.5, 32.6, 14.5, 8.1)),
    "Nasopharynx": ("鼻咽癌", (28.6, 30.7, 26.5, 9.1, 5.1)),
    "Colon and Rectum": ("大腸癌", (6.3, 14.0, 25.5, 24.0, 30.2)),
    "Liver": ("肝癌", (5.7, 14.9, 27.7, 26.7, 25.0)),
    "Pancreas": ("胰臟癌", (4.8, 13.5, 22.2, 26.6, 32.9)),
    "Lung": ("肺癌", (4.2, 12.7, 24.8, 25.1, 33.2)),
    "Breast": ("乳癌", (20.2, 32.3, 27.6, 12.8, 7.1)),
    "Cervix": ("子宮頸癌", (19.9, 25.8, 22.7, 13.7, 17.9)),
    "Esophagus": ("食道癌", (9.5, 32.5, 30.9, 14.6, 12.5)),
    "Stomach": ("胃癌", (5.2, 12.1, 21.0, 22.3, 39.4)),
    "Bladder": ("膀胱癌", (2.6, 9.5, 22.9, 24.7, 40.3)),
    "Corpus": ("子宮體癌", (16.7, 32.3, 35.0, 10.3, 5.7)),
    "Ovary": ("卵巢癌", (26.6, 28.8, 26.3, 9.6, 8.7)),
    "Prostate": ("攝護腺癌", (2.2, 17.0, 34.9, 34.7, 11.2)),
    "Larynx": ("喉癌", (5.1, 22.9, 33.0, 22.3, 16.7)),
}


def _survival(cases, month):
    if not any(time >= month for time, _ in cases):
        return None
    deaths = Counter(time for time, died in cases if died and time <= month)
    return prod(
        1 - count / sum(time >= event for time, _ in cases)
        for event, count in deaths.items()
    )


def _km_median_survival(cases):
    """KM median survival time with Brookmeyer-Crowley interpolation at S=0.5."""
    deaths = Counter(time for time, died in cases if died)
    if not deaths:
        return None
    survival = 1.0
    hit_half = None
    for event_time in sorted(deaths.keys()):
        d = deaths[event_time]
        n = sum(1 for time, _ in cases if time >= event_time)
        survival *= (1 - d / n)
        if abs(survival - 0.5) < 1e-10:
            hit_half = event_time
        elif survival < 0.5:
            if hit_half is not None:
                return round((hit_half + event_time) / 2, 1)
            return round(event_time, 1)
    if hit_half is not None:
        return round(hit_half, 1)
    return None


def _km_with_ci(cases, month):
    """KM estimate at *month* with 95 % CI (Greenwood)."""
    if not any(time >= month for time, _ in cases):
        return None, None, None
    deaths = Counter(time for time, died in cases if died and time <= month)
    survival = 1.0
    greenwood_sum = 0.0
    for event_time in sorted(deaths.keys()):
        d = deaths[event_time]
        n = sum(1 for time, _ in cases if time >= event_time)
        survival *= (1 - d / n)
        if n > d:
            greenwood_sum += d / (n * (n - d))
    if survival <= 0:
        return 0.0, 0.0, 0.0
    se = survival * greenwood_sum ** 0.5
    return survival, max(0, survival - 1.96 * se), min(1, survival + 1.96 * se)


_FIGO_CANCERS = {"Cervix", "Corpus", "Ovary"}
_BCLC_CANCERS = {"Liver"}
_BCLC_STAGES = ("all", "0", "A", "B", "C", "D", "999")
_AJCC_STAGES = ("all", "1", "2", "3", "4", "999")


def recalculate_cases(stream):
    required = ("hospid", "year", "pri_site", "fnstage", "select_memo", "age", "Status_OS", "Surv_Months")
    workbook = load_workbook(stream, read_only=True, data_only=True)
    try:
        rows = workbook.active.values
        headers = next(rows, ())
        if not all(field in headers for field in required):
            raise ValueError("工作表缺少必要欄位，請上傳存活率個案清單。")
        columns = [headers.index(field) for field in required]
        has_fnostage = "fnostage" in headers
        fnostage_col = headers.index("fnostage") if has_fnostage else None
        matched = Counter()
        cases = defaultdict(list)
        for row in rows:
            hospital, year, cancer, stage, memo, age, status, months = (
                str(row[column]).strip() for column in columns
            )
            if (hospital.lstrip("0") != "439010518" or year not in {"108", "109", "110", "111", "112"}
                    or cancer not in WEIGHTS):
                continue
            systems = []
            if stage.startswith(("1", "2", "3", "4", "999")):
                systems.append(("AJCC", stage[0] if stage != "999" else "999"))
            if has_fnostage and cancer in _FIGO_CANCERS:
                fno = str(row[fnostage_col] or "").strip()
                if not fno or fno == "None":
                    fno = "999"
                if fno == "999":
                    systems.append(("FIGO", "999"))
                elif fno[0] in "1234":
                    systems.append(("FIGO", fno[0]))
            elif has_fnostage and cancer in _BCLC_CANCERS:
                fno = str(row[fnostage_col] or "").strip().upper()
                if not fno or fno == "NONE":
                    fno = "999"
                if fno in ("0", "A", "B", "C", "D"):
                    systems.append(("BCLC", fno))
                elif fno == "999":
                    systems.append(("BCLC", "999"))
            if not systems:
                continue
            for sys, sk in systems:
                matched[(cancer, sys, "all")] += 1
                matched[(cancer, sys, sk)] += 1
            if not memo.startswith("15_"):
                continue
            try:
                age, months = int(age), float(months)
            except ValueError:
                raise ValueError("納入個案的年齡或追蹤月數格式有誤。") from None
            status = status.casefold()
            if age < 15 or not isfinite(months) or months < 0 or status not in {"death", "censor"}:
                raise ValueError("納入個案的年齡、追蹤月數或存活狀態超出試算範圍。")
            for sys, sk in systems:
                for key in [(cancer, sys, "all"), (cancer, sys, sk)]:
                    cases[key].append((age, months, status == "death"))
    finally:
        workbook.close()

    if not matched:
        raise ValueError("找不到符合試算條件的納入個案。")

    def _systems_for(cancer):
        out = [("AJCC", _AJCC_STAGES)]
        if has_fnostage:
            if cancer in _FIGO_CANCERS:
                out.append(("FIGO", _AJCC_STAGES))
            elif cancer in _BCLC_CANCERS:
                out.append(("BCLC", _BCLC_STAGES))
        return out

    return [
        (name, [
            (sys, [
                _summarize(cancer, stg, matched[(cancer, sys, stg)], cases[(cancer, sys, stg)])
                for stg in stage_order if matched[(cancer, sys, stg)]
            ])
            for sys, stage_order in _systems_for(cancer)
            if matched[(cancer, sys, "all")]
        ])
        for cancer, (name, _) in WEIGHTS.items()
    ]


def _summarize(cancer, stage, matched, cases):
    follow_up = [(months, died) for _, months, died in cases]
    annual = [_survival(follow_up, year * 12) for year in range(1, 6)]
    yearly = []
    n_remaining = len(follow_up)
    for year in range(1, 6):
        lo, hi = (year - 1) * 12, year * 12
        d = sum(1 for t, died in follow_up if died and (t <= hi if year == 1 else lo < t <= hi))
        c = sum(1 for t, died in follow_up if not died and (t <= hi if year == 1 else lo < t <= hi))
        rate, ci_lo, ci_hi = _km_with_ci(follow_up, hi)
        yearly.append({"n_start": n_remaining, "deaths": d, "censored": c,
                        "rate": rate, "ci_lower": ci_lo, "ci_upper": ci_hi})
        n_remaining -= d + c
    med_months = _km_median_survival(follow_up)
    limits = (55, 65, 75, 85) if cancer == "Prostate" else (45, 55, 65, 75)
    groups = []
    lower = 15
    for upper, weight in zip((*limits, None), WEIGHTS[cancer][1]):
        members = [(months, died) for age, months, died in cases if age >= lower and (upper is None or age < upper)]
        groups.append((lower, upper, weight, members))
        lower = upper
    def label(lower, upper):
        return f"{lower}+" if upper is None else f"{lower}–{upper - 1}"

    age_counts = [(label(lo, hi), len(members)) for lo, hi, _, members in groups]
    # Pilot rule: merge the first undersized group upward when possible.
    while len(groups) > 1:
        index = next((i for i, group in enumerate(groups) if len(group[3]) < 10), None)
        if index is None:
            break
        index = min(index, len(groups) - 2)
        lo, _, weight, members = groups[index]
        _, hi, next_weight, next_members = groups[index + 1]
        groups[index:index + 2] = [(lo, hi, weight + next_weight, members + next_members)]
    age_results = [
        (label(lo, hi), len(members), round(weight, 1), _survival(members, 60))
        for lo, hi, weight, members in groups
    ]
    adjusted = None
    if len(groups) > 1 and all(rate is not None for _, _, _, rate in age_results):
        adjusted = sum(weight * rate / 100 for _, _, weight, rate in age_results)
    return {
        "matched": matched, "included": len(cases),
        "first_year_deaths": sum(died and months <= 12 for months, died in follow_up),
        "annual": annual, "adjusted": adjusted, "age_results": age_results,
        "age_counts": age_counts, "stage": stage,
        "reference": cancer == "Bladder" and stage == "1",
        "yearly": yearly, "median_months": med_months,
    }
