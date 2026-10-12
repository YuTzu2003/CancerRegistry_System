document.addEventListener('DOMContentLoaded', () => {
  const storageKey = 'indicators_export_data';
  const missingNarrativeWarning = '請先產生語言模型敘述，再進行預覽或下載!!';
  const listContainer = document.getElementById('exportItemList');
  const backButton = document.getElementById('btnBackToIndicators');
  const previewButton = document.getElementById('btnPreviewPdf');
  const exportButton = document.getElementById('btnConfirmExport');
  const pageTitle = document.getElementById('indicatorsExportPageTitle');
  const pageLead = document.getElementById('indicatorsExportPageLead');
  const contentHint = document.getElementById('indicatorsExportContentHint');

  backButton?.addEventListener('click', () => history.back());

  let exportData = [];
  let exportMode = 'complete';
  try {
    const stored = JSON.parse(localStorage.getItem(storageKey) || '{}');
    exportData = Array.isArray(stored.items) ? stored.items : [];
    exportMode = stored.mode === 'basic' ? 'basic' : 'complete';
  } catch (error) {
    console.error('Unable to read monitoring-indicator export data:', error);
  }
  const includeNarrative = exportMode === 'complete';
  if (!includeNarrative) {
    if (pageTitle) pageTitle.textContent = '基本監測指標報告匯出設定';
    if (pageLead) pageLead.textContent = '預覽監測表與圖表，再選擇 PDF、Word 或兩者下載；不包含語言模型敘述。';
    if (contentHint) contentHint.textContent = '基本報告僅包含監測表與圖表，不需要先產生語言模型敘述。';
  }

  if (!exportData.length) {
    utils.alert('找不到可匯出的監測指標內容，請返回監測指標頁重新準備。', 'error');
    previewButton.disabled = true;
    exportButton.disabled = true;
    return;
  }

  exportData.forEach((item, index) => {
    const hasTable = Boolean(item.tableHtml?.trim());
    const hasChart = Boolean(item.chartImage?.trim() || item.chartHtml?.trim());
    const hasAi = includeNarrative && Boolean(item.llmText?.trim());
    const element = document.createElement('div');
    element.className = 'export-item';
    element.dataset.id = item.id;
    element.innerHTML = `
      <div class="d-flex align-items-center flex-grow-1">
        <i class="bi bi-grip-vertical text-muted fs-4 drag-handle-icon"></i>
        <div class="export-item-title ms-2"><i class="bi bi-clipboard-data text-primary me-2"></i>${escapeHtml(item.title)}</div>
        <div class="d-flex align-items-center gap-3 ms-4 flex-wrap" onmousedown="event.stopPropagation()">
          ${hasChart ? checkboxMarkup('chart', item.id, '圖表') : ''}
          ${hasTable ? checkboxMarkup('table', item.id, '監測表') : ''}
          ${hasAi ? checkboxMarkup('ai', item.id, '語言模型敘述') : ''}
        </div>
      </div>
      <div class="export-actions ms-3"><span class="badge bg-secondary">Item <span class="order-number">${index + 1}</span></span></div>`;
    listContainer.appendChild(element);
  });

  if (typeof Sortable !== 'undefined') {
    new Sortable(listContainer, {
      animation: 150,
      ghostClass: 'sortable-ghost',
      onEnd: () => document.querySelectorAll('.order-number').forEach((element, index) => {
        element.textContent = index + 1;
      })
    });
  }

  const selectedData = () => [...listContainer.children].map((element) => {
    const item = exportData.find((candidate) => candidate.id === element.dataset.id);
    return {
      ...item,
      includeTable: Boolean(element.querySelector('.item-cb-table')?.checked),
      includeChart: Boolean(element.querySelector('.item-cb-chart')?.checked),
      includeAi: includeNarrative && Boolean(element.querySelector('.item-cb-ai')?.checked)
    };
  }).filter((item) => item.includeTable || item.includeChart || item.includeAi);

  const runExport = async (previewOnly) => {
    if (includeNarrative && exportData.some((item) => !String(item.llmText || '').trim())) {
      utils.alert(missingNarrativeWarning, 'warning');
      return;
    }
    const formatPdf = previewOnly || document.getElementById('exportPdf').checked;
    const formatWord = !previewOnly && document.getElementById('exportWord').checked;
    if (!formatPdf && !formatWord) {
      utils.alert('請至少選擇一種匯出格式（PDF 或 Word）。', 'warning');
      return;
    }
    const charts = selectedData();
    if (!charts.length) {
      utils.alert(includeNarrative ? '請至少保留一項監測表、圖表或語言模型敘述。' : '請至少保留一項監測表或圖表。', 'warning');
      return;
    }

    window.utils?.showLoading?.(previewOnly ? '正在產生 PDF 預覽…' : '正在產生匯出檔案…');
    try {
      const response = await fetch('/api/indicators/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format_pdf: formatPdf, format_word: formatWord, charts })
      });
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new Error(error.error || '監測指標匯出失敗。');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      if (previewOnly) {
        window.open(url, '_blank');
        window.setTimeout(() => URL.revokeObjectURL(url), 60000);
        return;
      }
      const extension = formatPdf && formatWord ? 'zip' : formatPdf ? 'pdf' : 'docx';
      const link = document.createElement('a');
      link.href = url;
      link.download = `indicators_report.${extension}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => {
        URL.revokeObjectURL(url);
        localStorage.removeItem(storageKey);
      }, 1000);
    } catch (error) {
      utils.alert(error.message || '監測指標匯出失敗。', 'error');
    } finally {
      window.utils?.hideLoading?.();
    }
  };

  previewButton?.addEventListener('click', () => void runExport(true));
  exportButton?.addEventListener('click', () => void runExport(false));

  function checkboxMarkup(type, id, label) {
    const inputId = `indicator_export_${type}_${id}`.replace(/[^a-zA-Z0-9_-]/g, '_');
    return `<div class="form-check"><input class="form-check-input item-cb-${type}" type="checkbox" checked id="${inputId}"><label class="form-check-label" for="${inputId}">${label}</label></div>`;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[character]));
  }
});
