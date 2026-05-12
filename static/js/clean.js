(function () {
  'use strict';
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  let currentJobId = null;

  // ----------Step控制 ----------
  function setStep(n) {
    $$('#stepper .step').forEach((el) => {
      const s = Number(el.dataset.step);
      el.classList.toggle('done', s < n);
      el.classList.toggle('active', s === n);
    });
  }

  // ---------- 格式管理(CRUD) ----------
  document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('formatModal');
    const btnAdd = document.getElementById('btnAddFormat');
    const btnSave = document.getElementById('btnSaveFormat');
    const closeBtns = document.querySelectorAll('[data-close]');

    const fmtIdInput = document.getElementById('fmtId');
    const fmtNameInput = document.getElementById('fmtName');
    const fmtVersionInput = document.getElementById('fmtVersion');
    const fmtUpdatedInput = document.getElementById('fmtUpdated');

    const openModal = () => modal.removeAttribute('hidden');
    const closeModal = () => modal.setAttribute('hidden', '');
    closeBtns.forEach(btn => btn.addEventListener('click', closeModal));

    btnAdd.addEventListener('click', () => {
      document.getElementById('modalTitle').textContent = '新增參考資料格式';
      fmtIdInput.value = ''; fmtNameInput.value = ''; fmtVersionInput.value = ''; fmtUpdatedInput.value = '';
      openModal();
    });

    const table = document.getElementById('formatsTable');
    if (table) {
      table.addEventListener('click', async (e) => {
        const btn = e.target.closest('button');
        if (!btn) return;
        const action = btn.dataset.action;
        const tr = btn.closest('tr');
        if (!tr) return;
        const id = tr.dataset.id;

        if (action === 'edit') {
          document.getElementById('modalTitle').textContent = '編輯參考資料格式';
          fmtIdInput.value = id;
          fmtNameInput.value = tr.dataset.name;
          fmtVersionInput.value = tr.dataset.version;
          fmtUpdatedInput.value = tr.dataset.updated;
          openModal();
        } 
        else if (action === 'delete') {
          const displayName = tr.querySelector('.fmt-name').textContent.trim();
          const confirmed = await utils.confirm(`確定要刪除「${displayName}」嗎？`);
          if (confirmed.isConfirmed) {
            try {
              const res = await fetch(`/api/formats/${id}`, { method: 'DELETE' });
              const data = await res.json();
              if (data.ok) location.reload(); else utils.alert(data.message, 'error');
            } catch (err) { utils.alert('連線失敗', 'error'); }
          }
        }
      });
    }

    btnSave.addEventListener('click', async () => {
      const id = fmtIdInput.value;
      const payload = { name: fmtNameInput.value, version: fmtVersionInput.value, updated: fmtUpdatedInput.value };
      const isEdit = id !== '';
      const url = isEdit ? `/api/formats/${id}` : '/api/formats';
      if (!payload.name || !payload.version) return utils.alert('資料須填寫完畢！', 'warning');

      try {
        const res = await fetch(url, {
          method: isEdit ? 'PUT' : 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.ok) location.reload(); else utils.alert(data.message, 'error');
      } catch (err) { utils.alert('連線失敗', 'error'); }
    });
  });

  // ---------- 檔案上傳與預覽 ----------
  const fileInput = $('#fileInput');
  const fileChosen = $('#fileChosen');
  const fileName = $('#fileName');
  const dropZone = $('#dropZone');

  function updateFilePreview() {
    const f = fileInput.files?.[0];
    if (f) {
      fileName.textContent = `${f.name} · ${(f.size / 1024).toFixed(1)} KB`;
      fileChosen.hidden = false;
    } 
    else { fileChosen.hidden = true; }
  }
  // ---------- 重置 ----------
  function resetUI() {
    currentJobId = null;
    setStep(1);

    if ($('#kpiTotal')) $('#kpiTotal').textContent = '—';
    if ($('#kpiPassed')) $('#kpiPassed').textContent = '—';
    if ($('#kpiError')) $('#kpiError').textContent = '—';
    if ($('#fieldAnalysisContent')) $('#fieldAnalysisContent').hidden = true;
    if ($('#fieldAnalysisEmpty')) $('#fieldAnalysisEmpty').hidden = false;
    if ($('#analysisContent')) $('#analysisContent').hidden = true;
    if ($('#analysisEmpty')) $('#analysisEmpty').hidden = false;
    if ($('#cleaningAlertContainer')) $('#cleaningAlertContainer').innerHTML = '';

    const list = $('#outputFieldList');
    if (list) {
      list.innerHTML = '<span class="field-chip disabled"><i class="bi bi-asterisk"></i> 尚未載入欄位，清洗完成後自動帶入</span>';
    }
  
    if ($('#analysisByField tbody')) $('#analysisByField tbody').innerHTML = '';
    if ($('#analysisByType tbody')) $('#analysisByType tbody').innerHTML = '';
    if ($('#stat-completeness')) $('#stat-completeness').textContent = '-';
    if ($('#stat-correctness')) $('#stat-correctness').textContent = '-';
    if ($('#stat-consistency')) $('#stat-consistency').textContent = '-';
    if ($('#stat-dqi')) $('#stat-dqi').textContent = '-';
  }

  if (fileInput) fileInput.addEventListener('change', updateFilePreview);

  if (dropZone) {
    ['dragenter', 'dragover'].forEach(evt => dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.add('dragover'); }));
    ['dragleave', 'drop'].forEach(evt => dropZone.addEventListener(evt, e => { e.preventDefault(); dropZone.classList.remove('dragover'); }));
    dropZone.addEventListener('drop', e => {
      const f = e.dataTransfer?.files?.[0];
      if (f) { const dt = new DataTransfer(); dt.items.add(f); fileInput.files = dt.files; updateFilePreview(); }
    });
  }

  $('#cleanForm')?.addEventListener('reset', () => {
    resetUI();
    setTimeout(updateFilePreview, 10);
  });

  // ---------- 表單提交與Loading控制 ----------
  $('#cleanForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formatId = $('#formatSelect').value;
    const file = fileInput.files?.[0];

    const errors = [];
    if (!formatId) errors.push('請選擇參考資料格式');
    if (!file) errors.push('請上傳檔案');

    if (errors.length === 2) {
      return utils.alert('請選擇參考資料格式及上傳檔案', 'warning');
    } else if (errors.length === 1) {
      return utils.alert(errors[0], 'warning');
    }

    const loadingOverlay = document.getElementById('loadingOverlay');
    const btnStart = document.getElementById('btnStartClean');
    if (loadingOverlay) loadingOverlay.style.display = 'flex';
    if (btnStart) { 
      btnStart.disabled = true; 
      btnStart.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>處理中...'; 
    }

    setStep(2);
    const formData = new FormData();
    formData.append('format_id', formatId);
    formData.append('data_file', file);

    try {
      const response = await fetch('/api/cleanJob', { method: 'POST', body: formData });
      const result = await response.json();
      
      if (!response.ok || !result.ok) {
        const errorMsg = result.message || result.error || '清洗失敗';
        const alertContainer = $('#cleaningAlertContainer');
        if (alertContainer) {
          alertContainer.innerHTML = `
            <div class="alert alert-danger border shadow-sm mt-3" role="alert">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>${errorMsg}
            </div>`;
        }
        throw new Error(errorMsg);
      }
      
      renderResult(result);
      setStep(3);
    } catch (error) { 
      // alert(error.message); 
      setStep(1); 
    } finally {
      if (loadingOverlay) loadingOverlay.style.display = 'none';
      if (btnStart) { 
        btnStart.disabled = false; 
        btnStart.innerHTML = '<i class="bi bi-funnel"></i> 開始清洗'; 
      }
    }
  });

  // ---------- 清洗結果 ----------
  function renderResult(data) {

    if (data.project_id) {
      currentJobId = data.project_id;
    }

    // 顯示偵測到的體系
    const systemBadge = $('#detectedSystemBadge');
    const systemName = $('#detectedSystemName');
    if (data.detected_system && data.detected_system !== 'unknown') {
      if (systemBadge) systemBadge.style.display = 'inline-block';
      if (systemName) systemName.textContent = data.detected_system;
      
      // 自動勾選對應的命名方案
      const schemeValueMap = {
        "中文欄位名稱": "field_name_zh",
        "英文欄位名稱": "field_name_en",
        "台大雲林欄位名稱": "ntu_yunlin",
        "台大體系醫整庫欄位名稱": "ntu_system",
        "台灣癌症登記中心": "taiwan_cancer_registry",
        "雲醫癌AI模組": "AI_module"
      };
      const targetValue = schemeValueMap[data.detected_system];
      if (targetValue) {
        const radio = $(`input[name="nameScheme"][value="${targetValue}"]`);
        if (radio) {
          radio.checked = true;
        }
      }
    } else {
      if (systemBadge) systemBadge.style.display = 'none';
    }

    // Always sync naming selection to refresh field list after cleaning completes
    syncNamingSelection();

    const alertContainer = $('#cleaningAlertContainer');
    if (alertContainer && data.ok) {
      alertContainer.innerHTML = `
        <div class="alert alert-light border shadow-sm mt-3" role="alert">
          <i class="bi bi-check-circle-fill text-success me-2"></i>資料清洗並存檔完成！
        </div>`;
      if (window.autoHideAlerts) window.autoHideAlerts();
    }

    const s = data.stats || {};
    $('#kpiTotal').textContent = (s.total ?? 0).toLocaleString();
    $('#kpiPassed').textContent = (s.passed ?? 0).toLocaleString();
    $('#kpiError').textContent = (s.error ?? 0).toLocaleString();

    const analysis = data.analysis || {};
    const byField = analysis.by_field || [];
    const byType = analysis.by_type || [];

    // 清洗個案清單明細(左側)
    const fieldWrap = $('#fieldAnalysisContent');
    const fieldEmpty = $('#fieldAnalysisEmpty');
    if (byField.length) {
      fieldWrap.hidden = false;
      fieldEmpty.hidden = true;
      $('#analysisByField tbody').innerHTML = byField.map(r => `
        <tr>
          <td>${r.name}</td>
          <td><span class="badge-soft gray">${r.format || '—'}</span></td>
          <td style="text-align:right;">${r.errors ?? 0}</td>
        </tr>`).join('');
    }

    // 清洗結果分析(右側)
    if (byField.length || byType.length) {
      $('#analysisContent').hidden = false;
      $('#analysisEmpty').hidden = true;
      $('#stat-completeness').textContent = ((s.completeness || 0) * 100).toFixed(1) + '%';
      $('#stat-correctness').textContent = ((s.correctness || 0) * 100).toFixed(1) + '%';
      $('#stat-consistency').textContent = ((s.consistency || 0) * 100).toFixed(1) + '%';
      $('#stat-dqi').textContent = (s.dqi || 0).toFixed(2) + '%';

      $('#analysisByType tbody').innerHTML = byType.map(r => {
        let bgClass = '';
        if (r.type.startsWith('A:')) {
            bgClass = 'bg-warning bg-opacity-10';
        }
        else if (r.type.startsWith('B:')) {
            bgClass = 'bg-danger bg-opacity-10';
        }
        else if (r.type.startsWith('C:')) {
            bgClass = 'bg-info bg-opacity-10';
        }
        
        return `
          <tr class="${bgClass} text-dark">
            <td>${r.type}</td>
            <td style="text-align:right;">${r.count ?? 0}</td>
            <td style="text-align:right;">${r.ratio ?? '—'}</td>
          </tr>`;
      }).join('');
    }
  }

  // ---------- 欄位輸出設定 ----------
  async function updateFieldCategorization() {
    if (!currentJobId) return;
    
    const scheme = $('input[name="nameScheme"]:checked')?.value;
    const list = $('#outputFieldList');
    const info = $('#matchedFieldInfo');
    
    try {
      const res = await fetch('/api/categorize_fields', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId, scheme: scheme })
      });
      const data = await res.json();
      
      if (data.ok) {
        if (info && data.mapped && data.mapped.length > 0) {
          info.innerHTML = data.mapped.map(f => `
            <div class="d-flex justify-content-between mb-1">
              <span>${f.label}</span>
              <i class="bi bi-arrow-right mx-2 text-muted"></i>
              <span class="text-primary">${f.target}</span>
            </div>`).join('');
        } else if (info) {
          info.innerHTML = '<span class="text-muted">體系無匹配欄位</span>';
        }

        // 未匹配的欄位
        if (data.unmapped && data.unmapped.length > 0) {
          list.innerHTML = data.unmapped.map(f => `
            <label class="field-chip">
              <input type="checkbox" value="${f.key}" checked />${f.label}
            </label>`).join('');
          
          $$('#outputFieldList .field-chip input').forEach(cb => {
            const chip = cb.closest('.field-chip');
            const sync = () => chip.classList.toggle('selected', cb.checked);
            cb.addEventListener('change', sync); 
            sync();
          });
        } else {
          list.innerHTML = '<span class="text-muted" style="font-size:12px;">無額外欄位</span>';
        }
      }
    } catch (err) {
      console.error('Categorization failed', err);
    }
  }

  function syncNamingSelection() {
    $$('#namingScheme .naming-chip').forEach(chip => {
      const input = chip.querySelector('input[type="radio"]');
      chip.classList.toggle('selected', !!input?.checked);
    });
    updateFieldCategorization();
    if (currentJobId) setStep(4);
  }
  
  $$('#namingScheme input[type="radio"]').forEach(r => r.addEventListener('change', syncNamingSelection));
  syncNamingSelection();

  // ---------- 下載清洗結果 ----------
  $('#btnDownloadCleaned')?.addEventListener('click', () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    window.location.href = `/api/download/cleaned/${currentJobId}`;
  });

  $('#btnDownloadReport')?.addEventListener('click', () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    window.location.href = `/api/download/report/${currentJobId}`;
  });

  // ---------- 匯出 XLSX ----------
  $('#btnExportXlsx')?.addEventListener('click', async () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    
    const nameScheme = $('input[name="nameScheme"]:checked')?.value;
    const selectedFields = $$('#outputFieldList input[type="checkbox"]:checked').map(cb => cb.value);

    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) loadingOverlay.style.display = 'flex';

    try {
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: currentJobId,
          scheme: nameScheme,
          fields: selectedFields
        })
      });

      if (res.ok) {
        let filename = '';
        const disposition = res.headers.get('Content-Disposition');
        if (disposition) {
          const filenameStarRegex = /filename\*=UTF-8''([^;\n]*)/i;
          const starMatches = filenameStarRegex.exec(disposition);
          if (starMatches && starMatches[1]) {
            filename = decodeURIComponent(starMatches[1]);
          } 
          else {
            const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
            const matches = filenameRegex.exec(disposition);
            if (matches != null && matches[1]) {
              filename = matches[1].replace(/['"]/g, '');
              filename = decodeURIComponent(filename);
            }
          }
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
      } 
      else {
        const data = await res.json();
        utils.alert(data.error || '匯出失敗', 'error');
      }
    } catch (err) {utils.alert('連線失敗', 'error');
    } finally {if (loadingOverlay) loadingOverlay.style.display = 'none';
    }
  });

  // ---------- 預覽功能 ----------
  $('#btnPreviewOutput')?.addEventListener('click', async () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    
    const nameScheme = $('input[name="nameScheme"]:checked')?.value;
    const selectedFields = $$('#outputFieldList input[type="checkbox"]:checked').map(cb => cb.value);

    const loadingOverlay = document.getElementById('loadingOverlay');
    if (loadingOverlay) loadingOverlay.style.display = 'flex';

    try {
      const res = await fetch('/api/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: currentJobId,
          scheme: nameScheme,
          fields: selectedFields
        })
      });

      const data = await res.json();
      if (data.ok) {
        const thead = $('#previewThead');
        const tbody = $('#previewTbody');
        
        thead.innerHTML = data.headers.map(h => `<th>${h}</th>`).join('');
        tbody.innerHTML = data.data.map(row => `<tr>${row.map(val => `<td>${val}</td>`).join('')}</tr>`).join('');
        $('#previewModal').removeAttribute('hidden');
      } 
      else {
        utils.alert(data.error || '預覽失敗', 'error');
      }
    } 
    catch (err) {utils.alert('連線失敗', 'error');} 
    finally {if (loadingOverlay) loadingOverlay.style.display = 'none';}
  });
})();