(function () {
  'use strict';

  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));

  async function fetchJSON(url, options = {}) {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    return res.json();
  }

  // ---------- Stepper ----------
  function setStep(n) {
    $$('#stepper .step').forEach((el) => {
      const s = Number(el.dataset.step);
      el.classList.toggle('done', s < n);
      el.classList.toggle('active', s === n);
    });
  }

  // ---------- Format CRUD ----------
document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('formatModal');
  const btnAdd = document.getElementById('btnAddFormat');
  const btnSave = document.getElementById('btnSaveFormat');
  const closeBtns = document.querySelectorAll('[data-close]');

  // 表單輸入框
  const fmtIdInput = document.getElementById('fmtId');
  const fmtNameInput = document.getElementById('fmtName');
  const fmtVersionInput = document.getElementById('fmtVersion');
  const fmtUpdatedInput = document.getElementById('fmtUpdated');
  const openModal = () => modal.removeAttribute('hidden');
  const closeModal = () => modal.setAttribute('hidden', '');
  closeBtns.forEach(btn => btn.addEventListener('click', closeModal));

  // 新增
  btnAdd.addEventListener('click', () => {
    document.getElementById('modalTitle').textContent = '新增參考資料格式';
    fmtIdInput.value = '';
    fmtNameInput.value = '';
    fmtVersionInput.value = '';
    fmtUpdatedInput.value = '';
    openModal();
  });

  const table = document.getElementById('formatsTable');
  table.addEventListener('click', async (e) => {
    const btn = e.target.closest('button');
    if (!btn) return;

    const action = btn.dataset.action;
    const tr = btn.closest('tr');
    if (!tr) return;
    const id = tr.dataset.id;
    const name = tr.dataset.name;
    const version = tr.dataset.version;
    const updated = tr.dataset.updated;

    if (action === 'edit') {
      document.getElementById('modalTitle').textContent = '編輯參考資料格式';
      fmtIdInput.value = id;
      fmtNameInput.value = name;
      fmtVersionInput.value = version;
      fmtUpdatedInput.value = updated;
      openModal();
    } 

    else if (action === 'delete') {
      if (confirm(`確定要刪除「${name}」嗎？`)) {
        try {
          const res = await fetch(`/api/formats/${id}`, {
            method: 'DELETE',
          });
          const data = await res.json();
          if (data.ok) {
            alert('刪除成功');
            location.reload(); 
          } 
          else {
            alert(data.message || '刪除失敗');
          }
        } catch (err) {
          console.error('Error:', err);
          alert('Connect faild');
        }
      }
    }
  });

  // 儲存
  btnSave.addEventListener('click', async () => {
    const id = fmtIdInput.value;
    const payload = {name:fmtNameInput.value, version:fmtVersionInput.value, updated:fmtUpdatedInput.value};
    const isEdit = id !== '';
    const url = isEdit ? `/api/formats/${id}` : '/api/formats';
    const method = isEdit ? 'PUT' : 'POST';

    if (!payload.name || !payload.version) {
      alert('資料須填寫完畢！');
      return;
    }

    try {
      const res = await fetch(url, {
        method: method,
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
      });
      
      const data = await res.json();
      if (data.ok) {
        alert(isEdit ? '更新成功' : '新增成功');
        closeModal();
        location.reload();
      } 
      else {
        alert(data.message || '儲存失敗');
      }
    } catch (err) {
      console.error('Error:', err);
      alert('Connect faild');
    }
  });
});

// ---------- File input + drag & drop ----------
const fileInput  = $('#fileInput');
const fileChosen = $('#fileChosen');
const fileName   = $('#fileName');
const dropZone   = $('#dropZone');

function updateFilePreview() {
  const f = fileInput.files?.[0];

  if (f) {
    fileName.textContent = `${f.name} · ${(f.size / 1024).toFixed(1)} KB`;
    fileChosen.hidden = false;
  } else {
    fileChosen.hidden = true;
  }
}

fileInput.addEventListener('change', updateFilePreview);

// ---------- Drag & Drop ----------
['dragenter', 'dragover'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.add('dragover');
  })
);

['dragleave', 'drop'].forEach(evt =>
  dropZone.addEventListener(evt, e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
  })
);

dropZone.addEventListener('drop', e => {
  const f = e.dataTransfer?.files?.[0];

  if (f) {
    const dt = new DataTransfer();
    dt.items.add(f);
    fileInput.files = dt.files;
    updateFilePreview();
  }
});

// ---------- Reset ----------
$('#cleanForm').addEventListener('reset', () => {
  setTimeout(updateFilePreview, 10);
});

