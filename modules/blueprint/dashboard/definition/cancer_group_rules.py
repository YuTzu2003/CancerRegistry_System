COMMON_SOLID_HIST_EXCLUDE = ["9140", "9590-9993"]

def subgroup(key, name_zh, name_en="", **conditions):
    rule = {"key": key, "name_zh": name_zh, "name_en": name_en}
    rule.update({k: v for k, v in conditions.items() if v not in (None, [], {})})
    return rule

def solid_rule(key, name_zh, name_en, site_prefixes, *, site_exclude=None, subgroups=None):
    return {
        "key": key,
        "name_zh": name_zh,
        "name_en": name_en,
        "site_prefixes": site_prefixes,
        "site_exclude": site_exclude or [],
        "hist_exclude": COMMON_SOLID_HIST_EXCLUDE,
        "subgroups": subgroups or []
    }

def blood_rule(key, name_zh, name_en, *, hist_include=None, subgroups=None):
    return {
        "key": key,
        "name_zh": name_zh,
        "name_en": name_en,
        "hist_include": hist_include or [],
        "subgroups": subgroups or [],
        "requires_subgroup_match": bool(subgroups) and not hist_include
    }

# ===== 實體癌 Solid cancers =====

# 口腔癌 Oral Cavity
ORAL_CAVITY = solid_rule(
    "Oral_Cavity",
    "口腔癌",
    "Oral Cavity",
    ["C00", "C02", "C03", "C04", "C05", "C06"],
    site_exclude=["C024", "C051", "C052"]
)

# 口咽癌 Oropharynx
OROPHARYNX = solid_rule(
    "Oropharynx",
    "口咽癌",
    "Oropharynx",
    ["C01", "C024", "C051", "C052", "C09", "C10", "C142", "C148"],
    subgroups=[
        subgroup(
            "oropharynx_p16_positive",
            "口咽癌 P16+",
            "Oropharynx (P16+)",
            min_didiag_year=2018,
            field_equals={"ajcc_ed": ["08010"]}
        ),
        subgroup(
            "oropharynx_p16_negative",
            "口咽癌 P16-",
            "Oropharynx (P16-)",
            min_didiag_year=2018,
            field_equals={"ajcc_ed": ["08011"]}
        )
    ]
)

# 下咽癌 Hypopharynx
HYPOPHARYNX = solid_rule("Hypopharynx", "下咽癌", "Hypopharynx", ["C12", "C13", "C140"])

# 主唾液腺癌 Salivary Glands
SALIVARY_GLANDS = solid_rule("Salivary_Glands", "主唾液腺癌", "Salivary Glands", ["C07", "C08"])

# 鼻咽癌 Nasopharynx
NASOPHARYNX = solid_rule("Nasopharynx", "鼻咽癌", "Nasopharynx", ["C11"])

# 喉癌 Larynx
LARYNX = solid_rule("Larynx", "喉癌", "Larynx", ["C32"])

# 食道癌 Esophagus
ESOPHAGUS = solid_rule("Esophagus", "食道癌", "Esophagus", ["C15"])

# 胃癌 Stomach
STOMACH = solid_rule("Stomach", "胃癌", "Stomach", ["C16"])

# 結直腸癌 Colon and Rectum
COLON_AND_RECTUM = solid_rule(
    "Colorectal",
    "結直腸癌",
    "Colon and Rectum",
    ["C18", "C19", "C20"],
    subgroups=[
        subgroup("colon", "結腸癌", "Colon", site_prefixes=["C18"]),
        subgroup("rectum", "直腸癌", "Rectum", site_prefixes=["C19", "C20"])
    ]
)

# 肛門癌 Anus
ANUS = solid_rule("Anus", "肛門癌", "Anus", ["C21"])

# 肝癌 Liver
LIVER = solid_rule("Liver", "肝癌", "Liver", ["C220"])

# 胰臟癌 Pancreas
PANCREAS = solid_rule("Pancreas", "胰臟癌", "Pancreas", ["C25"])

