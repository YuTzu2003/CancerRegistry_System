window.dashboardChartInstance = null;
window.dashboardHistologyChartInstance = null;
window.dashboardSurvivalChartInstance = null;
window.dashboardStageDistributionChartInstance = null;
window.dashboardStageSexChartInstance = null;
window.dashboardStageAgeChartInstance = null;
window.DashboardRenderer = {};
window.DashboardRenderer.t = function(key, options) {
    return window.DashboardI18n ? window.DashboardI18n.t(key, options) : key;
};
window.DashboardRenderer.sourceLine = function() {
    return `<br><span class="text-muted fw-normal" style="font-size: 0.85em;">${this.t('source')}</span>`;
};
window.DashboardRenderer.axisLabelLines = function(value, maxLength = 68) {
    const lines = [];
    const segments = String(value ?? '')
        .trim()
        .replace(/\s*(?=[\[［])/g, '\n')
        .split('\n')
        .filter(Boolean);
    segments.forEach(segment => {
        let line = '';
        const segmentMaxLength = /^[\[［]/.test(segment) ? 88 : 82;
        segment.split(/\s+/).filter(Boolean).forEach(word => {
            const candidate = line ? `${line} ${word}` : word;
            if (line && candidate.length > segmentMaxLength) {
                lines.push(line);
                line = word;
            } else {
                line = candidate;
            }
        });
        if (line) lines.push(line);
    });
    return lines.length ? lines : [''];
};
window.DashboardRenderer.rightAlignedAxisLabel = function(value, maxLength = 68) {
    return this.axisLabelLines(value, maxLength)
        .map(text => `{${/^[\[［]/.test(text) ? 'bracket' : 'right'}|${text}}`)
        .join('\n');
};
window.DashboardRenderer.histologyRowHeight = function(names) {
    const maxLines = Math.max(1, ...names.map(name => this.axisLabelLines(name).length));
    return Math.max(40, maxLines * 18 + 8);
};
window.DashboardRenderer.reportCaption = function(kind, yearTitle, cancerTitle, description, options = {}) {
    const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
    const prefix = kind === 'table' ? this.t('table') : this.t('chart');
    const suffix = kind === 'table' ? this.t('table') : this.t('chart');
    if (isEnglish) {
        const subject = options.newDiagnosis
            ? `Newly diagnosed ${cancerTitle} patients`
            : cancerTitle;
        return `${prefix} ${yearTitle} ${subject} ${description}${kind === 'table' ? ' table' : ''}${this.sourceLine()}`;
    }
    const subject = options.newDiagnosis
        ? `年新診斷${cancerTitle}病患`
        : `年${cancerTitle}`;
    return `${prefix}、${yearTitle}${subject}${description}${suffix}${this.sourceLine()}`;
};
window.DashboardRenderer.getEnglishCancerPatientLabel = function(cancerTitle) {
    if (!cancerTitle) return 'Cancer';
    return /cancer|carcinoma|lymphoma|leukemia/i.test(cancerTitle)
        ? cancerTitle
        : `${cancerTitle} Cancer`;
};

window.DashboardRenderer.getGenderAgeChartOption = function(genderAgeData) {
        const categories = (genderAgeData?.categories || ['≦19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '≧85'])
            .map(label => ['<=19', '≤19', '≦19'].includes(label) ? '≦19' : ['>=85', '≥85', '≧85'].includes(label) ? '≧85' : label);
        const male = genderAgeData?.male || [];
        const female = genderAgeData?.female || [];
        const total = genderAgeData?.total || [];
        const maxValue = Math.max(0, ...male, ...female, ...total);
        const yMax = Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(this.getSelectedCancerTitle());
        const titleText = isEnglish
            ? `Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)} Patients, ${this.getSelectedYearTitle()}`
            : `${this.getSelectedYearTitle()}年新診斷${selectedCancer}病患${this.t('sexAge')}${this.t('distribution')}${this.t('chart')}`;

        return {
          title: {
            text: titleText,
            subtext: this.t('source'),
            left: 'center',
            top: 0,
            textStyle: { fontSize: 18, fontWeight: 'bold' },
            subtextStyle: { fontSize: 12 }
          },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: 72, right: 72, top: 98, bottom: 74, containLabel: false },
          legend: { data: [this.t('male'), this.t('female'), this.t('total')], top: 52, left: 'center', itemGap: 12 },
          toolbox: {
            right: 16,
            top: 0,
            feature: {
              dataView: { show: true, readOnly: false, title: this.t('dataView'), lang: [this.t('dataView'), this.t('close'), this.t('refresh')] },
              saveAsImage: { show: true, title: this.t('downloadImage') }
            }
          },
          xAxis: [{
            type: 'category',
            data: categories,
            name: this.t('age'),
            nameLocation: 'middle',
            nameGap: 30,
            axisPointer: { type: 'shadow' },
            axisTick: { alignWithLabel: true },
            axisLabel: { interval: 0 }
          }],
          yAxis: [{
            type: 'value',
            min: 0,
            max: yMax,
            minInterval: 1,
            splitNumber: 5,
            axisLabel: { formatter: '{value}' },
            splitLine: { lineStyle: { color: '#e5eaf3' } }
          }],
          series: [
            {
              name: this.t('male'),
              type: 'bar',
              data: male,
              barWidth: 20,
              barGap: '20%',
              barCategoryGap: '42%',
              itemStyle: { color: '#5470C6' }
            },
            {
              name: this.t('female'),
              type: 'bar',
              data: female,
              barWidth: 20,
              itemStyle: { color: '#EE6666' }
            },
            {
              name: this.t('total'),
              type: 'bar',
              data: total,
              barWidth: 20,
              z: 5,
              itemStyle: { color: '#91CC75' }
            }
          ]
        };
    };

// Shared annual-report rendering primitives used by both analysis and comparison pages.
window.DashboardRenderer.axisLabelLines = function(value, maxLength = 68) {
    return window.AnnualReportRenderer.axisLabelLines(value, maxLength);
};
window.DashboardRenderer.rightAlignedAxisLabel = function(value, maxLength = 68) {
    return window.AnnualReportRenderer.rightAlignedAxisLabel(value, maxLength);
};
window.DashboardRenderer.histologyRowHeight = function(names) {
    return window.AnnualReportRenderer.histologyRowHeight(names);
};
window.DashboardRenderer.getGenderAgeChartOption = function(genderAgeData) {
    const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
    const selectedCancer = this.getCancerTitleForSentence(this.getSelectedCancerTitle());
    const titleText = isEnglish
        ? `Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)} Patients, ${this.getSelectedYearTitle()}`
        : `${this.getSelectedYearTitle()}年新診斷${selectedCancer}病患${this.t('sexAge')}${this.t('distribution')}${this.t('chart')}`;

    return window.AnnualReportRenderer.getGenderAgeChartOption(genderAgeData, {
        title: titleText,
        source: this.t('source'),
        labels: {
            male: this.t('male'),
            female: this.t('female'),
            total: this.t('total'),
            age: this.t('age'),
            dataView: this.t('dataView'),
            close: this.t('close'),
            refresh: this.t('refresh'),
            downloadImage: this.t('downloadImage')
        }
    });
};

document.addEventListener('DOMContentLoaded', function() {
    /* ── 性別與年齡分佈圖表 ── */
    var chartDom = document.getElementById('main');
    if (chartDom) {
        var myChart = echarts.init(chartDom);
        window.dashboardChartInstance = myChart;
        myChart.setOption(window.DashboardRenderer.getGenderAgeChartOption({
          categories: ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85'],
          male: [],
          female: [],
          total: []
        }));
        
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }

    /* ── 組織型態分佈圖表 ── */
    var histChartDom = document.getElementById('histologyChart');
    if (histChartDom) {
        var myHistChart = echarts.init(histChartDom);
        window.dashboardHistologyChartInstance = myHistChart;
        var histOption = {
          title: { text: window.DashboardRenderer.t('histologyDistribution'), subtext: window.DashboardRenderer.t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold' } },
          tooltip: { 
            trigger: 'axis', 
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              const p = params[0];
              if (!p || p.value === undefined || p.value === '-') return '';
              const count = p.data && p.data.count !== undefined ? p.data.count : '-';
              const val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
              const countText = window.DashboardI18n?.getLanguage() === 'en' ? `N = ${count}` : `${count} 人`;
              return `${p.name}<br/>${p.marker}${window.DashboardRenderer.t('caseRatio')}: ${val}% (${countText})`;
            }
          },
          grid: {
            left: 410,
            right: 125,
            bottom: 50,
            top: 60,
            containLabel: false
          },
          legend: { show: false },
          toolbox: {
            feature: {
              dataView: { show: true, readOnly: false, title: window.DashboardRenderer.t('dataView'), lang: [window.DashboardRenderer.t('dataView'), window.DashboardRenderer.t('close'), window.DashboardRenderer.t('refresh')] },
              saveAsImage: { show: true, title: window.DashboardRenderer.t('downloadImage') }
            }
          },
          xAxis: { 
            type: 'value', 
            name: window.DashboardRenderer.t('percentage') + ' (%)',
            nameLocation: 'middle', 
            nameGap: 30,
            min: 0,
            interval: 10,
            axisLabel: {
              formatter: function(value) {
                return value.toFixed(1) + '%';
              }
            }
          },
          yAxis: { 
            type: 'category', 
            data: [], 
            inverse: true,
            axisLabel: {
              width: 350,
              align: 'right',
              margin: 16,
              formatter: function(value) {
                return window.DashboardRenderer.histologyAxisLabel(value);
              },
              rich: {
                right: { width: 350, align: 'right', lineHeight: 18, fontSize: 12 },
                bracket: { width: 350, align: 'right', lineHeight: 18, fontSize: 10.5 }
              }
            }
          },
          series: [
            {
              name: window.DashboardRenderer.t('caseRatio'),
              type: 'bar',
              data: [],
              itemStyle: { color: '#73c0de' },
              label: { 
                show: true,
                position: 'right',
                distance: 8,
                color: '#333',
                fontSize: 13,
                formatter: function(params) {
                  if (typeof params.value !== 'number') return params.value;
                  const count = params.data && params.data.count !== undefined ? params.data.count : '-';
                  const countText = window.DashboardI18n?.getLanguage() === 'en' ? `n = ${count}` : `${count} 人`;
                  return `${params.value.toFixed(1)}% (${countText})`;
                }
              }
            }
          ]
        };
        myHistChart.setOption(histOption);
        window.addEventListener('resize', function() {
            myHistChart.resize();
        });
    }
});


/* ── 個案分類分佈圖 ── */
window.DashboardRenderer.renderDiagnosisClassificationChart = function(chartData, yearTitle, cancerTitle) {
        let chartDom = document.getElementById('annualDiagnosisClassificationChart');
        if (!chartDom) return;
        
        if (!this.classificationChartInst) {
            this.classificationChartInst = echarts.init(chartDom);
        }

        const total = chartData.total_count || 1;
        const calcPctNum = (val) => Number((val / total * 100).toFixed(1));
        const colors = ['#5470C6','#91CC75','#FAC858','#EE6666','#73C0DE','#3BA272','#FC8452'];
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        const chartTitle = isEnglish
            ? `${this.getEnglishCancerPatientLabel(selectedCancer)} Case Class Distribution, ${yearTitle}`
            : `${yearTitle}年${selectedCancer}${this.t('classificationDistribution')}`;
        chartDom.style.height = '450px';
        this.classificationChartInst.resize();
        const labels = [
            this.t('class0'), this.t('class1'), this.t('class2'), this.t('class3')
        ];

        const option = {
            animation: false,
            title: {
                text: chartTitle,
                subtext: this.t('source'),
                left: 'center',
                textStyle: {fontSize: 18,fontWeight: 'bold',color: '#333'}
            },
            toolbox: {
                show: true,
                feature: {
                    dataView: { show: true, readOnly: false, title: this.t('dataView'), lang: [this.t('dataView'), this.t('close'), this.t('refresh')] },
                    saveAsImage: { show: true, title: this.t('downloadImage') }
                }
            },
            legend: {
                orient: 'vertical',
                right: '2%',
                top: 'middle',
                itemWidth: 14,
                itemHeight: 14,
                data: labels,
                textStyle: {
                    fontSize: 14,
                    lineHeight: 22,
                    width: 450,
                    overflow: 'break'
                }
            },
            tooltip: {
                trigger: 'axis',
                axisPointer: {type: 'shadow'}
            },
            grid: {
                left: '3%',
                right: '32%',
                top: '15%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: [
                {
                    type: 'category',
                    data: ['Class0', 'Class1', 'Class2', 'Class3'],
                    axisTick: {alignWithLabel: true}
                }
            ],
            yAxis: [
                {
                    type: 'value',
                    axisLabel: { formatter: '{value}%' }
                }
            ],
            series: [
                {
                    name: labels[0],
                    type: 'bar',
                    stack: 'total',
                    barWidth: '60%',
                    data: [calcPctNum(chartData.class0_total), '-', '-', '-'],
                    itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[0] },
                    label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' }
                },
                {
                    name: labels[1],
                    type: 'bar',
                    stack: 'total',
                    barWidth: '60%',
                    data: ['-', calcPctNum(chartData.class1_total), '-', '-'],
                    itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[1] },
                    label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' }
                },
                {
                    name: labels[2],
                    type: 'bar',
                    stack: 'total',
                    barWidth: '60%',
                    data: ['-', '-', calcPctNum(chartData.class2_total), '-'],
                    itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[2] },
                    label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' }
                },
                {
                    name: labels[3],
                    type: 'bar',
                    stack: 'total',
                    barWidth: '60%',
                    data: ['-', '-', '-', calcPctNum(chartData.class3_total)],
                    itemStyle: { borderRadius: [6, 6, 0, 0], color: colors[3] },
                    label: { show: true, position: 'top', color: '#333', fontSize: 14, fontWeight: 'bold', formatter: '{c}%' }
                }
            ]
        };
        this.classificationChartInst.setOption(option, true);
    };

/* ── 性別與年齡分佈表 ── */
window.DashboardRenderer.renderSexAgeTable = function(genderAgeData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualSexAgeTableHead');
        const body = document.getElementById('annualSexAgeTableBody');
        const caption = document.getElementById('annualSexAgeCaption');
        if (!head || !body) return;

        const ageLabels = (genderAgeData.categories || [])
            .map(label => ['<=19', '≤19', '≦19'].includes(label) ? '≦19' : ['>=85', '≥85', '≧85'].includes(label) ? '≧85' : label);
        if (caption) {
            const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
            caption.innerHTML = window.DashboardI18n?.getLanguage() === 'en'
                ? `Table . Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)} Patients,\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${this.t('sexAge')}${this.t('distribution')}`, { newDiagnosis: true });
        }

        head.innerHTML = `<tr><th rowspan="2">${this.t('sex')}</th><th colspan="${ageLabels.length}">${this.t('ageGroup')}</th><th rowspan="2">${this.t('subtotal')}</th><th rowspan="2">${this.t('percent')}</th></tr><tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>`;
        const sumMale = genderAgeData.male.reduce((a, b) => a + b, 0);
        const sumFemale = genderAgeData.female.reduce((a, b) => a + b, 0);
        const sumTotal = genderAgeData.total.reduce((a, b) => a + b, 0);
        const percentage = (value) => sumTotal ? `${((value / sumTotal) * 100).toFixed(1)}%` : '0.0%';
        body.innerHTML = `<tr><td>${this.t('male')}</td>${genderAgeData.male.map(value => `<td>${value}</td>`).join('')}<td>${sumMale}</td><td>${percentage(sumMale)}</td></tr><tr><td>${this.t('female')}</td>${genderAgeData.female.map(value => `<td>${value}</td>`).join('')}<td>${sumFemale}</td><td>${percentage(sumFemale)}</td></tr><tr><td>${this.t('total')}</td>${genderAgeData.total.map(value => `<td>${value}</td>`).join('')}<td>${sumTotal}</td><td>${percentage(sumTotal)}</td></tr><tr><td>${this.t('percent')}</td>${genderAgeData.total.map(value => `<td>${percentage(value)}</td>`).join('')}<td>${percentage(sumTotal)}</td><td>-</td></tr>`;
    };

