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

def blood_rule(key, name_zh, name_en, *, site_prefixes=None, hist_include=None, subgroups=None):
    return {
        "key": key,
        "name_zh": name_zh,
        "name_en": name_en,
        "site_prefixes": site_prefixes or ["C000-C809"],
        "hist_include": hist_include or [],
        "subgroups": subgroups or [],
        "requires_subgroup_match": bool(subgroups) and not hist_include
    }

# ===== 實體癌 Solid cancers =====

# 口腔癌症(含口腔、口咽、下咽) Oral_group
ORAL_GROUP = solid_rule(
    "Oral_group",
    "口腔癌",
    "Oral group",
    ["C00-C06", "C09-C10", "C12-C14"],
    subgroups=[
        subgroup(
            "Oral_Cavity",
            "口腔癌",
            "Oral Cavity",
            site_prefixes=["C00", "C02", "C03", "C04", "C05", "C06"],
            site_exclude=["C024", "C051", "C052"]
        ),
        subgroup(
            "Oropharynx",
            "口咽癌",
            "Oropharynx",
            site_prefixes=["C01", "C024", "C051", "C052", "C09", "C10", "C142", "C148"],
            child_keys=[
                "oropharynx_p16_positive",
                "oropharynx_p16_negative",
            ]
        ),
        subgroup(
            "oropharynx_p16_positive",
            "口咽癌 P16+",
            "Oropharynx (P16+)",
            site_prefixes=["C01", "C024", "C051", "C052", "C09", "C10", "C142", "C148"],
            min_didiag_year=2018,
            field_equals={"ajcc_ed": ["08010"]}
        ),
        subgroup(
            "oropharynx_p16_negative",
            "口咽癌 P16-",
            "Oropharynx (P16-)",
            site_prefixes=["C01", "C024", "C051", "C052", "C09", "C10", "C142", "C148"],
            min_didiag_year=2018,
            field_equals={"ajcc_ed": ["08011"]}
        ),
        subgroup(
            "Hypopharynx",
            "下咽癌",
            "Hypopharynx",
            site_prefixes=["C12", "C13", "C140"]
        )
    ]
)

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

# 胰臟癌 Pancreas
PANCREAS = solid_rule("Pancreas", "胰臟癌", "Pancreas", ["C25"])

# 結腸、直腸及肛門癌 Colon and Rectum、Anus
COLON_AND_RECTUM_ANUS = solid_rule(
    "Colon_and_Rectum_Anus",
    "結腸、直腸及肛門癌",
    "Colon and Rectum、Anus",
    ["C18-C21"],
    subgroups=[
        subgroup(
            "Colon",
            "結腸癌",
            "Colon",
            site_prefixes=["C18"]
        ),
        subgroup(
            "Rectum",
            "直腸癌",
            "Rectum",
            site_prefixes=["C19", "C20"]
        ),
        subgroup(
            "Anus",
            "肛門癌",
            "Anus",
            site_prefixes=["C21"]
        )
    ]
)

# 肝及肝內膽管癌 Liver and Intrahepatic bile duct
LIVER_AND_INTRAHEPATIC_BILE_DUCT = solid_rule(
    "Liver_and_Intrahepatic_bile_duct",
    "肝及肝內膽管癌",
    "Liver and Intrahepatic bile duct",
    ["C220-C221"],
    subgroups=[
        subgroup(
            "Liver",
            "肝",
            "Liver",
            site_prefixes=["C220"]
        ),
        subgroup(
            "Intrahepatic_bile_duct",
            "肝內膽管",
            "Intrahepatic bile duct",
            site_prefixes=["C221"]
        )
    ]
)

