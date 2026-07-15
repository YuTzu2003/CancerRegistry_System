window.dashboardChartInstance = null;
window.dashboardHistologyChartInstance = null;
window.DashboardRenderer = {};

window.DashboardRenderer.getGenderAgeChartOption = function(genderAgeData) {
        const categories = genderAgeData?.categories || ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85'];
        const male = genderAgeData?.male || [];
        const female = genderAgeData?.female || [];
        const total = genderAgeData?.total || [];
        const maxValue = Math.max(0, ...male, ...female, ...total);
        const yMax = Math.max(10, Math.ceil((maxValue * 1.15) / 5) * 5);

        return {
          title: {
            text: '性別與年齡分佈',
            subtext: '資料來源：癌症登記資料庫',
            left: 'center',
            top: 0,
            textStyle: { fontSize: 16, fontWeight: 'bold' },
            subtextStyle: { fontSize: 12 }
          },
          tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
          grid: { left: 72, right: 72, top: 70, bottom: 78, containLabel: false },
          legend: { data: ['男性', '女性', '總計'], bottom: 28, itemGap: 12 },
          toolbox: { right: 16, top: 0, feature: { dataView: { show: true, readOnly: false }, saveAsImage: { show: true } } },
          xAxis: [{
            type: 'category',
            data: categories,
            axisPointer: { type: 'shadow' },
            axisTick: { alignWithLabel: true },
            axisLabel: { interval: 0 }
          }],
          yAxis: [{
            type: 'value',
            name: '個案數',
            min: 0,
            max: yMax,
            minInterval: 1,
            splitNumber: 5,
            axisLabel: { formatter: '{value}' },
            splitLine: { lineStyle: { color: '#e5eaf3' } }
          }],
          series: [
            {
              name: '男性',
              type: 'bar',
              data: male,
              barWidth: 20,
              barGap: '20%',
              barCategoryGap: '42%',
              itemStyle: { color: '#5470C6' }
            },
            {
              name: '女性',
              type: 'bar',
              data: female,
              barWidth: 20,
              itemStyle: { color: '#EE6666' }
            },
            {
              name: '總計',
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
          title: { text: '組織型態分佈圖', subtext: '資料來源：癌症登記資料庫', left: 'center' },
          tooltip: { 
            trigger: 'axis', 
            axisPointer: { type: 'shadow' },
            formatter: function(params) {
              const p = params[0];
              if (!p || p.value === undefined || p.value === '-') return '';
              const count = p.data && p.data.count !== undefined ? p.data.count : '-';
              const val = typeof p.value === 'number' ? p.value.toFixed(1) : p.value;
              return `${p.name}<br/>${p.marker}個案比例: ${val}% (${count}人)`;
            }
          },
          grid: {
            left: 300,
            right: 40,
            bottom: 50,
            top: 60,
            containLabel: false
          },
          legend: { show: false },
          toolbox: { feature: { dataView: { show: true, readOnly: false }, saveAsImage: { show: true } } },
          xAxis: { 
            type: 'value', 
            name: '百分比 (%)', 
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
              width: 280,
              overflow: 'break',
              lineHeight: 16,
              align: 'center',
              margin: 148
            }
          },
          series: [
            {
              name: '個案比例',
              type: 'bar',
              data: [],
              itemStyle: { color: '#73c0de' },
              label: { 
                show: false, 
                position: 'right',
                formatter: function(params) {
                  return typeof params.value === 'number' ? params.value.toFixed(1) + '%' : params.value;
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
        const labels = [
            'Class0 本院診斷，未於本院接受首次治療',
            'Class1 本院診斷，並於本院接受全部或部分首次治療。',
            'Class2 他院診斷，於本院接受全部或部分首次治療。',
            'Class3 他院診斷，未於本院接受首次治療，或因復發／持續癌症問題至本院就診。'
        ];

        const option = {
            title: {
                text: '個案分類分佈圖',
                subtext: '資料來源：癌症登記資料庫',
                left: 'center',
                textStyle: {fontSize: 20,fontWeight: 'bold',color: '#333'}
            },
            toolbox: {
                show: true,
                feature: {
                    dataView: { show: true, readOnly: false, title: '數據檢視', lang: ['數據檢視', '關閉', '更新'] },
                    saveAsImage: { show: true, title: '下載圖片' }
                }
            },
            legend: {
                orient: 'vertical',
                right: '2%',
                top: 'middle',
                itemWidth: 14,
                itemHeight: 14,
                data: labels,
                textStyle: {fontSize: 14,lineHeight: 24,width: 450,overflow: 'break'}
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
        if (caption) caption.innerHTML = `表、${yearTitle}年新診斷${this.getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span>`;

        head.innerHTML = `<tr><th rowspan="2">性別</th><th colspan="${ageLabels.length}">年齡層次</th><th rowspan="2">總計</th></tr><tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>`;
        const sumMale = genderAgeData.male.reduce((a, b) => a + b, 0);
        const sumFemale = genderAgeData.female.reduce((a, b) => a + b, 0);
        const sumTotal = genderAgeData.total.reduce((a, b) => a + b, 0);
        body.innerHTML = `<tr><td>男</td>${genderAgeData.male.map(value => `<td>${value}</td>`).join('')}<td>${sumMale}</td></tr><tr><td>女</td>${genderAgeData.female.map(value => `<td>${value}</td>`).join('')}<td>${sumFemale}</td></tr><tr><td>總計</td>${genderAgeData.total.map(value => `<td>${value}</td>`).join('')}<td>${sumTotal}</td></tr>`;
    };

/* ── 組織型態不適用個案說明按鈕 ── */
window.DashboardRenderer.currentHistologyWarnings = [];

window.DashboardRenderer.escapeHtml = function(value) {
        return String(value ?? '')
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
            const message = this.escapeHtml(item.message || `${item.icdo_code || ''} 未納入 1.3 組織型態規則`);
            const rawDataMessage = item.raw_data_message
                ? `<span class="fw-bold text-danger ms-1">${this.escapeHtml(item.raw_data_message)}</span>`
                : '';
            const detail = this.escapeHtml(item.detail_message || '若此組織型態無特殊適用條件，則此組織代碼組合不屬於目前統計規則範圍');
            return `
                <div class="mb-3 text-start histology-warning-item">
                    <div class="text-nowrap">${user}：${message}${rawDataMessage}</div>
                    <div class="text-nowrap">說明：${detail}</div>
                </div>
            `;
        }).join('');
        const warningHtml = `
            <div class="text-center histology-warning-dialog">
                <div class="mb-3 text-nowrap">以下個案未納入組織型態統計：</div>
                <div class="mx-auto text-start" style="display: inline-block; min-width: max-content; max-width: none; overflow-x: visible; padding: 0 4px;">${warningLines}</div>
            </div>
        `;

        if (typeof Swal !== 'undefined') {
            Swal.fire({
                icon: 'warning',
                html: warningHtml,
                confirmButtonText: '確定',
                confirmButtonColor: '#dc3545',
                width: 'auto',
                allowOutsideClick: false,
                customClass: { popup: 'histology-warning-popup' }
            });
        } else {
            const alertLines = warnings.map(item => {
                const user = item.user || '未知個案';
                const message = item.message || `${item.icdo_code || ''} 未納入 1.3 組織型態規則`;
                const rawDataMessage = item.raw_data_message ? ` ${item.raw_data_message}` : '';
                const detail = item.detail_message || '若此組織型態無特殊適用條件，則此組織代碼組合不屬於目前統計規則範圍';
                return `${user}：${message}${rawDataMessage}\n說明：${detail}`;
            }).join('\n\n');
            alert(`以下個案未納入組織型態統計：\n\n${alertLines}`);
        }
    };

window.DashboardRenderer.renderHistologyWarningButton = function(histologyWarnings) {
        const button = document.getElementById('histologyWarningButton');
        if (!button) return;

        const warnings = Array.isArray(histologyWarnings) ? histologyWarnings : [];
        this.currentHistologyWarnings = warnings;

        if (warnings.length === 0) {
            button.classList.add('d-none');
            button.textContent = '不適用個案說明';
            return;
        }

        button.classList.remove('d-none');
        button.textContent = `不適用個案說明 (${warnings.length})`;
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
            return `註：有一筆組織型態不適用，已排除統計（${user} 不符合 M8211 診斷年度規範）`;
        }).join('<br>');
    };

/* ── 組織型態分佈表 ── */
window.DashboardRenderer.renderHistologyTable = function(histologyData, yearTitle, cancerTitle) {
        const body = document.getElementById('annualHistologyTableBody');
        const caption = document.getElementById('annualHistologyCaption');
        if (!body) return;
        if (caption) caption.innerHTML = `表、${yearTitle}年${this.getCancerTitleForSentence(cancerTitle)}組織型態分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span>`;
        if (!histologyData || histologyData.length === 0) {
            body.innerHTML = `<tr><td colspan="4" class="text-center py-4">無資料</td></tr>`;
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
                <td>合計</td>
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

        const columns = ['男性', '女性'];
        if (caption) caption.innerHTML = `表、${yearTitle}年新診斷${this.getCancerTitleForSentence(cancerTitle)}病患年齡中位數表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span>`;

        head.innerHTML = `<tr><th rowspan="2" style="vertical-align: middle;">項目</th><th colspan="${columns.length}">發生個案</th></tr><tr>${columns.map(label => `<th>${label}</th>`).join('')}</tr>`;
        body.innerHTML = `<tr><td>個案數(人)</td><td>${medianData.male_count}</td><td>${medianData.female_count}</td></tr><tr><td>年齡中位數</td><td>${medianData.male}</td><td>${medianData.female}</td></tr><tr><td>性別比</td><td>${medianData.male_ratio}</td><td>${medianData.female_ratio}</td></tr>`;
    };

/* ── 癌症登記可分析個案與確診個案表 ── */
window.DashboardRenderer.renderAnalyzableConfirmedTable = function(tableData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualAnalyzableConfirmedTableHead');
        const body = document.getElementById('annualAnalyzableConfirmedTableBody');
        const caption = document.getElementById('annualAnalyzableConfirmedCaption');
        const note = document.getElementById('annualAnalyzableConfirmedNote');
        if (!head || !body || !tableData) return;

        if (caption) caption.innerHTML = `表、${yearTitle}年${this.getCancerTitleForSentence(cancerTitle)}－癌症登記可分析個案與確診個案<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span>`;

        head.innerHTML = `<tr><th>${yearTitle}年癌症總數<br>(A)</th><th>*可分析個案數<br>(B)</th><th>可分析個案百分比 %<br>(B/A)</th><th>顯微鏡檢確診個案數<br>(C)</th><th>確診個案百分比 %<br>(C/B)</th></tr>`;
        body.innerHTML = `<tr><td>${tableData.total_count}</td><td>${tableData.analyzable_count}</td><td>${tableData.analyzable_percent}</td><td>${tableData.confirmed_count}</td><td>${tableData.confirmed_percent}</td></tr>`;

        if (note) {
            note.innerHTML = `<div>* 可分析個案包含：</div><div class="annual-analyzable-note-item">Class1 本院診斷，並於本院接受全部或部分首次治療。</div><div class="annual-analyzable-note-item">Class2 他院診斷，於本院接受全部或部分首次治療。</div>`;
        }
    };

/* ── 個案分類分佈表 ── */
window.DashboardRenderer.renderDiagnosisClassificationTable = function(tableData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualDiagnosisClassificationTableHead');
        const body = document.getElementById('annualDiagnosisClassificationTableBody');
        const caption = document.getElementById('annualDiagnosisClassificationCaption');
        if (!head || !body || !tableData) return;

        if (caption) caption.innerHTML = `表、${yearTitle}年${this.getCancerTitleForSentence(cancerTitle)}個案分類分佈表<br><span class="text-muted fw-normal" style="font-size: 0.85em;">資料來源：癌症登記資料庫</span>`;

        head.innerHTML = `<tr><th class="text-center">個案分類</th><th class="text-center">人數</th><th class="text-center">百分比%</th></tr>`;
        
        const total = tableData.total_count || 1;
        const calcPct = (val) => (val / total * 100).toFixed(1) + '%';
        
        const classMappings = [
            {
                title: 'Class0 本院診斷，未於本院接受首次治療',
                totalKey: 'class0_total',
                subClasses: [
                    { key: '0_1_0', label: '未接受任何治療即死亡或病危(0.1.0)' },
                    { key: '0_1_2', label: '首次療程未於本院進行，或本院僅提供支援／諮詢(0.1.2)' }
                ]
            },
            {
                title: 'Class1 本院診斷，並於本院接受全部或部分首次治療。',
                totalKey: 'class1_total',
                subClasses: [
                    { key: '1_1_1', label: '首次療程僅於本院完成(1.1.1)' },
                    { key: '1_1_3', label: '首次療程由本院與他院共同完成(1.1.3)' },
                    { key: '1_1_4', label: '首次療程為觀察、支持性或緩和治療(1.1.4)' }
                ]
            },
            {
                title: 'Class2 他院診斷，於本院接受全部或部分首次治療。',
                totalKey: 'class2_total',
                subClasses: [
                    { key: '2_2_1', label: '首次療程僅於本院完成(2.2.1)' },
                    { key: '2_2_3', label: '首次療程由本院與他院共同完成(2.2.3)' }
                ]
            },
            {
                title: 'Class3 他院診斷，未於本院接受首次治療，或因復發／持續癌症問題至本院就診。',
                totalKey: 'class3_total',
                subClasses: [
                    { key: '3_2_0', label: '未接受任何治療即死亡或病危(3.2.0)' },
                    { key: '3_3_2', label: '首次療程未於本院進行，或本院僅提供支援／諮詢(3.3.2)' }
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
        html += `<tr class="table-secondary fw-bold" style="font-weight: bold; border-top: 2px solid #6c757d;"><td class="text-center">總計</td><td class="text-center">${tableData.total_count}</td><td class="text-center">100.0%</td></tr>`;
        body.innerHTML = html;
    };

/* ── LLM敘述分析 ── */
window.DashboardRenderer.fetchLlmInsight = function(fieldKey, chartData, fields, responseContainerId, buttonId) {
        const container = document.getElementById(responseContainerId);
        const button = document.getElementById(buttonId);
        if (container) container.innerText = '分析中，請稍候...';
        if (button) button.disabled = true;

        const modeAi = document.getElementById('mode_ai') ? document.getElementById('mode_ai').value : 'balanced';
        const yearStart = document.getElementById('filterYearStart')?.value.trim() || '';
        const yearEnd = document.getElementById('filterYearEnd')?.value.trim() || '';
        return fetch('/api/chart_insight', {method: 'POST',headers: { 'Content-Type': 'application/json' },body: JSON.stringify({ field_key: fieldKey, data: chartData, fields: fields, mode_ai: modeAi, year_start: yearStart, year_end: yearEnd })})
        .then(res => res.json())
        .then(data => {
            if (button) button.disabled = false;
            if (data.success) {
                if (container) container.innerText = data.insight;
            } else {
                if (container) container.innerText = '產生敘述失敗：' + (data.error);
            }
        })
        .catch(err => {
            if (button) button.disabled = false;
            if (container) container.innerText = 'error';
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
        const cancerTitle = window.dashboardSelectedCancerTitle;
        if (cancerTitle && cancerTitle !== 'XX') return cancerTitle;
        const btnText = document.getElementById('btnCancerPickerText')?.innerText.trim();
        if (!btnText || btnText.includes('尚未選擇')) return 'XX';
        if (btnText.includes('全部癌症')) return '全部癌症';
        return btnText;
    };

// 組成癌症字串
window.DashboardRenderer.getCancerTitleForSentence = function(cancerTitle) {
        if (!cancerTitle || cancerTitle === 'XX') return 'XX癌';
        if (cancerTitle.includes('癌') || cancerTitle.includes('全部癌症')) return cancerTitle;
        return `${cancerTitle}癌`;
    };

/* ── 顯示年度資料區塊 ── */
window.DashboardRenderer.showAnnualDataContent = function() {
        document.querySelectorAll('.annual-data-content').forEach(el => {
            el.classList.remove('d-none');
        });
    };

document.addEventListener('DOMContentLoaded', function() {
    const btnPrepareExport = document.getElementById('btnPrepareExport');
    if (btnPrepareExport) {
        btnPrepareExport.addEventListener('click', function() {
            const exportData = [];
            let orderIndex = 0;
            
            const activeTargets = Array.from(document.querySelectorAll('#chartTabsContainer .chart-tab-btn')).map(btn => btn.dataset.target);
            
            document.querySelectorAll('.chart-pane').forEach(pane => {
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
                        llmText = llmDiv.textContent || llmDiv.innerText;
                    }

                    if (wasHidden) {
                        pane.classList.add('d-none');
                        pane.style.visibility = '';
                        pane.style.display = '';
                    }

                    let title = '未命名圖表';
                    if (paneId === 'chartPane-IncidenceAge') title = '性別年齡分佈';
                    else if (paneId === 'chartPane-IncidenceMedian') title = '年齡中位數';
                    else if (paneId === 'chartPane-DiagnosisAnalyzable') title = '可分析個案與確診個案';
                    else if (paneId === 'chartPane-DiagnosisHistology') title = '組織型態分佈';
                    else if (paneId === 'chartPane-DiagnosisClassification') title = '個案分類';

                    exportData.push({
                        id: paneId,
                        order: orderIndex++,
                        title: title,
                        tableHtml: tableHtml,
                        chartImage: chartImage,
                        llmText: llmText
                    });
                }
            });

            if (exportData.length === 0) {
                utils.alert('沒有可匯出的內容，請先查詢圖表！', 'warning');
                return;
            }

            localStorage.setItem('dashboard_export_data', JSON.stringify(exportData));
            window.location.href = '/dashboard/export_report';
        });
    }
});