/* ── 期別分布介面預覽資料 ──
 * API 無正式 stageReports 時才使用，正式資料會由 2.4 period_rule.py 產生。
 * stage_labels 可放 I、II、III、IV，也可放 IA1、IA2 或其他分期系統的期別名稱。
 */
window.DashboardRenderer.getStageDistributionPreviewData = function() {
        return {
            staging_system: 'AJCC',
            stage_labels: ['I', 'II', 'III', 'IV'],
            stage_totals: [37, 83, 80, 120],
            sex_rows: [
                { sex: '男性', values: [22, 45, 38, 56] },
                { sex: '女性', values: [15, 38, 42, 64] }
            ],
            age_rows: [
                { age: '≦19', values: [1, 0, 0, 3] },
                { age: '20-24', values: [0, 3, 4, 0] },
                { age: '25-29', values: [3, 5, 3, 5] },
                { age: '30-34', values: [5, 7, 6, 6] },
                { age: '35-39', values: [2, 9, 9, 11] },
                { age: '40-44', values: [0, 12, 12, 12] },
                { age: '45-49', values: [3, 5, 5, 5] },
                { age: '50-54', values: [3, 8, 8, 13] },
                { age: '55-59', values: [3, 15, 10, 10] },
                { age: '60-64', values: [5, 8, 8, 9] },
                { age: '65-69', values: [4, 10, 12, 11] },
                { age: '70-74', values: [3, 0, 1, 0] },
                { age: '75-79', values: [3, 0, 1, 18] },
                { age: '80-84', values: [2, 1, 1, 14] },
                { age: '≧85', values: [0, 0, 0, 3] }
            ],
            analyzable_count: 333,
            unknown_count: 5,
            not_applicable_count: 8,
            included_count: 320,
            is_preview: true
        };
    };

/* ── 期別分布資料格式正規化 ── */
window.DashboardRenderer.normalizeStageDistributionData = function(stageData) {
        const source = stageData || this.getStageDistributionPreviewData();
        const stageLabels = Array.isArray(source.stage_labels) && source.stage_labels.length
            ? source.stage_labels.map(label => String(label))
            : ['I', 'II', 'III', 'IV'];
        const normalizeValues = values => stageLabels.map((_, index) => Number(values?.[index] || 0));
        const stageTotals = normalizeValues(source.stage_totals);
        const includedCount = Number(source.included_count ?? stageTotals.reduce((sum, value) => sum + value, 0));
        const sexRows = (Array.isArray(source.sex_rows) ? source.sex_rows : [])
            .map(row => ({
                sex: String(row.sex || ''),
                values: normalizeValues(row.values)
            }))
            // 2.4：性別期別表圖不顯示總數為 0 的性別。
            .filter(row => row.values.some(value => value > 0));
        const ageRows = (Array.isArray(source.age_rows) ? source.age_rows : []).map(row => ({
            age: String(row.age || ''),
            values: normalizeValues(row.values)
        }));
        const chartStageLabels = Array.isArray(source.chart_stage_labels) && source.chart_stage_labels.length
            ? source.chart_stage_labels.map(label => String(label))
            : stageLabels;
        const normalizeChartValues = values => chartStageLabels.map((_, index) => Number(values?.[index] || 0));
        const chartAgeRows = (Array.isArray(source.chart_age_rows) ? source.chart_age_rows : source.age_rows || [])
            .map(row => ({
                age: String(row.age || ''),
                values: normalizeChartValues(row.values)
            }));

        return {
            staging_system: String(source.staging_system || 'AJCC'),
            stage_labels: stageLabels,
            stage_totals: stageTotals,
            sex_rows: sexRows,
            age_rows: ageRows,
            chart_stage_labels: chartStageLabels,
            chart_age_rows: chartAgeRows,
            analyzable_count: Number(source.analyzable_count ?? includedCount),
            unknown_count: Number(source.unknown_count || 0),
            not_applicable_count: Number(source.not_applicable_count || 0),
            included_count: includedCount,
            is_preview: source.is_preview === true
        };
    };

/* 英文模板本身會補上 Stage，避免 Breast Cancer Prognostic Stage 變成 Stage Stage。 */
window.DashboardRenderer.getStageSystemTitle = function(systemName) {
        const name = String(systemName || '').trim();
        return window.DashboardI18n?.getLanguage() === 'en'
            ? name.replace(/\s+Stage$/i, '')
            : name;
    };

/* ── 分期不呈現最細碼：依勾選項目切換昨天建立的三種表圖 ── */
window.DashboardRenderer.renderStageReportTabs = function(stageReports, yearTitle, cancerTitle) {
        const tabs = document.getElementById('annualStageReportTabs');
        const reports = Array.isArray(stageReports) ? stageReports : [];
        if (!tabs) return;
        tabs.replaceChildren();

        const sections = {
            stage: document.getElementById('annualStageDistributionSection'),
            sex: document.getElementById('annualStageSexSection'),
            age: document.getElementById('annualStageAgeSection')
        };
        const showReport = (report, button, { generateInsight = false } = {}) => {
            Object.values(sections).forEach(section => section?.classList.add('d-none'));
            tabs.querySelectorAll('button').forEach(item => item.classList.remove('active'));
            button?.classList.add('active');
            const view = report.view || 'stage';
            sections[view]?.classList.remove('d-none');
            const previewNotice = document.getElementById('annualStagePreviewNotice');
            previewNotice?.classList.toggle('d-none', report.is_preview !== true);
            if (previewNotice) previewNotice.textContent = this.t('stagePreview');

            if (view === 'sex') this.renderStageSexReport(report, yearTitle, cancerTitle);
            else if (view === 'age') this.renderStageAgeReport(report, yearTitle, cancerTitle);
            else this.renderStageDistributionReport(report, yearTitle, cancerTitle);
            this.configureStageInsight(report, { generate: generateInsight });

            requestAnimationFrame(() => {
                if (view === 'sex') window.dashboardStageSexChartInstance?.resize();
                else if (view === 'age') window.dashboardStageAgeChartInstance?.resize();
                else window.dashboardStageDistributionChartInstance?.resize();
            });
        };

        reports.forEach((report, index) => {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'btn btn-outline-dark btn-sm';
            const tabKey = report.view === 'sex' ? 'stageSexTab' : report.view === 'age' ? 'stageAgeTab' : 'stageTab';
            button.textContent = window.DashboardI18n?.getLanguage() === 'en'
                ? this.t(tabKey, { system: this.getStageSystemTitle(report.staging_system) })
                : (report.option || this.t(tabKey, { system: report.staging_system }));
            button.addEventListener('click', () => showReport(report, button, { generateInsight: true }));
            tabs.appendChild(button);
            if (index === 0) showReport(report, button);
        });
    };

/* 目前顯示的期別分頁共用同一個敘述區塊；切換分頁時改用該報表資料產生敘述。 */
window.DashboardRenderer.configureStageInsight = function(stageReport, { generate = true } = {}) {
        const button = document.getElementById('btnAiStageSummary');
        const response = document.getElementById('llmResponseStageSummary');
        if (!button || !response || !stageReport) return;

        const data = this.normalizeStageDistributionData(stageReport);
        const view = stageReport.view || 'stage';
        const viewLabel = view === 'sex' ? 'Stage Distribution by Sex'
            : view === 'age' ? 'Stage Distribution by Age Group'
            : 'Stage Distribution';
        const fieldKey = `${data.staging_system} ${viewLabel}`;
        const fields = view === 'sex'
            ? ['期別', '性別', '個案數', '百分比']
            : view === 'age'
                ? ['期別', '年齡層', '個案數', '百分比']
                : ['期別', '個案數', '百分比'];
        const insightData = {
            staging_system: data.staging_system,
            stage_labels: data.stage_labels,
            stage_totals: data.stage_totals,
            sex_rows: view === 'sex' ? data.sex_rows : undefined,
            age_rows: view === 'age' ? data.age_rows : undefined,
            analyzable_count: data.analyzable_count,
            unknown_count: data.unknown_count,
            not_applicable_count: data.not_applicable_count,
            included_count: data.included_count
        };

        const reportChanged = button.dataset.insightFieldKey !== fieldKey;
        button.style.display = 'block';
        button.textContent = this.t('regenerateInsight');
        button.dataset.insightFieldKey = fieldKey;
        button.onclick = event => this.fetchLlmInsightWithRetry(
            fieldKey,
            insightData,
            fields,
            'llmResponseStageSummary',
            'btnAiStageSummary',
            { forceRefresh: event?.isTrusted === true }
        );
        if (reportChanged) response.textContent = this.t('autoInsight');
        return generate ? button.onclick() : null;
    };

/* ── 表一、圖一：期別分布 ── */
window.DashboardRenderer.renderStageDistributionReport = function(stageData, yearTitle, cancerTitle) {
        const data = this.normalizeStageDistributionData(stageData);
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const titleCancer = isEnglish ? this.getEnglishCancerPatientLabel(cancerTitle) : selectedCancer;
        const systemName = data.staging_system;
        const percentage = value => data.included_count > 0 ? Number(value) / data.included_count * 100 : 0;
        const tableCaption = document.getElementById('annualStageDistributionCaption');
        const chartCaption = document.getElementById('annualStageDistributionChartCaption');
        const tableHead = document.getElementById('annualStageDistributionTableHead');
        const tableBody = document.getElementById('annualStageDistributionTableBody');
        const note = document.getElementById('annualStageDistributionNote');
        const chartNote = document.getElementById('annualStageDistributionChartNote');
        const previewNotice = document.getElementById('annualStagePreviewNotice');

        if (previewNotice) previewNotice.classList.toggle('d-none', !data.is_preview);
        const titleOptions = { year: yearTitle, cancer: titleCancer, system: this.getStageSystemTitle(systemName) };
        const noteText = this.t('stageStatisticsNote', {
            analyzable: data.analyzable_count, unknown: data.unknown_count,
            notApplicable: data.not_applicable_count, included: data.included_count
        });
        if (tableCaption) tableCaption.innerHTML = `${this.t('stageTableTitle', titleOptions)}${this.sourceLine()}`;
        if (chartCaption) chartCaption.textContent = this.t('stageFigureTitle', titleOptions);
        if (tableHead) {
            tableHead.innerHTML = `<tr><th>${this.t('stage')}</th>${data.stage_labels.map(label => `<th>${this.escapeHtml(label)}</th>`).join('')}<th>${this.t('subtotal')}</th></tr>`;
        }
        if (tableBody) {
            tableBody.innerHTML = `
                <tr><th>${this.t('total')}</th>${data.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${data.included_count}</td></tr>
                <tr><th>%</th>${data.stage_totals.map(value => `<td>${percentage(value).toFixed(1)}%</td>`).join('')}<td>${data.included_count > 0 ? '100.0%' : '0.0%'}</td></tr>`;
        }
        if (note) note.textContent = noteText;
        if (chartNote) chartNote.textContent = note?.textContent || '';

        /* 圖一：期別分布圖 */
        const chartDom = document.getElementById('annualStageDistributionChart');
        if (chartDom && typeof echarts !== 'undefined') {
            window.dashboardStageDistributionChartInstance?.dispose();
            window.dashboardStageDistributionChartInstance = echarts.init(chartDom);
            window.dashboardStageDistributionChartInstance.setOption({
                animation: false,
                title: {
                    text: this.t('stageChartTitle', titleOptions),
                    subtext: data.is_preview ? this.t('stagePreview') : this.t('source'),
                    left: 'center',
                    textStyle: { fontSize: 18, fontWeight: 'bold' }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: params => {
                        const item = params[0];
                        const count = data.stage_totals[item.dataIndex] || 0;
                        return `${systemName} ${item.name}<br/>${item.marker}${this.t('stageTooltipCount', { percent: percentage(count).toFixed(1), count })}`;
                    }
                },
                toolbox: {
                    right: 16,
                    feature: {
                        dataView: { show: true, readOnly: true, title: this.t('dataView') },
                        saveAsImage: { show: true, title: this.t('downloadImage') }
                    }
                },
                grid: { left: 70, right: 50, top: 60, bottom: 40, containLabel: true },
                xAxis: {
                    type: 'category',
                    data: data.stage_labels
                },
                yAxis: {
                    type: 'value',
                    min: 0,
                    max: 100,
                    interval: 10,
                    axisLabel: { formatter: '{value}%' }
                },
                series: [{
                    name: this.t('caseRatio'),
                    type: 'bar',
                    barWidth: 45,
                    data: data.stage_totals.map(value => Number(percentage(value).toFixed(1))),
                    itemStyle: {
                        color: '#D4B2F6',
                        borderColor: '#D4B2F6',
                        borderWidth: 1
                    },
                    label: {
                        show: true,
                        position: 'top',
                        distance: 4,
                        color: '#4b5563',
                        fontSize: 14,
                        fontWeight: 'bold',
                        formatter: params => `${Number(params.value || 0).toFixed(1)}%`
                    }
                }]
            });
        }

        return data;
    };

