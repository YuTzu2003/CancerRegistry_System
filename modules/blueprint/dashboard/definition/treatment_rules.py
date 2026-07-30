"""癌症登記年報的治療方式判定規則。

``classify_treatment_items`` 接收已對應欄位名稱的 dict／pandas Series，並回傳
依年報規定排序的治療項目清單；``classify_treatments`` 則回傳以「、」串接的文字。
"""

TREATMENT_ORDER = [
    # 手術及肝癌手術例外：皆占用「手術」的排序位置。
    "TURP",
    "TURBT",
    "RFA",
    "TAE",
    "PEI",
    "RFA/TAE/PEI混合治療",
    "Other method of local tumor destruction",
    "手術",
    # 其他治療依年報指定順序。
    "放療",
    "TACE",
    "化療",
    "荷爾蒙",
    "類固醇治療",
    "免疫",
    "骨髓/幹細胞移植",
    "內分泌處置",
    "標靶",
    "其他治療",
    "密切觀察或不予治療",
    "待確認",
]

SURGERY_RANGES = [(20, 90), (200, 900)]
SURGERY_EXCEPTIONS = (
    ("C619", [(21, 23), (25, 25), (210, 230), (250, 250)], "TURP"),
    ("C67", [(27, 27), (270, 270)], "TURBT"),
    ("C22", [(15, 15), (150, 150)], "TAE"),
    ("C22", [(16, 16), (160, 160)], "PEI"),
    ("C22", [(17, 17), (170, 170)], "RFA"),
    ("C22", [(18, 18), (180, 180)], "RFA/TAE/PEI混合治療"),
    ("C22", [(19, 19), (190, 190)], "Other method of local tumor destruction"),
)

CHEMOTHERAPY_RANGES = [(1, 13), (20, 21), (30, 31)]
TACE_ONLY_RANGES = [(4, 4)]
TACE_WITH_CHEMOTHERAPY_RANGES = [(5, 7)]
HORMONE_RANGES = [(1, 3), (20, 21), (30, 31)]
IMMUNOTHERAPY_RANGES = [(1, 7), (20, 23), (30, 33), (40, 41)]
STEM_CELL_TRANSPLANT_RANGES = [(10, 12), (20, 22), (25, 25), (40, 40), (50, 50)]
ENDOCRINE_PROCEDURE_RANGES = [(30, 30)]
TARGETED_THERAPY_RANGES = [(1, 1), (20, 21), (30, 31)]
OTHER_TREATMENT_RANGES = [(1, 3)]
LYMPHOID_HISTOLOGY_RANGES = [(9590, 9993)]

RADIOTHERAPY_DRT_EXCLUDED = {"", "0", "00000000", "88888888", "99999999"}
RADIOTHERAPY_STATUS_CODES = {"0", "00", "6", "09", "10"}
OBSERVATION_OR_NO_TREATMENT_CODE = "00000000"
TREATMENT_CONFLICT_LABEL = "待確認"


def normalize_text(value):
    """保留代碼前導零，並處理 Excel 將代碼讀成 ``20.0`` 的情況。"""
    if value is None:
        return ""
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return ""
    return text[:-2] if text.endswith(".0") else text


def normalize_number(value):
    """將數字代碼轉為整數；組織型態 ``9590/3`` 也可正確取得 9590。"""
    text = normalize_text(value).split("/", 1)[0]
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def in_ranges(value, ranges):
    code = normalize_number(value)
    return code is not None and any(start <= code <= end for start, end in ranges)


def site_starts_with(site, prefix):
    return normalize_text(site).upper().startswith(prefix)


def has_any_code(value_o, value_h, ranges):
    return in_ranges(value_o, ranges) or in_ranges(value_h, ranges)


def classify_surgery_items(site, optype_o, optype_h):
    """判定手術及特殊局部治療；特殊項目不會同時被列為一般手術。"""
    exceptions = {
        label
        for site_prefix, ranges, label in SURGERY_EXCEPTIONS
        if site_starts_with(site, site_prefix) and has_any_code(optype_o, optype_h, ranges)
    }
    if exceptions:
        return exceptions
    return {"手術"} if has_any_code(optype_o, optype_h, SURGERY_RANGES) else set()


def classify_chemotherapy_items(site, chem_o, chem_h):
    """肝癌的 TACE 例外優先於一般化療判定。"""
    if site_starts_with(site, "C22"):
        if has_any_code(chem_o, chem_h, TACE_WITH_CHEMOTHERAPY_RANGES):
            return {"TACE", "化療"}
        if has_any_code(chem_o, chem_h, TACE_ONLY_RANGES):
            return {"TACE"}
    return {"化療"} if has_any_code(chem_o, chem_h, CHEMOTHERAPY_RANGES) else set()


