window.DashboardI18n = (function() {
    const resources = {
        'zh-TW': {
            translation: {
                language: '語言', source: '資料來源：癌症登記資料庫', table: '表', chart: '圖', chartSexAge: '性別與年齡分佈', chartAgeMedian: '年齡中位數', chartAnalyzable: '可分析個案與確診個案', chartHistology: '組織型態', chartClassification: '個案分類',
                newDiagnosis: '新診斷', cancer: '癌', patient: '病患', distribution: '分佈',
                sexAge: '性別及年齡', ageGroup: '年齡層次', sex: '性別', male: '男', female: '女', total: '總計', cases: '個案數',
                ageMedian: '年齡中位數', item: '項目', incidentCases: '發生個案', sexRatio: '性別比',
                medianCharacteristic: '項目', medianN: '個案數(人)', medianAgeYears: '年齡中位數', medianMaleToFemaleRatio: '性別比', medianSex: '發生個案',
                analyzableConfirmed: '癌症登記可分析個案與確診個案', cancerTotal: '癌症總數', analyzableCases: '可分析個案數',
                analyzablePercent: '可分析個案百分比', confirmedCases: '顯微鏡檢確診個案數', confirmedPercent: '確診個案百分比',
                analyzableNote: '* 可分析個案包含：', analysisEligibleCases: '*可分析個案數', analysisEligiblePercent: '可分析個案百分比', microscopicallyConfirmedCases: '顯微鏡檢確診個案數', microscopicallyConfirmedPercent: '確診個案百分比', analysisEligibleNote: '* 可分析個案包含：', analysisEligibleClass1: 'Class1 本院診斷，並於本院接受全部或部分首次治療。', analysisEligibleClass2: 'Class2 他院診斷，於本院接受全部或部分首次治療。', histology: '組織型態', histologyDistribution: '組織型態分佈圖',
                icdoCode: 'ICD-O編碼', people: '人數', percentage: '百分比', caseRatio: '個案比例', noData: '無資料',
                generatingInsight: '分析中，請稍候...', regenerateInsight: '重新產生敘述', insightFailed: '產生敘述失敗：', autoInsight: '（系統將自動產生分析敘述）',
                llmInsight: '語言模型敘述', ineligibleCases: '不適用個案說明', warningDetails: '以下個案未納入組織型態統計：', details: '說明', confirm: '確定',
                histologyRuleExcluded: '{{code}} 未納入 1.3 組織型態規則。', histologyRuleExcludedDetail: '若此組織型態無特殊適用條件，則此組織代碼組合不屬於目前統計規則範圍。',
                histologyConditionMismatch: '{{code}} 不適用於此個案，組織型態與適用年度或原發部位不符，請再確認。', histologyConditionMismatchDetail: '此組織型態有特殊適用條件，請確認診斷年度與原發部位是否符合。', colonHistologyNote: '註：有一筆組織型態不適用，已排除統計（{{user}} 不符合 M8211 診斷年度規範）',
                histologyRawReview: '請確認原始資料：{{details}}',
                classification: '個案分類', classificationDistribution: '個案分類分佈圖', dataView: '數據檢視', close: '關閉', refresh: '更新', downloadImage: '下載圖片',
                class0: 'Class0 本院診斷，未於本院接受首次治療',
                class1: 'Class1 本院診斷，並於本院接受全部或部分首次治療。',
                class2: 'Class2 他院診斷，於本院接受全部或部分首次治療。',
                class3: 'Class3 他院診斷，未於本院接受首次治療，或因復發／持續癌症問題至本院就診。',
                class010: '未接受任何治療即死亡或病危(0.1.0)', class012: '首次療程未於本院進行，或本院僅提供支援／諮詢(0.1.2)',
                class111: '首次療程僅於本院完成(1.1.1)', class113: '首次療程由本院與他院共同完成(1.1.3)', class114: '首次療程為觀察、支持性或緩和治療(1.1.4)',
                class221: '首次療程僅於本院完成(2.2.1)', class223: '首次療程由本院與他院共同完成(2.2.3)',
                class320: '未接受任何治療即死亡或病危(3.2.0)', class332: '首次療程未於本院進行，或本院僅提供支援／諮詢(3.3.2)'
            }
        },
        en: {
            translation: {
                language: 'Language', source: 'Source: Cancer Registry Database', table: 'Table', chart: 'Figure', chartSexAge: 'Sex and age distribution', chartAgeMedian: 'Median age', chartAnalyzable: 'Analyzable and confirmed cases', chartHistology: 'Histology', chartClassification: 'Class',
                newDiagnosis: 'Newly diagnosed ', cancer: ' cancer', patient: ' patients', distribution: ' distribution',
                sexAge: 'Sex and age', ageGroup: 'Age', sex: 'Sex', male: 'Male', female: 'Female', total: 'Total', cases: 'Cases',
                ageMedian: 'Median age', item: 'Item', incidentCases: 'Incident cases', sexRatio: 'Sex ratio',
                medianCharacteristic: 'Characteristic', medianN: 'N', medianAgeYears: 'Median Age (years)', medianMaleToFemaleRatio: 'Male-to-Female Ratio', medianSex: 'Sex',
                analyzableConfirmed: 'Analyzable and microscopically confirmed cancer cases', cancerTotal: 'Total Cancer Cases', analyzableCases: 'Analyzable cases',
                analyzablePercent: 'Analyzable cases (%)', confirmedCases: 'Microscopically confirmed cases', confirmedPercent: 'Confirmed cases (%)',
                analyzableNote: '* Analyzable cases include:', analysisEligibleCases: '*Analysis-Eligible Cases (n)', analysisEligiblePercent: 'Analysis-Eligible Cases (%)', microscopicallyConfirmedCases: 'Microscopically Confirmed Cases (n)', microscopicallyConfirmedPercent: 'Microscopically Confirmed Cases (%)', analysisEligibleNote: 'Analysis-Eligible Cases :', analysisEligibleClass1: 'Class 1: Diagnosed and treated at our hospital (all or part of first course treatment)', analysisEligibleClass2: 'Class 2: Diagnosed elsewhere, treated at our hospital (all or part of first course treatment)', histology: 'Histology', histologyDistribution: 'Histology distribution',
                icdoCode: 'ICD-O', people: 'N', percentage: 'Percentage', caseRatio: 'Case proportion', noData: 'No data',
                generatingInsight: 'Generating analysis…', regenerateInsight: 'Regenerate analysis', insightFailed: 'Unable to generate analysis: ', autoInsight: '(The system will generate an analysis automatically.)',
                llmInsight: 'AI-generated narrative', ineligibleCases: 'Ineligible case details', warningDetails: 'The following cases were excluded from the histology statistics:', details: 'Details', confirm: 'OK',
                histologyRuleExcluded: '{{code}} is not included in the histology reporting rules.', histologyRuleExcludedDetail: 'This histology code combination is outside the current reporting rules.',
                histologyConditionMismatch: '{{code}} is not applicable to this case because its diagnosis year or primary site does not meet the histology requirements.', histologyConditionMismatchDetail: 'This histology has special eligibility requirements. Please verify the diagnosis year and primary site.', colonHistologyNote: 'Note: one ineligible histology case was excluded from the statistics ({{user}} does not meet the M8211 diagnosis-year requirement).',
                histologyRawReview: 'Please review the source data: {{details}}',
                classification: 'Case classification', classificationDistribution: 'Case classification distribution', dataView: 'Data view', close: 'Close', refresh: 'Refresh', downloadImage: 'Save image',
                class0: 'Class0  Diagnosed at Our Hospital, No First Course Treatmented at this hospital; no initial treatment received here.',
                class1: 'Class1  Diagnosed & First Course Treatment at Our Hospital',
                class2: 'Class2  Diagnosed Elsewhere, First Course Treatment at Our Hospital',
                class3: 'Class3  Diagnosed Elsewhere, No First Course Treatment at Our Hospital',
                class010: 'Died or critically ill before treatment(0.1.0)', class012: 'First course treatment elsewhere / Consultation or supportive care only(0.1.2)',
                class111: 'First Course Completed at Our Hospital(1.1.1)', class113: 'Shared First Course Treatment with another hospital(1.1.3)', class114: 'Observation / Supportive / Palliative Care(1.1.4)',
                class221: 'First Course Completed at Our Hospital(2.2.1)', class223: 'Shared First Course Treatment with another hospital(2.2.3)',
                class320: ' Died or Critically Ill Before Treatment(3.2.0)', class332: ' First Course Treatment Elsewhere / Consultation or Supportive Care Only(3.3.2)'
            }
        }
    };

    let language = 'zh-TW';
    const engine = window.i18next;
    if (engine) engine.init({ lng: language, fallbackLng: 'zh-TW', resources, initImmediate: false });
    document.documentElement.lang = language;

    const translate = (key, options) => {
        if (engine) return engine.t(key, options);
        return resources[language].translation[key] || resources['zh-TW'].translation[key] || key;
    };

    return {
        t: translate,
        getLanguage: () => engine ? engine.language : language,
        setLanguage: async (nextLanguage) => {
            language = nextLanguage;
            if (engine) await engine.changeLanguage(nextLanguage);
            document.documentElement.lang = nextLanguage;
            if (window.DashboardRenderer?.rerenderDashboardLanguage) {
                window.DashboardRenderer.rerenderDashboardLanguage({ regenerateInsights: true });
            }
        }
    };
})();