/* ── 表二、圖二：性別及期別分布 ── */
window.DashboardRenderer.renderStageSexReport = function(stageData, yearTitle, cancerTitle) {
        const data = this.normalizeStageDistributionData(stageData);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const titleCancer = isEnglish ? this.getEnglishCancerPatientLabel(cancerTitle) : cancerTitle;
        const systemName = data.staging_system;
        const tableCaption = document.getElementById('annualStageSexCaption');
        const chartCaption = document.getElementById('annualStageSexChartCaption');
        const tableHead = document.getElementById('annualStageSexTableHead');
        const tableBody = document.getElementById('annualStageSexTableBody');
        const note = document.getElementById('annualStageSexNote');
        const chartNote = document.getElementById('annualStageSexChartNote');
        const rowTotal = row => row.values.reduce((sum, value) => sum + value, 0);
        const percentage = value => data.included_count > 0 ? Number(value) / data.included_count * 100 : 0;

        const titleOptions = { year: yearTitle, cancer: titleCancer, system: this.getStageSystemTitle(systemName) };
        const sexLabel = sex => sex === '男性' ? this.t('male') : sex === '女性' ? this.t('female') : sex;
        const noteText = this.t('stageStatisticsNote', {
            analyzable: data.analyzable_count, unknown: data.unknown_count,
            notApplicable: data.not_applicable_count, included: data.included_count
        });
        if (tableCaption) tableCaption.innerHTML = `${this.t('stageSexTableTitle', titleOptions)}${this.sourceLine()}`;
        if (chartCaption) chartCaption.textContent = this.t('stageSexFigureTitle', titleOptions);
        if (tableHead) {
            tableHead.innerHTML = `<tr><th>${this.t('sex')}</th>${data.stage_labels.map(label => `<th>${this.escapeHtml(label)}</th>`).join('')}<th>${this.t('subtotal')}</th><th>%</th></tr>`;
        }
        if (tableBody) {
            const sexRowsHtml = data.sex_rows.map(row => {
                const total = rowTotal(row);
                return `<tr><th>${this.escapeHtml(sexLabel(row.sex))}</th>${row.values.map(value => `<td>${value}</td>`).join('')}<td>${total}</td><td>${percentage(total).toFixed(1)}%</td></tr>`;
            }).join('');
            tableBody.innerHTML = `${sexRowsHtml}
                <tr><th>${this.t('total')}</th>${data.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${data.included_count}</td><td>${data.included_count > 0 ? '100.0%' : '0.0%'}</td></tr>
                <tr><th>%</th>${data.stage_totals.map(value => `<td>${percentage(value).toFixed(1)}%</td>`).join('')}<td>${data.included_count > 0 ? '100.0%' : '0.0%'}</td><td>-</td></tr>`;
        }
        if (note) note.textContent = noteText;
        if (chartNote) chartNote.textContent = note?.textContent || '';

        /* 圖二：性別及期別分布圖 */
        const chartDom = document.getElementById('annualStageSexChart');
        if (chartDom && typeof echarts !== 'undefined') {
            window.dashboardStageSexChartInstance?.dispose();
            window.dashboardStageSexChartInstance = echarts.init(chartDom);
            const sexSeries = data.sex_rows.map(row => {
                const isMale = row.sex === '男性';
                return {
                    name: sexLabel(row.sex),
                    type: 'bar',
                    stack: 'stage-total',
                    barWidth: 45,
                    data: row.values.map(value => Number(percentage(value).toFixed(1))),
                    itemStyle: {
                        color: isMale ? '#5470C6' : '#EE6666',
                        borderColor: isMale ? '#5470C6' : '#EE6666',
                        borderWidth: 1
                    },
                    label: { show: false }
                };
            });
            const maleRow = data.sex_rows.find(row => row.sex === '男性');
            const femaleRow = data.sex_rows.find(row => row.sex === '女性');
            const topLabelData = data.stage_labels.map((_, index) => {
                const malePercent = percentage(maleRow?.values[index] || 0);
                const femalePercent = percentage(femaleRow?.values[index] || 0);
                return {
                    value: Number((malePercent + femalePercent).toFixed(1)),
                    malePercent,
                    femalePercent
                };
            });
            const topLabelSeries = {
                name: '__stageSexLabels',
                type: 'bar',
                barWidth: 45,
                barGap: '-100%',
                silent: true,
                z: 10,
                tooltip: { show: false },
                data: topLabelData,
                itemStyle: { color: 'transparent', borderColor: 'transparent' },
                label: {
                    show: true,
                    position: 'top',
                    distance: 4,
                    align: 'center',
                    fontSize: 14,
                    fontWeight: 'bold',
                    formatter: params => {
                        return [
                            `{female|${Number(params.data.femalePercent || 0).toFixed(1)}%}`,
                            `{male|${Number(params.data.malePercent || 0).toFixed(1)}%}`
                        ].join('\n');
                    },
                    rich: {
                        male: { color: '#36558f', fontSize: 14, fontWeight: 'bold', lineHeight: 17, width: 45, align: 'center' },
                        female: { color: '#b54848', fontSize: 14, fontWeight: 'bold', lineHeight: 17, width: 45, align: 'center' }
                    }
                }
            };
            window.dashboardStageSexChartInstance.setOption({
                animation: false,
                title: {
                    text: this.t('stageSexChartTitle', titleOptions),
                    subtext: data.is_preview ? this.t('stagePreview') : this.t('source'),
                    left: 'center',
                    textStyle: { fontSize: 18, fontWeight: 'bold' }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: params => {
                        const lines = params
                            .filter(item => item.seriesName !== '__stageSexLabels')
                            .map(item => {
                            const sexRow = data.sex_rows.find(row => sexLabel(row.sex) === item.seriesName);
                            const count = sexRow?.values[item.dataIndex] || 0;
                            return `${item.marker}${item.seriesName}: ${this.t('stageTooltipCount', { percent: Number(item.value).toFixed(1), count })}`;
                        });
                        return `${systemName} ${params[0]?.name || ''}<br/>${lines.join('<br/>')}`;
                    }
                },
                legend: {
                    show: true,
                    data: data.sex_rows.map(row => sexLabel(row.sex)),
                    top: 52,
                    left: 'center',
                    itemGap: 12
                },
                toolbox: {
                    right: 16,
                    feature: {
                        dataView: { show: true, readOnly: true, title: this.t('dataView') },
                        saveAsImage: { show: true, title: this.t('downloadImage') }
                    }
                },
                grid: { left: 70, right: 50, top: 95, bottom: 40, containLabel: true },
                xAxis: {
                    type: 'category',
                    data: data.stage_labels
                },
                yAxis: {
                    type: 'value',
                    min: 0,
                    max: 100,
                    interval: 10,
                    axisLabel: { formatter: '{value}%' }
                },
                series: [...sexSeries, topLabelSeries]
            });
        }
    };

/* ── 表三、圖三：年齡層及期別分布 ── */
window.DashboardRenderer.renderStageAgeReport = function(stageData, yearTitle, cancerTitle) {
        const data = this.normalizeStageDistributionData(stageData);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const titleCancer = isEnglish ? this.getEnglishCancerPatientLabel(cancerTitle) : cancerTitle;
        const chartStageLabels = data.chart_stage_labels;
        const chartAgeRows = data.chart_age_rows;
        const systemName = data.staging_system;
        const tableCaption = document.getElementById('annualStageAgeCaption');
        const chartCaption = document.getElementById('annualStageAgeChartCaption');
        const tableHead = document.getElementById('annualStageAgeTableHead');
        const tableBody = document.getElementById('annualStageAgeTableBody');
        const note = document.getElementById('annualStageAgeNote');
        const chartNote = document.getElementById('annualStageAgeChartNote');
        const rowTotal = row => row.values.reduce((sum, value) => sum + value, 0);
        const percentage = value => data.included_count > 0 ? Number(value) / data.included_count * 100 : 0;
        const titleOptions = { year: yearTitle, cancer: titleCancer, system: this.getStageSystemTitle(systemName) };
        const noteText = this.t('stageStatisticsNote', {
            analyzable: data.analyzable_count, unknown: data.unknown_count,
            notApplicable: data.not_applicable_count, included: data.included_count
        });

        if (tableCaption) tableCaption.innerHTML = `${this.t('stageAgeTableTitle', titleOptions)}${this.sourceLine()}`;
        if (chartCaption) chartCaption.textContent = this.t('stageAgeFigureTitle', titleOptions);
        if (tableHead) {
            tableHead.innerHTML = `<tr><th>${this.t('ageGroup')}</th>${data.stage_labels.map(label => `<th>${this.escapeHtml(label)}</th>`).join('')}<th>${this.t('subtotal')}</th><th>%</th></tr>`;
        }
        if (tableBody) {
            const ageRowsHtml = data.age_rows.map(row => {
                const total = rowTotal(row);
                return `<tr><th>${this.escapeHtml(row.age)}</th>${row.values.map(value => `<td>${value}</td>`).join('')}<td>${total}</td><td>${percentage(total).toFixed(1)}%</td></tr>`;
            }).join('');
            tableBody.innerHTML = `${ageRowsHtml}
                <tr><th>${this.t('total')}</th>${data.stage_totals.map(value => `<td>${value}</td>`).join('')}<td>${data.included_count}</td><td>${data.included_count > 0 ? '100.0%' : '0.0%'}</td></tr>
                <tr><th>%</th>${data.stage_totals.map(value => `<td>${percentage(value).toFixed(1)}%</td>`).join('')}<td>${data.included_count > 0 ? '100.0%' : '0.0%'}</td><td>-</td></tr>`;
        }
        if (note) note.textContent = noteText;
        if (chartNote) chartNote.textContent = noteText;

        /* 圖三：年齡層及期別分布圖 */
        const chartDom = document.getElementById('annualStageAgeChart');
        if (chartDom && typeof echarts !== 'undefined') {
            const stageColors = ['#F3AE9F', '#E9CB92', '#C3E4C3', '#A7B9DF', '#C8B0DC'];
            const ageStagePercentages = chartAgeRows.map(row => {
                const total = rowTotal(row);
                return chartStageLabels.map((_, stageIndex) => total > 0
                    ? Number((row.values[stageIndex] / total * 100).toFixed(1))
                    : 0);
            });
            const smallStageLabelData = [];
            ageStagePercentages.forEach((values, rowIndex) => {
                let cumulative = 0;
                values.forEach((value, stageIndex) => {
                    if (value > 0 && value <= 3) {
                        smallStageLabelData.push([
                            cumulative + value / 2,
                            chartAgeRows[rowIndex].age,
                            value,
                            stageIndex
                        ]);
                    }
                    cumulative += value;
                });
            });
            const smallStageLabelSeries = {
                name: '__smallStageLabels',
                type: 'custom',
                silent: true,
                tooltip: { show: false },
                z: 20,
                data: smallStageLabelData,
                renderItem: (params, api) => {
                    const point = api.coord([api.value(0), api.value(1)]);
                    const stageIndex = Number(api.value(3) || 0);
                    const horizontalShift = 8;
                    const lineStartY = point[1] - 10;
                    const lineEnd = [point[0] + horizontalShift, point[1] - 18];
                    return {
                        type: 'group',
                        children: [
                            {
                                type: 'line',
                                shape: { x1: point[0], y1: lineStartY, x2: lineEnd[0], y2: lineEnd[1] },
                                style: { stroke: stageColors[stageIndex % stageColors.length], lineWidth: 1.5 }
                            },
                            {
                                type: 'text',
                                style: {
                                    text: `${Number(api.value(2)).toFixed(1)}%`,
                                    x: lineEnd[0],
                                    y: lineEnd[1] - 2,
                                    fill: '#4b5563',
                                    font: '700 11px Arial, sans-serif',
                                    align: 'center',
                                    verticalAlign: 'bottom'
                                }
                            }
                        ]
                    };
                }
            };
            window.dashboardStageAgeChartInstance?.dispose();
            window.dashboardStageAgeChartInstance = echarts.init(chartDom);
            window.dashboardStageAgeChartInstance.setOption({
                animation: false,
                title: {
                    text: this.t('stageAgeChartTitle', titleOptions),
                    subtext: data.is_preview ? this.t('stagePreview') : this.t('source'),
                    left: 'center',
                    textStyle: { fontSize: 18, fontWeight: 'bold' }
                },
                tooltip: {
                    trigger: 'axis',
                    axisPointer: { type: 'shadow' },
                    formatter: params => {
                        const stageParams = params.filter(item => item.seriesName !== '__smallStageLabels');
                        const rowIndex = stageParams[0]?.dataIndex ?? 0;
                        const row = chartAgeRows[rowIndex];
                        const total = row ? rowTotal(row) : 0;
                        const lines = stageParams.map(item => {
                            const count = row?.values[item.seriesIndex] || 0;
                            return `${item.marker}${item.seriesName}: ${this.t('stageTooltipCount', { percent: Number(item.value).toFixed(1), count })}`;
                        });
                        return `${this.t('stageAgeTooltipTotal', { age: row?.age || '', total })}<br/>${lines.join('<br/>')}`;
                    }
                },
                legend: {
                    top: 52,
                    left: 'center',
                    data: chartStageLabels
                },
                toolbox: {
                    right: 16,
                    feature: {
                        dataView: { show: true, readOnly: true, title: this.t('dataView') },
                        saveAsImage: { show: true, title: this.t('downloadImage') }
                    }
                },
                grid: { left: 75, right: 45, top: 88, bottom: 45, containLabel: true },
                xAxis: {
                    type: 'value',
                    min: 0,
                    max: 100,
                    interval: 10,
                    axisLabel: { formatter: '{value}%' }
                },
                yAxis: {
                    type: 'category',
                    data: chartAgeRows.map(row => row.age),
                    axisTick: { show: false }
                },
                series: [...chartStageLabels.map((label, stageIndex) => ({
                    name: label,
                    type: 'bar',
                    stack: 'age-stage-total',
                    barMaxWidth: 22,
                    itemStyle: { color: stageColors[stageIndex % stageColors.length] },
                    label: {
                        show: true,
                        position: 'inside',
                        align: 'center',
                        verticalAlign: 'middle',
                        offset: [0, 1],
                        color: '#4b5563',
                        fontSize: 11,
                        fontFamily: 'Arial, sans-serif',
                        fontStyle: 'normal',
                        fontWeight: 700,
                        lineHeight: 22,
                        textBorderWidth: 0,
                        textShadowBlur: 0,
                        formatter: params => Number(params.value || 0) > 3
                            ? `${Number(params.value).toFixed(1)}%`
                            : ''
                    },
                    data: ageStagePercentages.map(values => values[stageIndex])
                })), smallStageLabelSeries]
            });
        }
    };

