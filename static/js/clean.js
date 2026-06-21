(function () {
  'use strict';
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  let currentJobId = null;

  // Step控制
  function setStep(n) {
    $$('#stepper .step').forEach((el) => {
      const s = Number(el.dataset.step);
      el.classList.toggle('done', s < n);
      el.classList.toggle('active', s === n);
    });
  }

  // 格式管理(CRUD)
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

  // 檔案上傳與預覽
  const fileInput = $('#fileInput');
  const fileChosen = $('#fileChosen');
  const fileName = $('#fileName');
  const dropZone = $('#dropZone');

  function updateFilePreview() {
    const f = fileInput.files?.[0];
    const txtOption = $('#txtConvertOption');
    if (f) {
      fileName.textContent = `${f.name} · ${(f.size / 1024).toFixed(1)} KB`;
      fileChosen.hidden = false;

      if (f.name.toLowerCase().endsWith('.txt') && txtOption) {
        txtOption.style.display = 'block';
      } else if (txtOption) {
        txtOption.style.display = 'none';
        const cb = $('#checkConvertTxt');
        if (cb) cb.checked = false;
      }
    } 
    else { 
      fileChosen.hidden = true; 
      if (txtOption) txtOption.style.display = 'none';
    }
  }
  // 重置 
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
    if ($('#dateErrorEditor')) $('#dateErrorEditor').innerHTML = '';

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

  // 表單提交與Loading控制
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
    
    const convertTxt = $('#checkConvertTxt')?.checked;
    formData.append('convert_txt', convertTxt ? 'true' : 'false');

    try {
      const response = await fetch('/api/cleanJob', { method: 'POST', body: formData });
      const result = await response.json();
      if (!response.ok || result.ok === false) {
        const errorMsg = result.message || result.error || '清洗失敗';

        // 標頭偵測失敗
        if (result.error === "標頭偵測失敗") {
            utils.alert(errorMsg, 'warning');
            throw new Error(errorMsg);
        }

        const alertContainer = $('#cleaningAlertContainer');
        if (alertContainer) {
          let downloadBtn = '';
          
          if (result.has_length_error) {
            if (result.log_data && result.xlsx_data) {
              // 記憶體下載方式 (不存入檔案)
              const baseName = result.filename ? result.filename.split('.')[0] : 'file';
              window._downloadB64 = function(b64, filename, type) {
                  const bin = atob(b64);
                  const arr = new Uint8Array(bin.length);
                  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
                  const blob = new Blob([arr], { type: type });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = filename;
                  a.click();
                  URL.revokeObjectURL(url);
              };

              downloadBtn = `
                <div class="d-flex flex-column gap-2 ms-3 flex-shrink-0 align-items-center">
                  <button type="button" onclick="_downloadB64('${result.xlsx_data}', '欄位檢核表_${baseName}.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')" class="btn btn-sm btn-outline-dark shadow-sm w-100">
                    <i class="bi bi-file-earmark-excel"></i> 下載欄位檢核表 XLSX
                  </button>
                  <button type="button" onclick="_downloadB64('${result.log_data}', '長度錯誤_${baseName}.log', 'text/plain')" class="btn btn-sm btn-outline-dark shadow-sm w-100">
                    <i class="bi bi-file-earmark-text"></i> 下載完整錯誤檔 Log
                  </button>
                </div>`;
            } else {
               // 原本的路徑 (存資料庫)
               const jobId = result.job_id || currentJobId;
               if (jobId) {
                  downloadBtn = `
                    <div class="d-flex flex-column gap-2 ms-3 flex-shrink-0 align-items-center">
                      <a href="/api/download/preview/${jobId}" class="btn btn-sm btn-outline-dark shadow-sm w-100">
                        <i class="bi bi-file-earmark-excel"></i> 下載欄位檢核表 XLSX
                      </a>
                      <a href="/api/download/length_log/${jobId}" class="btn btn-sm btn-outline-dark shadow-sm w-100">
                        <i class="bi bi-file-earmark-text"></i> 下載完整錯誤檔 Log
                      </a>
                    </div>`;
               }
            }
          }

          alertContainer.innerHTML = `
            <div class="alert alert-danger border shadow-sm mt-3 error-alert d-flex justify-content-between align-items-center" role="alert">
              <div class="d-flex align-items-start">
                <i class="bi bi-exclamation-triangle-fill alert-icon mt-1 me-2"></i>
                <div class="alert-message">${errorMsg}</div>
              </div>
              ${downloadBtn}
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

  // 清洗結果
  function renderResult(data) {
    if (data.job_id || data.project_id) {
      currentJobId = data.job_id || data.project_id;
    }

    // 預設切換至中文欄位名稱
    const zhRadio = $('input[name="nameScheme"][value="field_name_zh"]');
    if (zhRadio) {
      zhRadio.checked = true;
    }

    // 依據是否為無標頭固定長度 TXT 動態停用或啟用原始匯入資料欄位名稱選項
    const originalRadio = $('input[name="nameScheme"][value="original"]');
    if (originalRadio) {
      if (data.has_no_headers) {
        originalRadio.disabled = true;
        const chip = originalRadio.closest('.naming-chip');
        if (chip) {
          chip.style.opacity = '0.5';
          chip.style.cursor = 'not-allowed';
          chip.setAttribute('title', '無標頭的固定長度文字檔不支援還原原始欄位名稱');
        }
      } else {
        originalRadio.disabled = false;
        const chip = originalRadio.closest('.naming-chip');
        if (chip) {
          chip.style.opacity = '';
          chip.style.cursor = '';
          chip.removeAttribute('title');
        }
      }
    }
    syncNamingSelection();

    // 顯示偵測到的體系
    const systemBadge = $('#detectedSystemBadge');
    const systemName = $('#detectedSystemName');
    if (data.detected_system && data.detected_system !== 'unknown') {
      if (systemBadge) systemBadge.style.display = 'inline-block';
      if (systemName) systemName.textContent = data.detected_system;
    } else {
      if (systemBadge) systemBadge.style.display = 'none';
    }

    // Always sync naming selection to refresh field list after cleaning completes
    syncNamingSelection();

    const alertContainer = $('#cleaningAlertContainer');
    if (alertContainer && data.ok) {
      const dateErrorCount = data.date_error_count || 0;
      const dateErrorLimit = data.date_error_limit || 3;

      if (dateErrorCount > 0) {
        alertContainer.innerHTML = `
          <div class="alert alert-danger border shadow-sm mt-3 d-flex align-items-center justify-content-between" role="alert">
            <div class="d-flex align-items-center">
              <i class="bi bi-exclamation-triangle-fill me-2"></i>

              <span>
                過多日期邏輯錯誤共有 <strong>${dateErrorCount}</strong> 筆，已達系統限制<br>
                請先修正錯誤的日期資料，完成修正後再進行後續資料清洗作業
              </span>
            </div>

            <button
              class="btn btn-sm btn-danger ms-3"
              type="button"
              id="btnShowDateEditor"
            >
              <i class="bi bi-pencil-square"></i> 線上修正錯誤資料
            </button>
          </div>
        `;
      } else {
        alertContainer.innerHTML = `
          <div class="alert alert-light border shadow-sm mt-3" role="alert">
            <i class="bi bi-check-circle-fill text-success me-2"></i>資料清洗並存檔完成！
          </div>`;
        if (window.autoHideAlerts) window.autoHideAlerts();
      }
    }

    if ((data.date_errors || []).length > 0) {
      renderDateErrorEditor(data.date_errors || [], data.date_error_limit || 3);
    }

    const s = data.stats || {};

    if ($('#kpiTotal')) {$('#kpiTotal').textContent = (s.total ?? 0).toLocaleString();}
    if ($('#kpiPassed')) {$('#kpiPassed').textContent = (s.passed ?? 0).toLocaleString();}
    if ($('#kpiError')) {$('#kpiError').textContent = (s.error ?? 0).toLocaleString();}
    if ($('#stat-completeness')) {$('#stat-completeness').textContent = `${((s.completeness ?? 0) * 100).toFixed(2)}%`;}
    if ($('#stat-correctness')) {$('#stat-correctness').textContent = `${((s.correctness ?? 0) * 100).toFixed(2)}%`;}
    if ($('#stat-consistency')) {$('#stat-consistency').textContent = `${((s.consistency ?? 0) * 100).toFixed(2)}%`;}
    if ($('#stat-dqi')) {$('#stat-dqi').textContent = `${((s.dqi ?? 0) * 100).toFixed(2)}%`;}

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

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function toDateInputValue(value) {
    const dateText = String(value || '').trim().replaceAll('-', '').replaceAll('/', '');

    if (!/^\d{8}$/.test(dateText)) return '';
    if (dateText === '00000000' || dateText === '99999999') return '';

    return `${dateText.slice(0, 4)}-${dateText.slice(4, 6)}-${dateText.slice(6, 8)}`;
  }

  function getManualDateValue(value) {
    const dateText = String(value || '').trim().replaceAll('-', '').replaceAll('/', '');

    if (!dateText) return '';
    if (dateText === '00000000' || dateText === '99999999') return dateText;
    if (/^\d{8}$/.test(dateText)) return dateText;

    return '';
  }

  function normalizeDateInputValue(value) {
    return String(value || '').trim().replaceAll('-', '').replaceAll('/', '');
  }

  function dateInputValueFromNormalized(value) {
    const dateText = normalizeDateInputValue(value);

    if (!/^\d{8}$/.test(dateText)) return '';
    if (dateText === '00000000' || dateText === '99999999') return '';

    return `${dateText.slice(0, 4)}-${dateText.slice(4, 6)}-${dateText.slice(6, 8)}`;
  }

  function syncDateControls(source) {
    const group = source.closest('.d-flex');
    if (!group) return;

    const dateInput = group.querySelector('.date-fix-input');
    const manualInput = group.querySelector('.date-special-select');
    const picker = group.querySelector('.date-special-picker');

    if (!dateInput || !manualInput || !picker) return;

    if (source.classList.contains('date-fix-input')) {
      const normalizedDate = normalizeDateInputValue(dateInput.value);
      manualInput.value = normalizedDate;
      picker.value = '';
      return;
    }

    if (source.classList.contains('date-special-picker')) {
      if (!picker.value) return;

      manualInput.value = picker.value;
      dateInput.value = '';
      return;
    }

    if (source.classList.contains('date-special-select')) {
      const manualDate = normalizeDateInputValue(manualInput.value);
      manualInput.value = manualDate;

      if (manualDate === '00000000' || manualDate === '99999999') {
        picker.value = manualDate;
        dateInput.value = '';
        return;
      }

      picker.value = '';
      dateInput.value = dateInputValueFromNormalized(manualDate);
    }
  }

  function renderDateErrorEditor(errors, limit) {
    const editor = $('#dateErrorEditor');
    if (!editor) return;

    if (!errors || errors.length === 0) {
      editor.innerHTML = '';
      return;
    }

    const rowsHtml = errors.map((item, index) => {
      const fieldsHtml = (item.fields || []).map(field => `
        <div class="mb-2">
          <label class="form-label mb-1 small">${escapeHtml(field.name)}</label>
          <div class="d-flex gap-2">
            <input
              type="date"
              class="form-control form-control-sm date-fix-input"
              data-field="${escapeHtml(field.name)}"
              value="${escapeHtml(toDateInputValue(field.value))}"
            >
            <input
              type="text"
              class="form-control form-control-sm date-special-select"
              value="${escapeHtml(getManualDateValue(field.value))}"
              placeholder="YYYYMMDD"
              inputmode="numeric"
              style="max-width: 130px;"
            >
            <select class="form-select form-select-sm date-special-picker" style="max-width: 130px;">
              <option value="">選擇</option>
              <option value="00000000">00000000</option>
              <option value="99999999">99999999</option>
            </select>
          </div>
        </div>
      `).join('');

      const messagesHtml = (item.messages || []).map(msg => `
        <div class="text-danger small">${escapeHtml(msg)}</div>
      `).join('');

      return `
        <tr data-row-index="${item.row_index}">
          <td class="text-center align-middle">${item.clean_excel_row ?? (item.row_index + 2)}</td>
          <td>${fieldsHtml}</td>
          <td>${messagesHtml}</td>
          <td class="text-center align-middle">
            <button type="button" class="btn btn-sm btn-success btnSaveDateFix">
              儲存
            </button>
          </td>
        </tr>
      `;
    }).join('');

    editor.innerHTML = `
      <div class="card mt-3" id="dateErrorPanel">
        <div class="card-header fw-bold">
          <span>
            <i class="bi bi-pencil-square me-1"></i>
            線上修正日期邏輯錯誤
          </span>
        </div>
        <div class="card-body">
          <div class="table-responsive">
            <table class="table table-bordered table-sm align-middle">
              <thead>
                <tr>
                  <th class="text-center" style="width:70px;">序號</th>
                  <th>可修正日期欄位</th>
                  <th>錯誤原因</th>
                  <th class="text-center" style="width:90px;">操作</th>
                </tr>
              </thead>
              <tbody>
                ${rowsHtml}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    `;
  }

  // 欄位輸出設定
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

  // 下載清洗結果 
  $('#btnDownloadCleaned')?.addEventListener('click', () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    window.location.href = `/api/download/cleaned/${currentJobId}`;
  });

  $('#btnDownloadReport')?.addEventListener('click', () => {
    if (!currentJobId) return utils.alert('尚未執行清洗任務', 'warning');
    window.location.href = `/api/download/report/${currentJobId}`;
  });

  // 匯出 XLSX
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

  // 預覽功能
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

  function validateCancerDateValue(value, fieldName) {
    const dateText = normalizeDateInputValue(value);

    if (dateText === '') {
      return null;
    }

    if (dateText === '00000000' || dateText === '99999999') {
      return null;
    }

    if (!/^\d+$/.test(dateText)) {
      return `${fieldName}：日期只能輸入數字`;
    }

    if (dateText.length > 8) {
      return `${fieldName}：日期超過 8 位數，請輸入 YYYYMMDD`;
    }

    if (dateText.length < 8) {
      return `${fieldName}：日期不足 8 位數，請輸入 YYYYMMDD`;
    }

    const year = Number(dateText.slice(0, 4));
    const month = Number(dateText.slice(4, 6));
    const day = Number(dateText.slice(6, 8));

    if (month < 1 || month > 12) {
      return `${fieldName}：月份輸入錯誤，須介於 1 到 12`;
    }

    const isLeapYear =
      (year % 4 === 0 && year % 100 !== 0) ||
      (year % 400 === 0);

    const daysInMonth = [31, isLeapYear ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const maxDay = daysInMonth[month - 1];

    if (day < 1 || day > maxDay) {
      if (month === 2) {
        return `${fieldName}：${year} 年 2 月最多只有 ${maxDay} 天，請修正日期`;
      }

      return `${fieldName}：${month} 月最多只有 ${maxDay} 天，請修正日期`;
    }

    return null;
  }

  // 日期邏輯錯誤線上修正
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.code !== 'NumpadEnter') return;
    if (e.repeat) return;

    const control = e.target.closest('.date-fix-input, .date-special-select, .date-special-picker');
    if (!control) return;

    e.preventDefault();

    const tr = control.closest('tr');
    const btn = tr?.querySelector('.btnSaveDateFix');

    if (!btn || btn.disabled) return;

    btn.click();
  });

  document.addEventListener('click', async (e) => {
    const btn = e.target.closest('.btnSaveDateFix');
    if (!btn || !currentJobId) return;

    const tr = btn.closest('tr');
    const rowIndex = Number(tr.dataset.rowIndex);

    const updates = {};
    const validationErrors = [];

    tr.querySelectorAll('.date-fix-input').forEach(input => {
      const fieldName = input.dataset.field;
      const manualInput = input.closest('.d-flex')?.querySelector('.date-special-select');
      const value = normalizeDateInputValue(manualInput?.value) || normalizeDateInputValue(input.value);

      const errorMessage = validateCancerDateValue(value, fieldName);

      if (errorMessage) {
        validationErrors.push(errorMessage);
      }

      updates[fieldName] = value;
    });

    if (validationErrors.length > 0) {
      utils.alert(validationErrors.join('<br>'), 'error');
      return;
    }

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    try {
      const res = await fetch('/api/date_errors/update', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          job_id: currentJobId,
          row_index: rowIndex,
          updates: updates
        })
      });

      const text = await res.text();
      let data;

      try {
        data = JSON.parse(text);
      } catch (err) {
        console.error('後端回傳的不是 JSON：', text);
        throw new Error('後端回傳不是 JSON，請查看 Flask 終端機錯誤訊息');
      }

      if (!res.ok || !data.ok) {
        throw new Error(data.error || '修正失敗');
      }

      const s = data.stats || {};
      if ($('#kpiTotal')) $('#kpiTotal').textContent = (s.total ?? 0).toLocaleString();
      if ($('#kpiPassed')) $('#kpiPassed').textContent = (s.passed ?? 0).toLocaleString();
      if ($('#kpiError')) $('#kpiError').textContent = (s.error ?? 0).toLocaleString();
      if ($('#stat-completeness')) $('#stat-completeness').textContent = `${((s.completeness ?? 0) * 100).toFixed(1)}%`;
      if ($('#stat-correctness')) $('#stat-correctness').textContent = `${((s.correctness ?? 0) * 100).toFixed(1)}%`;
      if ($('#stat-consistency')) $('#stat-consistency').textContent = `${((s.consistency ?? 0) * 100).toFixed(1)}%`;
      if ($('#stat-dqi')) $('#stat-dqi').textContent = `${(s.dqi ?? 0).toFixed(2)}%`;

      const analysis = data.analysis || {};
      const byField = analysis.by_field || [];
      const byType = analysis.by_type || [];

      const fieldWrap = $('#fieldAnalysisContent');
      const fieldEmpty = $('#fieldAnalysisEmpty');
      const fieldTbody = $('#analysisByField tbody');

      if (fieldWrap && fieldEmpty && fieldTbody) {
        if (byField.length > 0) {
          fieldWrap.hidden = false;
          fieldEmpty.hidden = true;
          fieldTbody.innerHTML = byField.map(r => `
            <tr>
              <td>${escapeHtml(r.name)}</td>
              <td><span class="badge-soft gray">${escapeHtml(r.format || '—')}</span></td>
              <td style="text-align:right;">${r.errors ?? 0}</td>
            </tr>
          `).join('');
        } else {
          fieldWrap.hidden = true;
          fieldEmpty.hidden = false;
          fieldTbody.innerHTML = '';
        }
      }

      const analysisContent = $('#analysisContent');
      const analysisEmpty = $('#analysisEmpty');
      const typeTbody = $('#analysisByType tbody');

      if (analysisContent && analysisEmpty && typeTbody) {
        analysisContent.hidden = false;
        analysisEmpty.hidden = true;
        typeTbody.innerHTML = byType.map(r => {
          let bgClass = '';
          if (r.type.startsWith('A:')) bgClass = 'bg-warning bg-opacity-10';
          else if (r.type.startsWith('B:')) bgClass = 'bg-danger bg-opacity-10';
          else if (r.type.startsWith('C:')) bgClass = 'bg-info bg-opacity-10';

          return `
            <tr class="${bgClass} text-dark">
              <td>${escapeHtml(r.type)}</td>
              <td style="text-align:right;">${r.count ?? 0}</td>
              <td style="text-align:right;">${escapeHtml(r.ratio ?? '—')}</td>
            </tr>
          `;
        }).join('');
      }

      const dateErrorCount = data.date_error_count || 0;
      const limit = data.date_error_limit || 3;
      const alertContainer = $('#cleaningAlertContainer');

      if (alertContainer) {
        if (dateErrorCount > 0) {
          alertContainer.innerHTML = `
            <div class="alert alert-danger border shadow-sm mt-3 d-flex align-items-center justify-content-between" role="alert">

              <div class="d-flex align-items-center">
                <i class="bi bi-exclamation-triangle-fill me-2"></i>

                <span>過多日期邏輯錯誤剩下 <strong>${dateErrorCount}</strong> 筆，請繼續修正。</span>
              </div>

              <button class="btn btn-sm btn-danger ms-3" type="button" id="btnShowDateEditor">
                <i class="bi bi-pencil-square"></i> 繼續修正錯誤資料
              </button>

            </div>
          `;
        } else {
          alertContainer.innerHTML = `
            <div class="alert alert-success border shadow-sm mt-3" role="alert">
              <i class="bi bi-check-circle-fill me-2"></i>
                過多的日期邏輯錯誤已修改完成，可繼續資料清洗作業。
            </div>
          `;
        }
      }

      renderDateErrorEditor(data.date_errors || [], limit);

    } catch (err) {
      utils.alert(err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.innerHTML = '儲存';
    }
  });

  document.addEventListener('change', (e) => {
    const control = e.target.closest('.date-fix-input, .date-special-select, .date-special-picker');
    if (!control) return;

    syncDateControls(control);
  });

  document.addEventListener('input', (e) => {
    const manualInput = e.target.closest('.date-special-select');
    if (!manualInput) return;

    syncDateControls(manualInput);
  });

  document.addEventListener('click', (e) => {
    const btn = e.target.closest('#btnShowDateEditor');
    if (!btn) return;

    document.getElementById('dateErrorPanel')?.scrollIntoView({
      behavior: 'smooth',
      block: 'start'
    });
  });

})();