# 乳癌 Breast
BREAST = solid_rule(
    "Breast",
    "乳癌",
    "Breast",
    ["C50"],
    subgroups=[
        subgroup(
            "Breast_Female",
            "女性乳房",
            "Breast (Female)",
            field_equals={"sex": [2]}
        ),
        subgroup(
            "Breast_Male",
            "男性乳癌",
            "Breast(Male)",
            field_equals={"sex": [1]}
        ),
        subgroup(
            "Breast_in_situ",
            "乳癌原位癌",
            "Breast in situ",
            behavior_include=["2"]
        ),
        subgroup(
            "Breast_invasive",
            "乳癌侵襲癌",
            "Breast invasive",
            behavior_include=["3"]
        )
    ]
)

# 肺、支氣管、氣管癌 Lung and Bronchus、Trachea
LUNG_AND_BRONCHUS = solid_rule(
    "Lung_and_Bronchus_Trachea",
    "肺、支氣管、氣管癌",
    "Lung and Bronchus、Trachea",
    ["C33-C34"],
    subgroups=[
        subgroup(
            "Trachea",
            "氣管",
            "Trachea",
            site_prefixes=["C33"]
        ),
        subgroup(
            "Lung_and_Bronchus",
            "肺、支氣管",
            "Lung and Bronchus",
            site_prefixes=["C34"]
        ),
        subgroup(
            "Small_cell_carcinoma",
            "肺小細胞癌",
            "Small Cell Carcinoma",
            site_prefixes=["C34"],
            hist_include=["8002", "8041-8045"]
        ),
        subgroup(
            "Adenocarcinoma",
            "肺腺癌",
            "Adenocarcinoma",
            site_prefixes=["C34"],
            hist_include=["8050", "8130", "8140-8141", "8143-8144", "8146", "8201", "8211", "8213", "8230", "8250-8257", "8260", "8262-8263", "8265", "8290", "8310", "8320", "8323", "8333", "8480-8481", "8490", "8503", "8550-8552", "8572"]
        ),
        subgroup(
            "Squamous_cell_carcinoma",
            "肺鱗狀細胞癌",
            "Squamous Cell Carcinoma",
            site_prefixes=["C34"],
            hist_include=["8051-8052", "8070-8076", "8083-8084"]
        )
    ]
)