/* ── 期別與首次療程表 ── */
window.DashboardRenderer.renderStageFirstCourseTables = function(tables, yearTitle, cancerTitle) {
        const container = document.getElementById('annualStageFirstCourseTables');
        if (!container) return;
        if (!Array.isArray(tables) || !tables.length) {
            container.innerHTML = '<div class="text-secondary">目前沒有符合所選分期系統的首次療程資料。</div>';
            return;
        }
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        const systems = tables.map(item => item.system);
        const activeSystem = systems.includes(window.stageFirstCourseActiveSystem)
            ? window.stageFirstCourseActiveSystem
            : systems[0];
        const tabs = tables.length > 1
            ? `<div class="d-flex flex-wrap gap-2 mb-3" role="tablist">${tables.map(item => `<button type="button" class="btn btn-outline-dark btn-sm stage-first-course-tab${item.system === activeSystem ? ' active' : ''}" data-stage-system="${this.escapeHtml(item.system)}">${this.escapeHtml(item.system)}${isEnglish ? ' Stage' : '期別'}</button>`).join('')}</div>`
            : '';
        const panels = tables.map(item => {
            const stages = item.stage_columns || [];
            const rows = item.rows || [];
            const displayStage = (stage) => String(stage || '')
                .replace(/^Stage\s+/i, '')
                .trim();
            const treatmentEnglish = {
                '手術': 'Surgery',
                '放療': 'Radiotherapy',
                '化療': 'Chemotherapy',
                '標靶': 'Targeted Therapy',
                '荷爾蒙': 'Hormone Therapy',
                '類固醇治療': 'Steroid Therapy',
                '免疫': 'Immunotherapy',
                '骨髓/幹細胞移植': 'Hematopoietic Stem Cell Transplantation (HSCT)',
                '血液幹細胞移植': 'Hematopoietic Stem Cell Transplantation (HSCT)',
                '內分泌處置': 'Endocrine Procedure',
                '其他治療': 'Other Treatment',
                '密切觀察或不予治療': 'No Treatment',
                '待確認': 'Pending Confirmation',
                'RFA/TAE/PEI混合治療': 'RFA/TAE/PEI Combined Treatment',
            };
            const displayTreatment = (treatment) => isEnglish
                ? String(treatment || '').split('、').map(item => treatmentEnglish[item] || item).join('、')
                : treatment;
        const title = isEnglish
                ? `Table . ${this.escapeHtml(item.system)} Stage and First Course Treatment Distribution of Newly Diagnosed ${this.getEnglishCancerPatientLabel(selectedCancer)} Cases,\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${item.system}期別與首次療程`);
            const rowPercentage = row => item.total_count
                ? `${(Number(row.subtotal || 0) / Number(item.total_count) * 100).toFixed(1)}%`
                : '0.0%';
            const bodyRows = rows.map(row => `<tr><td class="text-start ps-3">${this.escapeHtml(displayTreatment(row.treatment))}</td>${row.values.map(value => `<td>${value}</td>`).join('')}<td>${row.subtotal}</td><td>${rowPercentage(row)}</td></tr>`).join('');
            const totals = (item.totals || []).map(value => `<td>${value}</td>`).join('');
            const percentages = (item.percentages || []).map(value => `<td>${value}%</td>`).join('');
            const analyzableCount = Number(item.analyzable_count || 0);
            const includedCount = Number(item.included_count ?? item.total_count ?? 0);
            const excludedUnclassifiedTreatment = Number(item.excluded_unclassified_treatment || 0);
            const excludedCount = Number(item.excluded_unknown || 0)
                + Number(item.excluded_not_applicable || 0)
                + excludedUnclassifiedTreatment;
            const unclassifiedTreatmentClause = excludedUnclassifiedTreatment
                ? `; ${excludedUnclassifiedTreatment} case(s) had treatment data that could not be classified using the defined treatment codes`
                : '';
            const stageNote = isEnglish
                ? `Note: Of ${analyzableCount} analyzable cases (Class 1-2), ${Number(item.excluded_unknown || 0)} had unknown stage and ${Number(item.excluded_not_applicable || 0)} had non-applicable stage${unclassifiedTreatmentClause}. A total of ${excludedCount} case(s) were excluded from the stage and first-course treatment distribution (percentage denominator = ${includedCount}).`
                : `\u8a3b\uff1a\u53ef\u5206\u6790\u500b\u6848\u6578\uff08Class 1\u20132\uff09\u5171\u8a08 ${analyzableCount} \u4f8b\uff0c\u5176\u4e2d\u5206\u671f\u4e0d\u660e ${Number(item.excluded_unknown || 0)} \u4f8b\u3001\u5206\u671f\u4e0d\u9069\u7528 ${Number(item.excluded_not_applicable || 0)} \u4f8b${excludedUnclassifiedTreatment ? `\uff1b\u53e6\u6709 ${excludedUnclassifiedTreatment} \u4f8b\u6cbb\u7642\u65b9\u5f0f\u7121\u6cd5\u4f9d\u65e2\u5b9a\u6cbb\u7642\u4ee3\u78bc\u5224\u5b9a` : ''}\u3002\u4e0a\u8ff0\u5171 ${excludedCount} \u4f8b\u672a\u7d0d\u5165\u671f\u5225\u8207\u9996\u6b21\u7642\u7a0b\u5206\u4f48\u767e\u5206\u6bd4\u8a08\u7b97\uff08\u767e\u5206\u6bd4\u5206\u6bcd\uff1d${includedCount}\uff09\u3002`;
            const definitionNote = isEnglish
                ? 'Note: First course treatment refers to all treatments administered before disease progression or recurrence.'
                : '註：首次療程的定義係指在癌病惡化或復發之前所執行的治療方法。';
            return `<div class="stage-first-course-panel${item.system === activeSystem ? '' : ' d-none'}" data-stage-system="${this.escapeHtml(item.system)}"><table class="annual-report-table"><caption class="surgery-table-caption">${title}</caption><thead><tr><th rowspan="2">${isEnglish ? 'First Course of Treatment' : '首次療程'}</th><th colspan="${Math.max(stages.length, 1)}">${this.escapeHtml(item.system)}${isEnglish ? ' Stage' : '期別'}</th><th rowspan="2">${isEnglish ? 'Total' : '小計'}</th><th rowspan="2">%</th></tr><tr>${stages.map(stage => `<th>${this.escapeHtml(displayStage(stage))}</th>`).join('')}</tr></thead><tbody>${bodyRows}<tr class="fw-bold"><td>${this.t('total')}</td>${totals}<td>${Number(item.total_count || 0)}</td><td>${item.total_count ? '100.0%' : '0.0%'}</td></tr><tr><td>%</td>${percentages}<td>${item.total_count ? '100.0%' : '0.0%'}</td><td>-</td></tr></tbody></table><div class="small text-secondary mt-2 mb-0">${definitionNote}</div><div class="small text-secondary mt-0 mb-0">${stageNote}</div></div>`;
        }).join('');
        container.innerHTML = `${tabs}${panels}`;
        container.querySelectorAll('.stage-first-course-tab').forEach(button => {
            button.addEventListener('click', () => {
                const system = button.dataset.stageSystem;
                window.stageFirstCourseActiveSystem = system;
                container.querySelectorAll('.stage-first-course-tab').forEach(tab => tab.classList.toggle('active', tab === button));
                container.querySelectorAll('.stage-first-course-panel').forEach(panel => {
                    panel.classList.toggle('d-none', panel.dataset.stageSystem !== system);
                });
                const insightButton = document.getElementById('btnAiTreatmentFirstCourse');
                if (insightButton && window.lastChartData && typeof insightButton.onclick === 'function') {
                    insightButton.onclick();
                }
            });
        });
    };

/* ── 組織型態不適用個案說明按鈕 ── */
window.DashboardRenderer.currentHistologyWarnings = [];

window.DashboardRenderer.decodeHtmlEntities = function(value) {
        const textarea = document.createElement('textarea');
        textarea.innerHTML = String(value ?? '');
        return textarea.value;
    };

window.DashboardRenderer.escapeHtml = function(value) {
        return this.decodeHtmlEntities(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    };

window.DashboardRenderer.showHistologyWarningDetails = function(histologyWarnings) {
        const warnings = Array.isArray(histologyWarnings) ? histologyWarnings : [];
        if (warnings.length === 0) return;

        const warningLines = warnings.map(item => {
            const user = this.escapeHtml(item.user || '未知個案');
            const warningText = this.getHistologyWarningText(item);
            const message = this.escapeHtml(warningText.message);
            const rawWarningText = this.getHistologyRawWarningText(item);
            const rawDataMessage = rawWarningText
                ? `<span class="fw-bold text-danger ms-1">${this.escapeHtml(rawWarningText)}</span>`
                : '';
            const detail = this.escapeHtml(warningText.detail);
            return `
                <div class="mb-3 text-start histology-warning-item">
                    <div class="text-nowrap">${user}：${message}${rawDataMessage}</div>
                    <div class="text-nowrap">${this.t('details')}：${detail}</div>
                </div>
            `;
        }).join('');
        const warningHtml = `
            <div class="text-center histology-warning-dialog">
                <div class="mb-3 text-nowrap">${this.t('warningDetails')}</div>
                <div class="mx-auto text-start" style="display: inline-block; min-width: max-content; max-width: none; overflow-x: visible; padding: 0 4px;">${warningLines}</div>
            </div>
        `;

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                html: warningHtml,
                confirmButtonText: this.t('confirm'),
                confirmButtonColor: '#dc3545',
                width: 'auto',
                allowOutsideClick: false,
                customClass: { popup: 'histology-warning-popup' }
            });
        } else {
            const alertLines = warnings.map(item => {
                const user = item.user || '未知個案';
                const warningText = this.getHistologyWarningText(item);
                const message = warningText.message;
                const rawWarningText = this.getHistologyRawWarningText(item);
                const rawDataMessage = rawWarningText ? ` ${rawWarningText}` : '';
                const detail = warningText.detail;
                return `${user}：${message}${rawDataMessage}\n${this.t('details')}：${detail}`;
            }).join('\n\n');
            window.utils?.alert(`${this.t('warningDetails')}\n\n${alertLines}`, 'warning');
        }
    };

window.DashboardRenderer.renderHistologyWarningButton = function(histologyWarnings) {
        const button = document.getElementById('histologyWarningButton');
        if (!button) return;

        const warnings = Array.isArray(histologyWarnings) ? histologyWarnings : [];
        this.currentHistologyWarnings = warnings;

        if (warnings.length === 0) {
            button.classList.add('d-none');
            button.textContent = this.t('ineligibleCases');
            return;
        }

        button.classList.remove('d-none');
        button.textContent = `${this.t('ineligibleCases')} (${warnings.length})`;
        if (button.dataset.boundHistologyWarning !== '1') {
            button.addEventListener('click', () => {
                this.showHistologyWarningDetails(this.currentHistologyWarnings);
            });
            button.dataset.boundHistologyWarning = '1';
        }
    };

/* ── 結腸癌組織型態表格註記 ── */
window.DashboardRenderer.renderColonHistologyTableNote = function(histologyWarnings) {
        const tableNote = document.getElementById('annualHistologyTableNote');
        if (!tableNote) return;

        const warnings = Array.isArray(histologyWarnings) ? histologyWarnings : [];
        const colonNotes = warnings.filter(item => {
            const code = String(item.icdo_code || '');
            const site = String(item.site || '').toUpperCase();
            return code === '8211/2' && site.startsWith('C18');
        });

        if (colonNotes.length === 0) {
            tableNote.classList.add('d-none');
            tableNote.innerHTML = '';
            return;
        }

        tableNote.classList.remove('d-none');
        tableNote.innerHTML = colonNotes.map(item => {
            const user = item.user || '未知個案';
            return this.t('colonHistologyNote', { user });
        }).join('<br>');
    };

/* ── 組織型態分佈表 ── */
window.DashboardRenderer.histologyDisplayName = function(item) {
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        return isEnglish
            ? (item?.name_en || item?.name || '')
            : (item?.name_zh || item?.name || '');
    };

window.DashboardRenderer.histologyAxisLabel = function(value) {
        const text = String(value ?? '').replace(/\s*\n\s*/g, ' ').trim();
        // 原位癌後綴屬於名稱的一部分，中文與英文皆固定同一列。
        return /[\u3400-\u9fff]/.test(text) || /\(in situ\)$/i.test(text)
            ? `{right|${text}}`
            : this.rightAlignedAxisLabel(text);
    };

window.DashboardRenderer.renderHistologyTable = function(histologyData, yearTitle, cancerTitle, noDataReason = '') {
        const body = document.getElementById('annualHistologyTableBody');
        const caption = document.getElementById('annualHistologyCaption');
        if (!body) return;
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        if (caption) {
            caption.innerHTML = isEnglish
                ? `Table. Histological Distribution of ${this.getEnglishCancerPatientLabel(selectedCancer)},\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${this.t('histology')}${this.t('distribution')}`);
        }
        if (!histologyData || histologyData.length === 0) {
            const reason = this.escapeHtml(noDataReason || '查無符合條件的組織型態資料。');
            body.innerHTML = `<tr><td colspan="3" class="text-center py-4">${this.t('noData')}<br><span class="text-muted small">${reason}</span></td></tr>`;
            this.renderColonHistologyTableNote([]);
            return;}

        const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
        const totalCount = validData.reduce((sum, item) => sum + item.count, 0);
        const rowsHtml = validData.map(item => {
            const pct = totalCount > 0 ? ((item.count / totalCount) * 100).toFixed(1) : '0.0';
            return `
                <tr>
                    <td class="text-start">${this.escapeHtml(this.histologyDisplayName(item))}</td>
                    <td>${item.count}</td>
                    <td>${pct}%</td>
                </tr>
            `;
        }).join('');

        const totalRowHtml = `
            <tr class="fw-bold" style="background-color: var(--gray-50);">
                <td>${this.t('total')}</td>
                <td>${totalCount}</td>
                <td>100.0%</td>
            </tr>`;
        body.innerHTML = rowsHtml + totalRowHtml;
    };

