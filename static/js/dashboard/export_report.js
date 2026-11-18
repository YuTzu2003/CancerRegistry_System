document.addEventListener('DOMContentLoaded', async function() {
    document.getElementById('btnBackToDashboard')?.addEventListener('click', function() {
        sessionStorage.setItem('dashboard_reset_filters_on_return', '1');
        history.back();
    });

    const draftId = document.getElementById('exportReportContext')?.dataset.draftId || '';
    let rawData = draftId ? '' : localStorage.getItem('dashboard_export_data');
    if (draftId) {
        try {
            const response = await fetch('/api/dashboard/export-drafts/' + encodeURIComponent(draftId));
            const draft = await response.json();
            if (!response.ok || !draft.success) {
                throw new Error(draft.error || '找不到匯出資料');
            }
            rawData = JSON.stringify(draft.data);
        } catch (error) {
            console.error('Export draft load failed:', error);
            rawData = '';
        }
    }
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

    const exportContentLabels = {
        chart: { 'zh-TW': '圖表', en: 'Figure' },
        table: { 'zh-TW': '表格', en: 'Table' },
        ai: { 'zh-TW': '分析敘述', en: 'Analysis and description' }
    };
    function getItemCapabilities(item) {
        return {
            table: Boolean(item.tableHtml && item.tableHtml.trim()),
            chart: Boolean(item.chartImage && item.chartImage.trim()),
            ai: Boolean(
                item.llmText
                && item.llmText.trim()
                && item.llmText.trim() !== '定義還沒串接使用。'
                && !item.llmText.includes('自動產生')
                && !item.llmText.includes('generate an analysis automatically')
            )
        };
    }

    function groupExportItems(exportData, isEnglish) {
        const groups = new Map();
        exportData.forEach(item => {
            const key = item.cancerSectionKey || '__all__';
            const title = item.cancerSectionTitle || (isEnglish ? 'Selected cancers' : '所選癌別');
            if (!groups.has(key)) groups.set(key, { key, title, items: [] });
            groups.get(key).items.push(item);
        });
        return Array.from(groups.values());
    }

    function getDisplayTitle(item, groupTitle) {
        const prefix = `${groupTitle}｜`;
        return item.title?.startsWith(prefix) ? item.title.slice(prefix.length) : item.title;
    }

    function updateOrderNumbers() {
        listContainer.querySelectorAll('.order-number').forEach((el, index) => {
            el.innerText = index + 1;
        });
    }

    function syncGroupSelection(groupEl) {
        const control = groupEl.querySelector('.group-cb-all');
        const items = Array.from(groupEl.querySelectorAll('.item-cb-chart, .item-cb-table, .item-cb-ai'));
        if (!control) return;
        const selectedCount = items.filter(input => input.checked).length;
        control.checked = items.length > 0 && selectedCount === items.length;
        control.indeterminate = selectedCount > 0 && selectedCount < items.length;
        control.disabled = items.length === 0;
    }

    function renderExportItems() {
        const exportData = getCurrentExportData();
        const isEnglish = exportLanguageSelect.value === 'en';
        const groups = groupExportItems(exportData, isEnglish);
        listContainer.innerHTML = '';

        groups.forEach(group => {
            const groupEl = document.createElement('details');
            groupEl.className = 'export-cancer-group';
            groupEl.dataset.cancerKey = group.key;
            groupEl.open = false;

            groupEl.innerHTML = `
                <summary>
                    <i class="bi bi-grip-vertical export-group-drag-handle" title="${isEnglish ? 'Drag to reorder cancer sections' : '可拖曳調整癌別順序'}"></i>
                    <span class="export-group-title"><i class="bi bi-folder2-open me-2"></i>${group.title}</span>
                    <span class="export-group-count">${group.items.length} ${isEnglish ? 'items' : '項'}</span>
                </summary>
                <div class="export-group-items">
                    <div class="export-group-toolbar">
                        <span>${isEnglish ? 'Export content' : '匯出內容'}</span>
                        <label class="form-check mb-0">
                            <input class="form-check-input group-cb-all" type="checkbox" checked>
                            <span class="form-check-label">${isEnglish ? 'Select all items in this cancer section' : '全選本癌別'}</span>
                        </label>
                    </div>
                    <div class="export-group-item-list"></div>
                </div>
            `;
            const itemsEl = groupEl.querySelector('.export-group-item-list');
            groupEl.querySelector('.export-group-drag-handle').addEventListener('click', event => {
                event.preventDefault();
                event.stopPropagation();
            });

            group.items.forEach(item => {
                const capabilities = getItemCapabilities(item);
                const div = document.createElement('div');
                div.className = 'export-item';
                div.dataset.id = item.id;
                div.innerHTML = `
                    <div class="d-flex align-items-center flex-grow-1 min-w-0">
                        <i class="bi bi-grip-vertical text-muted fs-4 drag-handle-icon" title="${isEnglish ? 'Drag to reorder within this cancer section' : '可拖曳調整此癌別內的順序'}"></i>
                        <div class="export-item-title ms-2"><i class="bi bi-graph-up-arrow text-primary me-2"></i>${getDisplayTitle(item, group.title)}</div>
                        <div class="d-flex align-items-center gap-3 ms-4 flex-wrap export-item-controls" onmousedown="event.stopPropagation()">
                            ${capabilities.chart ? `<div class="form-check"><input class="form-check-input item-cb-chart" type="checkbox" checked id="cb_chart_${item.id}"><label class="form-check-label" for="cb_chart_${item.id}">${exportContentLabels.chart[isEnglish ? 'en' : 'zh-TW']}</label></div>` : ''}
                            ${capabilities.table ? `<div class="form-check"><input class="form-check-input item-cb-table" type="checkbox" checked id="cb_table_${item.id}"><label class="form-check-label" for="cb_table_${item.id}">${exportContentLabels.table[isEnglish ? 'en' : 'zh-TW']}</label></div>` : ''}
                            ${capabilities.ai ? `<div class="form-check"><input class="form-check-input item-cb-ai" type="checkbox" checked id="cb_ai_${item.id}"><label class="form-check-label" for="cb_ai_${item.id}">${exportContentLabels.ai[isEnglish ? 'en' : 'zh-TW']}</label></div>` : ''}
                        </div>
                    </div>
                    <div class="export-actions ms-3"><span class="badge bg-secondary">Item <span class="order-number"></span></span></div>
                `;
                itemsEl.appendChild(div);
            });

            const groupSelectAll = groupEl.querySelector('.group-cb-all');
            groupSelectAll.addEventListener('change', () => {
                groupEl.querySelectorAll('.item-cb-chart, .item-cb-table, .item-cb-ai').forEach(input => {
                    input.checked = groupSelectAll.checked;
                });
                syncGroupSelection(groupEl);
            });
            groupEl.querySelectorAll('.item-cb-chart, .item-cb-table, .item-cb-ai').forEach(input => {
                input.addEventListener('change', () => syncGroupSelection(groupEl));
            });
            syncGroupSelection(groupEl);

            listContainer.appendChild(groupEl);
            if (typeof Sortable !== 'undefined') {
                new Sortable(itemsEl, {
                    animation: 150,
                    handle: '.drag-handle-icon',
                    ghostClass: 'sortable-ghost',
                    onEnd: updateOrderNumbers
                });
            }
        });
        if (typeof Sortable !== 'undefined') {
            new Sortable(listContainer, {
                animation: 150,
                draggable: '.export-cancer-group',
                handle: '.export-group-drag-handle',
                ghostClass: 'sortable-ghost',
                onEnd: updateOrderNumbers
            });
        }
        updateOrderNumbers();
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

        const sortedIds = Array.from(listContainer.querySelectorAll('.export-item')).map(el => el.dataset.id);
        const sortedData = sortedIds.map(id => {
            const baseData = exportData.find(d => d.id === id);
            const itemEl = listContainer.querySelector('.export-item[data-id="'+id+'"]');
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
                    if (draftId) {
                        fetch('/api/dashboard/export-drafts/' + encodeURIComponent(draftId), { method: 'DELETE' })
                            .catch(() => {});
                    } else {
                        localStorage.removeItem('dashboard_export_data');
                    }
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
