RULES = {
    '申報醫院代碼': {
        'ID':'1.1',
        'field': 'Reporting Hospital Code', 
        'max_length': 10, 
        'digit': True,
        'description': '確認申報醫院之醫事機構代碼。',
        'purpose': '確認申報醫院。'
    },
    '病歷號碼': {
        'ID':'1.2',
        'field': 'Medical Record Number', 
        'max_length': 10, 
        'SV': ['9999999999'],
        'description': '記錄個案於申報醫院之病歷號碼。',
        'purpose': '用來辨識個案及作為調閱病歷之依據；亦可作為辨識個案是否有多重原發腫瘤之依據。'
    },
    '姓名': {
        'ID':'1.3',
        'field': 'Name',
        'max_length': 10,
        'description': '填寫個案的姓名。',
        'purpose': '用來辨識個案。'
    },
    '身分證統一編號': {
        'ID':'1.4',
        'field': 'ID Number',
        'length': 10,
        'regex': r'^[A-Za-z][1289]\d{8}$',
        'SV': ['9999999999'],
        'description': '記錄個案的身分證統一編號。',
        'purpose': '用來辨識個案。' 
    },
    '性別': {
        'ID':'1.5',
        'field': 'Sex',
        'length': 1,
        'digit': True,
        'choices': ['1', '2', '3', '4', '9'],
        'description': '確認個案的性別。',
        'purpose': '可作為各癌症部位性別比例及預後之比較。個案若有多重原發，其病歷紀錄上的性別都應相同。',
        'definition': '1:男性。2:女性。3:雙性人或其他。4:變性人。9:不詳。'
    },
    '出生日期': {
        'ID':'1.6',
        'field': 'Date of Birth',
        'length': 8,
        'SV': ['99999999'],
        'is_date': '%Y%m%d',
        'description': '確認個案的出生日期。',
        'purpose': '有助於確認個案的身份；對於以個案世代研究 (patient cohort) 作為腫瘤分析也很有幫助。'
    },
    '戶籍地代碼': {
        'ID':'1.7',
        'field': 'Residence Code',
        'length':4,
        'digit': True,
        'range': [100, 9999],
        'description': '記錄個案在診斷為癌症時之戶籍地代碼。',
        'purpose': '為個案流行病學之地域資料，並可作為癌症群聚或環境因素研究分析。'
    },
    '診斷年齡': {
        'ID':'2.1',
        'field': 'Age at Diagnosis',
        'length': 3,
        'digit': True,
        'pattern_range': '000-120, 999',
        'description': '記錄個案診斷此癌症時之實足年齡。',
        'purpose': '有助於個案的確認，且對於統計分析癌症相關資料時，年齡常是一個重要的因素。' 
    },
    '癌症發生順序號碼': {
        'ID':'2.2',
        'field': 'Sequence Number',
        'length': 2,
        'digit': True,     
        'range': [1, 99],
        'description': '指個案一生中所罹患惡性腫瘤的發生順序。',
        'purpose': '可用來選擇單一原發腫瘤個案及進行特定的追蹤研究，並可分析發生多發腫瘤的因子。' 
    },
    '個案分類': {
        'ID':'2.3',
        'field': 'Class of Case',
        'length': 1,
        'digit': True,     
        'choices': ['0', '1', '2', '3', '5', '7', '8', '9'],
        'description': '將個案進行分類。',
        'purpose': '在做治療和存活分析時，本欄位將個案分為可分析和不可分析個案兩類。進而提供申報醫院進行研究個案之選擇。',
        'definition': (
            '0:本院診斷，未於本院接受首次治療。\n'
            '1:本院診斷，並於本院接受全部或部分首次治療。\n'
            '2:他院診斷，於本院接受全部或部分首次治療。\n'
            '3:他院診斷，未於本院接受首次治療，或因復發/持續癌症問題至本院就診。\n'
            '5:死亡解剖後才確認癌症。\n'
            '7:未因癌症診斷或治療至本院就醫 (不需申報)。\n'
            '8:僅依死亡證明診斷癌症 (不需申報)。\n'
            '9:不詳。'
        ),
    },
    '診斷狀態分類': {
        'ID':'2.3.1',
        'field': 'Class of Diagnosis Status',
        'length': 1,
        'digit': True,     
        'choices': ['1', '2', '3', '5', '7', '8'],
        'description': '記錄個案至申報醫院首次為此癌症就診時的癌症診療情境。',
        'purpose': '與新增欄位 2.3.2「治療狀態分類」並用，以確保欄位 2.3「個案分類」的正確性。',
        'definition': (
            '1:於本院診斷癌症。\n'
            '2:於他院診斷，於首次療程期間或未確認復發前至本院就診。\n'
            '3:於他院診斷，癌症復發或惡化後才至本院就診。\n'
            '5:死亡解剖後才診斷為癌症。\n'
            '7:僅有病理報告，未因癌症診斷或治療至本院就醫。\n'
            '8:僅依死亡證明診斷癌症。\n'
        ),
    },
    '治療狀態分類': {
        'ID':'2.3.2',
        'field': 'Class of Treatment Status',
        'length': 1,
        'digit': True,     
        'range': [0, 9],
        'description': '記錄此個案在申報時的治療狀態。',
        'purpose': '與新增欄位 2.3.1「診斷狀態分類」並用，以確保欄位 2.3「個案分類」的正確性。此欄位並協助記錄個案未於申報醫院接受首次療程的原因，以協助申報醫院改善管理個案流失；並提供此數據作為公衛行政資源調整的依據。',
        'definition': (
            '0:未接受任何治療即死亡或病危。\n'
            '1:首次療程僅於本院完成。\n'
            '2:首次療程未於本院進行，或本院僅提供支援/諮詢。\n'
            '3:首次療程由本院與他院共同完成。\n'
            '4:首次療程為觀察、支持性或緩和治療。\n'
            '5:首次療程僅接受另類治療。\n'
            '6:個案拒絕首次治療。\n'
            '7:因癌症或治療併發症至本院就診。\n'
            '8:因其他疾病至本院就診 (免申報)。\n'
            '9:不詳。\n'
        ),
    },
    '首次就診日期': {
        'ID':'2.4',
        'field': 'Date of First Contact',
        'length': 8,
        'SV': ['99999999'],  
        'is_date': '%Y%m%d',
        'description': '個案因此癌症至申報醫院門診或住院之最早日期。',
        'purpose': '可用來計算個案首次就診至進行癌症登記之時間間隔；也可用來計算首次就診至治療之時間差距，以作為監控癌症照護品質之用。'
    },
    '最初診斷日期':{
        'ID':'2.5',
        'field': 'Date of Initial Diagnosis',
        'length': 8,
        'SV': ['99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄此癌症最早被醫師診斷的日期。',
        'purpose': '可計算癌症最初診斷日期至完成分期或開始治療的時間間隔。'
    },
    '原發部位':{
        'ID':'2.6',
        'field': 'Primary Site',
        'length': 4,
        'pattern_range': 'C000-C809',
        'description': '確認癌症原發部位。',
        'purpose': '原發部位是分期及決定治療方針之依據；同時也影響其預後及病程。'
    },
    '側性':{
        'ID':'2.7',
        'field': 'Laterality',
        'length': 1,
        'digit': True,     
        'choices': ['0','1', '2', '3', '4', '5', '9'],
        'description': '確認癌症起源於成對器官或身體的某一側。本欄位只適用於原發腫瘤部位。',
        'purpose': '側性可提供分期及癌病侵犯程度的資訊，並可確定原發侵犯的數目。',
        'definition': (
            '0:非成對器官。\n'
            '1:原發部位在右側。\n'
            '2:原發部位在左側。\n'
            '3:成對器官，僅單側侵犯，但無法判定左右側。\n'
            '4:成對器官，雙側侵犯且為單一原發，無法判定起源側\n'
            '5:身體中線器官或中線腫瘤。\n'
            '9:成對器官，但側位不明。\n'
        ),
    },
    '組織型態':{
        'ID':'2.8',
        'field': 'Histology',
        'length':4,
        'digit': True,
        'range': [8000, 9993],
        'description': '原發腫瘤細胞於顯微鏡下之結構。',
        'purpose': '作為分期及決定治療方針之根據；同時也影響其預後及病程。'
    },
    '性態碼':{
        'ID':'2.9',
        'field': 'Behavior Code',
        'length': 1,
        'digit': True,     
        'choices': ['2', '3'],
        'description': '記錄病理診斷中的性態碼。',
        'purpose': '病理醫師常使用 benign(0)、borderline(1)、in situ(2)、malignant, primary site(3)、malignant,metastatic site(6)、或 malignant, uncertain whether primary or metastatic site(9) 來描述腫瘤的性態。其中性態碼為 2、3、6 或 9 (若為 6 或 9 者，須申報原發部位，且性態碼改為 3) 的個案必須申報至癌症登記中心。'
    },
    '臨床分級/分化':{
        'ID':'2.10.1',
        'field': 'Grade Clinical',
        'length': 1,
        'pattern_range': '1-5, 8-9, A-E, H, L-M, S, X',
        'description': '收錄實質腫瘤於首次治療前的分級/分化。分級/分化為腫瘤和正常組織的相似程度。Well differentiated (Grade I) 和正常組織最相似；Undifferentiated (Grade IV) 和正常組織差異最大。',
        'purpose': '與個案的預後有關。分級/分化可用以評估癌症嚴重程度；分級/分化及細胞型態對於許多癌症而言是重要的預後因子。分級/分化對於某些癌症更是判定期別的依據之一。'
    },
    '病理分級/分化':{
        'ID':'2.10.2',
        'field': 'Grade Pathological',
        'length': 1,
        'pattern_range': '1-5, 8-9, A-E, H, L, M, S, X',
        'description': '收錄實質腫瘤於原發部位手術之後的分級/分化。分級/分化為腫瘤和正常組織的相似的程度。Well differentiated (Grade I)和正常組織最相似；Undifferentiated (Grade IV)和正常組織差異最大。',
        'purpose': '與個案的預後有關。分級/分化可用以評估癌症嚴重程度；分級/分化及細胞型態對於許多癌症而言是重要的預後因子。分級/分化對於某些癌症更是判定病理期別的依據之一。'
    },
    '癌症確診方式':{
        'ID':'2.11',
        'field': 'Diagnostic Confirmation',
        'length': 1,
        'digit': True,
        'range': [1, 9],
        'description': '記錄個案於申報醫院或外院之最精確的診斷依據。',
        'purpose': '作為統計癌症經顯微鏡檢確認之比例。完整的癌症發生率統計應包括臨床及病理確診的個案。'
    },
    '首次顯微鏡檢證實日期':{
        'ID':'2.12',
        'field': 'Date of First Microscopic Confirmation',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案此癌症最早顯微鏡檢證實的日期。',
        'purpose': '瞭解最初診斷日期與首次顯微鏡檢證實日期之不同，亦可計算至完成分期或開始治療的時間間隔。'
    },
    '腫瘤大小':{
        'ID':'2.13',
        'field': 'Tumor Size',
        'length': 3,
        'digit': True,
        'SV': ['998', '999'],
        'range': [0, 990],
        'description': '描述原發腫瘤之最大尺寸或直徑，單位通常為亳米(mm)。',
        'purpose': '腫瘤大小是重要的癌症預後因子，也是判定 AJCC 期別的依據。'
    },
    '神經侵襲':{
        'ID':'2.13.1',
        'field': 'Perineural Invasion',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '7', '8', '9'],
        'description': '記錄病歷中原發部位病理報告記載神經侵襲的情形。',
        'purpose': '做為預後評估。腫瘤是否有神經侵襲，為臨床治療上的重要因素之一。'
    },
    '淋巴管或血管侵犯':{
        'ID':'2.13.2',
        'field': 'Lymph-vascular invasion',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '7', '8', '9'],
        'description': '依據原發部位病理報告記錄是否出現淋巴管或血管侵犯。',
        'purpose': '做為治療評估。腫瘤是否有淋巴管或血管侵犯，為臨床治療上的重要因素之一。'
    },
    '區域淋巴結檢查數目':{
        'ID':'2.14',
        'field': 'Regional Lymph Nodes Examined',
        'length': 2,
        'digit': True,
        'range': [0, 90],
        'SV': ['95', '96', '97', '98', '99'],
        'description': '記錄經由病理醫師檢驗的區域淋巴結總數。',
        'purpose': '本欄位可用以評估病理報告品質、手術廣泛程度，及治療品質之測量指標。'
    },
    '區域淋巴結侵犯數目':{
        'ID':'2.15',
        'field': 'Regional Lymph Nodes Positive',
        'length': 2,
        'digit': True,
        'range': [0, 90],
        'SV': ['95', '97', '98', '99'],
        'description': '記錄經由病理醫師檢驗呈陽性的區域淋巴結總數。',
        'purpose': '本欄位可用以評估病理報告品質、手術廣泛程度，及治療品質之測量指標。'
    },
    '診斷性及分期性手術處置日期':{
        'ID':'3.1',
        'field': 'Date of Surgical Diagnostic and Staging Procedure',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在任何醫療機構，為診斷或分期而執行的手術處置日期。',
        'purpose': '記錄非治療目的所用之手術處置資源。'
    },
    '外院診斷性及分期性手術處置':{
        'ID':'3.2',
        'field': 'Surgical Diagnostic and Staging Procedure at Other Facility',
        'length': 2,
        'digit': True,
        'pattern_range': '00-07, 09-14',
        'description': '記錄在外院為診斷或分期而執行的手術處置。',
        'purpose': '記錄在外院非治療目的所用之手術處置資源。'
    },
    '申報醫院診斷性及分期性手術處置':{
        'ID':'3.3',
        'field': 'Surgical Diagnostic and Staging Procedure at This Facility',
        'length': 2,
        'digit': True,
        'pattern_range': '00-07, 09-14',
        'description': '記錄在申報醫院為診斷或分期而執行的手術處置。',
        'purpose': '記錄在申報醫院非治療目的所用之手術處置資源。'
    },
    '臨床 T':{
        'ID':'3.4',
        'field': 'Clinical T',
        'max_length': 4,
        'pattern_range': 'X, 0, A, IS, ISU, ISD, ISDC, ISPA, ISLA, 1M, 1, 1A, 1A1, 1A2, 1B, 1B1, 1B2 , 1B3, 1C, 1C1, 1C2, 1C3, 1D, 2, 2A, 2A1, 2A2, 2B, 2C, 2D, 3, 3A, 3B, 3C, 3D, 3E, 4, 4A, 4B, 4C, 4D, 4E, 8888, 9999',
        'description': '指原發腫瘤大小或侵犯程度。',
        'purpose': '作為 TNM 分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '臨床 N':{
        'ID':'3.5',
        'field': 'Clinical N',
        'max_length': 3,
        'pattern_range': 'X ,0 , 0A, 0B, 1M, 1, 1A, 1B, 1C, 2, 2M, 2A, 2B, 2C, 3, 3A, 3B, 3C, 888, 999',
        'description': '指是否有區域淋巴結的轉移和轉移的範圍。',
        'purpose': '作為TNM分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '臨床 M':{
        'ID':'3.6',
        'field': 'Clinical M',
        'max_length': 3,
        'pattern_range': 'X, B, 0, 0B, 1, 1A, 1A0, 1A1, 1B, 1B0, 1B1, 1C, 1C0, 1C1, 1D, 1D0, 1D1, 1E, 888, 999',
        'description': '指是否有遠端轉移。',
        'purpose': '作為TNM分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '臨床期別組合':{
        'ID':'3.7',
        'field': 'Clinical Stage Group',
        'max_length': 3,
        'pattern_range': '0, 0A, 0IS, 1, 1A, 1A1, 1A2, 1A3, 1B, 1B1, 1B2, 1B3, 1C, 1E, 1S, 2, 2A, 2A1, 2A2, 2B, 2C, 2E, 2BU, 3, 3A, 3A1, 3A2, 3B, 3C, 3C1, 3C2, 4, 4A, 4A1, 4A2, 4B, 4C, OC, 888, 999, BBB',
        'description': '基於臨床 T、N 和 M 來決定疾病於解剖部位上的侵犯程度。',
        'purpose': 'TNM分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '臨床分期字根/字首':{
        'ID':'3.8',
        'field': 'Clinical Stage (Prefix/Suffix) Descriptor',
        'length': 1,
        'digit': True,     
        'choices': ['0', '3', '9'],
        'description': '指 AJCC 臨床分期字根/字首的描述符號。',
        'purpose': '是為了辨別出特殊的個案，而這些特殊的個案在全國統計資料中，需分別統計。這些字根或字首僅是附加在原來的分期中，並不會因此而改變分期。'
    },
    '病理 T':{
        'ID':'3.10',
        'field': 'Pathologic T',
        'max_length': 4,
        'pattern_range': 'X, 0, A, IS, ISU, ISD, ISDC, ISPA, ISLA, 1M, 1, 1A, 1A1, 1A2, 1B, 1B1, 1B2, 1B3, 1C, 1C1, 1C2, 1C3, 1D, 2, 2A, 2A1, 2A2, 2B, 2C, 2D, 3, 3A, 3B, 3C, 3D, 4, 4A, 4B, 4C, 4D, 4E, 8888, 9999',
        'description': '指原發腫瘤大小或侵犯程度。',
        'purpose': '作為TNM分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '病理 N':{
        'ID':'3.11',
        'field': 'Pathologic N',
        'max_length': 3,
        'pattern_range': 'X, 0, 0A, 0B, 0C, 0D, 1, 1A, 1AS, 1B, 1C, 1M, 2M, 2, 2A, 2B, 2C, 3, 3A, 3B, 3C, 888, 999',
        'description': '指是否有區域淋巴結的轉移和轉移的範圍。',
        'purpose': '作為TNM分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '病理 M':{
        'ID':'3.12',
        'field': 'Pathologic M',
        'max_length': 3,
        'pattern_range': 'X, B, 0, 1, 1A, 1A0, 1A1, 1B, 1B0, 1B1, 1C, 1C0, 1C1, 1D, 1D0, 1D1, 1E, C, CA, CA0, CA1, CB, CB0, CB1, CC, CC0, CC1, CD, CD0, CD1, CE, 888, 999',
        'description': '指是否有遠端轉移。',
        'purpose': '做為TNM分期依據資料，該分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '病理期別組合':{
        'ID':'3.13',
        'field': 'Pathologic Stage Group',
        'max_length': 3,
        'pattern_range': '0, 0A, 0IS, 1, 1A, 1A1, 1A2, 1A3, 1B, 1B1, 1B2, 1B3, 1C, 1S, 2, 2A, 2A1, 2A2, 2B, 2C, 3, 3A, 3A1, 3A2, 3B, 3C, 3C1, 3C2, 3D, 4, 4A, 4A1, 4A2, 4B, 4C, OC, 888, 999, BBB',
        'description': '基於病理 T、N 和 M 來決定疾病於解剖上的侵犯程度。',
        'purpose': 'TNM分期系統可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。 '
    },
    '病理分期字根/字首':{
        'ID':'3.14',
        'field': 'Pathologic Stage (Prefix/Suffix) Descriptor',
        'length': 1,
        'digit': True,
        'choices': ['0', '3', '4', '6', '9'],
        'description': '指 AJCC 病理分期字根/字首的描述符號。',
        'purpose': '是為了辨別出特殊的個案，而這些特殊個案在全國統計資料中，需分別統計。這些字根或是字首僅是附加在原來的分期中，並不會因此而改變分期。'
    },
    'AJCC 癌症分期版本與章節': {
        'ID':'3.16',
        'field': 'The Edition and Chapter of AJCC Cancer Staging',
        'length': 5,
        'SV': ['00000', '88888', '99999'],
        'regex': r'^(0[1-7]888|08(00[1-9]|0[1-7]\d|08[0-3])|V9(00[1-9]|0[1-7]\d|08[0-3]))$',
        'description': '記錄判定個案癌症期別所使用之AJCC癌症分期手冊的版本。',
        'purpose': 'AJCC 分期及T、N、M組成之編碼及規則會隨時間演進而改變，以利個案分析之用。'
    },
    '其他分期系統':{
        'ID':'3.17',
        'field': 'Other Staging System',
        'length': 2,
        'digit': True,
        'choices': ['00', '01', '02', '06', '07', '09', '11', '12', '13', '20', '21', '22'],
        'description': '若非AJCC癌症分期系統，可選擇下列其他分期系統摘錄。',
        'purpose': '對癌症進行分期，有利於治療計畫、預後評估及存活分析。'
    },
    '其他分期系統期別(臨床分期)':{
        'ID':'3.19',
        'field': 'Clinical Other Staging System',
        'max_length': 4,
        'choices': ['0', '1', '1A', '1A1', '1A2', '1B', '1B1', '1B2', '1B3', '1C', '1C1', '1C2', '1C3','2', '2A', '2A1', '2A2', '2B', '2C','3', '3A', '3A1', '3A11', '3A12', '3A2', '3B', '3C', '3CR', '3CP', '3C1', '3C1R', '3C1P','3C2', '3C2R', '3C2P','4', '4A', '4B','8888', '9999','A', 'B', 'C', 'D', 'L', 'E', 'X','0000'],
        'description': '依所選擇「其他分期系統」之分類標準予以編碼。 ',
        'purpose': '瞭解使用之其他分期系統，並可用以評估癌症治療及控制的趨勢。醫師則用以進行預後的 推估、治療的規劃、新療法的評估、結果的分析、追蹤的策劃和早期偵測結果的評定。'
    },
    '其他分期系統期別(病理分期)':{
        'ID':'3.21',
        'field': 'Pathologic Other Staging System',
        'max_length': 4,
        'pattern_range': '0, 1, 1A, 1A1, 1A2, 1A3, 1B, 1B1, 1B2, 1C, 1C1, 1C2, 1C3, 2, 2A, 2A1, 2A2, 2B, 2C, 3, 3A, 3A1, 3A11, 3A12, 3A2, 3B, 3B1, 3B2, 3C, 3C1, 3C11, 3C12, 3C2, 3C21, 3C22, 4, 4A, 4B, 4C, 8888, 9999, A, B1, B2, B3, C1, C2, C3, D, 0000',
        'description': '若非 AJCC 癌症分期系統，可選擇下列其他分期系統摘錄。'
    },
    '首次療程開始日期':{
        'ID':'4.1',
        'field': 'Date of First Course of Treatment',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在任何醫療機構，開始首次療程 (包括手術、放射治療、全身性治療、局部藥物治療、其他治療) 的日期。',
        'purpose': '評估診斷和開始治療間是否有延遲的情況，亦可當做存活分析的開始計算點。若是未進行任何治療，則無法記錄欄位日期，亦無法計算存活分析。因此，提供醫師決定不進行治療或個案、個案家屬與監護者拒絕治療的日期資訊是很重要的。'
    },
    '首次手術日期':{
        'ID':'4.1.1',
        'field': 'Date of First Surgical Procedure',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在任何醫療機構，最早針對癌症進行手術的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '原發部位最確切的手術切除日期':{
        'ID':'4.1.2',
        'field': 'Date of Most Definite Surgical Resection of the Primary Site',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在任何醫療機構的首次療程中，針對原發部位腫瘤執行最確切手術切除的日期。',
        'purpose': '用來測量癌症確診日期和對原發部位腫瘤所執行最確切手術治療日期之間隔時間，亦可用於評估治療效果。'
    },
    '外院原發部位手術方式':{
        'ID':'4.1.3',
        'field': 'Surgical Procedure of Primary Site at Other Facility',
        'length': 2,
        'digit': True,
        'SV':['00','90','98','99'],
        'pattern_range': '10-80',
        'description': '記錄個案於外院對原發部位所進行的外科手術方式。',
        'purpose': '用來比較不同治療方式的效果。'
    },
    '申報醫院原發部位手術方式':{
        'ID':'4.1.4',
        'field': 'Surgical Procedure of Primary Site at This Facility',
        'length': 2,
        'digit': True,
        'SV':['00','90','98','99'],
        'pattern_range': '10-80',
        'description': '記錄在申報醫院對原發部位所進行的手術方式。',
        'purpose': '用來比較不同治療方式的效果。'
    },
    '微創手術':{
        'ID':'4.1.4.1',
        'field': 'Minimally Invasive Surgery',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '4', '8', '9'],
        'description': '記錄原發部位於申報醫院採用微創 (Minimally Invasive Surgery) 或機械臂 (Robotic Surgery) 手術的狀況。',
        'purpose': '追蹤應用微創及機械臂方式執行手術及使用傳統開放式手術之差異，以監測微創及機械臂手術的方式與趨勢。'
    },
    '原發部位手術邊緣':{
        'ID':'4.1.5',
        'field': 'Surgical Margins of The Primary Site',
        'length': 1,
        'pattern_range': '0-5, 7-9, A-F',
        'description': '記錄原發腫瘤切除後手術邊緣的最後狀態。',
        'purpose': '作為治療品質監測、分期或評估腫瘤復發預後因子等用途。'
    },
    '原發部位手術切緣距離':{
        'ID':'4.1.5.1',
        'field': 'Surgical Margins Distance of the Primary Site',
        'length': 3,
        'pattern_range': '000-980, 987, 988, 990-991, 999, A01-A09',
        'description': '記錄原發腫瘤切除後，病理報告中的腫瘤細胞手術切緣的最近距離。',
        'purpose': '作為治療品質監測與評估腫瘤復發或預後的影響。'
    },
    '外院區域淋巴結手術範圍':{
        'ID':'4.1.6',
        'field': 'Scope of Regional Lymph Node Surgery at Other Facility',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '4', '5', '6', '7', '9'],
        'description': '記錄在外院進行原發部位手術或是另一獨立手術中，同時將區域淋巴結切除、切片或抽吸的範圍。',
        'purpose': '用來比較與評估手術治療範圍。'
    },
    '申報醫院區域淋巴結手術範圍':{
        'ID':'4.1.7',
        'field': 'Scope of Regional Lymph Node Surgery at This Facility',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '4', '5', '6', '7', '9'],
        'description': '記錄在申報醫院進行原發部位手術或是另一獨立手術中，同時將區域淋巴結切除、切片或抽吸的範圍。',
        'purpose': '用來比較與評估手術治療範圍。'
    },
    '外院其他部位手術方式':{
        'ID':'4.1.8',
        'field': 'Surgical Procedure/Other Site at Other Facility',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '4', '5', '9'],
        'description': '記錄在外院進行手術切除原發腫瘤外之鄰近部位組織/器官、遠端淋巴結或遠端轉移。',
        'purpose': '利於評估腫瘤侵犯的範圍。'
    },
    '申報醫院其他部位手術方式':{
        'ID':'4.1.9',
        'field': 'Surgical Procedure/Other Site at This Facility',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '4', '5', '9'],
        'description': '記錄在申報醫院進行手術切除原發腫瘤外之鄰近部位組織/器官、遠端淋巴結或遠端轉移。',
        'purpose': '利於評估腫瘤侵犯的範圍。'
    },
    '原發部位未手術原因':{
        'ID':'4.1.10',
        'field': 'Reason for No Surgery of Primary Site',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '2', '3', '5', '6', '7', '8', '9'],
        'description': '記錄個案在任何醫療機構，未接受原發部位手術的原因。',
        'purpose': '提供照護品質相關的資訊，並且描述原發部位未接受手術的原因。'
    },
    '放射治療臨床標靶體積摘要':{
        'ID':'4.2.1.1',
        'field': 'RT Target Summary',
        'max_length': 2,
        'digit': True,
        'range': [0, 63],
        'SV': ['-1', '-9'],
        'description': '記錄在申報醫院的首次療程中，進行放射治療之放射線標靶體積涵蓋的範圍 (局部原發腫瘤「T」、區域淋巴結「N」和遠端轉移「M」)。',
        'purpose': '以簡單可組合編碼方法登錄個別癌症的放射治療的目標範圍，該資訊可被用於評估放射治療的醫療模式。'
    },
    '放射治療儀器':{
        'ID':'4.2.1.2',
        'field': 'RT Modality',
        'max_length': 3,
        'digit': True,
        'range': [0, 127],
        'SV': ['-1', '-9'],
        'description': '記錄在申報醫院的首次療程中，進行放射治療所使用的治療儀器或治療方式。',
        'purpose': '可作為治療結果分析之依據。'
    },
    '放射治療開始日期':{
        'ID':'4.2.1.3',
        'field': 'Date of RT Started',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在申報醫院的首次療程中，進行放射治療的開始日期。',
        'purpose': '在併用多重治療模式中，病理期別是很多癌症的重要預後因素，也是決定後續輔助治療與否的依據，因此記錄個別治療方式之時間順序及實際間隔，是非常重要的；手術前的放射治療可能會改變期別，並影響其應用於分析評估之使用方式。'
    },
    '放射治療結束日期':{
        'ID':'4.2.1.4',
        'field': 'Date of RT Ended',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在申報醫院的首次療程中，進行放射治療的結束日期。',
        'purpose': '整個放射治療療程的長短是腫瘤控制及併發症的重要因素。此資訊可作為放療之品質指標，及應用於藉以維持不中斷持續放療的輔助療法之成效評估。'
    },
    '放射治療與手術順序':{
        'ID':'4.2.1.5',
        'field': 'Sequence of Radiotherapy and Surgery',
        'max_length': 2,
        'digit': True,
        'range': [0, 7],
        'SV': ['-9','-8','-7','-6','-1'],
        'description': '記錄在任何醫療機構的首次療程中，針對治療區域，放射治療及手術的時間順序關係。',
        'purpose': '放射治療及手術的時間順序關係可能無法由相關日期直接計算得知。此項目提供更詳實的時間順序關係。'
    },
    '區域治療與全身性治療順序':{
        'ID':'4.2.1.6',
        'field': 'Sequence of Locoregional Therapy and Systemic Therapy',
        'max_length': 2,
        'range': [0, 7],
        'SV': ['-9','-8','-7','-1'],
        'description': '記錄在任何醫療機構的首次療程中，針對原發部位的手術或放射治療，與全身性治療的時間順序關係。',
        'purpose': '區域治療與全身性治療的時間順序關係可能無法由相關日期直接計算得知。此項目提供經判斷後更直接正確的時間順序關係。'
    },
    '放射治療執行狀態':{
        'ID':'4.2.1.8',
        'field': 'RT Status',
        'length': 2,
        'digit': True,
        'SV': ['99'],       
        'range': [0, 10], 
        'description': '記錄在申報醫院的首次療程中，接受放射治療的執行狀態。',
        'purpose': '有助於了解建議之治療模式未被採用的理由及確認治療的執行度。'
    },
    '體外放射治療技術':{
        'ID':'4.2.2.1',
        'field': 'EBRT Technique',
        'max_length': 3,
        'digit': True,
        'range': [0, 111],
        'SV': ['-9','-1'],
        'description': '記錄在申報醫院的首次療程中，進行體外放射治療所使用的技術。',
        'purpose': '本項目的資料有助於分析治療技術與治療效果的關係。'
    },
    '最高放射劑量臨床標靶體積':{
        'ID':'4.2.2.2.1',
        'field': 'Target of CTV_H',
        'max_length': 2,
        'digit': True,
        'range': [0, 63],
        'SV': ['-9','-1'],
        'description': '記錄在申報醫院的首次療程中，利用放射線涵蓋之局部原發腫瘤 (T)、區域淋巴結 (N) 或遠端轉移 (M) 來區分並記錄體外射治療中接受最高劑量的目標區域之範圍。一般而言，此最高劑量區域也就是腫瘤負荷最重的區域。',
        'purpose': '''在作治療效果分析時，放射腫瘤醫師會將局部治療失敗的因素分為下列四類：
                        1. 治療部位：是在原發部位失敗，還是淋巴引流區域失敗。
                        2. 腫瘤負荷的輕重：是在臨床可辨識的顯著腫瘤體積 (GTV) 內失敗，還是在可能有顯微性侵犯的臨床標靶體積內 (CTV) 內失敗。
                        3. 治療是否涵蓋足夠的範圍：是在放射治療範圍內失敗，是在放射治療邊緣失敗，還是在放射治療範圍外失敗。
                        4. 腫瘤的放射線敏感度 (Radiosensitivity)：失敗是否和腫瘤病理及其分化程度相關。
                        5. 本項目 CTV_H 合併前兩點的資訊以供未來分析之用。'''
    },
    '最高放射劑量臨床標靶體積劑量':{
        'ID':'4.2.2.2.2',
        'field': 'Dose to CTV_H (cGy)',
        'length': 5,
        'digit': True,      
        'range': [0, 99999],
        'description': '記錄在申報醫院的首次療程中，CTV_H 的放射劑量。本欄位的單位是 centiGray (縮寫 cGy)，與舊單位 “rads” 相同大小。',
        'purpose': '可分析放射治療範圍內失敗的原因是放射劑量不足，或是受限於周邊正常組織的放射線耐受度。' 
    },
    '最高放射劑量臨床標靶體積治療次數':{
        'ID':'4.2.2.2.3',
        'field': 'Number of Fractions to CTV_H',
        'length': 2,
        'digit': True,      
        'range': [0, 99],
        'description': '記錄在申報醫院的首次療程中，CTV_H的放射治療次數(fractions or sessions)。',
        'purpose': '放射治療控制腫瘤效果的好壞與破壞正常組織毒性的高低，和標靶體積的大小，總劑量的高低，分次劑量(dose per fraction)的大小，及整個射線療程的長短相關。一般而言，分次劑量愈大腫瘤控制效果愈好，但同時正常組織毒性愈高。如要計算CTV_H的平均放射分次劑量，只要將「最高放射劑量臨床標靶體積劑量」除以「最高放射劑量臨床標靶體積治療次數」即可得知。' 
    },
    '較低放射劑量臨床標靶體積':{
        'ID':'4.2.2.3.1',
        'field': 'Target of CTV_L',
        'max_length': 2,
        'digit': True,
        'range': [0, 63],
        'SV': ['-9','-1'],
        'description': '記錄在申報醫院的首次療程中，利用放射線涵蓋之局部原發腫瘤(T)，區域淋巴結(N)或遠端轉移(M)來區分並記錄體外射線治療中接受次高劑量的目標區域之範圍。',
        'purpose': '評估放射治療效果及檢討失敗原因。'
    },
    '較低放射劑量臨床標靶體積劑量':{
        'ID':'4.2.2.3.2',
        'field': 'Dose to CTV_L (cGy)',
        'length': 5,
        'digit': True,      
        'range': [0, 99999],
        'description': '記錄在申報醫院的首次療程中，CTV_L 的放射劑量。本欄位的單位是 centiGray (縮寫cGy)，與舊單位“rads”相同大小。',
        'purpose': '評估放射治療效果及檢討失敗原因 (放射治療範圍內失敗的原因是放射劑量不足，或是受限於周邊正常組織的放射線耐受度)。' 
    },
    '較低放射劑量臨床標靶體積治療次數':{
        'ID':'4.2.2.3.3',
        'field': 'Number of Fractions to CTV_L',
        'length': 2,
        'digit': True,      
        'range': [0, 99],
        'description': '記錄在申報醫院的首次療程中，CTV_L 的放射治療次數 (fractions or sessions)。',
        'purpose': '評估放射治療效果，也可用來計算 CTV_L 的平均放射分次劑量，只要將「較低放射劑量之臨床標靶體積的放射線劑量」除以「較低放射劑量之臨床標靶體積的放射治療次數」即可得知。' 
    },
    '其他放射治療儀器':{
        'ID':'4.2.3.1',
        'field': 'Other RT Modality',
        'max_length': 2,
        'digit': True, 
        'choices': ['-9','-1','0', '2', '4', '8', '16', '32', '64'],
        'description': '記錄在申報醫院的首次療程中，進行放射治療所使用的特殊放射治療儀器或治療方式。',
        'purpose': '可作為治療結果分析之依據。'
    },
    '其他放射治療技術':{
        'ID':'4.2.3.2',
        'field': 'Other RT Technique',
        'max_length': 2,
        'digit': True,
        'choices': ['-9','-1','0', '1', '2', '3', '4', '5', '6', '7', '9', '10', '12', '17', '18', '20', '33', '34', '36', '65', '66', '68', '97', '98', '99'],
        'description': '記錄在申報醫院的首次療程中，進行特殊放射治療所使用的技術。',
        'purpose': '有助於分析治療技術與治療效果的關係。'
    },
    '其他放射治療臨床標靶體積':{
        'ID':'4.2.3.3.1',
        'field': 'Target of Other RT',
        'max_length': 2,
        'digit': True,
        'range': [0, 63],
        'SV': ['-9','-1'],
        'description': '記錄在申報醫院的首次療程中，利用放射線涵蓋局部原發腫瘤 (T)，區域淋巴結 (N) 或遠端轉移 (M) 來區分並記錄特殊放射治療的目標區域之範圍。',
        'purpose': '評估放射治療效果及檢討失敗原因。'
    },
    '其他放射治療臨床標靶體積劑量':{
        'ID':'4.2.3.3.2',    
        'field': 'Dose to Target of Other RT',
        'length': 5,
        'digit': True,      
        'range': [0, 99999],
        'description': '記錄在申報醫院的首次療程中，特殊放射治療的劑量。',
        'purpose': '評估放射治療效果及檢討失敗原因。' 
    },
    '其他放射治療臨床標靶體積治療次數':{
        'ID':'4.2.3.3.3',
        'field': 'Number of Fractions of Other RT',
        'length': 2,
        'digit': True,      
        'range': [0, 99],
        'description': '記錄在申報醫院的首次療程中，其他特殊放射治療次數 (fractions or sessions)。',
        'purpose': '評估放射治療效果。也可用來計算其他特殊放射治療的平均放射分次劑量，只要將「其他放射治療的放射線劑量」除以「其他放射治療的放射治療次數」即可得知。' 
    },
    '全身性治療開始日期':{
        'ID':'4.3.1',
        'field': 'Date of Systemic Therapy Started',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在任何醫療機構的首次療程中，全身性治療開始日期 (包含外院資料)。全身性治療包括化學治療、荷爾蒙/類固醇治療、免疫治療、骨髓/幹細胞移植或內分泌處置、標靶治療。',
        'purpose': '可以歸納各種治療方法的順序，評估診斷至治療及治療後至復發的時間間隔。'
    },
    '外院化學治療':{
        'ID':'4.3.2',
        'field': 'Chemotherapy at Other Facility',
        'length': 2,
        'digit': True,      
        'range': [0, 13],
        'SV': ['20', '21', '30', '31', '99'],
        'description': '記錄個案在外院首次療程中，所給予化學治療相關情形。化學治療包括多種抗癌藥物，可干擾癌細胞中DNA的合成和分裂。',
        'purpose': '全身性治療可為單一藥物或複合處方能包括給予個案一種或是多種的治療物質。本欄位可評估外院首次療程的化學治療。'
    },
    '申報醫院化學治療':{
        'ID':'4.3.3',
        'field': 'Chemotherapy at This Facility',
        'length': 2,
        'digit': True,      
        'range': [0, 13],
        'SV': ['20', '21', '30', '31', '81', '82', '83', '85', '86', '87', '88', '99'],
        'description': '記錄個案於申報醫院首次療程中，所給予化學治療相關情形。若個案未接受化學治療，則記錄未進行化學治療的原因。化學治療包括多種抗癌藥物，可干擾癌細胞中 DNA 的合成和分裂。',
        'purpose': '全身性治療可能包括單一或複合藥物處方。本欄位可評估首次療程的化學治療，及了解個案未接受化學治療的原因。'
    },
    '申報醫院化學治療開始日期':{
        'ID':'4.3.4',
        'field': 'Date of Chemotherapy Started at this Facility',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在申報醫院化學治療開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '外院荷爾蒙/類固醇治療':{
        'ID':'4.3.5',
        'field': 'Hormone/Steroid Therapy at Other Facility',
        'length': 2,
        'digit': True,      
        'choices': ['00', '01', '02', '03', '20', '21', '30', '31', '99'],
        'description': '記載個案在外院首次療程中，所給予荷爾蒙/類固醇治療的相關情形。荷爾蒙/類固醇治療包括了很多種藥物，其作用為控制影響癌症的生長。',
        'purpose': '全身性治療可能包括單一或複合藥物處方。本欄位可評估外院首次療程的荷爾蒙/類固醇治療。'
    },
    '申報醫院荷爾蒙/類固醇治療':{
        'ID':'4.3.6',
        'field': 'Hormone/Steroid Therapy at This Facility',
        'length': 2,
        'digit': True,
        'choices': ['00', '01', '02', '03', '20', '21', '30', '31', '82', '83', '85', '86', '87', '88', '99'],
        'description': '記載個案在申報醫院首次療程中，所給予荷爾蒙/類固醇治療的相關情形。假如個案沒有接受荷爾蒙/類固醇治療，則將沒有接受荷爾蒙/類固醇治療的原因加以編碼。荷爾蒙/類固醇治療包括了很多種藥物，其作用為控制影響癌症的生長。',
        'purpose': '全身性治療可能包括單一或複合藥物處方。本欄位可評估申報醫院首次療程的荷爾蒙治療/類固醇，及了解個案未接受荷爾蒙/類固醇治療的原因。'
    },
    '申報醫院荷爾蒙/類固醇治療開始日期':{
        'ID':'4.3.7',
        'field': 'Date of Hormone/Steroid Therapy Started at This Facility',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在申報醫院荷爾蒙/類固醇治療開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '外院免疫治療':{
        'ID':'4.3.8',
        'field': 'Immunotherapy at Other Facility',
        'length': 2,
        'digit': True,      
        'range': [0, 7],
        'SV': ['20', '21', '22', '23', '30', '31', '32', '33', '99'],
        'description': '記載個案在外院首次療程中，所給予免疫治療的相關情形。免疫治療包括了生物或是化學物質，這些物質可以改變人體免疫系統或改變人體對腫瘤細胞的免疫反應。',
        'purpose': '全身性治療可能包括單一或複合藥物處方。這項資料乃評估外院首次治療中給予個案的免疫治療，以及照護的品質。'
    },
    '申報醫院免疫治療':{
        'ID':'4.3.9',
        'field': 'Immunotherapy at This Facility',
        'length': 2,
        'digit': True,      
        'range': [0, 7],
        'SV': ['20', '21', '22', '23', '30', '31', '32', '33', '82', '83', '85', '86', '87', '88', '99'],
        'description': '記載申報醫院於首次療程中，所給予免疫治療的相關情形。假如個案沒有接受免疫治療，要將沒有接受免疫治療的原因加以編碼。免疫治療主要是利用生物反應或是化學物質，這些物質可以改變人體免疫系統或是改變人體對腫瘤細胞的免疫反應。',
        'purpose': '全身性治療可能包括單一或複合藥物處方。本欄位可評估申報醫院首次療程的免疫治療，及了解個案未接受免疫治療的原因。'
    },
    '申報醫院免疫治療開始日期':{
        'ID':'4.3.10',
        'field': 'Date of Immunotherapy Started at This Facility',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在申報醫院免疫治療開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '骨髓/幹細胞移植或內分泌處置':{
        'ID':'4.3.11',
        'field': 'Hematologic Transplant and Endocrine Procedure',
        'length': 2,
        'digit': True,      
        'choices': ['00', '10', '11', '12', '20', '21', '22', '25', '30', '40', '50', '82', '83', '85', '86', '87', '88', '99'],
        'description': '記錄個案在任何醫療機構首次治療時，給予骨髓/幹細胞移植或內分泌處置情形。若個案未接受此等治療，則依據其原因加以編碼。此等治療包括骨髓移植、幹細胞移植、或以放射線照射或手術切除之內分泌處置。',
        'purpose': '瞭解與骨髓/幹細胞移植或內分泌處置有關的治療型式及照護品質，及個案未接受骨髓/幹細胞移植或內分泌處置的原因。'
    },
    '申報醫院骨髓/幹細胞移植或內分泌處置開始日期':{
        'ID':'4.3.12',
        'field': 'Date of Hematologic Transplant and Endocrine Procedures Started at This Facility',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在申報醫院骨髓/幹細胞移植或內分泌處置開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '外院標靶治療':{
        'ID':'4.3.13',
        'field': 'Targeted therapy at Other Facility',
        'length': 2,
        'digit': True,      
        'choices': ['00', '01', '20', '21', '30', '31', '99'],
        'description': '記錄個案在外院首次療程中，所給予標靶治療相關情形。標靶治療包括多種抗癌藥物，可能與細胞癌化過程有關的分子或是酵素，為一種新的標的性治療藥物直接作用於癌細胞中的異常蛋白，是與癌細胞異常增生或是抗藥性增加有關的細胞訊息傳導路徑、或是促進腫瘤異常的血管增生及癌細胞轉移的調控機轉等。以透過對這些異常機轉的抑制以達到抗癌的治療效果，故此類標靶藥物具有癌細胞專一性。',
        'purpose': '本欄位可評估外院首次療程的標靶治療。'
    },
    '申報醫院標靶治療':{
        'ID':'4.3.14',
        'field': 'Targeted therapy at This Facility',
        'length': 2,
        'digit': True,      
        'choices': ['00', '01', '20', '21', '30', '31', '82', '83', '85', '86', '87', '88', '99'],
        'description': '記錄個案在申報醫院首次療程中，所給予標靶治療相關情形。標靶治療包括多種抗癌藥物，可能與細胞癌化過程有關的分子或是酵素，為一種新的標地性治療藥物直接作用於癌細胞中的異常蛋白，是與癌細胞異常增生或是抗藥性增加有關的細胞訊息傳導路徑、或是促進腫瘤異常的血管增生及癌細胞轉移的調控機轉等。以透過對這些異常機轉的抑制以達到抗癌的治療效果，故此類標靶藥物具有癌細胞專一性。',
        'purpose': '本欄位可評估申報醫院首次療程的標靶治療。'
    },
    '申報醫院標靶治療開始日期':{
        'ID':'4.3.15',
        'field': 'Date of Targeted therapy Started at This Facility',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案在申報醫院標靶治療開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '申報醫院緩和照護': {
        'ID':'4.4',
        'field': 'Palliative Care at This Facility',
        'length': 1,
        'digit': True,
        'SV': ['9'],       
        'range': [0, 7],
        'description': '申報醫院為緩解或減輕個案症狀所提供之照護，包括手術治療、放射治療、全身性治療 (化學治療、荷爾蒙治療或其他全身性藥物) 及疼痛控制治療。',
        'purpose': '申報醫院可藉本欄位探知其照護為緩和性而非診斷或治癒性目的。'
    },
    '其他治療': {
        'ID':'4.5.1',
        'field': 'Other Treatment',
        'length': 2,
        'digit': True,
        'choices': ['00', '01', '02', '03', '99'],
        'description': '記錄個案在任何醫療機構的首次療程中，所給予其他治療相關情形。其他治療的定義為未能歸類於手術、放射治療、全身性藥物治療或輔助性治療 (ancillary treatment)。',
        'purpose': '其他治療的資訊用來敘述及評估照護品質和治療成效。'
    },
    '其他治療開始日期':{
        'ID':'4.5.2',
        'field': 'Date of Other Treatment Started',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '收錄其他治療在任何醫療機構開始的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '首次復發或癌症狀態追蹤日期':{
        'ID':'5.1',
        'field': 'Date of First Recurrence or Cancer Status Follow-Up',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄此癌症首次復發或癌症狀態追蹤的日期。',
        'purpose': '評估首次治療的效果。'
    },
    '首次復發型式':{
        'ID':'5.2',
        'field': 'Type of First Recurrence',
        'length': 2,
        'digit': True,      
        'choices': ['00', '04', '06', '10', '13', '14', '15', '16', '17', '20', '21', '22', '25', '26', '27', '30', '36', '40', '46', '51', '52', '53', '54', '55', '56', '57', '58', '59', '60', '62', '70', '88', '99'],
        'description': '個案經病歷記載經過一段無病 (disease-free intermission) 或緩解 (remission) 期間，首次出現復發的型式。',
        'purpose': '評估治療的成效及預後因子。'
    },
    '最後聯絡或死亡日期':{
        'ID':'5.3',
        'field': 'Date of Last Contact or Death',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄個案的最後聯絡日期或是死亡日期。',
        'purpose': '作為個案追蹤和治療結果研究之用。'
    },
    '生存狀態':{
        'ID':'5.4',
        'field': 'Vital Status',
        'length': 1,
        'digit': True,
        'choices': ['0', '1'],
        'description': '記錄個案「最後聯絡或死亡日期」的存活狀態。',
        'purpose': '作為個案追蹤和治療結果研究之用。'
    },
    '摘錄者': {
        'ID':'6.1',
        'field': 'Abstracted by', 
        'max_length': 10, 
        'description': '記錄摘錄此癌症登記個案人員之癌症登記證照編號或姓名。',
        'purpose': '作為申報醫院內部於數名工作人員在資料庫之品質管控與管理。'
    },
    '身高': {
        'ID':'7.1',
        'field': 'Height',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄個案於首次治療前的身高。',
        'purpose': '肥胖是致癌的危險因子，為瞭解個案肥胖狀態，需得知個案身體質量指數 (BMI)，而身高是計算 BMI 所需數值。'
    },
    '體重': {
        'ID':'7.2',
        'field': 'Weight',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄個案於首次治療前的體重。',
        'purpose': '肥胖是致癌的危險因子，為瞭解個案肥胖狀態，需得知個案身體質量指數 (BMI)，而體重是計算 BMI 所需數值。'
    },
    '吸菸行為': {
        'ID':'7.3',
        'field': 'Smoking Behavior',
        'length': 6,
        'digit': True,     
        'range': [0, 999999],
        'description': '記錄個案於最初診斷日前的吸菸行為。',
        'purpose': '吸菸是致癌的危險因子。'
    },
    '嚼檳榔行為': {
        'ID':'7.4',
        'field': 'Betel Nut Chewing Behavior',
        'length': 6,
        'digit': True,     
        'range': [0, 999999],
        'description': '記錄個案於最初診斷日前的嚼檳榔行為。',
        'purpose': '嚼檳榔是致癌的危險因子。'
    },
    '喝酒行為':{
        'ID':'7.5',
        'field': 'Drinking Behavior',
        'length': 3,
        'digit': True,
        'choices': ['000', '001', '002', '003', '004', '009', '999'],
        'description': '記錄個案於最初診斷日前的喝酒行為。',
        'purpose': '喝酒是致癌的危險因子。'
    },
    '首次治療前生活功能狀態評估': {
        'ID':'7.6',
        'field': 'Assessment of Performance Status before Treatment',
        'length': 3,
        'digit': True,
        'choices': ['000', '001', '002', '003', '004', '005', '100', '104', '204', '209', '303', '304', '309', '403', '409', '502', '503', '509', '602', '609', '701', '702', '709', '801', '809', '900', '901', '909', '988', '999'],
        'description': '記錄醫師於首次治療前最近一次評估個案的生活功能狀態。',
        'purpose': '本項目的資料可作為訂定個案治療計畫參考之用。'
    },
    '癌症部位特定因子 1':{
        'ID':'8.1',
        'field': 'Site-Specific Factor 1',
        'length': 3, 
        'patterns': [
                        {'name': '白血病', 'regex': r'^8XX$'},
                        {'name': '子宮體癌、乳癌', 'regex': r'^[ISW]\d{2}$'},
                        {'name': '肝癌', 'regex': r'^[A]\d{2}$'},
                        {'name': '一般癌別', 'regex': r'^\d{3}$'},
        ],  
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 2':{
        'ID':'8.2',
        'field': 'Site-Specific Factor 2',
        'length': 3,
        'patterns': [
                        {'name': '白血病', 'regex': r'^8XX$'},
                        {'name': '子宮體癌、乳癌', 'regex': r'^[ISW]\d{2}$'},
                        {'name': '一般癌別', 'regex': r'^\d{3}$'},
        ],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 3':{
        'ID':'8.3',
        'field': 'Site-Specific Factor 3',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 4':{
        'ID':'8.4',
        'field': 'Site-Specific Factor 4',
        'length': 3,
        'patterns': [
                        {'name': '胰臟癌', 'regex': r'^[A]\d{2}$'},
                        {'name': '一般癌別', 'regex': r'^\d{3}$'},
        ],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 5':{
        'ID':'8.5',
        'field': 'Site-Specific Factor 5',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 6':{
        'ID':'8.6',
        'field': 'Site-Specific Factor 6',
        'length': 3,
        'patterns': [
                        {'name': '肺癌', 'regex': r'^[A-Z]\d{2}$'},
                        {'name': '一般癌別', 'regex': r'^\d{3}$'},
        ],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 7':{
        'ID':'8.7',
        'field': 'Site-Specific Factor 7',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 8':{
        'ID':'8.8',
        'field': 'Site-Specific Factor 8',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 9':{
        'ID':'8.9',
        'field': 'Site-Specific Factor 9',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '癌症部位特定因子 10':{
        'ID':'8.10',
        'field': 'Site-Specific Factor 10',
        'length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄與癌症預後和治療決策有關之癌症部位特定因子',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    }
}