# 肺癌 Lung and Bronchus
LUNG_AND_BRONCHUS = solid_rule(
    "Lung",
    "肺癌",
    "Lung and Bronchus",
    ["C34"],
    subgroups=[
        subgroup(
            "small_cell_carcinoma",
            "肺小細胞癌",
            "Small Cell Carcinoma",
            hist_include=["8002", "8041-8045"]
        ),
        subgroup(
            "adenocarcinoma",
            "肺腺癌",
            "Adenocarcinoma",
            hist_include=["8050", "8130", "8140-8141", "8143-8144", "8146", "8201", "8211", "8213", "8230", "8250-8257", "8260", "8262-8263", "8265", "8290", "8310", "8320", "8323", "8333", "8480-8481", "8490", "8503", "8550-8552", "8572"]
        ),
        subgroup(
            "squamous_cell_carcinoma",
            "肺鱗狀細胞癌",
            "Squamous Cell Carcinoma",
            hist_include=["8051-8052", "8070-8076", "8083-8084"]
        )
    ]
)

# 乳癌 Breast
BREAST = solid_rule(
    "breast",
    "乳癌",
    "Breast",
    ["C50"],
    subgroups=[
        subgroup("breast_in_situ", "乳癌原位癌", "Breast in situ", behavior_include=["2"]),
        subgroup("breast_invasive", "乳癌侵襲癌", "Breast invasive", behavior_include=["3"])
    ]
)

# 子宮頸癌 Cervix Uteri
CERVIX_UTERI = solid_rule(
    "Cervix_Uteri",
    "子宮頸癌",
    "Cervix Uteri",
    ["C53"],
    subgroups=[
        subgroup("cervix_cin3_in_situ", "子宮頸 CIN3 及原位癌", "Cervix CIN3 and in situ", behavior_include=["2"]),
        subgroup("cervix_invasive", "子宮頸侵襲癌", "Cervix invasive", behavior_include=["3"])
    ]
)

# 子宮體癌 Corpus Uteri
CORPUS_UTERI = solid_rule("Corpus_Uteri", "子宮體癌", "Corpus Uteri", ["C54", "C55"])

# 卵巢癌 Ovary
OVARY = solid_rule("Ovary", "卵巢癌", "Ovary", ["C56"])

# 攝護腺癌 Prostate
PROSTATE = solid_rule("Prostate", "攝護腺癌", "Prostate", ["C619"])

# 膀胱癌 Bladder
BLADDER = solid_rule(
    "Bladder",
    "膀胱癌",
    "Bladder",
    ["C67"],
    subgroups=[
        subgroup("bladder_in_situ", "膀胱癌原位癌", "Bladder in situ", behavior_include=["2"]),
        subgroup("bladder_invasive", "膀胱癌侵襲癌", "Bladder invasive", behavior_include=["3"])
    ]
)

# ===== 血液淋巴癌 Hematologic cancers =====

# 惡性淋巴瘤 Lymphoma
LYMPHOMA = blood_rule(
    "Lymphoma",
    "惡性淋巴瘤",
    "Lymphoma",
    subgroups=[
        subgroup(
            "Hodgkin_lymphomahodgkin",
            "何杰金氏淋巴瘤",
            "Hodgkin lymphoma",
            hist_include=["9650-9653", "9659", "9661-9665", "9667"]
        ),
        subgroup(
            "B-cell_lymphoid_neoplasms",
            "B細胞淋巴系腫瘤",
            "B-cell lymphoid neoplasms",
            hist_include=["9689", "9699", "9671", "9761", "9597", "9675", "9690-9691", "9695", "9698", "9673", "9687", "9826", "9680", "9684", "9688", "9712", "9735", "9737", "9738", "9679", "9596", "9670", "9678", "9728", "9833", "9940"]
        ),
        subgroup(
            "T/NK-cell_lymphoid_neoplasms",
            "T/NK細胞淋巴系腫瘤",
            "T/NK-cell lymphoid neoplasms",
            hist_include=["9719", "9700", "9701", "9709", "9718", "9726", "9717", "9716", "9708", "9702", "9705", "9714", "9827", "9724", "9729", "9834", "9948"]
        ),
        subgroup("Plasma_cell_neoplasms", "漿細胞腫瘤", "Plasma cell neoplasms", hist_include=["9731-9734"]),
        subgroup(
            "Histiocytic_and_dendritic_cell_neoplasms",
            "組織球與樹突細胞腫瘤",
            "Histiocytic and dendritic cell neoplasms",
            hist_include=["9751", "9755-9759"]
        ),
        subgroup(
            "Malignant_lymphoma_NOS_and_others",
            "未分類及其他惡性淋巴瘤",
            "Malignant lymphoma, NOS and others",
            hist_include=["9590-9591", "9750", "9754", "9760", "9764"]
        )
    ]
)

