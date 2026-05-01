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
        'SV': '9999999999',
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
        'SV': '9999999999',
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
        'purpose': '可作為各癌症部位性別比例及預後之比較。個案若有多重原發，其病歷紀錄上的性別都應相同。'
    },
    '出生日期': {
        'ID':'1.6',
        'field': 'Date of Birth',
        'length': 8,
        'SV': '99999999',
        'is_date': '%Y%m%d',
        'description': '確認個案的出生日期。',
        'purpose': '有助於確認個案的身份；對於以個案世代研究(patient cohort)作為腫瘤分析也很有幫助。'
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
        'max_length': 3,
        'digit': True,
        'SV': '999',       
        'range': [0, 120],
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
        'purpose': '在做治療和存活分析時，本欄位將個案分為可分析和不可分析個案兩類。進而提供申報醫院進行研究個案之選擇。'
    },
    '診斷狀態分類': {
        'ID':'2.3.1',
        'field': 'Class of Diagnosis Status',
        'length': 1,
        'digit': True,     
        'choices': ['1', '2', '3', '5', '7', '8'],
        'description': '記錄個案至申報醫院首次為此癌症就診時的癌症診療情境。',
        'purpose': '與新增欄位2.3.2「治療狀態分類」並用，以確保欄位 2.3「個案分類」的正確性。'
    },
    '治療狀態分類': {
        'ID':'2.3.2',
        'field': 'Class of Treatment Status',
        'length': 1,
        'digit': True,     
        'range': [0, 9],
        'description': '記錄此個案在申報時的治療狀態。',
        'purpose': '此欄位用於確保個案分類欄位 2.3 的正確性，並協助記錄個案未於申報醫院接受首次療程的原因，供申報醫院改善流失管理及作為公衛行政資源調整依據。'
    },
    '首次就診日期': {
        'ID':'2.4',
        'field': 'Date of First Contact',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '個案因此癌症至申報醫院門診或住院之最早日期。',
        'purpose': '可用來計算個案首次就診至進行癌症登記之時間間隔；也可用來計算首次就診至治療之時間差距，以監控癌症照護品質。'
    },
    '最初診斷日期':{
        'ID':'2.5',
        'field': 'Date of Initial Diagnosis',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄此癌症最早被醫師診斷的日期。',
        'purpose': '可計算癌症最初診斷日期至完成分期或開始治療的時間間隔。'
    },
    '原發部位':{
        'ID':'2.6',
        'field': 'Primary Site',
        'max_length': 5,
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
        'purpose': '側性可提供分期及癌病侵犯程度的資訊，並可確定原發侵犯的數目。'
    },
    '組織型態':{
        'ID':'2.8',
        'field': 'Histology',
        'max_length':5,
        #'digit': True,
        'range': [8000, 9999],
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
        'purpose': '病理醫師常使用 0、1、2、3、6、9 等碼來描述腫瘤性態；若性態碼為 2、3、6 或 9（或已轉為 3），需申報至癌症登記中心，以便統計、監測。'
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
        'pattern_range': '1-5, 8-9, A-E, H, L-M, S, X',
        'description': '收錄實質腫瘤於原發部位手術之後的分級/分化。分級/分化為腫瘤和正常組織的相似的程度。Well differentiated (Grade I)和正常組織最相似；Undifferentiated (Grade IV)和正常組織差異最大。',
        'purpose': '與個案的預後有關。分級/分化可用以評估癌症嚴重程度；分級/分化及細胞型態對於許多癌症而言是重要的預後因子。分級/分化對於某些癌症更是判定病理期別的依據之一。'
    },
    '癌症確診方式':{
        'ID':'2.11',
        'field': 'Diagnostic Confirmation',
        'length':1,
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
    '首次手術日期':{
        'ID':'4.1.1',
        'field': 'Date of First Surgical Procedure',
        'length': 8,
        'SV': ['00000000', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在任何醫療機構，最早針對癌症進行手術的日期。',
        'purpose': '可進行多種治療模式的排序或是評估多種治療的時間間隔。'
    },
    '申報醫院原發部位手術方式':{
        'ID':'4.1.4',
        'field': 'Surgical Procedure of Primary Site at This Facility',
        'max_length': 3,
        'digit': True,
        'pattern_range': '000, 800-900, 990',
        'description': '記錄在申報醫院對原發部位所進行的手術方式。',
        'purpose': '用來比較不同治療方式的效果。'
    },
    '放射治療開始日期':{
        'ID':'4.2.1.3',
        'field': 'Date of RT Started',
        'length': 8,
        'SV': ['00000000', '88888888', '99999999'],  
        'is_date': '%Y%m%d',
        'description': '記錄在申報醫院的首次療程中，進行放射治療的開始日期。',
        'purpose': '在併用多重治療模式中，病理期別是許多癌症的重要預後因素，也是決定後續輔助治療與否的依據；故需記錄各治療方式之時間順序及實際間隔。手術前之放射治療可能改變期別，影響其在分析評估中的應用。'
    },
    '放射治療機構':{
        'ID':'4.2.1.7',
        'field': 'Institute of RT',
        'length': 1,
        'digit': True,
        'choices': ['0', '1', '9'],
        'description': '記錄在申報醫院的首次療程中，進行放射治療的相關情形。',
        'purpose': '本欄位資料對於瞭解放射治療的轉介形式和評估對個案進行放射治療的場所其品質和結果，可以提供相當有用的資訊。'
    },
    '申報醫院化學治療':{
        'ID':'4.3.3',
        'field': 'Chemotherapy at This Facility',
        'length': 2,
        'digit': True,      
        'range': [4, 13],
        'SV': '00, 01, 20, 21, 30, 31, 88, 99',
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
    '申報醫院荷爾蒙/類固醇治療':{
        'ID':'4.3.6',
        'field': 'Hormone/Steroid Therapy at This Facility',
        'length': 2,
        'digit': True,
        'choices': ['00', '01', '02', '03', '20', '21', '30', '31', '88', '99'],
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
    '申報醫院免疫治療':{
        'ID':'4.3.9',
        'field': 'Immunotherapy at This Facility',
        'length': 2,
        'digit': True,      
        'range': [0, 7],
        'SV': '20, 21, 22, 23, 30, 31, 32, 33, 40, 41, 88, 99',
        'description': '記載申報醫院於首次療程中，所給予免疫治療的相關情形。若個案未接受免疫治療，需編碼其未接受的原因。',
        'purpose': '評估申報醫院首次療程中的免疫治療情形，並了解個案未接受免疫治療的原因。'
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
        'choices': ['00', '10', '20', '30', '40', '88', '99'],
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
    '申報醫院標靶治療':{
        'ID':'4.3.14',
        'field': 'Targeted therapy at This Facility',
        'length': 2,
        'digit': True,      
        'choices': ['00', '01', '20', '21', '30', '31', '88', '99'],
        'description': '記錄個案在申報醫院首次療程中，所給予標靶治療相關情形。標靶治療包括多種抗癌藥物，可能與細胞癌化過程有關的分子或是酵素，為一種新的標的性治療藥物直接作用於癌細胞中的異常蛋白，是與癌細胞異常增生或是抗藥性增加有關的細胞訊息傳導路徑、或是促進腫瘤異常的血管增生及癌細胞轉移的調控機轉等。以透過對這些異常機轉的抑制以達到抗癌的治療效果，故此類標靶藥物具有癌細胞專一性。',
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
        'SV': '9',       
        'range': [0, 7],
        'description': '申報醫院為緩解或減輕個案症狀所提供之照護，包括手術治療、放射治療、全身性治療 (化學治療、荷爾蒙治療或其他全身性藥物) 及疼痛控制治療。',
        'purpose': '申報醫院可藉本欄位探知其照護為緩和性而非診斷或治癒性目的。'
    },
    '其他治療': {
        'ID':'4.5.1',
        'field': 'Other Treatment',
        'length': 2,
        'digit': True,
        'choices': ['00', '01', '99'],
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
        'max_length': 3,
        'digit': True,     
        'range': [0, 999],
        'description': '記錄個案於首次治療前的體重。',
        'purpose': '肥胖是致癌的危險因子，為瞭解個案肥胖狀態，需得知個案身體質量指數 (BMI)，而體重是計算 BMI 所需數值。'
    },
    '吸菸行為': {
        'ID':'7.3',
        'field': 'Smoking Behavior',
        'max_length': 6,
        'digit': True,     
        'range': [0, 999999],
        'description': '記錄個案於最初診斷日前的吸菸行為。',
        'purpose': '吸菸是致癌的危險因子。'
    },
    '嚼檳榔行為': {
        'ID':'7.4',
        'field': 'Betel Nut Chewing Behavior',
        'max_length': 6,
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
    '其他因子 6':{
        'ID':'7.6',
        'field': 'Other Factor 6',
        'length': 3,
        'digit': True,
        'SV': '988',
        'description': '記錄與癌症預後和治療決策相關之其他因子。',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '同癌家族病史': {
        'ID':'7.7',
        'field': 'Family History of Same Cancer',
        'length': 6,
        'regex': r'^[019]{2}[0-9AX]{4}$',
        'description': '記錄個案有血緣關係之家庭成員中是否患有相同癌症的家族病史。',
        'purpose': '家族病史為致癌的危險因子之一。'
    },
    '其他因子 8':{
        'ID':'7.8',
        'field': 'Other Factor 8',
        'length': 3,
        'digit': True,
        'SV': '988',
        'description': '記錄與癌症預後和治療決策相關之其他因子。',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '其他因子 9':{
        'ID':'7.9',
        'field': 'Other Factor 9',
        'length': 3,
        'digit': True,
        'SV': '988',
        'description': '記錄與癌症預後和治療決策相關之其他因子。',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
    '其他因子 10':{
        'ID':'7.10',
        'field': 'Other Factor 10',
        'length': 3,
        'digit': True,
        'SV': '988',
        'description': '記錄與癌症預後和治療決策相關之其他因子。',
        'purpose': '因應臨床實務需求及癌症診療品質提升。'
    },
}

