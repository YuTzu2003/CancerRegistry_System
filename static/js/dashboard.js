window.dashboardChartInstance = null;
window.dashboardHistologyChartInstance = null;
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
        const categories = genderAgeData?.categories || ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85'];
        const male = genderAgeData?.male || [];
        const female = genderAgeData?.female || [];
        const total = genderAgeData?.total || [];
        const maxValue = Math.max(0, ...male, ...female, ...total);
        const yMax = Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(this.getSelectedCancerTitle());
        const titleText = isEnglish
            ? `Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)} Patients, ${this.getSelectedYearTitle()}`
            : this.t('sexAge') + this.t('distribution');

        return {
          title: {
            text: titleText,
            subtext: this.t('source'),
            left: 'center',
            top: 0,
            textStyle: { fontSize: 16, fontWeight: 'bold' },
            subtextStyle: { fontSize: 12 }
          },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: 72, right: 72, top: 70, bottom: 78, containLabel: false },
          legend: { data: [this.t('male'), this.t('female'), this.t('total')], bottom: 28, itemGap: 12 },
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
            axisPointer: { type: 'shadow' },
            axisTick: { alignWithLabel: true },
            axisLabel: { interval: 0 }
          }],
          yAxis: [{
            type: 'value',
            name: this.t('cases'),
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
              type: 'line',
              data: total,
              symbol: 'circle',
              symbolSize: 5,
              smooth: false,
              z: 5,
              itemStyle: { color: '#91CC75' },
              lineStyle: { color: '#91CC75', width: 2 }
            }
          ]
        };
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
          title: { text: window.DashboardRenderer.t('histologyDistribution'), subtext: window.DashboardRenderer.t('source'), left: 'center' },
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
            left: 500,
            right: 60,
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
              width: 420,
              align: 'right',
              margin: 20,
              formatter: function(value) {
                return window.DashboardRenderer.rightAlignedAxisLabel(value);
              },
              rich: {
                right: { width: 420, align: 'right', lineHeight: 18, fontSize: 12 },
                bracket: { width: 420, align: 'right', lineHeight: 18, fontSize: 10.5 }
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
            : this.t('classificationDistribution');
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
                textStyle: {fontSize: 20,fontWeight: 'bold',color: '#333'}
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

        const ageLabels = genderAgeData.categories || [];
        if (caption) {
            const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
            caption.innerHTML = window.DashboardI18n?.getLanguage() === 'en'
                ? `Table . Age and Sex Distribution of Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)} Patients, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${this.t('sexAge')}${this.t('distribution')}`, { newDiagnosis: true });
        }

        head.innerHTML = `<tr><th rowspan="2">${this.t('sex')}</th><th colspan="${ageLabels.length}">${this.t('ageGroup')}</th><th rowspan="2">${this.t('total')}</th></tr><tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>`;
        const sumMale = genderAgeData.male.reduce((a, b) => a + b, 0);
        const sumFemale = genderAgeData.female.reduce((a, b) => a + b, 0);
        const sumTotal = genderAgeData.total.reduce((a, b) => a + b, 0);
        body.innerHTML = `<tr><td>${this.t('male')}</td>${genderAgeData.male.map(value => `<td>${value}</td>`).join('')}<td>${sumMale}</td></tr><tr><td>${this.t('female')}</td>${genderAgeData.female.map(value => `<td>${value}</td>`).join('')}<td>${sumFemale}</td></tr><tr><td>${this.t('total')}</td>${genderAgeData.total.map(value => `<td>${value}</td>`).join('')}<td>${sumTotal}</td></tr>`;
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
            alert(`${this.t('warningDetails')}\n\n${alertLines}`);
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
window.DashboardRenderer.renderHistologyTable = function(histologyData, yearTitle, cancerTitle, noDataReason = '') {
        const body = document.getElementById('annualHistologyTableBody');
        const caption = document.getElementById('annualHistologyCaption');
        if (!body) return;
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const selectedCancer = this.getCancerTitleForSentence(cancerTitle);
        if (caption) {
            caption.innerHTML = isEnglish
                ? `Table. Histological Distribution of ${this.getEnglishCancerPatientLabel(selectedCancer)}, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, `${this.t('histology')}${this.t('distribution')}`);
        }
        if (!histologyData || histologyData.length === 0) {
            const reason = this.escapeHtml(noDataReason || '查無符合條件的組織型態資料。');
            body.innerHTML = `<tr><td colspan="4" class="text-center py-4">${this.t('noData')}<br><span class="text-muted small">${reason}</span></td></tr>`;
            this.renderColonHistologyTableNote([]);
            return;}

        const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
        const totalCount = validData.reduce((sum, item) => sum + item.count, 0);
        const rowsHtml = validData.map(item => {
            const pct = totalCount > 0 ? ((item.count / totalCount) * 100).toFixed(1) : '0.0';
            return `
                <tr>
                    <td>${item.code}</td>
                    <td class="text-start">${item.name}</td>
                    <td>${item.count}</td>
                    <td>${pct}%</td>
                </tr>
            `;
        }).join('');

        const totalRowHtml = `
            <tr class="fw-bold" style="background-color: var(--gray-50);">
                <td>${this.t('total')}</td>
                <td></td>
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
                ? `Table . Median Age of Patients Newly Diagnosed with ${this.getEnglishCancerPatientLabel(selectedCancer)}, ${yearTitle}${this.sourceLine()}`
                : this.reportCaption('table', yearTitle, selectedCancer, this.t('ageMedian'), { newDiagnosis: true });
        }

        head.innerHTML = `<tr><th rowspan="2" style="vertical-align: middle;">${this.t('medianCharacteristic')}</th><th colspan="${columns.length}">${this.t('medianSex')}</th></tr><tr>${columns.map(label => `<th>${label}</th>`).join('')}</tr>`;
        body.innerHTML = `<tr><td>${this.t('medianN')}</td><td>${medianData.male_count}</td><td>${medianData.female_count}</td></tr><tr><td>${this.t('medianAgeYears')}</td><td>${medianData.male}</td><td>${medianData.female}</td></tr><tr><td>${this.t('medianMaleToFemaleRatio')}</td><td>${medianData.male_ratio}</td><td>${medianData.female_ratio}</td></tr>`;
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
                ? `Table . Analysis-Eligible and Confirmed Cases of ${this.getEnglishCancerPatientLabel(selectedCancer)} in the Cancer Registry, ${yearTitle}${this.sourceLine()}`
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
                ? `Table . ${this.getEnglishCancerPatientLabel(selectedCancer)} Case Class Distribution, ${yearTitle}${this.sourceLine()}`
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
        const cacheKey = `${language}|${modeAi}|${fieldKey}`;
        const sourceText = options.sourceText || (language === 'en'
            ? this.insightCache.get(`zh-TW|${modeAi}|${fieldKey}`) || ''
            : '');
        const cachedInsight = this.insightCache.get(cacheKey);
        if (cachedInsight) {
            if (shouldDisplay && container) container.innerText = cachedInsight;
            if (shouldManageButton && button) button.disabled = false;
            return Promise.resolve({ success: true, cached: true });
        }

        const showResult = (result) => {
            if (!shouldDisplay || (window.DashboardI18n?.getLanguage() || 'zh-TW') !== language) return;
            if (result.success) {
                if (container) container.innerText = result.insight;
            } else if (container) {
                container.innerText = this.t('insightFailed') + (result.error || 'error');
            }
        };
        const pendingRequest = this.insightRequests.get(cacheKey);
        if (pendingRequest) {
            if (shouldDisplay && container) container.innerText = this.t('generatingInsight');
            return pendingRequest.then(result => {
                showResult(result);
                return result;
            });
        }

        if (shouldDisplay && container) container.innerText = this.t('generatingInsight');
        if (shouldManageButton && button) button.disabled = true;

        const yearStart = document.getElementById('filterYearStart')?.value.trim() || '';
        const yearEnd = document.getElementById('filterYearEnd')?.value.trim() || '';
        const cacheGeneration = this.insightCacheGeneration;
        const request = fetch('/api/chart_insight', {method: 'POST',headers: { 'Content-Type': 'application/json' },body: JSON.stringify({ field_key: fieldKey, data: chartData, fields: fields, mode_ai: modeAi, year_start: yearStart, year_end: yearEnd, language, source_text: sourceText })})
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                if (this.insightCacheGeneration === cacheGeneration) this.insightCache.set(cacheKey, data.insight);
            }
            return data;
        })
        .catch(() => ({ success: false, error: 'error' }))
        .finally(() => {
            if (this.insightRequests.get(cacheKey) === request) this.insightRequests.delete(cacheKey);
        });
        this.insightRequests.set(cacheKey, request);
        return request.then(result => {
            if (shouldManageButton && button) button.disabled = false;
            showResult(result);
            return result;
        });
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