/* ── 年齡中位數表 ── */
window.DashboardRenderer.renderAgeMedianTable = function(medianData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualAgeMedianTableHead');
        const body = document.getElementById('annualAgeMedianTableBody');
        const caption = document.getElementById('annualAgeMedianCaption');
        if (!head || !body || !medianData) return;

        const columns = [this.t('male'), this.t('female')];
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        if (caption) {
            caption.innerHTML = window.DashboardI18n?.getLanguage() === 'en'
                ? `Table . Median Age of Patients Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)},\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, this.t('ageMedian'), { newDiagnosis: true });
        }

        head.innerHTML = `<tr><th rowspan="2" style="vertical-align: middle;">${this.t('medianCharacteristic')}</th><th colspan="${columns.length}">${this.t('medianSex')}</th></tr><tr>${columns.map(label => `<th>${label}</th>`).join('')}</tr>`;
        body.innerHTML = `<tr><td>${this.t('medianN')}</td><td>${medianData.male_count}</td><td>${medianData.female_count}</td></tr><tr><td>${this.t('medianAgeYears')}</td><td>${medianData.male}</td><td>${medianData.female}</td></tr><tr><td>${this.t('medianMaleToFemaleRatio')}</td><td>${medianData.male_ratio}</td><td>${medianData.female_ratio}</td></tr>`;
    };

/* ── 存活觀察值摘要表 ── */
window.DashboardRenderer.renderSurvivalExclusionButton = function(summary) {
        const button = document.getElementById('survivalExclusionButton');
        if (!button) return;
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        button.textContent = isEnglish ? 'Excluded data details' : '排除資料說明';
        this.currentSurvivalExclusionSummary = summary || {};

        button.onclick = () => {
            const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
            const item = this.currentSurvivalExclusionSummary || {};
            const reasons = isEnglish ? [
                ['Class0 excluded', item.class0], ['Class3 excluded', item.class3], ['Other case classes excluded', item.other_class],
                ['Invalid diagnosis date', item.invalid_diagnosis_date], ['Invalid last-contact/death date', item.invalid_last_contact_date],
                ['Invalid vital status', item.invalid_vital_status], ['Last-contact date earlier than diagnosis', item.last_contact_before_diagnosis],
                ['Stage 0 not shown in this table', item.stage0], ['No usable pathological or clinical stage', item.no_usable_stage],
                ['Stage IV without usable M0/M1', item.stage4_missing_m]
            ] : [
                ['排除 Class0', item.class0], ['排除 Class3', item.class3], ['排除其他個案分類', item.other_class],
                ['診斷日期無效或不完整', item.invalid_diagnosis_date], ['最後聯絡或死亡日期無效或不完整', item.invalid_last_contact_date],
                ['生存狀態不是 0 或 1', item.invalid_vital_status], ['最後聯絡或死亡日期早於診斷日期', item.last_contact_before_diagnosis],
                ['Stage 0 未列入本表', item.stage0], ['病理與臨床期別皆無法使用', item.no_usable_stage],
                ['Stage IV 無法判斷 M0／M1', item.stage4_missing_m]
            ];
            const reasonRows = reasons.filter(([, count]) => Number(count || 0) > 0)
                .map(([label, count]) => `<tr><td class="text-start">${this.escapeHtml(label)}</td><td class="text-end">${Number(count)} 筆</td></tr>`).join('');
            const html = `
                <div class="table-responsive">
                  <table class="table table-bordered table-sm align-middle mb-2">
                    <tbody>
                      <tr class="table-light fw-bold"><td class="text-start">${isEnglish ? 'Records after selected filters' : '符合查詢條件的原始資料'}</td><td class="text-end">${Number(item.source_count || 0)} ${isEnglish ? 'records' : '筆'}</td></tr>
                      ${reasonRows || `<tr><td colspan="2">${isEnglish ? 'No records were excluded.' : '沒有資料被排除。'}</td></tr>`}
                      <tr class="table-light fw-bold"><td class="text-start">${isEnglish ? 'Total excluded' : '排除合計'}</td><td class="text-end">${Number(item.excluded_count || 0)} ${isEnglish ? 'records' : '筆'}</td></tr>
                      <tr class="table-success fw-bold"><td class="text-start">${isEnglish ? 'Included in table' : '最後納入表格'}</td><td class="text-end">${Number(item.included_count || 0)} ${isEnglish ? 'records' : '筆'}</td></tr>
                    </tbody>
                  </table>
                </div>
                <div class="small text-muted text-start">${isEnglish
                    ? 'Current rule: Class1/2 only; pathological stage is used first, with clinical stage as fallback.'
                    : '目前規則：僅納入 Class1、Class2；病理期別優先，無可用病理期別時改採臨床期別。'}</div>`;
            if (typeof Swal !== 'undefined') {
                Swal.fire({
                    title: isEnglish ? 'Excluded data details' : '排除資料說明',
                    html,
                    width: 720,
                    confirmButtonText: isEnglish ? 'OK' : '確定',
                    confirmButtonColor: '#212529'
                });
            } else {
                const text = reasons.filter(([, count]) => Number(count || 0) > 0).map(([label, count]) => `${label}：${count} 筆`).join('\n');
                window.utils?.alert(`${isEnglish ? 'Excluded data details' : '排除資料說明'}\n\n${text}`, 'warning');
            }
        };
    };

window.DashboardRenderer.renderSurvivalChart = function(survivalData, yearTitle, cancerTitle) {
        const chartDom = document.getElementById('annualSurvivalChart');
        const caption = document.getElementById('annualSurvivalChartCaption');
        if (!chartDom || typeof echarts === 'undefined') return;
        if (window.dashboardSurvivalChartInstance) window.dashboardSurvivalChartInstance.dispose();
        window.dashboardSurvivalChartInstance = echarts.init(chartDom);

        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        const seriesData = Array.isArray(survivalData?.chart_series) ? survivalData.chart_series : [];
        const includedCount = Number(survivalData?.exclusion_summary?.included_count || 0);
        const colors = ['#5470c6', '#2fb344', '#d6c66b', '#7030a0', '#f59f00'];
        const plusSymbol = 'path://M-6,-1 L-1,-1 L-1,-6 L1,-6 L1,-1 L6,-1 L6,1 L1,1 L1,6 L-1,6 L-1,1 L-6,1 Z';
        const visibleContainerWidth = document.querySelector('#chartsArea > .col-12')?.clientWidth || window.innerWidth;
        const initialChartWidth = chartDom.clientWidth || Math.max(320, visibleContainerWidth - 50);
        const legendLeft = Math.max(0, initialChartWidth - 260);
        const chartSeries = [];
        seriesData.forEach((item, index) => {
            const color = colors[index % colors.length];
            chartSeries.push({
                name: item.stage,
                type: 'line',
                step: 'end',
                showSymbol: false,
                symbol: 'none',
                animation: false,
                data: item.curve || [],
                lineStyle: { width: 3, color },
                itemStyle: { color },
                emphasis: { focus: 'series' }
            });
            chartSeries.push({
                name: `${item.stage}-${isEnglish ? 'censored' : '設限'}`,
                type: 'scatter',
                symbol: plusSymbol,
                symbolSize: 9,
                data: item.censored || [],
                itemStyle: { color },
                tooltip: {
                    valueFormatter: value => String(value)
                }
            });
        });
        const title = isEnglish
            ? `Kaplan–Meier Survival Curve (N=${includedCount})`
            : `Kaplan–Meier存活曲線圖 (N=${includedCount})`;
        window.dashboardSurvivalChartInstance.setOption({
            animation: false,
            color: colors,
            title: { text: title, subtext: this.t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold' } },
            tooltip: {
                trigger: 'item',
                formatter: params => {
                    const value = params.value?.value || params.value;
                    const months = Number(value?.[0] || 0).toFixed(1);
                    const survival = (Number(value?.[1] || 0) * 100).toFixed(1);
                    const count = Number(params.data?.count || 0);
                    return `${params.seriesName}<br>${isEnglish ? 'Months' : '存活月數'}：${months}<br>${isEnglish ? 'Survival' : '累積存活率'}：${survival}%${count ? `<br>${isEnglish ? 'Censored' : '設限數'}：${count}` : ''}`;
                }
            },
            legend: {
                type: 'scroll', orient: 'vertical', left: legendLeft, top: 116, bottom: 38,
                itemWidth: 18, itemHeight: 8, itemGap: 4,
                textStyle: { fontSize: 11, lineHeight: 14 }
            },
            toolbox: {
                right: 12,
                feature: {
                    dataView: { show: true, readOnly: true, title: this.t('dataView'), lang: [this.t('dataView'), this.t('close'), this.t('refresh')] },
                    saveAsImage: { show: true, title: this.t('downloadImage') }
                }
            },
            grid: { left: 78, right: 280, top: 70, bottom: 70 },
            xAxis: {
                type: 'value', min: 0, name: isEnglish ? 'Surv_Months' : '存活月數',
                nameLocation: 'middle', nameGap: 38,
                splitLine: { lineStyle: { color: '#e5e7eb' } }
            },
            yAxis: {
                type: 'value', min: 0, max: 1, interval: 0.2,
                name: isEnglish ? 'Cum Survival' : '累積存活率',
                nameLocation: 'middle', nameGap: 52,
                axisLabel: { formatter: value => Number(value).toFixed(1) },
                splitLine: { lineStyle: { color: '#e5e7eb' } }
            },
            series: chartSeries,
            graphic: [{
                id: 'survivalLegendTitle', type: 'group', left: legendLeft, top: 92,
                children: [
                    { type: 'rect', shape: { x: 0, y: 0, width: 190, height: 18 }, style: { fill: 'transparent' }, silent: true },
                    { type: 'text', x: 0, y: 0, style: { text: 'AJCC 8th', fill: '#4b5563', fontSize: 12, fontWeight: 600 } }
                ]
            }, ...(seriesData.length ? [] : [{
                type: 'text', left: 'center', top: 'middle',
                style: { text: this.t('noData'), fill: '#6b7280', fontSize: 14 }
            }])]
        }, true);
        if (caption) {
            caption.innerHTML = isEnglish
                ? `Figure. Kaplan–Meier Survival Curves of ${this.getEnglishCancerPatientLabel(selectedCancer)}, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('chart', yearTitle, selectedCancer, 'Kaplan–Meier存活曲線');
        }
    };

window.DashboardRenderer.updateSurvivalChartLayout = function() {
        const chart = window.dashboardSurvivalChartInstance;
        if (!chart) return;
        chart.resize();
        const legendLeft = Math.max(0, chart.getWidth() - 260);
        chart.setOption({
            legend: { left: legendLeft },
            graphic: [{ id: 'survivalLegendTitle', left: legendLeft }]
        });
    };

window.DashboardRenderer.renderSurvivalTable = function(survivalData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualSurvivalTableHead');
        const body = document.getElementById('annualSurvivalTableBody');
        const caption = document.getElementById('annualSurvivalCaption');
        if (!head || !body) return;

        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        if (caption) {
            caption.innerHTML = isEnglish
                ? `Table. Kaplan–Meier Survival of ${this.getEnglishCancerPatientLabel(selectedCancer)},\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, 'Kaplan–Meier存活率');
        }
        head.innerHTML = isEnglish
            ? '<tr><th rowspan="2">AJCC8th</th><th rowspan="2">Total</th><th rowspan="2">Events</th><th colspan="2">Censored</th></tr><tr><th>Count</th><th>Percentage</th></tr>'
            : '<tr><th rowspan="2">AJCC8th</th><th rowspan="2">總數</th><th rowspan="2">事件<br>數目</th><th colspan="2">設限</th></tr><tr><th>數目</th><th>百分比</th></tr>';

        const rows = Array.isArray(survivalData?.rows) ? survivalData.rows : [];
        body.innerHTML = rows.length
            ? rows.map(item => `
                <tr class="${item.stage === 'Overall' ? 'fw-bold table-light' : ''}">
                  <td>${this.escapeHtml(item.stage)}</td><td>${Number(item.total || 0)}</td>
                  <td>${Number(item.events || 0)}</td><td>${Number(item.censored || 0)}</td>
                  <td>${Number(item.percentage || 0).toFixed(1)}%</td>
                </tr>`).join('')
            : `<tr><td colspan="5" class="text-center py-4">${this.t('noData')}<br><span class="text-muted small">${this.escapeHtml(survivalData?.no_data_reason || '查無符合條件的存活資料。')}</span></td></tr>`;
        this.renderSurvivalExclusionButton(survivalData?.exclusion_summary || {});
        this.renderSurvivalChart(survivalData, yearTitle, cancerTitle);
    };

/* ── 癌症登記可分析個案與確診個案表 ── */
window.DashboardRenderer.renderAnalyzableConfirmedTable = function(tableData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualAnalyzableConfirmedTableHead');
        const body = document.getElementById('annualAnalyzableConfirmedTableBody');
        const caption = document.getElementById('annualAnalyzableConfirmedCaption');
        const note = document.getElementById('annualAnalyzableConfirmedNote');
        if (!head || !body || !tableData) return;

        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        if (caption) {
            caption.innerHTML = isEnglish
                ? `Table . Analysis-Eligible and Confirmed Cases of ${this.getEnglishCancerPatientLabel(selectedCancer)} in the Cancer Registry,\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, this.t('analyzableConfirmed'));
        }

        const totalCasesHeader = isEnglish ? `${this.t('cancerTotal')}, ${yearTitle}` : `${yearTitle} ${this.t('cancerTotal')}`;
        head.innerHTML = `<tr><th>${totalCasesHeader}<br>(A)</th><th>${this.t('analysisEligibleCases')}<br>(B)</th><th>${this.t('analysisEligiblePercent')}<br>(B/A)</th><th>${this.t('microscopicallyConfirmedCases')}<br>(C)</th><th>${this.t('microscopicallyConfirmedPercent')}<br>(C/B)</th></tr>`;
        body.innerHTML = `<tr><td>${tableData.total_count}</td><td>${tableData.analyzable_count}</td><td>${tableData.analyzable_percent}</td><td>${tableData.confirmed_count}</td><td>${tableData.confirmed_percent}</td></tr>`;

        if (note) {
            note.innerHTML = `<div>${this.t('analysisEligibleNote')}</div><div class="annual-analyzable-note-item">${this.t('analysisEligibleClass1')}</div><div class="annual-analyzable-note-item">${this.t('analysisEligibleClass2')}</div>`;
        }
    };

/* ── 個案分類分佈表 ── */
window.DashboardRenderer.renderDiagnosisClassificationTable = function(tableData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualDiagnosisClassificationTableHead');
        const body = document.getElementById('annualDiagnosisClassificationTableBody');
        const caption = document.getElementById('annualDiagnosisClassificationCaption');
        if (!head || !body || !tableData) return;

        if (caption) {
            const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
            caption.innerHTML = window.DashboardI18n?.getLanguage() === 'en'
                ? `Table . ${this.getEnglishCancerPatientLabel(selectedCancer)} Case Class Distribution,\u00a0${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${this.t('classification')}${this.t('distribution')}`);
        }

        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const percentageHeader = isEnglish ? '%' : `${this.t('percentage')}%`;
        const classificationHeader = isEnglish ? 'Class' : this.t('classification');
        head.innerHTML = `<tr><th class="text-center">${classificationHeader}</th><th class="text-center">${this.t('people')}</th><th class="text-center">${percentageHeader}</th></tr>`;
        
        const total = tableData.total_count || 1;
        const calcPct = (val) => (val / total * 100).toFixed(1) + '%';
        
        const classMappings = [
            {
                title: this.t('class0'),
                totalKey: 'class0_total',
                subClasses: [
                    { key: '0_1_0', label: this.t('class010') },
                    { key: '0_1_2', label: this.t('class012') }
                ]
            },
            {
                title: this.t('class1'),
                totalKey: 'class1_total',
                subClasses: [
                    { key: '1_1_1', label: this.t('class111') },
                    { key: '1_1_3', label: this.t('class113') },
                    { key: '1_1_4', label: this.t('class114') }
                ]
            },
            {
                title: this.t('class2'),
                totalKey: 'class2_total',
                subClasses: [
                    { key: '2_2_1', label: this.t('class221') },
                    { key: '2_2_3', label: this.t('class223') }
                ]
            },
            {
                title: this.t('class3'),
                totalKey: 'class3_total',
                subClasses: [
                    { key: '3_2_0', label: this.t('class320') },
                    { key: '3_3_2', label: this.t('class332') }
                ]
            }
        ];
        
        let html = '';
        classMappings.forEach(cls => {
            const clsTotal = tableData[cls.totalKey] || 0;
            if (clsTotal > 0) {
                html += `<tr class="table-light" style="border-top: 2px solid #6c757d;"><td style="font-size: 1.1em; font-weight: 900;">${cls.title}</td><td class="text-center fw-bold" style="font-weight: bold;">${clsTotal}</td><td class="text-center fw-bold" style="font-weight: bold;">${calcPct(clsTotal)}</td></tr>`;
                cls.subClasses.forEach(sub => {
                    const count = tableData[sub.key] || 0;
                    if (count > 0) {
                        html += `<tr><td class="ps-4">${sub.label}</td><td class="text-end">${count}</td><td class="text-end">${calcPct(count)}</td></tr>`;
                    }
                });
            }
        });    
        html += `<tr class="table-secondary fw-bold" style="font-weight: bold; border-top: 2px solid #6c757d;"><td class="text-center">${this.t('total')}</td><td class="text-center">${tableData.total_count}</td><td class="text-center">100.0%</td></tr>`;
        body.innerHTML = html;
    };