# 白血病及骨髓瘤 Leukemia and myeloid neoplasm
LEUKEMIA_AND_MYELOID_NEOPLASM = blood_rule(
    "Leukemia_and_myeloid_neoplasm",
    "白血病及骨髓瘤",
    "Leukemia and myeloid neoplasm",
    subgroups=[
        subgroup(
            "AML",
            "急性骨髓性白血病",
            "Acute myeloid leukemia (AML)",
            hist_include=["9865", "9866", "9869", "9871", "9896", "9897", "9911", "9895", "9920", "9861", "9840", "9867" "9870", "9872-9874", "9891", "9910", "9931", "9930", "9898", "9727"]
        ),
        subgroup(
            "ALL",
            "急性淋巴性白血病",
            "Acute lymphoblastic leukemia (ALL)",
            hist_include=["9811-9818", "9835-9836", "9837"]
        ),
        subgroup(
            "CML",
            "慢性骨髓性白血病",
            "Chronic myeloid leukemia (CML, BCR-ABL1-positive)",
            hist_include=["9875"]
        ),
        subgroup("CLL", "慢性淋巴性白血病", "Chronic lymphocytic leukemia (CLL)", hist_include=["9823"]),
        subgroup(
            "Acute_leukemias_of_ambiguous_lineage",
            "系統歧異不明之急性白血病",
            "Acute leukemias of ambiguous lineage",
            hist_include=["9801", "9806-9809"]
        ),
        subgroup(
            "Myeloproliferative_neoplasms",
            "骨髓增生性腫瘤",
            "Myeloproliferative neoplasms",
            hist_include=["9740-9742", "9945", "9863", "9876", "9946", "9950", "9960", "9961-9967", "99753"]
        ),
        subgroup(
            "Myelodysplastic_syndromes",
            "骨髓發育不良症候群",
            "Myelodysplastic syndromes",
            hist_include=["9980", "9982-9987", "9989", "9991", "9992"]
        ),
        subgroup(
            "Acute_biphenotypic_leukemia",
            "急性雙表型白血病",
            "Acute biphenotypic leukemia",
            hist_include=["9805"]
        ),
        subgroup("Other_Leukemia", "其他白血病", "Other Leukemia", hist_include=["9820", "9832", "9860"]),
        subgroup("Leukemia", "未分類白血病", "Leukemia, NOS", hist_include=["9800"])
    ]
)

CANCER_GROUP_RULES = [
    ORAL_CAVITY,
    OROPHARYNX,
    HYPOPHARYNX,
    SALIVARY_GLANDS,
    NASOPHARYNX,
    LARYNX,
    ESOPHAGUS,
    STOMACH,
    COLON_AND_RECTUM,
    ANUS,
    LIVER,
    PANCREAS,
    LUNG_AND_BRONCHUS,
    BREAST,
    CERVIX_UTERI,
    CORPUS_UTERI,
    OVARY,
    PROSTATE,
    BLADDER,
    LYMPHOMA,
    LEUKEMIA_AND_MYELOID_NEOPLASM
]