"""Version 115 indicators indicator definitions."""
from modules.blueprint.indicators.calculators import (
    calculate_oral_indicator_1,
    calculate_oral_indicator_2,
    calculate_oral_indicator_3,
    calculate_oral_indicator_4,
    calculate_oral_indicator_5,
    calculate_oral_indicator_6,
)


INDICATOR_DEFINITIONS = {
    "Oral_Cavity": [
        {
            "id": 1,
            "direction": "正向指標",
            "source": "hospital_self_reported",
            "name": "口腔癌病人手術後6週內開始輔助治療（放射治療或化學放射治療）的比率。",
            "numerator_definition": "分母中，手術後6週內開始輔助治療（放射治療或化學放射治療）的人數。",
            "denominator_definition": "手術後接受輔助治療（放射治療或化學放射治療）的人數。",
            "selection_reason": "會影響局部區域的控制：根據研究文獻，口腔癌接受術後輔助治療須在6週內給予，才能達到預期效果；超過6週對局部控制效果不佳。",
            "registry_fields": "分母中，取放射治療開始日期（4.2.1.3）與申報醫院化學治療開始日期（4.3.4）較早者，減原發部位最確切的手術切除日期（4.1.2）≦42天。",
            "notes": "申報醫院原發部位手術方式（4.1.4）=30–90，且符合以下任一：A. 手術日早於放射治療開始日；B. 手術日早於化學治療開始日，且放射治療開始日期不等於00000000。術後放射治療通常於手術後4–6週開始，應避免延遲超過6週，以降低頭頸癌局部區域復發率。",
            "calculator": calculate_oral_indicator_1,
        },
        {
            "id": 2,
            "direction": "負向指標",
            "source": "hospital_self_reported",
            "name": "口腔癌病人手術後30天內死亡的比率。",
            "numerator_definition": "分母中，手術後30天內死亡的人數。",
            "denominator_definition": "口腔癌手術的人數。（排除緩和治療。）",
            "selection_reason": "手術死亡率為醫院手術及術前評估品質的重要指標之一。",
            "registry_fields": "分母中，生存狀態（5.4）=0，且最後聯絡或死亡日期（5.3）減原發部位最確切的手術切除日期（4.1.2）≦30天。",
            "notes": "申報醫院原發部位手術方式（4.1.4）=30–90，且申報醫院緩和照護（4.4）=0。",
            "calculator": calculate_oral_indicator_2,
        },
        {
            "id": 3,
            "direction": "負向指標",
            "source": "hospital_self_reported",
            "name": "口腔癌病人開始接受放射治療（不含化療）後90天內死亡的比率。",
            "numerator_definition": "口腔癌病人開始接受放射治療（不含化療）後90天內死亡的人數。",
            "denominator_definition": "口腔癌病人接受放射治療（不含化療）的人數。（排除緩和治療）",
            "calculator": calculate_oral_indicator_3,
        },
        {
            "id": 4,
            "direction": "負向指標",
            "source": "hospital_self_reported",
            "name": "口腔癌病人開始接受同步化學治療及放射治療後90天內死亡的比率。",
            "numerator_definition": "口腔癌病人開始接受同步化學治療及放射治療後90天內死亡的人數。",
            "denominator_definition": "口腔癌病人接受同步化學治療及放射治療的人數。（排除緩和治療）",
            "calculator": calculate_oral_indicator_4,
        },
        {
            "id": 5,
            "direction": "正向指標",
            "source": "hospital_self_reported",
            "name": "第一個口腔癌淋巴結病理檢查15顆（含）以上的比率。",
            "numerator_definition": "分母中，口腔癌切除標本淋巴結病理檢查報告15顆（含）以上的人數。",
            "denominator_definition": "第一個癌是口腔癌且接受頸部淋巴廓清術的人數。",
            "calculator": calculate_oral_indicator_5,
        },
        {
            "id": 6,
            "direction": "負向指標",
            "source": "hospital_self_reported",
            "name": "病理切片證實為口腔鱗狀細胞癌並施行口腔根除性手術，其病理切緣（pathological margins）小於4 mm的比例。",
            "numerator_definition": "病理切緣小於4 mm（不包含4 mm）的人數；若有多個手術切緣距離，採最近距離。",
            "denominator_definition": "口腔鱗狀細胞癌施行根除性手術且有紀錄病理切緣的人數。（排除病理切緣不詳者及病理報告描述手術切緣為非侵襲癌。）",
            "calculator": calculate_oral_indicator_6,
        },
    ],
}


def get_indicator_definitions(cancer_key):
    return INDICATOR_DEFINITIONS.get(str(cancer_key or ""), [])