window.DashboardRenderer.regenerateInsightsForLanguage = function() {
        const buttons = Array.from(document.querySelectorAll('button[id^="btnAi"]'))
            .filter(button => button.style.display !== 'none' && typeof button.onclick === 'function');
        return Promise.all(buttons.map(button => button.onclick()));
    };

window.DashboardRenderer.updateHistologyChart = function(histologyData, noDataReason = '') {
        if (!window.dashboardHistologyChartInstance || !histologyData) return;
        const yearTitle = this.getSelectedYearTitle();
        const cancerTitle = this.getCancerTitleForSentence(this.getSelectedCancerTitle());
        const isEnglish = window.DashboardI18n?.getLanguage() === 'en';
        const validData = histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
        const totalValid = validData.reduce((sum, item) => sum + item.count, 0);
        const topData = [...validData].reverse();
        const categories = topData.map(item => item.name);
        const chartSeriesData = topData.map(item => ({
            value: totalValid > 0 ? Number(((item.count / totalValid) * 100).toFixed(1)) : 0,
            count: item.count
        }));
        const chartDom = document.getElementById('histologyChart');
        const chartTitle = isEnglish
            ? `Histological Distribution of ${this.getEnglishCancerPatientLabel(cancerTitle)}, ${yearTitle}`
            : `${yearTitle} ${cancerTitle} ${this.t('histologyDistribution')}`;
        if (chartDom) {
            chartDom.style.height = `${Math.max(450, categories.length * this.histologyRowHeight(categories))}px`;
            window.dashboardHistologyChartInstance.resize();
        }
        if (categories.length === 0) {
            if (chartDom) chartDom.style.height = '450px';
            window.dashboardHistologyChartInstance.setOption({
                title: { text: chartTitle, subtext: this.t('source'), left: 'center' },
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
                left: 'center'
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
            histologyCodeHeader: this.t('icdoCode'), histologyNameHeader: this.t('histology'),
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
        this.updateChartCaptions(yearTitle, cancerTitle);
        if (window.dashboardChartInstance) window.dashboardChartInstance.setOption(this.getGenderAgeChartOption(window.lastChartData.genderAgeData), true);
        this.updateHistologyChart(window.lastChartData.histologyData, window.lastChartData.histologyNoDataReason);
        if (options.regenerateInsights) this.regenerateInsightsForLanguage();
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
    const collectExportData = async () => {
            const exportData = [];
            let orderIndex = 0;
            const exportLanguage = window.DashboardI18n?.getLanguage() || 'zh-TW';
            const modeAi = document.getElementById('mode_ai')?.value || 'balanced';
            const insightFieldKeys = {
                'chartPane-IncidenceAge': '性別與年齡分佈',
                'chartPane-IncidenceMedian': '年齡中位數',
                'chartPane-DiagnosisAnalyzable': '癌症登記可分析個案與確診個案',
                'chartPane-DiagnosisHistology': '組織型態分佈',
                'chartPane-DiagnosisClassification': '個案分類'
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
                    }

                    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));

                    const chartInstance = paneId === 'chartPane-IncidenceAge'
                        ? window.dashboardChartInstance
                        : paneId === 'chartPane-DiagnosisHistology'
                            ? window.dashboardHistologyChartInstance
                            : paneId === 'chartPane-DiagnosisClassification'
                                ? window.DashboardRenderer?.classificationChartInst
                                : null;
                    if (chartInstance) {
                        await new Promise(resolve => {
                            let completed = false;
                            const finish = () => {
                                if (completed) return;
                                completed = true;
                                chartInstance.off('finished', finish);
                                resolve();
                            };
                            chartInstance.on('finished', finish);
                            chartInstance.resize();
                            setTimeout(finish, 500);
                        });
                    }

                    let chartImage = '';
                    if (paneId === 'chartPane-IncidenceAge' && window.dashboardChartInstance) {
                        chartImage = window.dashboardChartInstance.getDataURL({ type: 'png', backgroundColor: '#fff', pixelRatio: 2 });
                    } else if (paneId === 'chartPane-DiagnosisHistology' && window.dashboardHistologyChartInstance) {
                        chartImage = window.dashboardHistologyChartInstance.getDataURL({ type: 'png', backgroundColor: '#fff', pixelRatio: 2 });
                    } else if (paneId === 'chartPane-DiagnosisClassification' && window.DashboardRenderer && window.DashboardRenderer.classificationChartInst) {
                        chartImage = window.DashboardRenderer.classificationChartInst.getDataURL({ type: 'png', backgroundColor: '#fff', pixelRatio: 2 });
                    }
                    
                    const tableWrap = pane.querySelector('.annual-report-table-wrap');
                    let tableHtml = tableWrap ? tableWrap.innerHTML : '';
                    
                    let llmText = '';
                    const llmDiv = pane.querySelector('[id^="llmResponse"]');
                    if (llmDiv) {
                        const insightButton = pane.querySelector('button[id^="btnAi"]');
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

                    exportData.push({
                        id: paneId,
                        order: orderIndex++,
                        title: title,
                        tableHtml: tableHtml,
                        chartImage: chartImage,
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
            let preparationError = null;
            btnPrepareExport.disabled = true;
            if (window.utils?.showLoading) {
                window.utils.showLoading('正在準備匯出內容中，請稍候…');
            }
            try {
                for (const language of ['zh-TW', 'en']) {
                    await window.DashboardI18n?.setLanguage(language);
                    await window.DashboardRenderer?.regenerateInsightsForLanguage?.();
                    exportDataByLanguage[language] = await collectExportData();
                }
            } catch (error) {
                preparationError = error;
            } finally {
                await window.DashboardI18n?.setLanguage(originalLanguage);
                await window.DashboardRenderer?.regenerateInsightsForLanguage?.();
                btnPrepareExport.disabled = false;
            }

            if (preparationError) {
                if (window.utils?.hideLoading) window.utils.hideLoading();
                utils.alert('匯出內容準備失敗，請再試一次。', 'error');
                return;
            }

            if (!exportDataByLanguage['zh-TW']?.length) {
                if (window.utils?.hideLoading) window.utils.hideLoading();
                utils.alert('沒有可匯出的內容，請先查詢圖表！', 'warning');
                return;
            }

            localStorage.setItem('dashboard_export_data', JSON.stringify({
                version: 2,
                languages: exportDataByLanguage
            }));
            window.location.href = '/dashboard/export_report';
        });
    }
});