/* ── LLM敘述分析 ── */
window.DashboardRenderer.fetchLlmInsight = function(fieldKey, chartData, fields, responseContainerId, buttonId, options = {}) {
        const container = document.getElementById(responseContainerId);
        const button = document.getElementById(buttonId);
        const modeAi = document.getElementById('mode_ai') ? document.getElementById('mode_ai').value : 'balanced';
        const language = options.language || window.DashboardI18n?.getLanguage() || 'zh-TW';
        const shouldDisplay = options.display !== false;
        const shouldManageButton = options.manageButton !== false;
        const yearStart = document.getElementById('filterYearStart')?.value.trim() || '';
        const yearEnd = document.getElementById('filterYearEnd')?.value.trim() || '';
        const sessionKey = this.getInsightSessionKey(fieldKey, chartData, fields, modeAi, yearStart, yearEnd);
        const cacheKey = `${language}|${modeAi}|${fieldKey}`;
        const storedInsights = options.forceRefresh === true ? null : this.getSessionInsights(sessionKey);
        if (storedInsights) {
            Object.entries(storedInsights).forEach(([storedLanguage, insight]) => {
                this.insightCache.set(`${storedLanguage}|${modeAi}|${fieldKey}`, insight);
            });
        }
        const cachedInsight = storedInsights?.[language] || this.insightCache.get(cacheKey);
        if (cachedInsight && options.forceRefresh !== true) {
            if (shouldDisplay && container) container.innerText = cachedInsight;
            if (shouldManageButton && button) button.disabled = false;
            return Promise.resolve({ success: true, cached: true });
        }

        const showResult = (result) => {
            if (!shouldDisplay || (window.DashboardI18n?.getLanguage() || 'zh-TW') !== language) return;
            if (result.success) {
                if (container) container.innerText = result.insights?.[language] || result.insight;
            } else if (container) {
                container.innerText = this.t('insightFailed') + (result.error || 'error');
            }
        };
        const requestKey = sessionKey;
        const pendingRequest = this.insightRequests.get(requestKey);
        if (pendingRequest) {
            if (shouldDisplay && container) container.innerText = this.t('generatingInsight');
            return pendingRequest.then(result => {
                showResult(result);
                return result;
            });
        }

        if (shouldDisplay && container) container.innerText = this.t('generatingInsight');
        if (shouldManageButton && button) button.disabled = true;

        const cacheGeneration = this.insightCacheGeneration;
        const request = fetch('/api/chart_insight', {method: 'POST',headers: { 'Content-Type': 'application/json' },body: JSON.stringify({ field_key: fieldKey, data: chartData, fields: fields, mode_ai: modeAi, year_start: yearStart, year_end: yearEnd, language })})
        .then(async res => {
            try {
                return await res.json();
            } catch (_) {
                return { success: false, error: `HTTP ${res.status}` };
            }
        })
        .then(data => {
            if (data.success) {
                if (this.insightCacheGeneration === cacheGeneration) {
                    Object.entries(data.insights || {}).forEach(([resultLanguage, insight]) => {
                        this.insightCache.set(`${resultLanguage}|${modeAi}|${fieldKey}`, insight);
                    });
                    this.setSessionInsights(sessionKey, data.insights);
                }
            }
            return data;
        })
        .catch(error => ({
            success: false,
            error: error.message || 'error'
        }))
        .finally(() => {
            if (this.insightRequests.get(requestKey) === request) this.insightRequests.delete(requestKey);
        });
        this.insightRequests.set(requestKey, request);
        return request.then(result => {
            if (shouldManageButton && button) button.disabled = false;
            showResult(result);
            return result;
        });
    };

window.DashboardRenderer.fetchLlmInsightWithRetry = async function(fieldKey, chartData, fields, responseContainerId, buttonId, options = {}) {
        let result = null;
        for (let attempt = 0; attempt < 3; attempt += 1) {
            result = await this.fetchLlmInsight(
                fieldKey, chartData, fields, responseContainerId, buttonId,
                { ...options, forceRefresh: options.forceRefresh === true || attempt > 0 }
            );
            if (result?.success) return result;
        }
        return result;
    };

// 取得年度字串
window.DashboardRenderer.getSelectedYearTitle = function() {
        const startYear = document.getElementById('filterYearStart')?.value.trim();
        const endYear = document.getElementById('filterYearEnd')?.value.trim();
        if (startYear && endYear && startYear !== endYear) return `${startYear}-${endYear}`;
        return startYear || endYear || 'XXXX';
    };

// 取得癌症標題
window.DashboardRenderer.getSelectedCancerTitle = function() {
        const language = window.DashboardI18n?.getLanguage();
        const cancerNameMap = window.dashboardCancerNameTranslations || {};
        const selectedKeys = window.dashboardSelectedCancerDisplayKeys || [];
        if (language === 'en' && selectedKeys.length > 0) {
            const translatedNames = selectedKeys
                .map(key => cancerNameMap[key]?.en)
                .filter(Boolean);
            if (translatedNames.length > 0) return translatedNames.join(', ');
        }
        const cancerTitle = window.dashboardSelectedCancerTitle;
        if (cancerTitle && cancerTitle !== 'XX') return cancerTitle;
        const btnText = document.getElementById('btnCancerPickerText')?.innerText.trim();
        if (!btnText || btnText.includes('尚未選擇')) return 'XX';
        if (btnText.includes('全部癌症')) return '全部癌症';
        return btnText;
    };

// 組成癌症字串
window.DashboardRenderer.getCancerTitleForSentence = function(cancerTitle) {
        if (!cancerTitle || cancerTitle === 'XX') return `XX${this.t('cancer')}`;
        if (window.DashboardI18n?.getLanguage() === 'en' && (window.dashboardSelectedCancerDisplayKeys || []).length > 0) return cancerTitle;
        if (cancerTitle.includes('癌') || /cancer/i.test(cancerTitle) || cancerTitle.includes('全部癌症')) return cancerTitle;
        return `${cancerTitle}${this.t('cancer')}`;
    };

window.DashboardRenderer.insightCache = new Map();
window.DashboardRenderer.insightRequests = new Map();
window.DashboardRenderer.insightCacheGeneration = 0;
window.DashboardRenderer.insightSessionPrefix = 'dashboard-bilingual-insight-v1:';

window.DashboardRenderer.hashInsightContext = function(value) {
        let first = 0x811c9dc5;
        let second = 0x9e3779b9;
        for (let index = 0; index < value.length; index += 1) {
            const code = value.charCodeAt(index);
            first = Math.imul(first ^ code, 0x01000193);
            second = Math.imul(second ^ code, 0x85ebca6b);
        }
        return `${(first >>> 0).toString(16).padStart(8, '0')}${(second >>> 0).toString(16).padStart(8, '0')}`;
    };

window.DashboardRenderer.getInsightSessionKey = function(fieldKey, chartData, fields, modeAi, yearStart, yearEnd) {
        const context = JSON.stringify({
            version: 'v1-bilingual',
            fileId: window.dashboardAnalysisFileId || '',
            fieldKey,
            chartData,
            fields,
            modeAi,
            yearStart,
            yearEnd
        });
        return `${this.insightSessionPrefix}${this.hashInsightContext(context)}`;
    };

window.DashboardRenderer.getSessionInsights = function(sessionKey) {
        try {
            const value = JSON.parse(window.sessionStorage.getItem(sessionKey) || 'null');
            return value?.['zh-TW'] && value?.en ? value : null;
        } catch (_) {
            return null;
        }
    };

window.DashboardRenderer.setSessionInsights = function(sessionKey, insights) {
        if (!insights?.['zh-TW'] || !insights?.en) return;
        try {
            window.sessionStorage.setItem(sessionKey, JSON.stringify({
                'zh-TW': insights['zh-TW'],
                en: insights.en
            }));
        } catch (_) {
            // Storage may be unavailable or full; the in-memory cache still supports this page session.
        }
    };

window.DashboardRenderer.clearInsightCache = function() {
        this.insightCache.clear();
        this.insightCacheGeneration += 1;
        this.insightRequests.clear();
    };

window.DashboardRenderer.getHistologyWarningText = function(item) {
        const code = item.icdo_code || '';
        if (item.warning_type === 'condition_mismatch') {
            return {
                message: this.t('histologyConditionMismatch', { code }),
                detail: this.t('histologyConditionMismatchDetail')
            };
        }
        if (item.warning_type === 'not_in_mapping') {
            return {
                message: this.t('histologyRuleExcluded', { code }),
                detail: this.t('histologyRuleExcludedDetail')
            };
        }
        return {
            message: item.message || this.t('histologyRuleExcluded', { code }),
            detail: item.detail_message || this.t('histologyRuleExcludedDetail')
        };
    };

window.DashboardRenderer.getHistologyRawWarningText = function(item) {
        if (!item.raw_data_message) return '';
        const rawMessage = this.decodeHtmlEntities(item.raw_data_message).replace(/\*\*/g, '');
        if (window.DashboardI18n?.getLanguage() !== 'en') return rawMessage;
        return rawMessage
            .replace(/（/g, '(')
            .replace(/）/g, ')')
            .replace(/原始資料/g, 'Source data')
            .replace(/診斷年度/g, 'Diagnosis year')
            .replace(/原發部位/g, 'Primary site');
    };

