document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('btnBackToDashboard')?.addEventListener('click', function() {
        sessionStorage.setItem('dashboard_reset_filters_on_return', '1');
        history.back();
    });

    const rawData = localStorage.getItem('dashboard_export_data');
    if (!rawData) {
        utils.alert('找不到可匯出的資料！將返回上一頁。', 'error').then(() => {
            sessionStorage.setItem('dashboard_reset_filters_on_return', '1');
            history.back();
        });
        return;
    }
    
    const storedExportData = JSON.parse(rawData);
    const exportDataByLanguage = Array.isArray(storedExportData)
        ? { 'zh-TW': storedExportData }
        : (storedExportData.languages || {});
    const sharedChartImages = storedExportData.sharedChartImages || {};
    const exportLanguageSelect = document.getElementById('exportLanguage');
    const exportLanguagePicker = document.getElementById('exportLanguagePicker');
    const exportLanguageLabel = document.getElementById('exportLanguageLabel');
    const listContainer = document.getElementById('exportItemList');

    const languageLabels = { 'zh-TW': '繁體中文', en: 'English' };
    const updateExportLanguageLabel = () => {
        exportLanguageLabel.textContent = languageLabels[exportLanguageSelect.value] || '繁體中文';
    };

    document.querySelectorAll('.export-language-option').forEach(option => {
        option.addEventListener('click', () => {
            exportLanguageSelect.value = option.dataset.language;
            updateExportLanguageLabel();
            exportLanguagePicker.open = false;
            exportLanguageSelect.dispatchEvent(new Event('change'));
        });
    });

    if (!exportDataByLanguage['zh-TW']?.length && !exportDataByLanguage.en?.length) {
        utils.alert('找不到可匯出的內容，請返回儀表板重新準備。', 'error');
        return;
    }

    if (!exportDataByLanguage.en?.length) {
        exportLanguageSelect.value = 'zh-TW';
        exportLanguageSelect.disabled = true;
        exportLanguagePicker.setAttribute('hidden', '');
    }

    updateExportLanguageLabel();

    const getCurrentExportData = () => {
        const items = exportDataByLanguage[exportLanguageSelect.value]
            || exportDataByLanguage['zh-TW']
            || exportDataByLanguage.en
            || [];
        return items.map(item => ({
            ...item,
            chartImage: item.chartImage || sharedChartImages[item.chartImageKey] || ''
        }));
    };
    const exportItemLabels = {
        'chartPane-IncidenceAge': '性別年齡分布',
        'chartPane-IncidenceMedian': '年齡中位數',
        'chartPane-DiagnosisAnalyzable': '可分析個案與確診個案',
        'chartPane-DiagnosisHistology': '組織型態',
        'chartPane-DiagnosisClassification': '個案分類',
        'chartPane-TreatmentFirstCourse': '期別與首次療程',
        'chartPane-TreatmentSurgery': '期別與手術術式'
    };

    function renderExportItems() {
        const exportData = getCurrentExportData();
        listContainer.innerHTML = '';
        exportData.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = 'export-item';
        div.dataset.id = item.id;
        
        const hasTable = item.tableHtml && item.tableHtml.trim().length > 0;
        const hasChart = item.chartImage && item.chartImage.trim().length > 0;
        const hasAi = item.llmText
            && item.llmText.trim().length > 0
            && !item.llmText.includes('自動產生')
            && !item.llmText.includes('generate an analysis automatically');

        div.innerHTML = `
            <div class="d-flex align-items-center flex-grow-1">
                <i class="bi bi-grip-vertical text-muted fs-4 drag-handle-icon"></i>
                <div class="export-item-title ms-2"><i class="bi bi-graph-up-arrow text-primary me-2"></i> ${item.id.startsWith('chartPane-TreatmentSurgery-') ? item.title : (exportItemLabels[item.id.replace(/-\d+$/, '')] || item.title)}</div>
                <div class="d-flex align-items-center gap-3 ms-4 flex-wrap" onmousedown="event.stopPropagation()">
                    ${hasChart ? '<div class="form-check"><input class="form-check-input item-cb-chart" type="checkbox" checked id="cb_chart_'+item.id+'"><label class="form-check-label" for="cb_chart_'+item.id+'">圖表</label></div>' : ''}
                    ${hasTable ? '<div class="form-check"><input class="form-check-input item-cb-table" type="checkbox" checked id="cb_table_'+item.id+'"><label class="form-check-label" for="cb_table_'+item.id+'">表格</label></div>' : ''}
                    ${hasAi ? '<div class="form-check"><input class="form-check-input item-cb-ai" type="checkbox" checked id="cb_ai_'+item.id+'"><label class="form-check-label" for="cb_ai_'+item.id+'">AI敘述</label></div>' : ''}
                </div>
            </div>
            <div class="export-actions ms-3">
                <span class="badge bg-secondary">Item <span class="order-number">${index + 1}</span></span>
            </div>
        `;
            listContainer.appendChild(div);
        });

        if (typeof Sortable !== 'undefined') {
            new Sortable(listContainer, {
                animation: 150,
                ghostClass: 'sortable-ghost',
                onEnd: function() {
                    document.querySelectorAll('.order-number').forEach((el, idx) => {
                        el.innerText = idx + 1;
                    });
                }
            });
        }
    }

    renderExportItems();
    exportLanguageSelect.addEventListener('change', renderExportItems);

    function doExport(isPreview) {
        const exportData = getCurrentExportData();
        let doPdf = document.getElementById('exportPdf').checked;
        let doWord = document.getElementById('exportWord').checked;
        
        if (isPreview) {
            doPdf = true;
            doWord = false;
        } else {
            if (!doPdf && !doWord) {
                utils.alert('請至少選擇一種匯出格式 (PDF 或 Word)。', 'warning');
                return;
            }
        }

        const sortedIds = Array.from(listContainer.children).map(el => el.dataset.id);
        const sortedData = sortedIds.map(id => {
            const baseData = exportData.find(d => d.id === id);
            const itemEl = document.querySelector('.export-item[data-id="'+id+'"]');
            const cbTable = itemEl.querySelector('.item-cb-table');
            const cbChart = itemEl.querySelector('.item-cb-chart');
            const cbAi = itemEl.querySelector('.item-cb-ai');
            return {
                ...baseData,
                includeTable: cbTable ? cbTable.checked : false,
                includeChart: cbChart ? cbChart.checked : false,
                includeAi: cbAi ? cbAi.checked : false
            };
        }).filter(item => item.includeTable || item.includeChart || item.includeAi);

        const payload = {
            format_pdf: doPdf,
            format_word: doWord,
            export_language: exportLanguageSelect.value,
            charts: sortedData
        };

        if (window.utils && window.utils.showLoading) {
            window.utils.showLoading('匯出中，請稍候...');
        }

        fetch('/api/dashboard/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) throw new Error('操作失敗');
            return response.blob();
        })
        .then(blob => {
            if (window.utils && window.utils.hideLoading) window.utils.hideLoading();
            const url = window.URL.createObjectURL(blob);
            
            if (isPreview) {
                window.open(url, '_blank');
            } else {
                let filename = 'export_report';
                if (doPdf && doWord) filename += '.zip';
                else if (doPdf) filename += '.pdf';
                else filename += '.docx';
                
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                
                setTimeout(() => {
                    window.URL.revokeObjectURL(url);
                    localStorage.removeItem('dashboard_export_data');
                }, 1000);
            }
        })
        .catch(err => {
            if (window.utils && window.utils.hideLoading) window.utils.hideLoading();
            utils.alert('發生錯誤：' + err.message, 'error');
        });
    }

    document.getElementById('btnConfirmExport').addEventListener('click', function() {
        doExport(false);
    });
    
    document.getElementById('btnPreviewPdf').addEventListener('click', function() {
        doExport(true);
    });
});
