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

    // Background export: enqueue a render job, poll its status, then download.
    const EXPORT_JOB_KEY = 'dashboard_export_job';
    const EXPORT_POLL_INTERVAL_MS = 1500;
    const EXPORT_MAX_WAIT_MS = 5 * 60 * 1000;
    let exportInFlight = false;

    function setExportButtonsEnabled(enabled) {
        ['btnConfirmExport', 'btnPreviewPdf'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = !enabled;
        });
    }

    function finishExport() {
        exportInFlight = false;
        setExportButtonsEnabled(true);
        if (window.utils && window.utils.hideLoading) window.utils.hideLoading();
    }

    function filenameFromDisposition(disposition, fallback) {
        if (!disposition) return fallback;
        let match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
        if (match) { try { return decodeURIComponent(match[1]); } catch (e) { /* fall through */ } }
        match = /filename="?([^";]+)"?/i.exec(disposition);
        return match ? match[1] : fallback;
    }

    // Bound the WHOLE request — connection, headers AND body read — under one
    // timeout: consume(response) reads the body and runs inside the same deadline,
    // and the AbortController cancels a stalled body, not just a stalled connect.
    function timedFetch(url, timeoutMs, consume) {
        const controller = new AbortController();
        let timer;
        const timeout = new Promise((_, reject) => {
            timer = setTimeout(() => { controller.abort(); reject(new Error('請求逾時')); }, timeoutMs);
        });
        const op = fetch(url, { signal: controller.signal }).then(response => consume(response));
        return Promise.race([op, timeout]).finally(() => clearTimeout(timer));
    }

    function clearPendingIfMatches(taskId) {
        // Clear only when this is still our job, so an older tab finishing does not
        // wipe the pending record a newer export just wrote. No pending / malformed
        // state is left for the resume handler to deal with on next load.
        try {
            const pending = JSON.parse(localStorage.getItem(EXPORT_JOB_KEY) || 'null');
            if (pending && pending.taskId === taskId) localStorage.removeItem(EXPORT_JOB_KEY);
        } catch (e) { /* leave malformed state for the resume handler */ }
    }

    function saveBlobResponse(response) {
        const name = filenameFromDisposition(response.headers.get('Content-Disposition'), 'export_report');
        return response.blob().then(blob => {
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
        });
    }

    function cleanupExportArtifacts() {
        if (draftId) {
            fetch('/api/dashboard/export-drafts/' + encodeURIComponent(draftId), { method: 'DELETE' }).catch(() => {});
        } else {
            localStorage.removeItem('dashboard_export_data');
        }
    }

    // Poll until the job is completed/failed, a deadline passes, or the session
    // is lost — never loops forever.
    // onFailed(message, isTerminal): isTerminal=true only when the server reports a
    // final state; timeouts/network/login stay non-terminal so the job can resume.
    function pollExportJob(taskId, onComplete, onFailed) {
        const deadline = Date.now() + EXPORT_MAX_WAIT_MS;
        const tick = () => {
            if (Date.now() > deadline) { onFailed('匯出時間過長，請稍後再試或重新匯出。', false); return; }
            timedFetch('/api/dashboard/export-jobs/' + encodeURIComponent(taskId) + '/status', 10000, response => {
                if (response.redirected || response.status === 401 || response.status === 403) {
                    throw new Error('登入狀態已失效，請重新登入後再試。');
                }
                return response.json();
            })
                .then(data => {
                    if (data && data.status === 'completed') { onComplete(data); return; }
                    if (data && data.status === 'failed') { onFailed((data && data.error) || '匯出失敗', true); return; }
                    if (data && data.ok === false) { onFailed(data.error || '找不到匯出工作', true); return; }
                    setTimeout(tick, EXPORT_POLL_INTERVAL_MS); // queued / running
                })
                .catch(error => {
                    if (error && /登入/.test(error.message)) { onFailed(error.message, false); return; }
                    if (Date.now() > deadline) { onFailed('匯出時間過長，請稍後再試或重新匯出。', false); return; }
                    setTimeout(tick, 3000); // transient / aborted request: retry within the deadline
                });
        };
        tick();
    }

    function runExportJob(taskId, isPreview, previewTab) {
        const downloadUrl = '/api/dashboard/export-jobs/' + encodeURIComponent(taskId) + '/download';
        pollExportJob(taskId, () => {
            if (isPreview) {
                clearPendingIfMatches(taskId);
                // as_attachment is off for ?disposition=inline PDFs, so the tab
                // renders the preview instead of downloading it.
                const inlineUrl = downloadUrl + '?disposition=inline';
                if (previewTab && !previewTab.closed) previewTab.location = inlineUrl;
                else utils.alert('預覽分頁被瀏覽器攔截，請允許彈出視窗後再試。', 'warning');
                finishExport();
                return;
            }
            // Confirm a real file comes back before clearing state; a login page
            // (HTML / redirect) or error leaves the pending record for a retry.
            timedFetch(downloadUrl, 60000, response => {
                if (!response.ok || response.redirected) throw new Error('下載失敗，請重新匯出。');
                if ((response.headers.get('Content-Type') || '').toLowerCase().indexOf('text/html') !== -1) {
                    throw new Error('登入狀態已失效，請重新登入後再試。');
                }
                return saveBlobResponse(response);
            })
                .then(() => {
                    clearPendingIfMatches(taskId);
                    cleanupExportArtifacts();
                    finishExport();
                })
                .catch(error => {
                    finishExport(); // keep EXPORT_JOB_KEY so a reload can retry
                    utils.alert('發生錯誤：' + error.message, 'error');
                });
        }, (message, isTerminal) => {
            if (isTerminal) clearPendingIfMatches(taskId);
            if (isPreview && previewTab && !previewTab.closed) {
                previewTab.document.body.textContent = '預覽失敗：' + message;
            }
            finishExport();
            utils.alert('發生錯誤：' + message, 'error');
        });
    }

    function doExport(isPreview) {
        if (exportInFlight) return;
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

        if (!sortedData.length) {
            utils.alert('請至少選擇一項匯出內容。', 'warning');
            return;
        }

        const payload = {
            format_pdf: doPdf,
            format_word: doWord,
            export_language: exportLanguageSelect.value,
            charts: sortedData
        };

        exportInFlight = true;
        setExportButtonsEnabled(false);

        // The preview tab must be opened synchronously inside the click handler;
        // a window.open() from the async completion callback would be blocked.
        let previewTab = null;
        if (isPreview) {
            previewTab = window.open('', '_blank');
            if (previewTab) previewTab.document.write('<!doctype html><meta charset="utf-8"><title>預覽</title><p style="font-family:sans-serif;padding:16px">預覽產生中，請稍候…</p>');
        } else if (window.utils && window.utils.showLoading) {
            window.utils.showLoading('匯出中，請稍候...');
        }

        fetch('/api/dashboard/export-jobs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (response.redirected || response.status === 401 || response.status === 403) {
                throw new Error('登入狀態已失效，請重新登入後再試。');
            }
            return response.json();
        })
        .then(data => {
            if (!data.ok || !data.task_id) throw new Error(data.error || '操作失敗');
            if (!isPreview) {
                // Remember the job so an accidental refresh can resume the download.
                try { localStorage.setItem(EXPORT_JOB_KEY, JSON.stringify({ taskId: data.task_id, at: Date.now() })); } catch (e) {}
            }
            runExportJob(data.task_id, isPreview, previewTab);
        })
        .catch(err => {
            if (isPreview && previewTab && !previewTab.closed) previewTab.close();
            finishExport();
            utils.alert('發生錯誤：' + err.message, 'error');
        });
    }

    document.getElementById('btnConfirmExport').addEventListener('click', function() {
        doExport(false);
    });
    
    document.getElementById('btnPreviewPdf').addEventListener('click', function() {
        doExport(true);
    });

    // Resume a download whose page was refreshed while the export was still
    // rendering (the server keeps the finished file; we only need the job id).
    try {
        const pending = JSON.parse(localStorage.getItem(EXPORT_JOB_KEY) || 'null');
        // Resume regardless of how long the job has been running: a job that is
        // gone returns 404 (terminal) and clears itself. The 24h bound matches the
        // server-side retention so a truly ancient record is dropped, not resumed.
        if (pending && pending.taskId && (Date.now() - (pending.at || 0) < 24 * 60 * 60 * 1000)) {
            exportInFlight = true;
            setExportButtonsEnabled(false);
            if (window.utils && window.utils.showLoading) window.utils.showLoading('繼續先前的匯出…');
            runExportJob(pending.taskId, false, null);
        } else if (pending) {
            localStorage.removeItem(EXPORT_JOB_KEY);
        }
    } catch (e) {
        localStorage.removeItem(EXPORT_JOB_KEY); // drop malformed resume state
    }
});