def has_radiotherapy(drt_1st, rtstatus):
    """符合 drt_1st 或 rtstatus 任一條件即列為放療。"""
    return (
        normalize_text(drt_1st) not in RADIOTHERAPY_DRT_EXCLUDED
        or normalize_text(rtstatus) in RADIOTHERAPY_STATUS_CODES
    )


def is_observation_or_no_treatment(dtrt_1st):
    return normalize_text(dtrt_1st) == OBSERVATION_OR_NO_TREATMENT_CODE


def is_prostate_turp_and_surgery_combination(site, optype_o, optype_h):
    """首次療程表專用：外院 TURP（22）且本院一般手術（30）同時存在。"""
    return (
        site_starts_with(site, "C619")
        and normalize_number(optype_o) == 22
        and normalize_number(optype_h) == 30
    )


def classify_treatment_items(record):
    """依全部規則回傳排序後的治療項目清單。

    record 需提供下列標準鍵：site、hist、optype_o、optype_h、drt_1st、
    rtstatus、chem_o、chem_h、horm_o、horm_h、immu_o、immu_h、htep_h、
    target_o、target_h、other、dtrt_1st。
    """
    treatments = set()
    get = record.get

    treatments.update(classify_surgery_items(get("site"), get("optype_o"), get("optype_h")))

    if has_radiotherapy(get("drt_1st"), get("rtstatus")):
        treatments.add("放療")

    treatments.update(classify_chemotherapy_items(get("site"), get("chem_o"), get("chem_h")))

    hormone_given = has_any_code(get("horm_o"), get("horm_h"), HORMONE_RANGES)
    if hormone_given:
        if in_ranges(get("hist"), LYMPHOID_HISTOLOGY_RANGES):
            treatments.add("類固醇治療")
        else:
            treatments.add("荷爾蒙")

    if has_any_code(get("immu_o"), get("immu_h"), IMMUNOTHERAPY_RANGES):
        treatments.add("免疫")

    if in_ranges(get("htep_h"), STEM_CELL_TRANSPLANT_RANGES):
        treatments.add("骨髓/幹細胞移植")

    if in_ranges(get("htep_h"), ENDOCRINE_PROCEDURE_RANGES):
        treatments.add("內分泌處置")

    if has_any_code(get("target_o"), get("target_h"), TARGETED_THERAPY_RANGES):
        treatments.add("標靶")

    if in_ranges(get("other"), OTHER_TREATMENT_RANGES):
        treatments.add("其他治療")

    # DTRT_1ST 為 00000000 時，理論上不應存在任何首次癌症治療。
    # 若治療欄位仍符合其他定義，保留資料矛盾訊號，供年報表格另外列示或追查。
    if is_observation_or_no_treatment(get("dtrt_1st")):
        if treatments:
            return [TREATMENT_CONFLICT_LABEL]
        return ["密切觀察或不予治療"]

    return [item for item in TREATMENT_ORDER if item in treatments]


def classify_first_course_treatment_items(record):
    """回傳「期別與首次療程」表專用的治療組合。

    攝護腺 C619 個案在外院術式為 22、申報醫院術式為 30 時，同時列示
    TURP 與手術。若 DTRT_1ST 為 00000000 卻仍有治療，則標示為待確認。
    """
    normalized_record = dict(record)
    observation_or_no_treatment = is_observation_or_no_treatment(
        normalized_record.get("dtrt_1st")
    )
    # 先排除觀察碼，以辨識是否同時出現其他治療欄位。
    normalized_record["dtrt_1st"] = ""
    treatments = set(classify_treatment_items(normalized_record))

    if is_prostate_turp_and_surgery_combination(
        normalized_record.get("site"),
        normalized_record.get("optype_o"),
        normalized_record.get("optype_h"),
    ):
        treatments.update({"TURP", "手術"})

    if observation_or_no_treatment:
        return [TREATMENT_CONFLICT_LABEL] if treatments else ["密切觀察或不予治療"]

    return [item for item in TREATMENT_ORDER if item in treatments]


def classify_treatments(record):
    """回傳供圖表統計使用、以「、」分隔的治療分類文字。"""
    return "、".join(classify_treatment_items(record))


def classify_first_course_treatments(record):
    """回傳供「期別與首次療程」表使用、以「、」分隔的治療分類文字。"""
    return "、".join(classify_first_course_treatment_items(record))
