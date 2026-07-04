// 畫面切換與多選框邏輯
(function() {
  const table = document;
  table.querySelectorAll('.group-checkbox').forEach(groupChk => {
    groupChk.addEventListener('change', function() {
      table.querySelectorAll('.group-checkbox').forEach(chk => {
        const gName = chk.dataset.group;
        const subContainer = document.getElementById(`subItems-${gName}`);
        if (subContainer) {
          if (chk.checked) {
            subContainer.classList.remove('d-none');
            subContainer.style.display = 'flex';
            subContainer.querySelectorAll('.item-checkbox:checked').forEach(item => {item.dispatchEvent(new Event('change'));});
          } else {
            subContainer.classList.add('d-none');
            subContainer.style.display = 'none';
          }
        }
      });
    });
  });

  table.querySelectorAll('.item-checkbox').forEach(itemChk => {
    itemChk.addEventListener('change', function() {
      const chip = this.closest('.field-chip') || this.closest('.naming-chip');
      if (chip) chip.classList.toggle('selected', this.checked);
      updateGroupCheckbox(this.dataset.parent);
    });
  });

  function updateGroupCheckbox(groupName) {
    if (!groupName) return;
    let chkId = '';
    if (groupName === 'incidence') chkId = 'chkGroupIncidence';
    else if (groupName === 'diagnosis') chkId = 'chkGroupDiagnosis';
    else if (groupName === 'stage') chkId = 'chkGroupStage';
    else if (groupName === 'treatment') chkId = 'chkGroupTreatment';
    else if (groupName === 'cross_year') chkId = 'chkGroupCrossYear';
    
    if (!chkId) return;
    const container = document.getElementById(`subItems-${groupName}`);
    if (!container) return;
    const label = document.querySelector(`label[for="${chkId}"]`);
    if (label) {
      const checkedCount = container.querySelectorAll('.item-checkbox:checked').length;
      let text = label.innerHTML;
      text = text.replace(/\s*<span class="badge.*<\/span>$/, '');
      if (checkedCount > 0) {
        text += ` <span class="badge bg-primary rounded-pill ms-1" style="font-size:0.75rem;">${checkedCount}</span>`;
      }
      label.innerHTML = text;
    }
  }
})();


// 圖表
window.dashboardChartInstance = null;
document.addEventListener('DOMContentLoaded', function() {
    /* ── 性別與年齡分佈圖表 ── */
    var chartDom = document.getElementById('main');
    if (chartDom) {
        var myChart = echarts.init(chartDom);
        window.dashboardChartInstance = myChart;
        var option = {
          title: { text: '性別與年齡分佈', subtext: '請點擊查詢載入資料', left: 'center' },
          tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
          legend: { data: ['男性', '女性', '總計'], bottom: 10 },
          toolbox: { feature: { dataView: { show: true, readOnly: false }, saveAsImage: { show: true } } },
          xAxis: [{ type: 'category', data: ['<=19', '20-24', '25-29', '30-34', '35-39', '40-44', '45-49', '50-54', '55-59', '60-64', '65-69', '70-74', '75-79', '80-84', '>=85'], axisPointer: { type: 'shadow' } }],
          yAxis: [{ type: 'value', name: '各別數', axisLabel: { formatter: '{value}' } }, { type: 'value', name: '總計', axisLabel: { formatter: '{value}' } }],
          series: [
            { name: '男性', type: 'bar', data: [], itemStyle: { color: '#5470C6' } },
            { name: '女性', type: 'bar', data: [], itemStyle: { color: '#EE6666' } },
            { name: '總計', type: 'line', yAxisIndex: 1, data: [], itemStyle: { color: '#91CC75' }, smooth: false }
          ]
        };
        myChart.setOption(option);
        
        window.addEventListener('resize', function() {
            myChart.resize();
        });
    }
});

// 表格與輔助功能
window.DashboardRenderer = {
    // 取得年度字串
    getSelectedYearTitle: function() {
        const startYear = document.getElementById('filterYearStart')?.value.trim();
        const endYear = document.getElementById('filterYearEnd')?.value.trim();
        if (startYear && endYear && startYear !== endYear) return `${startYear}-${endYear}`;
        return startYear || endYear || 'XXXX';
    },

    // 取得癌症標題
    getSelectedCancerTitle: function() {
        const cancerTitle = window.dashboardSelectedCancerTitle;
        if (cancerTitle && cancerTitle !== 'XX') return cancerTitle;
        const btnText = document.getElementById('btnCancerPickerText')?.innerText.trim();
        if (!btnText || btnText.includes('尚未選擇')) return 'XX';
        if (btnText.includes('全部癌症')) return '全部癌症';
        return btnText;
    },

    // 組成癌症字串
    getCancerTitleForSentence: function(cancerTitle) {
        if (!cancerTitle || cancerTitle === 'XX') return 'XX癌';
        if (cancerTitle.includes('癌') || cancerTitle.includes('全部癌症')) return cancerTitle;
        return `${cancerTitle}癌`;
    },

    /* ── 性別與年齡分佈表 ── */
    renderSexAgeTable: function(genderAgeData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualSexAgeTableHead');
        const body = document.getElementById('annualSexAgeTableBody');
        const caption = document.getElementById('annualSexAgeCaption');
        if (!head || !body) return;

        const ageLabels = genderAgeData.categories || [];
        if (caption) caption.innerText = `表、${yearTitle}年新診斷${this.getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈表`;

        head.innerHTML = `<tr><th rowspan="2">性別</th><th colspan="${ageLabels.length}">年齡層次</th><th rowspan="2">總計</th></tr><tr>${ageLabels.map(label => `<th>${label}</th>`).join('')}</tr>`;

        const sumMale = genderAgeData.male.reduce((a, b) => a + b, 0);
        const sumFemale = genderAgeData.female.reduce((a, b) => a + b, 0);
        const sumTotal = genderAgeData.total.reduce((a, b) => a + b, 0);

        body.innerHTML = `<tr><td>男</td>${genderAgeData.male.map(value => `<td>${value}</td>`).join('')}<td>${sumMale}</td></tr><tr><td>女</td>${genderAgeData.female.map(value => `<td>${value}</td>`).join('')}<td>${sumFemale}</td></tr><tr><td>總計</td>${genderAgeData.total.map(value => `<td>${value}</td>`).join('')}<td>${sumTotal}</td></tr>`;
    },

    /* ── 年齡中位數表 ── */
    renderAgeMedianTable: function(medianData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualAgeMedianTableHead');
        const body = document.getElementById('annualAgeMedianTableBody');
        const caption = document.getElementById('annualAgeMedianCaption');
        if (!head || !body || !medianData) return;

        const columns = ['男性', '女性'];
        if (caption) caption.innerText = `表、${yearTitle}年新診斷${this.getCancerTitleForSentence(cancerTitle)}病患年齡中位數表`;

        head.innerHTML = `<tr><th rowspan="2" style="vertical-align: middle;">項目</th><th colspan="${columns.length}">發生個案</th></tr><tr>${columns.map(label => `<th>${label}</th>`).join('')}</tr>`;
        body.innerHTML = `<tr><td>個案數(人)</td><td>${medianData.male_count}</td><td>${medianData.female_count}</td></tr><tr><td>年齡中位數</td><td>${medianData.male}</td><td>${medianData.female}</td></tr><tr><td>性別比</td><td>${medianData.male_ratio}</td><td>${medianData.female_ratio}</td></tr>`;
    },

    /* ── 癌症登記可分析個案與確診個案表 ── */
    renderAnalyzableConfirmedTable: function(tableData, yearTitle, cancerTitle) {
        const head = document.getElementById('annualAnalyzableConfirmedTableHead');
        const body = document.getElementById('annualAnalyzableConfirmedTableBody');
        const caption = document.getElementById('annualAnalyzableConfirmedCaption');
        const note = document.getElementById('annualAnalyzableConfirmedNote');
        if (!head || !body || !tableData) return;

        if (caption) caption.innerText = `表、${yearTitle}年${this.getCancerTitleForSentence(cancerTitle)}－癌症登記可分析個案與確診個案`;

        head.innerHTML = `<tr><th>${yearTitle}年癌症總數<br>(A)</th><th>*可分析個案數<br>(B)</th><th>可分析個案百分比 %<br>(B/A)</th><th>顯微鏡檢確診個案數<br>(C)</th><th>確診個案百分比 %<br>(C/B)</th></tr>`;
        body.innerHTML = `<tr><td>${tableData.total_count}</td><td>${tableData.analyzable_count}</td><td>${tableData.analyzable_percent}</td><td>${tableData.confirmed_count}</td><td>${tableData.confirmed_percent}</td></tr>`;

        if (note) {
            note.innerHTML = `<div>* 可分析個案包含：</div><div class="ms-3">Class1 本院診斷，並於本院接受全部或部分首次治療。</div><div class="ms-3">Class2 他院診斷，於本院接受全部或部分首次治療。</div>`;
        }
    },

    /* ── 顯示年度資料區塊 ── */
    showAnnualDataContent: function() {
        document.querySelectorAll('.annual-data-content').forEach(el => {
            el.classList.remove('d-none');
        });
    },
    
    /* ── LLM敘述分析 ── */
    fetchLlmInsight: function(fieldKey, chartData, fields, responseContainerId, buttonId) {
        const container = document.getElementById(responseContainerId);
        const button = document.getElementById(buttonId);
        if (container) container.innerText = '分析中，請稍候...';
        if (button) button.disabled = true;

        fetch('/api/chart_insight', {method: 'POST',headers: { 'Content-Type': 'application/json' },body: JSON.stringify({ field_key: fieldKey, data: chartData, fields: fields })})
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
    }
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
                        }
                    }

                    let chartImage = '';
                    if (paneId === 'chartPane-IncidenceAge' && window.dashboardChartInstance) {
                        chartImage = window.dashboardChartInstance.getDataURL({ type: 'png', backgroundColor: '#fff', pixelRatio: 2 });
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
                alert('沒有可匯出的內容，請先查詢圖表！');
                return;
            }

            localStorage.setItem('dashboard_export_data', JSON.stringify(exportData));
            window.location.href = '/dashboard/export_report';
        });
    }
});