window.DashboardRenderer.updateChartCaptions = function(yearTitle, cancerTitle) {
        const cancer = this.getCancerTitleForSentence(cancerTitle);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const captions = {
            annualSexAgeChartCaption: isEnglish
                ? `Figure : Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(cancer)} Patients, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('chart', yearTitle, cancer, `${this.t('sexAge')}${this.t('distribution')}`, { newDiagnosis: true }),
            annualHistologyChartCaption: isEnglish
                ? `Figure. Histological Distribution of ${this.getEnglishCancerPatientLabel(cancer)}, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('chart', yearTitle, cancer, `${this.t('histology')}${this.t('distribution')}`),
            annualDiagnosisClassificationChartCaption: isEnglish
                ? `Figure. ${this.getEnglishCancerPatientLabel(cancer)} Case Class Distribution, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('chart', yearTitle, cancer, `${this.t('classification')}${this.t('distribution')}`)
        };
        Object.entries(captions).forEach(([id, content]) => {
            const element = document.getElementById(id);
            if (element) element.innerHTML = content;
        });
    };

window.DashboardRenderer.refreshInsightControls = function() {
        document.querySelectorAll('.llm-insight-title').forEach(title => {
            title.textContent = this.t('llmInsight');
        });
        document.querySelectorAll('button[id^="btnAi"]').forEach(button => {
            if (button.style.display !== 'none') button.textContent = this.t('regenerateInsight');
        });
    };

window.DashboardRenderer.regenerateInsightsForLanguage = function({ excludeButtonIds = [] } = {}) {
        const excluded = new Set(excludeButtonIds);
        const buttons = Array.from(document.querySelectorAll('button[id^="btnAi"]'))
            .filter(button => !excluded.has(button.id) && button.style.display !== 'none' && typeof button.onclick === 'function');
        return Promise.all(buttons.map(button => button.onclick()));
    };

window.DashboardRenderer.ensureInsightsForLanguage = async function({ retry = true, excludeButtonIds = [] } = {}) {
        const run = () => this.regenerateInsightsForLanguage({ excludeButtonIds });
        let results = await run();
        if (retry && results.some(result => !result?.success)) results = await run();
        if (results.some(result => !result?.success)) {
            throw new Error('部分語言模型敘述尚未準備完成');
        }
        return results;
    };
window.DashboardRenderer.updateHistologyChart = function(histologyData, noDataReason = '') {
        if (!window.dashboardHistologyChartInstance || !histologyData) return;
        const yearTitle = this.getSelectedYearTitle();
        const cancerTitle = this.getCancerTitleForSentence(this.getSelectedCancerTitle());
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
        const totalValid = validData.reduce((sum, item) => sum + item.count, 0);
        const topData = [...validData].reverse();
        const categories = topData.map(item => this.histologyDisplayName(item));
        const chartSeriesData = topData.map(item => ({
            value: totalValid > 0 ? Number(((item.count / totalValid) * 100).toFixed(1)) : 0,
            count: item.count
        }));
        const chartDom = document.getElementById('histologyChart');
        const chartTitle = isEnglish
            ? `Histological Distribution of ${this.getEnglishCancerPatientLabel(cancerTitle)}, ${yearTitle}`
            : `${yearTitle}年${cancerTitle}${this.t('histologyDistribution')}`;
        if (chartDom) {
            chartDom.style.height = `${Math.max(450, categories.length * this.histologyRowHeight(categories))}px`;
            window.dashboardHistologyChartInstance.resize();
        }
        if (categories.length === 0) {
            if (chartDom) chartDom.style.height = '450px';
            window.dashboardHistologyChartInstance.setOption({
                title: { text: chartTitle, subtext: this.t('source'), left: 'center', textStyle: { fontSize: 18, fontWeight: 'bold' } },
                tooltip: { show: false },
                toolbox: { show: false },
                xAxis: { show: false, data: [] },
                yAxis: { show: false, data: [] },
                series: [{ data: [] }],
                graphic: [{
                    type: 'text',
                    left: 'center',
                    top: 'middle',
                    style: {
                        text: `${this.t('noData')}\n${noDataReason || '查無符合條件的組織型態資料。'}`,
                        fill: '#6b7280',
                        fontSize: 14,
                        fontWeight: 500,
                        lineHeight: 24,
                        textAlign: 'center'
                    }
                }]
            }, { replaceMerge: ['graphic'] });
            window.dashboardHistologyChartInstance.resize();
            return;
        }
        window.dashboardHistologyChartInstance.setOption({
            title: {
                text: chartTitle,
                subtext: this.t('source'),
                left: 'center',
                textStyle: { fontSize: 18, fontWeight: 'bold' }
            },
            tooltip: { show: true },
            graphic: [],
            xAxis: { show: true, name: `${this.t('percentage')} (%)` },
            yAxis: { show: true, data: categories },
            toolbox: {
                show: true,
                feature: {
                    dataView: { show: true, readOnly: false, title: this.t('dataView'), lang: [this.t('dataView'), this.t('close'), this.t('refresh')] },
                    saveAsImage: { show: true, title: this.t('downloadImage') }
                }
            },
            series: [{ name: this.t('caseRatio'), data: chartSeriesData }]
        }, { replaceMerge: ['graphic'] });
    };

window.DashboardRenderer.rerenderDashboardLanguage = function(options = {}) {
        const selector = document.getElementById('dashboardLanguageSelect');
        if (selector && window.DashboardI18n) selector.value = window.DashboardI18n.getLanguage();
        const languageLabel = document.getElementById('dashboardLanguageLabel');
        if (languageLabel && selector) languageLabel.textContent = selector.value === 'en' ? 'English' : '繁體中文';
        const headerMap = {
            histologyNameHeader: this.t('histology'),
            histologyCountHeader: this.t('people'),
            histologyPercentageHeader: window.DashboardI18n?.getLanguage() === 'en' ? '%' : `${this.t('percentage')}%`
        };
        Object.entries(headerMap).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) element.textContent = value;
        });
        this.refreshInsightControls();
        if (!window.lastChartData) return;
        const yearTitle = this.getSelectedYearTitle();
        const cancerTitle = this.getSelectedCancerTitle();
        this.renderSexAgeTable(window.lastChartData.genderAgeData, yearTitle, cancerTitle);
        this.renderAgeMedianTable(window.lastChartData.ageMedianData, yearTitle, cancerTitle);
        this.renderAnalyzableConfirmedTable(window.lastChartData.analyzableConfirmedData, yearTitle, cancerTitle);
        this.renderHistologyTable(window.lastChartData.histologyData, yearTitle, cancerTitle, window.lastChartData.histologyNoDataReason);
        this.renderColonHistologyTableNote(window.lastChartData.histologyWarnings || []);
        this.renderHistologyWarningButton(this.currentHistologyWarnings);
        this.renderDiagnosisClassificationTable(window.lastChartData.diagnosisClassificationData, yearTitle, cancerTitle);
        this.renderDiagnosisClassificationChart(window.lastChartData.diagnosisClassificationData, yearTitle, cancerTitle);
        if (window.lastChartData.stageReports) {
            this.renderStageReportTabs(window.lastChartData.stageReports, yearTitle, cancerTitle);
        }
        this.renderStageFirstCourseTables(window.lastChartData.stageFirstCourseData, yearTitle, cancerTitle);
        this.renderStageSurgeryTables(window.lastChartData.stageSurgeryData, yearTitle, cancerTitle);
        this.renderSurvivalTable(window.lastChartData.survivalData, yearTitle, cancerTitle);
        this.updateChartCaptions(yearTitle, cancerTitle);
        if (window.dashboardChartInstance) window.dashboardChartInstance.setOption(this.getGenderAgeChartOption(window.lastChartData.genderAgeData), true);
        this.updateHistologyChart(window.lastChartData.histologyData, window.lastChartData.histologyNoDataReason);
        if (options.regenerateInsights && !window.dashboardExportPreparing) this.regenerateInsightsForLanguage();
    };

/* ── 顯示年度資料區塊 ── */
window.DashboardRenderer.showAnnualDataContent = function() {
        document.querySelectorAll('.annual-data-content').forEach(el => {
            el.classList.remove('d-none');
        });
    };

document.addEventListener('DOMContentLoaded', function() {
    const languageSelect = document.getElementById('dashboardLanguageSelect');
    if (languageSelect && window.DashboardI18n) {
        const languagePicker = document.getElementById('dashboardLanguagePicker');
        const updateLanguage = (language) => {
            languageSelect.value = language;
            languagePicker.open = false;
            window.DashboardI18n.setLanguage(language);
        };
        languageSelect.value = window.DashboardI18n.getLanguage();
        languageSelect.addEventListener('change', () => window.DashboardI18n.setLanguage(languageSelect.value));
        document.querySelectorAll('.dashboard-language-option').forEach(option => {
            option.addEventListener('click', () => updateLanguage(option.dataset.language));
        });
        window.DashboardRenderer.rerenderDashboardLanguage();
    }
    const captureChartImage = async (chart, optionOverrides = {}) => {
            const originalOption = chart.getOption();
            const captureOption = {
                ...originalOption,
                animation: false,
                animationDuration: 0,
                animationDurationUpdate: 0
            };
            if (optionOverrides.title?.show === false) {
                captureOption.title = (originalOption.title || []).map(title => ({ ...title, show: false }));
            }
            if (optionOverrides.xAxis?.name === '') {
                captureOption.xAxis = (originalOption.xAxis || []).map(axis => ({ ...axis, name: '' }));
            }
            chart.getZr()?.animation?.stop?.();
            chart.clear();
            chart.setOption(captureOption, true);
            chart.resize();
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            chart.getZr()?.flush?.();
            const image = chart.getDataURL({ type: 'png', backgroundColor: '#fff', pixelRatio: 2 });
            chart.clear();
            chart.setOption(originalOption, true);
            chart.resize();
            return image;
    };

    /* 將期別圖名與統計註解合成進匯出圖片，避免 PDF／Word 只擷取 ECharts 畫布。 */
    const appendStageChartAnnotations = async (imageDataUrl, captionText, noteText) => {
            if (!imageDataUrl || (!captionText && !noteText)) return imageDataUrl;
            const image = new Image();
            await new Promise((resolve, reject) => {
                image.onload = resolve;
                image.onerror = reject;
                image.src = imageDataUrl;
            });

            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            const horizontalPadding = 64;
            const topPadding = 36;
            const maxTextWidth = image.width - horizontalPadding * 2;
            const wrapText = (text, font, maxWidth) => {
                context.font = font;
                const characters = Array.from(String(text || ''));
                const lines = [];
                let line = '';
                characters.forEach(character => {
                    const candidate = line + character;
                    if (line && context.measureText(candidate).width > maxWidth) {
                        lines.push(line);
                        line = character;
                    } else {
                        line = candidate;
                    }
                });
                if (line) lines.push(line);
                return lines;
            };
            // ECharts 以 pixelRatio 2 匯出，因此外加文字也使用兩倍字級，縮入報表後才會與既有主題一致。
            const captionFont = 'bold 28px sans-serif';
            const noteFont = '32px sans-serif';
            const captionLines = wrapText(captionText, captionFont, maxTextWidth);
            const noteLines = wrapText(noteText, noteFont, maxTextWidth);
            const captionLineHeight = 40;
            const noteLineHeight = 46;
            const annotationHeight = 22
                + captionLines.length * captionLineHeight
                + (captionLines.length && noteLines.length ? 12 : 0)
                + noteLines.length * noteLineHeight
                + 28;

            canvas.width = image.width;
            canvas.height = image.height + topPadding + annotationHeight;
            context.fillStyle = '#ffffff';
            context.fillRect(0, 0, canvas.width, canvas.height);
            context.drawImage(image, 0, topPadding);

            let y = topPadding + image.height + 22;
            context.fillStyle = '#111827';
            context.textBaseline = 'top';
            context.textAlign = 'center';
            context.font = captionFont;
            captionLines.forEach(line => {
                context.fillText(line, canvas.width / 2, y);
                y += captionLineHeight;
            });
            if (captionLines.length && noteLines.length) y += 12;
            context.textAlign = 'center';
            context.font = noteFont;
            noteLines.forEach(line => {
                context.fillText(line, canvas.width / 2, y);
                y += noteLineHeight;
            });
            return canvas.toDataURL('image/png');
    };

    const collectExportData = async (sharedChartImages = {}, options = {}) => {
            const exportData = [];
            let orderIndex = 0;
            const exportLanguage = window.DashboardI18n?.getLanguage() || 'zh-TW';
            const modeAi = document.getElementById('mode_ai')?.value || 'balanced';
            const generateInsights = options.generateInsights === true;
            const insightFieldKeys = {
                'chartPane-IncidenceAge': '性別與年齡分佈',
                'chartPane-IncidenceMedian': '年齡中位數',
                'chartPane-DiagnosisAnalyzable': '癌症登記可分析個案與確診個案',
                'chartPane-DiagnosisHistology': '組織型態分佈',
                'chartPane-DiagnosisClassification': '個案分類',
                'chartPane-StageSummary': '期別',
                'chartPane-TreatmentFirstCourse': '期別與首次療程',
                'chartPane-TreatmentSurgery': '期別與手術術式',
                'chartPane-CrossYearSurvival': '存活率'
            };
            
            const activeTargets = Array.from(document.querySelectorAll('#chartTabsContainer .chart-tab-btn')).map(btn => btn.dataset.target);
            
            for (const pane of document.querySelectorAll('.chart-pane')) {
                if (pane.id !== 'chartPane-Empty' && activeTargets.includes('#' + pane.id)) {
                    const paneId = pane.id;
                    
                    const wasHidden = pane.classList.contains('d-none');
                    if (wasHidden) {
                        pane.classList.remove('d-none');
                        pane.style.visibility = 'hidden';
                        pane.style.display = 'block';
                        if (paneId === 'chartPane-IncidenceAge' && typeof echarts !== 'undefined') {
                            const inst = echarts.getInstanceByDom(pane.querySelector('#main'));
                            if (inst) inst.resize();
                        } else if (paneId === 'chartPane-DiagnosisHistology' && typeof echarts !== 'undefined') {
                            const inst = echarts.getInstanceByDom(pane.querySelector('#histologyChart'));
                            if (inst) inst.resize();
                        }
                        if (paneId === 'chartPane-DiagnosisClassification' && window.DashboardRenderer && window.DashboardRenderer.classificationChartInst) {
                            window.DashboardRenderer.classificationChartInst.resize();
                        }
                        if (paneId === 'chartPane-CrossYearSurvival' && window.dashboardSurvivalChartInstance) {
                            window.dashboardSurvivalChartInstance.resize();
                        }
                    }

                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

                    /* 期別可能同時選擇多個分期系統與呈現方式，逐一匯出成獨立項目。 */
                    if (paneId === 'chartPane-StageSummary') {
                        const stageReports = Array.isArray(window.lastChartData?.stageReports)
                            ? window.lastChartData.stageReports
                            : [];
                        for (let stageIndex = 0; stageIndex < stageReports.length; stageIndex += 1) {
                            const report = stageReports[stageIndex];
                            const view = report.view || 'stage';
                            const section = view === 'sex'
                                ? document.getElementById('annualStageSexSection')
                                : view === 'age'
                                    ? document.getElementById('annualStageAgeSection')
                                    : document.getElementById('annualStageDistributionSection');
                            ['annualStageDistributionSection', 'annualStageSexSection', 'annualStageAgeSection']
                                .forEach(id => document.getElementById(id)?.classList.add('d-none'));
                            section?.classList.remove('d-none');
                            if (view === 'sex') window.DashboardRenderer.renderStageSexReport(report, window.DashboardRenderer.getSelectedYearTitle(), window.DashboardRenderer.getSelectedCancerTitle());
                            else if (view === 'age') window.DashboardRenderer.renderStageAgeReport(report, window.DashboardRenderer.getSelectedYearTitle(), window.DashboardRenderer.getSelectedCancerTitle());
                            else window.DashboardRenderer.renderStageDistributionReport(report, window.DashboardRenderer.getSelectedYearTitle(), window.DashboardRenderer.getSelectedCancerTitle());
                            if (generateInsights) {
                                const insightResult = await window.DashboardRenderer.configureStageInsight(report);
                                if (!insightResult?.success) throw new Error('Stage insight generation failed.');
                                options.onInsightComplete?.();
                            }
                            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

                            const chart = view === 'sex'
                                ? window.dashboardStageSexChartInstance
                                : view === 'age'
                                    ? window.dashboardStageAgeChartInstance
                                    : window.dashboardStageDistributionChartInstance;
                            const stageTableWrap = section?.querySelector('.annual-report-table-wrap');
                            const stageChartCaption = section?.querySelector('.annual-chart-caption');
                            const stageChartNote = section?.querySelector('.annual-stage-chart-note');
                            const stageButton = document.getElementById('btnAiStageSummary');
                            const stageFieldKey = stageButton?.dataset.insightFieldKey || '';
                            const stageResponse = document.getElementById('llmResponseStageSummary');
                            const stageLlmText = stageFieldKey
                                ? (window.DashboardRenderer?.insightCache?.get(`${exportLanguage}|${modeAi}|${stageFieldKey}`)
                                    || stageResponse?.textContent
                                    || '')
                                : '';
                            const tabKey = view === 'sex' ? 'stageSexTab' : view === 'age' ? 'stageAgeTab' : 'stageTab';
                            const stageTitle = exportLanguage === 'en'
                                ? window.DashboardRenderer.t(tabKey, { system: window.DashboardRenderer.getStageSystemTitle(report.staging_system) })
                                : (report.option || window.DashboardRenderer.t(tabKey, { system: report.staging_system }));
                            const rawStageChartImage = chart ? await captureChartImage(chart) : '';
                            const annotatedStageChartImage = await appendStageChartAnnotations(
                                rawStageChartImage,
                                stageChartCaption?.textContent?.trim() || '',
                                stageChartNote?.textContent?.trim() || ''
                            );

                            exportData.push({
                                id: `chartPane-StageSummary-${stageIndex}`,
                                order: orderIndex++,
                                title: stageTitle,
                                tableHtml: stageTableWrap ? stageTableWrap.innerHTML : '',
                                chartImage: annotatedStageChartImage,
                                chartImageKey: '',
                                llmText: stageLlmText
                            });
                        }

                        if (wasHidden) {
                            pane.classList.add('d-none');
                            pane.style.visibility = '';
                            pane.style.display = '';
                        }
                        continue;
                    }

                    if (paneId === 'chartPane-TreatmentSurgery') {
                        const surgeryTables = Array.isArray(window.lastChartData?.stageSurgeryData)
                            ? window.lastChartData.stageSurgeryData
                            : [];
                        const surgeryContainer = document.getElementById('annualStageSurgeryTables');
                        const surgeryInsightButton = document.getElementById('btnAiTreatmentSurgery');
                        const tableKeyOf = (table, index) => `${table.manual_key || 'unknown'}::${table.system || 'stage'}::${index}`;
                        const tableKeys = surgeryTables.map(tableKeyOf);
                        const activeTableKey = tableKeys.includes(window.stageSurgeryActiveTableKey)
                            ? window.stageSurgeryActiveTableKey
                            : tableKeys[0];

                        for (let surgeryIndex = 0; surgeryIndex < surgeryTables.length; surgeryIndex += 1) {
                            const table = surgeryTables[surgeryIndex];
                            window.stageSurgeryActiveTableKey = tableKeyOf(table, surgeryIndex);
                            window.DashboardRenderer.renderStageSurgeryTables(
                                surgeryTables,
                                window.DashboardRenderer.getSelectedYearTitle(),
                                window.DashboardRenderer.getSelectedCancerTitle()
                            );

                            if (generateInsights && typeof surgeryInsightButton?.onclick === 'function') {
                                const insightResult = await surgeryInsightButton.onclick();
                                if (!insightResult?.success) throw new Error('Surgery insight generation failed.');
                                options.onInsightComplete?.();
                            }

                            const tablePanel = Array.from(
                                surgeryContainer?.querySelectorAll('.stage-surgery-panel') || []
                            ).find(panel => panel.dataset.stageSurgeryKey === tableKeyOf(table, surgeryIndex));
                            const fieldKey = surgeryInsightButton?.dataset.insightFieldKey || '';
                            const llmText = fieldKey
                                ? (window.DashboardRenderer?.insightCache?.get(`${exportLanguage}|${modeAi}|${fieldKey}`) || '')
                                : '';
                            const stageSystem = table.system || (exportLanguage === 'en' ? 'Unspecified' : '未指定');
                            const title = exportLanguage === 'en'
                                ? `${table.cancer_name_en || table.manual_key} (${stageSystem} Stage) and Surgical Procedure`
                                : `${table.cancer_name || table.manual_key}（${stageSystem}期別）與手術術式`;

                            exportData.push({
                                id: `chartPane-TreatmentSurgery-${surgeryIndex}`,
                                order: orderIndex++,
                                title,
                                tableHtml: tablePanel ? tablePanel.innerHTML : '',
                                chartImage: '',
                                chartImageKey: '',
                                llmText
                            });
                        }

                        window.stageSurgeryActiveTableKey = activeTableKey;
                        window.DashboardRenderer.renderStageSurgeryTables(
                            surgeryTables,
                            window.DashboardRenderer.getSelectedYearTitle(),
                            window.DashboardRenderer.getSelectedCancerTitle()
                        );

                        if (wasHidden) {
                            pane.classList.add('d-none');
                            pane.style.visibility = '';
                            pane.style.display = '';
                        }
                        continue;
                    }
                    if (paneId === 'chartPane-TreatmentFirstCourse') {
                        const treatmentTables = Array.isArray(window.lastChartData?.stageFirstCourseData)
                            ? window.lastChartData.stageFirstCourseData
                            : [];
                        const treatmentContainer = document.getElementById('annualStageFirstCourseTables');
                        const treatmentInsightButton = document.getElementById('btnAiTreatmentFirstCourse');
                        const systems = treatmentTables.map(table => table.system);
                        const activeSystem = systems.includes(window.stageFirstCourseActiveSystem)
                            ? window.stageFirstCourseActiveSystem
                            : systems[0];

                        for (let treatmentIndex = 0; treatmentIndex < treatmentTables.length; treatmentIndex += 1) {
                            const table = treatmentTables[treatmentIndex];
                            window.stageFirstCourseActiveSystem = table.system;
                            window.DashboardRenderer.renderStageFirstCourseTables(
                                treatmentTables,
                                window.DashboardRenderer.getSelectedYearTitle(),
                                window.DashboardRenderer.getSelectedCancerTitle()
                            );

                            if (generateInsights && typeof treatmentInsightButton?.onclick === 'function') {
                                const insightResult = await treatmentInsightButton.onclick();
                                if (!insightResult?.success) throw new Error('First-course insight generation failed.');
                                options.onInsightComplete?.();
                            }

                            const tablePanel = Array.from(
                                treatmentContainer?.querySelectorAll('.stage-first-course-panel') || []
                            ).find(panel => panel.dataset.stageSystem === table.system);
                            const fieldKey = treatmentInsightButton?.dataset.insightFieldKey || '';
                            const llmText = fieldKey
                                ? (window.DashboardRenderer?.insightCache?.get(`${exportLanguage}|${modeAi}|${fieldKey}`) || '')
                                : '';
                            const stageSystem = table.system || (exportLanguage === 'en' ? 'Unspecified' : '未指定');
                            const title = exportLanguage === 'en'
                                ? `${table.system} Stage and First Course Treatment`
                                : `${table.system}期別與首次療程`;

                            exportData.push({
                                id: `chartPane-TreatmentFirstCourse-${treatmentIndex}`,
                                order: orderIndex++,
                                title,
                                tableHtml: tablePanel ? tablePanel.innerHTML : '',
                                chartImage: '',
                                chartImageKey: '',
                                llmText
                            });
                        }

                        window.stageFirstCourseActiveSystem = activeSystem;
                        window.DashboardRenderer.renderStageFirstCourseTables(
                            treatmentTables,
                            window.DashboardRenderer.getSelectedYearTitle(),
                            window.DashboardRenderer.getSelectedCancerTitle()
                        );

                        if (wasHidden) {
                            pane.classList.add('d-none');
                            pane.style.visibility = '';
                            pane.style.display = '';
                        }
                        continue;
                    }

                    let chartImage = '';
                    let chartImageKey = '';
                    if (paneId === 'chartPane-IncidenceAge' && window.dashboardChartInstance) {
                        chartImage = await captureChartImage(window.dashboardChartInstance);
                    } else if (paneId === 'chartPane-DiagnosisHistology' && window.dashboardHistologyChartInstance) {
                        chartImageKey = 'histology-full';
                        if (!sharedChartImages[chartImageKey]) {
                            sharedChartImages[chartImageKey] = await captureChartImage(
                                window.dashboardHistologyChartInstance,
                                { title: { show: false }, xAxis: { name: '' } }
                            );
                        }
                    } else if (paneId === 'chartPane-DiagnosisClassification' && window.DashboardRenderer && window.DashboardRenderer.classificationChartInst) {
                        chartImage = await captureChartImage(window.DashboardRenderer.classificationChartInst);
                    } else if (paneId === 'chartPane-CrossYearSurvival' && window.dashboardSurvivalChartInstance) {
                        chartImage = await captureChartImage(window.dashboardSurvivalChartInstance);
                    }
                    
                    const tableWrap = pane.querySelector('.annual-report-table-wrap');
                    let tableHtml = tableWrap ? tableWrap.innerHTML : '';
                    
                    let llmText = '';
                    const llmDiv = pane.querySelector('[id^="llmResponse"]');
                    if (llmDiv) {
                        const insightButton = pane.querySelector('button[id^="btnAi"]');
                        if (generateInsights && typeof insightButton?.onclick === 'function') {
                            const insightResult = await insightButton.onclick();
                            if (!insightResult?.success) throw new Error('Insight generation failed.');
                            options.onInsightComplete?.();
                        }
                        const fieldKey = insightButton?.dataset.insightFieldKey || insightFieldKeys[paneId];
                        const cachedInsight = fieldKey
                            ? window.DashboardRenderer?.insightCache?.get(`${exportLanguage}|${modeAi}|${fieldKey}`)
                            : '';
                        llmText = cachedInsight || (exportLanguage === 'en'
                            ? ''
                            : llmDiv.textContent || llmDiv.innerText);
                    }

                    if (wasHidden) {
                        pane.classList.add('d-none');
                        pane.style.visibility = '';
                        pane.style.display = '';
                    }

                    let title = window.DashboardRenderer.t('chartSexAge');
                    if (paneId === 'chartPane-IncidenceAge') title = window.DashboardRenderer.t('chartSexAge');
                    else if (paneId === 'chartPane-IncidenceMedian') title = window.DashboardRenderer.t('chartAgeMedian');
                    else if (paneId === 'chartPane-DiagnosisAnalyzable') title = window.DashboardRenderer.t('chartAnalyzable');
                    else if (paneId === 'chartPane-DiagnosisHistology') title = window.DashboardRenderer.t('chartHistology');
                    else if (paneId === 'chartPane-DiagnosisClassification') title = window.DashboardRenderer.t('chartClassification');
                    else if (paneId === 'chartPane-StageSummary') title = window.DashboardRenderer.t('chartStage');
                    else if (paneId === 'chartPane-TreatmentFirstCourse') title = window.DashboardI18n?.getLanguage() === 'en' ? 'Stage and First Course Treatment' : '期別與首次療程';
                    else if (paneId === 'chartPane-TreatmentSurgery') title = window.DashboardI18n?.getLanguage() === 'en' ? 'Stage and Surgical Procedure' : '期別與手術術式';
                    else if (paneId === 'chartPane-CrossYearSurvival') title = window.DashboardI18n?.getLanguage() === 'en' ? 'Survival' : '存活率';

                    exportData.push({
                        id: paneId,
                        order: orderIndex++,
                        title: title,
                        tableHtml: tableHtml,
                        chartImage: chartImage,
                        chartImageKey: chartImageKey,
                        llmText: llmText
                    });
                }
            }

            return exportData;
    };

    const btnPrepareExport = document.getElementById('btnPrepareExport');
    if (btnPrepareExport) {
        btnPrepareExport.addEventListener('click', async function() {
            const originalLanguage = window.DashboardI18n?.getLanguage() || 'zh-TW';
            const exportDataByLanguage = {};
            const sharedChartImages = {};
            let preparationError = null;
            btnPrepareExport.disabled = true;
            window.dashboardExportPreparing = true;
            if (window.utils?.showLoading) {
                window.utils.showLoading('資料分析中，請稍後...');
            }
            try {

                const activePaneIds = new Set(Array.from(document.querySelectorAll('#chartTabsContainer .chart-tab-btn')).map(button => button.dataset.target));
                let totalInsights = 0;
                if (activePaneIds.has('#chartPane-StageSummary')) totalInsights += (window.lastChartData?.stageReports || []).length;
                if (activePaneIds.has('#chartPane-TreatmentFirstCourse')) totalInsights += (window.lastChartData?.stageFirstCourseData || []).length;
                if (activePaneIds.has('#chartPane-TreatmentSurgery')) totalInsights += (window.lastChartData?.stageSurgeryData || []).length;
                for (const paneId of activePaneIds) {
                    if (['#chartPane-StageSummary', '#chartPane-TreatmentFirstCourse', '#chartPane-TreatmentSurgery'].includes(paneId)) continue;
                    const pane = document.querySelector(paneId);
                    if (pane?.querySelector('[id^=llmResponse]') && pane.querySelector('[id^=btnAi]')) totalInsights += 1;
                }
                let completedInsights = 0;
                const updateInsightProgress = () => window.utils?.showLoading?.('正在產生LLM敘述(' + completedInsights + '/' + Math.max(totalInsights, 1) + ')...');
                updateInsightProgress();
                const onInsightComplete = () => {
                    completedInsights += 1;
                    updateInsightProgress();
                };
                await window.DashboardI18n?.setLanguage('zh-TW');
                exportDataByLanguage['zh-TW'] = await collectExportData(sharedChartImages, { generateInsights: true, onInsightComplete });
                await window.DashboardI18n?.setLanguage('en');
                exportDataByLanguage.en = await collectExportData(sharedChartImages);
            } catch (error) {
                console.error('Export preparation failed:', error);
                preparationError = error;
            } finally {
                await window.DashboardI18n?.setLanguage(originalLanguage);
                window.dashboardExportPreparing = false;
                btnPrepareExport.disabled = false;
            }

            if (preparationError) {
                if (window.utils?.hideLoading) window.utils.hideLoading();
                const isInsightFailure = /insight generation failed/i.test(String(preparationError?.message || ''));
                utils.alert(isInsightFailure ? '語言模型敘述尚未完成；系統未建立不完整匯出，請稍後再試。' : '匯出內容準備失敗，請再試一次。', 'error');
                return;
            }

            if (!exportDataByLanguage['zh-TW']?.length) {
                if (window.utils?.hideLoading) window.utils.hideLoading();
                utils.alert('沒有可匯出的內容，請先查詢圖表！', 'warning');
                return;
            }

            localStorage.setItem('dashboard_export_data', JSON.stringify({
                version: 3,
                languages: exportDataByLanguage,
                sharedChartImages: sharedChartImages
            }));
            window.location.href = '/dashboard/export_report';
        });
    }
});

/* ── 期別與手術術式表（附錄 B） ── */
window.DashboardRenderer.renderStageSurgeryTables = function(tables, yearTitle, cancerTitle) {
    const container = document.getElementById('annualStageSurgeryTables');
    if (!container) return;
    if (!Array.isArray(tables) || !tables.length) {
        container.innerHTML = '<div class="text-secondary">目前沒有符合所選癌別的手術術式資料；請選擇已匯入術式對照的癌別與至少一項期別分析。</div>';
        return;
    }
    const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
    const tableKeyOf = (item, index) => `${item.manual_key || 'unknown'}::${item.system || 'stage'}::${index}`;
    const tableKeys = tables.map(tableKeyOf);
    const activeTableKey = tableKeys.includes(window.stageSurgeryActiveTableKey)
        ? window.stageSurgeryActiveTableKey
        : tableKeys[0];
    const panels = tables.map((item, tableIndex) => {
        const tableKey = tableKeyOf(item, tableIndex);
        const tableCancer = isEnglish ? (item.cancer_name_en || cancerTitle) : (item.cancer_name || cancerTitle);
        const stages = item.stage_columns || [];
        const rows = item.rows || [];
        const rowByKey = new Map(rows.map(row => [row.row_key, row]));
        const levelOf = (row) => {
            const configuredLevel = row.display_level;
            if (configuredLevel !== null && configuredLevel !== undefined && configuredLevel !== ''
                && Number.isFinite(Number(configuredLevel))) {
                return Math.max(0, Number(configuredLevel));
            }
            let level = 0, parent = rowByKey.get(row.parent_row_key), seen = new Set();
            while (parent && !seen.has(parent.row_key)) {
                seen.add(parent.row_key); level += 1; parent = rowByKey.get(parent.parent_row_key);
            }
            return level;
        };
        const bodyRows = rows.map(row => {
            const isHeading = String(row.row_type || '').toLowerCase() === 'heading';
            const code = row.code_short && row.code_long
                ? `${row.code_short}/${row.code_long}`
                : row.code_short || row.code_long || '';
            const label = isHeading
                ? row.procedure || ''
                : `${code}${code && row.procedure ? ' ' : ''}${row.procedure || ''}`;            const indent = Math.min(levelOf(row), 3) * 1.5;
            const values = (row.values || []).map(value => `<td>${value}</td>`).join('');
            return `<tr class="${isHeading ? 'table-light fw-semibold' : ''}"><td class="text-start" data-surgery-level="${levelOf(row)}" style="padding-left: calc(0.75rem + ${indent}rem) !important">${this.escapeHtml(label)}</td>${values}<td>${Number(row.subtotal || 0)}</td><td>${item.total_count ? (Number(row.subtotal || 0) / Number(item.total_count || 0) * 100).toFixed(1) : '0.0'}%</td></tr>`;
        }).join('');
        const totals = (item.totals || []).map(value => `<td>${value}</td>`).join('');
        const percentages = (item.percentages || []).map(value => `<td>${value}%</td>`).join('');
        const stageSystem = item.system || (isEnglish ? 'Unspecified' : '未指定');
        const title = isEnglish
            ? `Table. Surgical Procedure Distribution of Newly Diagnosed ${tableCancer} Cancer Cases by ${this.escapeHtml(stageSystem)} Stage, ${yearTitle}`
            : `表、${yearTitle}年新診斷${tableCancer}病患${stageSystem}期別與手術術式分佈`;
        return `<div class="stage-surgery-panel${tableKey === activeTableKey ? '' : ' d-none'}" data-stage-surgery-key="${this.escapeHtml(tableKey)}"><table class="annual-report-table"><caption class="surgery-table-caption">${title}${this.sourceLine()}</caption><thead><tr><th class="text-center">${isEnglish ? 'Surgical Codes/Surgical Procedure' : '術式編碼/術式名稱'}</th><th colspan="${Math.max(stages.length, 1)}">${this.escapeHtml(item.system)} ${isEnglish ? 'Stage' : '期別'}</th><th rowspan="2">${isEnglish ? 'Total' : '小計'}</th><th rowspan="2">%</th></tr><tr><th class="text-center surgery-table-classification">${isEnglish ? '(Taiwan Cancer Registry Surgery Codes)' : '（按台灣癌症登記術式編碼分類）'}</th>${stages.map(stage => `<th>${this.escapeHtml(String(stage || '').replace(/^Stage\s+/i, ''))}</th>`).join('')}</tr></thead><tbody>${bodyRows}<tr class="fw-bold"><td>${isEnglish ? 'Total' : '總計'}</td>${totals}<td>${Number(item.total_count || 0)}</td><td>${item.total_count ? '100.0%' : '0.0%'}</td></tr><tr><td>%</td>${percentages}<td>${item.total_count ? '100.0%' : '0.0%'}</td><td>-</td></tr></tbody></table></div>`;
    }).join('');
    const tabs = tables.length > 1 ? `<div class="d-flex flex-wrap gap-2 mb-3">${tables.map((item, index) => { const tableKey = tableKeyOf(item, index); const label = isEnglish ? `${item.cancer_name_en || item.manual_key} ${item.system} Stage` : `${item.cancer_name || item.manual_key}${item.system}期別`; return `<button type="button" class="btn btn-outline-dark btn-sm stage-surgery-tab${tableKey === activeTableKey ? ' active' : ''}" data-stage-surgery-key="${this.escapeHtml(tableKey)}">${this.escapeHtml(label)}</button>`; }).join('')}</div>` : '';
    container.innerHTML = `${tabs}${panels}`;
    container.querySelectorAll('.stage-surgery-tab').forEach(button => button.addEventListener('click', () => {
        window.stageSurgeryActiveTableKey = button.dataset.stageSurgeryKey;
        container.querySelectorAll('.stage-surgery-tab').forEach(tab => tab.classList.toggle('active', tab === button));
        container.querySelectorAll('.stage-surgery-panel').forEach(panel => panel.classList.toggle('d-none', panel.dataset.stageSurgeryKey !== button.dataset.stageSurgeryKey));
        document.getElementById('btnAiTreatmentSurgery')?.onclick?.();
    }));
};