# 子宮頸癌 Cervix Uteri
CERVIX_UTERI = solid_rule(
    "Cervix_Uteri",
    "子宮頸癌",
    "Cervix Uteri",
    ["C53"],
    subgroups=[
        subgroup(
            "Cervix_cin3_in_situ", 
            "子宮頸 CIN3 及原位癌", 
            behavior_include=["2"]
        ),
        subgroup(
            "Cervix_invasive", 
            "子宮頸侵襲癌", 
            behavior_include=["3"]
        )
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
        subgroup(
            "Bladder_in_situ",
            "膀胱癌原位癌",
            behavior_include=["2"]
        ),
        subgroup(
            "Bladder_invasive",
            "膀胱癌侵襲癌",
            behavior_include=["3"]
        )
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
            "Non_Hodgkin_lymphoma",
            "非何杰金氏淋巴瘤",
            "Non-Hodgkin lymphoma",
            child_keys=[
                "B-cell_lymphoid_neoplasms",
                "T/NK-cell_lymphoid_neoplasms",
                "Plasma_cell_neoplasms",
                "Histiocytic_and_dendritic_cell_neoplasms",
                "Malignant_lymphoma_NOS_and_others",
            ]
        ),
        subgroup(
            "B-cell_lymphoid_neoplasms",
            "B細胞淋巴系腫瘤",
            "B-cell lymphoid neoplasms",
            child_keys=[
                "Marginal_zone_lymphoma",
                "Lymphoplasmacytic_lymphoma",
                "Follicular_lymphoma",
                "Mantle_cell_lymphoma",
                "Burkitt_lymphoma",
                "Diffuse_large_B-cell_lymphoma",
                "Primary_mediastinal_large_B-cell_lymphoma",
                "Other_B-cell_lymphomas",
            ]
        ),
        subgroup(
            "Marginal_zone_lymphoma",
            "Marginal zone lymphoma (splenic, nodal and MALT)",
            hist_include=["9689", "9699"]
        ),
        subgroup(
            "Lymphoplasmacytic_lymphoma",
            "Lymphoplasmacytic lymphoma",
            hist_include=["9671", "9761"]
        ),
        subgroup(
            "Follicular_lymphoma",
            "Follicular lymphoma",
            hist_include=["9597", "9675", "9690-9691", "9695", "9698"]
        ),
        subgroup(
            "Mantle_cell_lymphoma",
            "Mantle cell lymphoma",
            hist_include=["9673"]
        ),
        subgroup(
            "Burkitt_lymphoma",
            "Burkitt lymphoma",
            hist_include=["9687", "9826"]
        ),
        subgroup(
            "Diffuse_large_B-cell_lymphoma",
            "Diffuse large B-cell lymphoma (any subtype)",
            hist_include=["9680", "9684", "9688", "9712", "9735", "9737", "9738"]
        ),
        subgroup(
            "Primary_mediastinal_large_B-cell_lymphoma",
            "Primary mediastinal (thymic) large B-cell lymphoma",
            hist_include=["9679"]
        ),
        subgroup(
            "Other_B-cell_lymphomas",
            "Other B-cell lymphomas",
            hist_include=["9596", "9670", "9678", "9728", "9833", "9940"]
        ),
        subgroup(
            "T/NK-cell_lymphoid_neoplasms",
            "T/NK細胞淋巴系腫瘤",
            "T/NK-cell lymphoid neoplasms",
            child_keys=[
                "Extranodal_NK/T_cell_lymphoma_nasal_or_other_type",
                "Cutaneous_T_cell_lymphoma",
                "Enteropathy-type_T-cell_lymphoma",
                "Hepatosplenic_T-cell_lymphoma",
                "Subcutaneous_panniculitis-like_T-cell_Lymphoma",
                "Peripheral_T-cell_lymphoma_NOS",
                "Angioimmunoblastic_T-cell_lymphoma",
                "Anaplastic_large_cell_lymphoma",
                "Adult_T-cell_lymphoma/leukemia",
                "Other_T-cell_lymphomas"
            ]
        ),
        subgroup(
            "Extranodal_NK/T_cell_lymphoma_nasal_or_other_type",
            "Extranodal NK/T cell lymphoma, nasal or other type",
            hist_include=["9719"]
        ),
        subgroup(
            "Cutaneous_T_cell_lymphoma",
            "Cutaneous T cell lymphoma (Including Mycosis fungoides/Sëzary syndrome)",
            hist_include=["9700", "9701", "9709", "9718", "9726"]
        ),
        subgroup(
            "Enteropathy-type_T-cell_lymphoma",
            "Enteropathy-type T-cell lymphoma",
            hist_include=["9717"]
        ),
        subgroup(
            "Hepatosplenic_T-cell_lymphoma",
            "Hepatosplenic T-cell lymphoma",
            hist_include=["9716"]
        ),
        subgroup(
            "Subcutaneous_panniculitis-like_T-cell_Lymphoma",
            "Subcutaneous panniculitis-like T-cell Lymphoma",
            hist_include=["9708"]
        ),
        subgroup(
            "Peripheral_T-cell_lymphoma_NOS",
            "Peripheral T-cell lymphoma, NOS",
            hist_include=["9702"]
        ),
        subgroup(
            "Angioimmunoblastic_T-cell_lymphoma",
            "Angioimmunoblastic T-cell lymphoma",
            hist_include=["9705"]
        ),
        subgroup(
            "Anaplastic_large_cell_lymphoma",
            "Anaplastic large cell lymphoma",
            hist_include=["9714"]
        ),
        subgroup(
            "Adult_T-cell_lymphoma/leukemia",
            "Adult T-cell lymphoma/leukemia",
            hist_include=["9827"]
        ),
        subgroup(
            "Other_T-cell_lymphomas",
            "Other T-cell lymphomas",
            hist_include=["9724", "9729", "9834", "9948"]
        ),
        subgroup(
            "Plasma_cell_neoplasms",
            "漿細胞腫瘤",
            "Plasma cell neoplasms",
            hist_include=["9731-9734"]
        ),
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
            "AML",
            child_keys=[
                "AML_with_recurrent_genetic_abnormalities",
                "AML_with_myelodysplasia_related_changes",
                "Therapy_related_myeloid_neoplasms",
                "Acute_myeloid_leukemia_NOS",
                "Other_acute_myeloid_leukemia",
                "Myeloid_sarcoma",
                "Myeloid_proliferations_related_to_Down_Syndrome",
                "Blastic_plasmacytoid_dendritic_cell_neoplasm",
            ]
        ),
        subgroup(
            "AML_with_recurrent_genetic_abnormalities",
            "AML with recurrent genetic abnormalities",
            hist_include=["9865", "9866", "9869", "9871", "9896", "9897", "9911"]
        ),
        subgroup(
            "AML_with_myelodysplasia_related_changes",
            "AML with myelodysplasia-related changes",
            hist_include=["9895"]
        ),
        subgroup(
            "Therapy_related_myeloid_neoplasms",
            "Therapy-related myeloid neoplasms",
            hist_include=["9920"]
        ),
        subgroup(
            "Acute_myeloid_leukemia_NOS",
            "Acute myeloid leukemia, NOS",
            hist_include=["9861"]
        ),
        subgroup(
            "Other_acute_myeloid_leukemia",
            "Other acute myeloid leukemia",
            hist_include=["9840", "9867", "9870", "9872-9874", "9891", "9910", "9931"]
        ),
        subgroup(
            "Myeloid_sarcoma",
            "Myeloid sarcoma",
            hist_include=["9930"]
        ),
        subgroup(
            "Myeloid_proliferations_related_to_Down_Syndrome",
            "Myeloid proliferations related to Down Syndrome",
            hist_include=["9898"]
        ),
        subgroup(
            "Blastic_plasmacytoid_dendritic_cell_neoplasm",
            "Blastic plasmacytoid dendritic cell neoplasm",
            hist_include=["9727"]
        ),
        subgroup(
            "CML",
            "慢性骨髓性白血病",
            "CML, Only BCR-ABL1-positive",
            hist_include=["9875"]
        ),
        subgroup(
            "ALL",
            "急性淋巴性白血病",
            "ALL",
            child_keys=[
                "B_lymphoblastic_leukemia_lymphoma",
                "T_lymphoblastic_leukemia_lymphoma",
            ]
        ),
        subgroup(
            "B_lymphoblastic_leukemia_lymphoma",
            "B lymphoblastic leukemia / lymphoma",
            hist_include=["9811-9818", "9835-9836"]
        ),
        subgroup(
            "T_lymphoblastic_leukemia_lymphoma",
            "T lymphoblastic leukemia / lymphoma",
            hist_include=["9837"]
        ),
        subgroup(
            "CLL",
            "慢性淋巴性白血病",
            "CLL",
            hist_include=["9823"]
        ),
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
        subgroup(
            "Other_Leukemia",
            "其他白血病",
            "Other Leukemia",
            hist_include=["9820", "9832", "9860"]
        ),
        subgroup(
            "Leukemia_NOS",
            "未分類白血病",
            "Leukemia, NOS",
            hist_include=["9800"]
        )
    ]
)

CANCER_GROUP_RULES = [
    ORAL_GROUP,
    SALIVARY_GLANDS,
    NASOPHARYNX,
    LARYNX,
    ESOPHAGUS,
    STOMACH,
    COLON_AND_RECTUM_ANUS,
    LIVER_AND_INTRAHEPATIC_BILE_DUCT,
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