"""
Cancer grouping rules for the annual report module.

"""

CANCER_GROUP_RULES = [
    {
        "key": "colon_and_rectum",
        "name_zh": "結直腸癌",
        "name_en": "Colon and Rectum",
        "site_prefixes": ["C18", "C19", "C20"],
        "hist_exclude": ["9140", "9590-9993"],
        "subgroups": [
            {
                "key": "colon",
                "name_zh": "結腸癌",
                "name_en": "Colon",
                "site_prefixes": ["C18"],
            },
            {
                "key": "rectum",
                "name_zh": "直腸癌",
                "name_en": "Rectum",
                "site_prefixes": ["C19", "C20"],
            },
        ],
    },
    {
        "key": "lung_and_bronchus",
        "name_zh": "肺癌",
        "name_en": "Lung and Bronchus",
        "site_prefixes": ["C34"],
        "hist_exclude": ["9140", "9590-9993"],
        "subgroups": [
            {
                "key": "small_cell_carcinoma",
                "name_zh": "肺小細胞癌",
                "name_en": "Small Cell Carcinoma",
                "hist_include": ["8002", "8041-8045"],
            },
            {
                "key": "adenocarcinoma",
                "name_zh": "肺腺癌",
                "name_en": "Adenocarcinoma",
                "hist_include": [
                    "8050",
                    "8130",
                    "8140-8141",
                    "8143-8144",
                    "8146",
                    "8201",
                    "8211",
                    "8213",
                    "8230",
                    "8250-8257",
                    "8260",
                    "8262-8263",
                    "8265",
                    "8290",
                    "8310",
                    "8320",
                    "8323",
                    "8333",
                    "8480-8481",
                    "8490",
                    "8503",
                    "8550-8552",
                    "8572",
                ],
            },
            {
                "key": "squamous_cell_carcinoma",
                "name_zh": "肺鱗狀細胞癌",
                "name_en": "Squamous Cell Carcinoma",
                "hist_include": ["8051-8052", "8070-8076", "8083-8084"],
            },
        ],
    },
]