// ---------- Submit ----------
$('#cleanForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const formatId = $('#formatSelect').value;
  const file = fileInput.files?.[0];

  if (!formatId) {
    alert('請選擇參考資料格式');
    return;
  }

  if (!file) {
    alert('請選擇上傳檔案');
    return;
  }

  setStep(2);

  const formData = new FormData();
  formData.append('format_id', formatId);
  formData.append('data_file', file);

  try {
    const response = await fetch('/api/cleanJob', {
      method: 'POST',
      body: formData
    });

    const text = await response.text();
    let result;
    try {
      result = JSON.parse(text);
    } catch (e) {
      console.error("後端不是 JSON：", text);
      throw new Error("伺服器回傳格式錯誤（可能 API 錯誤或後端 error）");
    }

    if (!response.ok || !result.ok) {
      throw new Error(result.message || result.error || '清洗失敗');
    }

    renderResult(result);
    setStep(3);

  } catch (error) {
    alert(error.message);
    setStep(1);
  }
});

  // ---------- Render results (placeholders) ----------
  function renderResult(data) {
    // KPI
    const s = data.summary || {};
    $('#kpiTotal').textContent  = (s.total_rows  ?? 0).toLocaleString();
    $('#kpiPassed').textContent = (s.passed_rows ?? 0).toLocaleString();
    $('#kpiError').textContent  = (s.error_rows  ?? 0).toLocaleString();

    // Issues table
    const issues = data.issues || [];
    const issuesWrap = $('#issuesTableWrap');
    const issuesEmpty = $('#issuesEmpty');
    const tbody = $('#issuesBody');
    if (issues.length) {
      tbody.innerHTML = issues.map((row, idx) => `
        <tr>
          <td>${idx + 1}</td>
          <td>${row.case_id ?? '—'}</td>
          <td>${row.field ?? '—'}</td>
          <td><span class="badge-soft ${row.level === 'error' ? 'red' : 'amber'}">${row.type ?? '—'}</span></td>
          <td><code>${row.value ?? ''}</code></td>
          <td>${row.suggestion ?? '—'}</td>
        </tr>`).join('');
      issuesWrap.hidden = false;
      issuesEmpty.hidden = true;
    } else {
      issuesWrap.hidden = true;
      issuesEmpty.hidden = false;
    }

    // Analysis
    const analysis = data.analysis || {};
    const byField = analysis.by_field || [];
    const byType  = analysis.by_type  || [];
    if (byField.length || byType.length) {
      $('#analysisContent').hidden = false;
      $('#analysisEmpty').hidden = true;
      $('#analysisByField tbody').innerHTML = byField.map((r) => `
        <tr>
          <td>${r.name}</td>
          <td><span class="badge-soft gray">${r.format || '—'}</span></td>
          <td style="text-align:right;">${r.errors ?? 0}</td>
        </tr>`).join('');
      $('#analysisByType tbody').innerHTML = byType.map((r) => `
        <tr>
          <td>${r.type}</td>
          <td style="text-align:right;">${r.count ?? 0}</td>
          <td style="text-align:right;">${r.ratio ?? '—'}</td>
        </tr>`).join('');
    } else {
      $('#analysisContent').hidden = true;
      $('#analysisEmpty').hidden = false;
    }

    // Output fields (placeholder handling)
    const list = $('#outputFieldList');
    const fields = data.output_fields || [];
    if (fields.length) {
      list.innerHTML = fields.map((f) => `
        <label class="field-chip">
          <input type="checkbox" value="${f.key}" checked />
          ${f.label}
        </label>`).join('');
      bindChipToggle();
    } else {
      list.innerHTML = `
        <span class="field-chip disabled"><i class="bi bi-asterisk"></i> 無可輸出欄位（待後端回填）</span>`;
    }

    // Enable download / export buttons once a cleaning run has completed.
    if (window.__setResultDownloadsEnabled) {
      window.__setResultDownloadsEnabled(true);
    }
  }

  function bindChipToggle() {
    $$('#outputFieldList .field-chip input').forEach((cb) => {
      const chip = cb.closest('.field-chip');
      const sync = () => chip.classList.toggle('selected', cb.checked);
      cb.addEventListener('change', sync);
      sync();
    });
  }

  $('#btnSelectAll')?.addEventListener('click', () => {
    $$('#outputFieldList .field-chip input').forEach((cb) => { cb.checked = true; cb.dispatchEvent(new Event('change')); });
  });
  $('#btnClearAll')?.addEventListener('click', () => {
    $$('#outputFieldList .field-chip input').forEach((cb) => { cb.checked = false; cb.dispatchEvent(new Event('change')); });
  });

  // ---------- Naming scheme chip group ----------
  function syncNamingSelection() {
    $$('#namingScheme .naming-chip').forEach((chip) => {
      const input = chip.querySelector('input[type="radio"]');
      chip.classList.toggle('selected', !!input?.checked);
    });
  }
  $$('#namingScheme input[type="radio"]').forEach((r) => {
    r.addEventListener('change', syncNamingSelection);
  });
  syncNamingSelection();

  function getSelectedNaming() {
    return $('#namingScheme input[type="radio"]:checked')?.value || 'chinese';
  }

  // ---------- Result download placeholders ----------
  function bindDownloadHandler(btn, buildFilename) {
    btn?.addEventListener('click', () => {
      if (btn.disabled) return;
      // Placeholder: real export endpoint to be implemented on backend.
      alert(`即將下載：${buildFilename()}\n（後端 XLSX 匯出介接完成後將自動下載）`);
    });
  }
  bindDownloadHandler(
    $('#btnDownloadIssues'),
    () => `cleaning_issues_${new Date().toISOString().slice(0, 10)}.xlsx`
  );
  bindDownloadHandler(
    $('#btnDownloadAnalysis'),
    () => `cleaning_analysis_${new Date().toISOString().slice(0, 10)}.xlsx`
  );
  bindDownloadHandler(
    $('#btnExportXlsx'),
    () => {
      const base = ($('#outputFileName')?.value || 'cleaned_data').trim();
      const scheme = getSelectedNaming();
      return `${base}__${scheme}.xlsx`;
    }
  );
  $('#btnPreviewOutput')?.addEventListener('click', () => {
    if ($('#btnPreviewOutput').disabled) return;
    const selected = $$('#outputFieldList .field-chip input:checked').length;
    alert(`預覽：命名方案 = ${getSelectedNaming()}，勾選欄位 ${selected} 個`);
  });

  function setResultDownloadsEnabled(enabled) {
    [
      '#btnDownloadIssues',
      '#btnDownloadAnalysis',
      '#btnExportXlsx',
      '#btnPreviewOutput',
    ].forEach((sel) => {
      const el = $(sel);
      if (el) el.disabled = !enabled;
    });
  }

  // Expose so renderResult can call it
  window.__setResultDownloadsEnabled = setResultDownloadsEnabled;
})();
