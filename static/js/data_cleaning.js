/* ============================================================
   資料清洗模組 - 前端互動
   ============================================================ */
(function () {
  'use strict';

  // ---------- Helpers ----------
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
  const modal    = $('#formatModal');
  const modalTitle = $('#modalTitle');
  const fmtForm  = $('#formatForm');
  const fields   = {
    id: $('#fmtId'),
    name: $('#fmtName'),
    version: $('#fmtVersion'),
    updated: $('#fmtUpdated'),
  };

  function openModal(title, data) {
    modalTitle.textContent = title;
    fields.id.value      = data?.id || '';
    fields.name.value    = data?.name || '';
    fields.version.value = data?.version || '';
    fields.updated.value = data?.updated || '';
    modal.hidden = false;
    // Focus the first field for quick entry
    setTimeout(() => fields.name.focus(), 30);
  }
  function closeModal() { modal.hidden = true; }

  $('#btnAddFormat')?.addEventListener('click', () => openModal('新增參考資料格式', null));
  modal.addEventListener('click', (e) => {
    if (e.target.matches('[data-close]') || e.target === modal) closeModal();
  });

  // Table delegation: edit + delete
  $('#formatsTable tbody').addEventListener('click', async (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const tr = btn.closest('tr');
    const id = tr.dataset.id;
    const action = btn.dataset.action;

    if (action === 'edit') {
      openModal('編輯參考資料格式', {
        id,
        name:    tr.dataset.name,
        version: tr.dataset.version,
        updated: tr.dataset.updated,
      });
    } else if (action === 'delete') {
      if (!confirm(`確定要刪除格式「${tr.dataset.name}」？`)) return;
      try {
        await fetchJSON(`/api/formats/${id}`, { method: 'DELETE' });
        location.reload();
      } catch (err) {
        alert('刪除失敗：' + err.message);
      }
    }
  });

  $('#btnSaveFormat')?.addEventListener('click', async () => {
    if (!fmtForm.reportValidity()) return;
    const payload = {
      name:    fields.name.value,
      version: fields.version.value,
      updated: fields.updated.value,
    };
    try {
      if (fields.id.value) {
        await fetchJSON(`/api/formats/${fields.id.value}`, {
          method: 'PUT',
          body: JSON.stringify(payload),
        });
      } else {
        await fetchJSON('/api/formats', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
      }
      location.reload();
    } catch (err) {
      alert('儲存失敗：' + err.message);
    }
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

  ['dragenter', 'dragover'].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.add('dragover');
    })
  );
  ['dragleave', 'drop'].forEach((evt) =>
    dropZone.addEventListener(evt, (e) => {
      e.preventDefault();
      dropZone.classList.remove('dragover');
    })
  );
  dropZone.addEventListener('drop', (e) => {
    const f = e.dataTransfer?.files?.[0];
    if (f) {
      const dt = new DataTransfer();
      dt.items.add(f);
      fileInput.files = dt.files;
      updateFilePreview();
    }
  });

  // ---------- Submit cleaning ----------
  $('#cleanForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const fmt  = $('#formatSelect').value;
    const file = fileInput.files?.[0];
    if (!fmt)  { alert('請選擇參考資料格式'); return; }
    if (!file) { alert('請選擇上傳檔案');     return; }

    setStep(2);

    const fd = new FormData();
    fd.append('format_id', fmt);
    fd.append('data_file', file);

    try {
      const res = await fetch('/api/clean', { method: 'POST', body: fd });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || '清洗失敗');
      renderResult(data);
      setStep(3);
    } catch (err) {
      alert(err.message);
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
