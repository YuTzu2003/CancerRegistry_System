(function() {
  const cancerData = [
    {id:'All_Cancers',name:'全癌別(C00-C80)'},
    {id:'oral_group',name:'口腔癌症(含口腔、口咽、下咽)', 
        children: [
                  { id:'Oral_Cavity',name:'口腔 Oral Cavity'},
                  { id:'Oropharynx',name:'口咽 Oropharynx'},
                  { id:'Hypopharynx',name:'下咽 Hypopharynx'}]},

    {id:'Salivary_Glands',name:'主唾液腺 Salivary Glands'},
    {id:'Nasopharynx',name:'鼻咽 Nasopharynx'},
    {id:'Larynx',name:'喉部 Larynx'},
    {id:'Esophagus',name:'食道 Esophagus'},
    {id:'Stomach',name:'胃 Stomach'},
    {id:'Pancreas',name:'胰臟 Pancreas'},
    {id:'Colorectal',name:'結腸、直腸及肛門', 
        children: [
                  {id:'Colon',name:'結腸癌 Colon'},
                  {id:'Rectum',name:'直腸癌 Rectum'},
                  {id:'Anus',name:'肛門癌 Anus'}]},

    {id:'liver_group',name:'肝及肝內膽管', 
        children: [
                  {id:'Liver',name:'肝 Liver'},
                  {id:'Intrahepatic_bile_duct',name:'肝內膽管Intrahepatic bile duct'}]},
    {id:'breast',name:'乳房',
        children: [
                  {id:'Breast(Female)',name:'女性乳房 Breast(Female)'},
                  {id:'Breast(Male)',name:'男性乳癌 Breast(Male)'}]},

    {id:'lung_group',name:'肺、支氣管、氣管', 
        children: [
                  {id:'Trachea',name:'氣管' },
                  {id:'Lung',name:'肺、支氣管'}]},

    {id:'Cervix_Uteri',name:'子宮頸 Cervix Uteri'},
    {id:'Corpus_Uteri',name:'子宮體 Corpus Uteri'},
    {id:'Ovary',name:'卵巢 Ovary'},
    {id:'Prostate',name:'攝護腺 Prostate'},
    {id:'Bladder',name: '膀胱 Bladder' },
    {id:'Lymphoma',name: '惡性淋巴瘤 （Lymphoma）', 
        children: [
                  {id:'Hodgkin_lymphomahodgkin',name:'何杰金氏淋巴瘤（Hodgkin lymphoma）'},
                  {id:'Non-Hodgkin_lymphoma',name:'非何杰金氏淋巴瘤（Non-Hodgkin lymphoma）', 
                      children: [
                                {id:'B-cell_lymphoid_neoplasms',name:'B細胞淋巴系腫瘤（B-cell lymphoid neoplasms）'},
                                {id:'T/NK-cell_lymphoid_neoplasms', name: 'T/NK細胞淋巴系腫瘤（T/NK-cell lymphoid neoplasms）'},
                                {id:'Plasma_cell_neoplasms', name: '漿細胞腫瘤（Plasma cell neoplasms）'},
                                {id:'Histiocytic_and_dendritic_cell_neoplasms', name: '組織球與樹突細胞腫瘤（Histiocytic and dendritic cell neoplasms）'},
                                {id:'Malignant_lymphoma_NOS_and_others', name: '未分類及其他惡性淋巴瘤（Malignant lymphoma, NOS and others）'}]}]},

    {id:'Leukemia_and_myeloid_neoplasm',name:'白血病及骨髓瘤 (Leukemia and myeloid neoplasm)', 
        children: [
                  {id:'AML',name:'急性骨髓性白血病 (AML)' },
                  {id:'CML',name:'慢性骨髓性白血病 (CML,Only BCR-ABL1-positive)' },
                  {id:'ALL',name:'急性淋巴性白血病 (ALL)' },
                  {id:'CLL',name:'慢性淋巴性白血病 (CLL)' },
                  {id:'Acute_leukemias_of_ambiguous_lineage',name:'系統歧異不明之急性白血病 (Acute leukemias of ambiguous lineage)'},
                  {id:'Myeloproliferative_neoplasms',name:'骨髓增生性腫瘤 (Myeloproliferative neoplasms)'},
                  {id:'Myelodysplastic_syndromes',name:'骨髓發育不良症候群 (Myelodysplastic syndromes)'},
                  {id:'Acute_biphenotypic_leukemia',name:'急性雙表型白血病 (Acute biphenotypic leukemia)'},
                  {id:'Other_Leukemia',name:'其他白血病 (Other Leukemia)'},
                  {id:'Leukemia',name:'未分類白血病 (Leukemia, NOS )'}]}];

  /* ── State Management ── */
  const selectedCancers = new Set();
  const allLeafIds = [];
  const idToNode = {};

  function getLeafIds(node) {
    if (!node.children) return [node.id];
    let leaves = [];
    node.children.forEach(c => leaves.push(...getLeafIds(c)));
    return leaves;
  }
  
  function buildIndex(node) {
    idToNode[node.id] = node;
    if (node.children) node.children.forEach(buildIndex);
  }
  
  cancerData.forEach(c => {
    allLeafIds.push(...getLeafIds(c));
    buildIndex(c);
  });
  
  // Default: Select all cancers
  //allLeafIds.forEach(id => selectedCancers.add(id));
  let currentCategory = cancerData[0];

  /* ── UI Rendering ── */
  function getBadgeHtml(cat) {
    const leafIds = getLeafIds(cat);
    const selectedCount = leafIds.filter(id => selectedCancers.has(id)).length;
    
    if (selectedCount === 0) return '';
    if (selectedCount < leafIds.length) {
      return `<span class="badge bg-warning text-dark ms-2 rounded-pill">${selectedCount}</span>`;
    }
    return `<i class="bi bi-check-circle-fill text-success ms-2"></i>`;
  }

  function renderCategories() {
    const list = document.getElementById('cancerCategoryList');
    if (!list) return;
    
    let html = '';
    
    // 1. Render "不分癌別" divider header
    html += `
      <div class="list-group-item bg-light border-0 py-2 fw-bold text-secondary text-uppercase" 
           style="font-size: 11px; letter-spacing: 0.5px; cursor: default; pointer-events: none; margin-bottom: 5px;">
        不分癌別
      </div>
    `;
    
    // 2. Render "全癌別(C00-C80)" clickable item
    const allCancersCat = cancerData.find(c => c.id === 'All_Cancers');
    if (allCancersCat) {
      const isActive = currentCategory.id === allCancersCat.id;
      const cls = isActive ? 'active fw-bold text-primary bg-white' : 'text-secondary';
      const border = isActive ? '4px solid #0d6efd' : '4px solid transparent';
      html += `
        <a href="#" class="list-group-item list-group-item-action bg-transparent border-0 py-3 cat-nav-btn ${cls}" 
           style="border-left: ${border};" data-cat-id="${allCancersCat.id}">
          <div class="d-flex justify-content-between align-items-center">
            <span>${allCancersCat.name}</span>
            ${getBadgeHtml(allCancersCat)}
          </div>
        </a>
      `;
    }
    
    // 3. Render "常見癌別" divider header
    html += `
      <div class="list-group-item bg-light border-0 py-2 fw-bold text-secondary text-uppercase" 
           style="font-size: 11px; letter-spacing: 0.5px; cursor: default; pointer-events: none; margin-top: 10px; margin-bottom: 5px;">
        常見癌別
      </div>
    `;
    
    // 3. Render all other specific cancers
    cancerData.forEach(cat => {
      if (cat.id === 'All_Cancers') return;
      const isActive = currentCategory.id === cat.id;
      const cls = isActive ? 'active fw-bold text-primary bg-white' : 'text-secondary';
      const border = isActive ? '4px solid #0d6efd' : '4px solid transparent';
      
      html += `
        <a href="#" class="list-group-item list-group-item-action bg-transparent border-0 py-3 cat-nav-btn ${cls}" 
           style="border-left: ${border};" data-cat-id="${cat.id}">
          <div class="d-flex justify-content-between align-items-center">
            <span>${cat.name}</span>
            ${getBadgeHtml(cat)}
          </div>
        </a>
      `;
    });
    
    list.innerHTML = html;
  }

  function renderNodesHTML(nodes, padding) {
    return nodes.map(node => {
      const isGroup = !!node.children;
      const leafIds = getLeafIds(node);
      const checkedCount = leafIds.filter(id => selectedCancers.has(id)).length;
      
      const isChecked = checkedCount === leafIds.length ? 'checked' : '';
      const isIndeterminate = checkedCount > 0 && checkedCount < leafIds.length ? 'data-indeterminate="true"' : '';
      
      const mt = isGroup ? 'mt-3' : '';
      const lblCls = isGroup ? 'fw-semibold text-dark border-bottom pb-1 mb-1 w-100' : 'text-secondary';
      const scale = isGroup ? 'scale(1.1)' : 'scale(1)';
      
      let html = `
        <div class="form-check mb-2 d-flex align-items-center gap-2 ${mt}" style="margin-left: ${padding}rem;">
          <input type="checkbox" class="form-check-input mt-0 chk-node" id="chk_${node.id}" 
                 data-node-id="${node.id}" style="transform: ${scale};" ${isChecked} ${isIndeterminate}>
          <label class="form-check-label ${lblCls}" for="chk_${node.id}">${node.name}</label>
        </div>
      `;
      
      if (isGroup) {
        html += renderNodesHTML(node.children, padding + 1.5);
      }
      return html;
    }).join('');
  }

  function renderDetails() {
    const container = document.getElementById('cancerDetailList');
    if (!container) return;
    
    const leaves = getLeafIds(currentCategory);
    const checkedCount = leaves.filter(id => selectedCancers.has(id)).length;
    const isChecked = checkedCount === leaves.length ? 'checked' : '';
    const isIndeterminate = checkedCount > 0 && checkedCount < leaves.length ? 'data-indeterminate="true"' : '';
    
    let html = `
      <div class="form-check mb-3 pb-2 border-bottom d-flex align-items-center gap-2">
        <input type="checkbox" class="form-check-input mt-0 chk-node" id="chk_cat_${currentCategory.id}" 
               data-node-id="${currentCategory.id}" style="transform: scale(1.2);" ${isChecked} ${isIndeterminate}>
        <label class="form-check-label fw-bold text-dark fs-6" for="chk_cat_${currentCategory.id}">
          ${currentCategory.name} (全選)
        </label>
      </div>
    `;
    
    if (currentCategory.children) {
      html += renderNodesHTML(currentCategory.children, 0);
    }
    
    container.innerHTML = html;
    
    // Checkboxes natively don't support indeterminate attribute in HTML, must be set via JS
    container.querySelectorAll('input[data-indeterminate="true"]').forEach(el => {
      el.indeterminate = true;
    });
  }

  function updateStatus() {
    const status = document.getElementById('cancerPickerStatus');
    const specificSelectedCount = Array.from(selectedCancers).filter(id => id !== 'All_Cancers').length;
    const totalSpecificCount = allLeafIds.filter(id => id !== 'All_Cancers').length;
    
    if (status) {
      status.innerHTML = `<i class="bi bi-info-circle me-1"></i>已選取：<span class="fw-bold text-primary">${specificSelectedCount}</span> / ${totalSpecificCount} 項癌別`;
    }
    
    const btnText = document.getElementById('btnCancerPickerText');
    if (btnText) {
      if (selectedCancers.has('All_Cancers') || (specificSelectedCount === totalSpecificCount && totalSpecificCount > 0)) {
        btnText.textContent = '不分癌別 全癌別(C00-C80)';
      } else if (specificSelectedCount === 0) {
        btnText.textContent = '— 尚未選擇癌別 —';
      } else {
        btnText.innerHTML = `<span class="text-primary fw-bold">已選取 ${specificSelectedCount} 項</span>`;
      }
    }
  }

  /* ── Event Listeners (Delegation) ── */
  document.getElementById('cancerCategoryList')?.addEventListener('click', (e) => {
    const btn = e.target.closest('.cat-nav-btn');
    if (!btn) return;
    e.preventDefault();
    
    currentCategory = idToNode[btn.getAttribute('data-cat-id')];
    renderCategories();
    renderDetails();
  });
  
  document.getElementById('cancerDetailList')?.addEventListener('change', (e) => {
    if (!e.target.classList.contains('chk-node')) return;
    
    const node = idToNode[e.target.getAttribute('data-node-id')];
    const isChecked = e.target.checked;
    
    if (node.id === 'All_Cancers') {
      // Toggle all cancers
      if (isChecked) {
        allLeafIds.forEach(id => selectedCancers.add(id));
      } else {
        selectedCancers.clear();
      }
    } else {
      // Toggle specific cancer
      getLeafIds(node).forEach(id => {
        if (isChecked) selectedCancers.add(id);
        else selectedCancers.delete(id);
      });
      
      // Check if all other specific leaf IDs are selected
      const otherLeaves = allLeafIds.filter(id => id !== 'All_Cancers');
      const allOthersChecked = otherLeaves.every(id => selectedCancers.has(id));
      if (allOthersChecked) {
        selectedCancers.add('All_Cancers');
      } else {
        selectedCancers.delete('All_Cancers');
      }
    }
    
    renderCategories();
    renderDetails();
    updateStatus();
  });

  document.getElementById('btnConfirmCancer')?.addEventListener('click', () => {
    const modalEl = document.getElementById('cancerPickerModal');
    if (modalEl) {
      const modalInstance = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      modalInstance.hide();
    }
  });
  
  /* ── 我的最愛預設範本邏輯 ── */
  let userPresets = [];

  function loadPresets() {
    const select = document.getElementById('favPresetSelect');
    if (!select) return;

    fetch('/api/favorites')
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          userPresets = data.favorites || [];
          populatePresetSelect();
        } else {
          console.error("無法載入最愛範本: " + data.error);
          select.innerHTML = '<option value="">— 載入失敗 —</option>';
        }
      })
      .catch(err => {
        console.error("載入最愛範本出錯", err);
        select.innerHTML = '<option value="">— 載入失敗 —</option>';
      });
  }

  function populatePresetSelect() {
    const select = document.getElementById('favPresetSelect');
    if (!select) return;

    if (userPresets.length === 0) {
      select.innerHTML = '<option value="">— 尚無已儲存的範本 —</option>';
      togglePresetActionButtons(false);
      return;
    }

    let html = '<option value="">— 選擇最愛範本套用 —</option>';
    userPresets.forEach(preset => {
      html += `<option value="${preset.id}">${preset.name}</option>`;
    });
    select.innerHTML = html;
    togglePresetActionButtons(false);
  }

  function togglePresetActionButtons(show) {
    const btnRename = document.getElementById('btnRenamePreset');
    const btnDelete = document.getElementById('btnDeletePreset');
    if (btnRename && btnDelete) {
      const displayStyle = show ? 'inline-block' : 'none';
      btnRename.style.display = displayStyle;
      btnDelete.style.display = displayStyle;
    }
  }

  // 套用範本
  document.getElementById('favPresetSelect')?.addEventListener('change', function(e) {
    const presetId = parseInt(e.target.value, 10);
    if (!presetId) {
      togglePresetActionButtons(false);
      return;
    }

    const preset = userPresets.find(p => p.id === presetId);
    if (!preset) return;

    // 1. 設定性態碼
    const behaviorSelect = document.getElementById('filterBehavior');
    if (behaviorSelect) {
      behaviorSelect.value = preset.behavior;
    }

    // 2. 套用癌別
    selectedCancers.clear();
    if (preset.cancers && preset.cancers.length > 0) {
      preset.cancers.forEach(id => selectedCancers.add(id));
    }

    // 3. 更新介面
    renderCategories();
    renderDetails();
    updateStatus();
    togglePresetActionButtons(true);
  });

  // 新增範本
  document.getElementById('btnSavePreset')?.addEventListener('click', function() {
    const behaviorSelect = document.getElementById('filterBehavior');
    const behavior = behaviorSelect ? behaviorSelect.value : 'all';
    const cancers = Array.from(selectedCancers);

    if (cancers.length === 0) {
      Swal.fire({ icon: 'warning', title: '請先選擇癌別', text: '最愛範本必須包含至少一項癌別設定。', confirmButtonColor: '#2563eb' });
      return;
    }

    Swal.fire({
      title: '將目前條件加入最愛',
      input: 'text',
      inputPlaceholder: '請輸入範本名稱（例如：口鼻、大腸分析等）',
      showCancelButton: true,
      confirmButtonText: '儲存',
      cancelButtonText: '取消',
      confirmButtonColor: '#2563eb',
      inputValidator: (value) => {
        if (!value || !value.trim()) {
          return '範本名稱不能為空！';
        }
        if (userPresets.some(p => p.name === value.trim())) {
          return '已存在相同名稱的範本！';
        }
      }
    }).then(result => {
      if (result.isConfirmed) {
        const name = result.value.trim();
        fetch('/api/favorites', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, behavior, cancers })
        })
        .then(r => r.json())
        .then(data => {
          if (data.ok) {
            Swal.fire({ icon: 'success', title: '儲存成功', text: `範本「${name}」已加入我的最愛。`, confirmButtonColor: '#2563eb' });
            loadPresets();
          } else {
            Swal.fire({ icon: 'error', title: '儲存失敗', text: data.error || '未知錯誤', confirmButtonColor: '#2563eb' });
          }
        })
        .catch(err => {
          Swal.fire({ icon: 'error', title: '儲存失敗', text: '網路或伺服器出錯。', confirmButtonColor: '#2563eb' });
        });
      }
    });
  });

  // 重新命名範本
  document.getElementById('btnRenamePreset')?.addEventListener('click', function() {
    const select = document.getElementById('favPresetSelect');
    const presetId = parseInt(select ? select.value : '', 10);
    if (!presetId) return;

    const preset = userPresets.find(p => p.id === presetId);
    if (!preset) return;

    Swal.fire({
      title: '重新命名最愛範本',
      input: 'text',
      inputValue: preset.name,
      inputPlaceholder: '請輸入新的範本名稱',
      showCancelButton: true,
      confirmButtonText: '修改',
      cancelButtonText: '取消',
      confirmButtonColor: '#2563eb',
      inputValidator: (value) => {
        if (!value || !value.trim()) {
          return '範本名稱不能為空！';
        }
        if (userPresets.some(p => p.name === value.trim() && p.id !== presetId)) {
          return '已存在相同名稱的範本！';
        }
      }
    }).then(result => {
      if (result.isConfirmed) {
        const name = result.value.trim();
        fetch(`/api/favorites/${presetId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name })
        })
        .then(r => r.json())
        .then(data => {
          if (data.ok) {
            Swal.fire({ icon: 'success', title: '修改成功', text: `已重新命名為「${name}」。`, confirmButtonColor: '#2563eb' });
            fetch('/api/favorites')
              .then(r => r.json())
              .then(data => {
                if (data.ok) {
                  userPresets = data.favorites || [];
                  populatePresetSelect();
                  // 重新選取該項目
                  const newSelect = document.getElementById('favPresetSelect');
                  if (newSelect) {
                    newSelect.value = presetId;
                    togglePresetActionButtons(true);
                  }
                }
              });
          } else {
            Swal.fire({ icon: 'error', title: '修改失敗', text: data.error || '未知錯誤', confirmButtonColor: '#2563eb' });
          }
        })
        .catch(err => {
          Swal.fire({ icon: 'error', title: '修改失敗', text: '網路或伺服器出錯。', confirmButtonColor: '#2563eb' });
        });
      }
    });
  });

  // 刪除範本
  document.getElementById('btnDeletePreset')?.addEventListener('click', function() {
    const select = document.getElementById('favPresetSelect');
    const presetId = parseInt(select ? select.value : '', 10);
    if (!presetId) return;

    const preset = userPresets.find(p => p.id === presetId);
    if (!preset) return;

    Swal.fire({
      title: '確定刪除此最愛範本？',
      text: `將刪除「${preset.name}」範本`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: '刪除',
      cancelButtonText: '取消',
      confirmButtonColor: '#dc2626',
      cancelButtonColor: '#6c757d'
    }).then(result => {
      if (result.isConfirmed) {
        fetch(`/api/favorites/${presetId}`, {
          method: 'DELETE'
        })
        .then(r => r.json())
        .then(data => {
          if (data.ok) {
            Swal.fire({ icon: 'success', title: '已刪除', text: `範本「${preset.name}」已被刪除。`, confirmButtonColor: '#2563eb' });
            loadPresets();
          } else {
            Swal.fire({ icon: 'error', title: '刪除失敗', text: data.error || '未知錯誤', confirmButtonColor: '#2563eb' });
          }
        })
        .catch(err => {
          Swal.fire({ icon: 'error', title: '刪除失敗', text: '網路或伺服器出錯。', confirmButtonColor: '#2563eb' });
        });
      }
    });
  });

  // 載入我的最愛列表
  loadPresets();

  // 重置按鈕邏輯
  document.getElementById('btnResetFilters')?.addEventListener('click', function() {
    // 1. 性態碼恢復預設
    const behaviorSelect = document.getElementById('filterBehavior');
    if (behaviorSelect) behaviorSelect.value = 'all';

    // 2. 清空年度輸入框
    const yearStart = document.getElementById('filterYearStart');
    const yearEnd = document.getElementById('filterYearEnd');
    if (yearStart) yearStart.value = '';
    if (yearEnd) yearEnd.value = '';

    // 3. 清空最愛選單並隱藏操作按鈕
    const presetSelect = document.getElementById('favPresetSelect');
    if (presetSelect) presetSelect.value = '';
    togglePresetActionButtons(false);

    // 4. 清空已選癌別
    selectedCancers.clear();

    // 5. 重新渲染畫面
    renderCategories();
    renderDetails();
    updateStatus();
  });

  // Initialize
  renderCategories();
  renderDetails();
  updateStatus();
})();

/* ── Dashboard Upload (Admin only) ─────────────────────── */
(function() {
  const form = document.getElementById('dashUploadForm');
  const fileInput = document.getElementById('dashFileInput');
  
  if (!form || !fileInput) return;

  form.addEventListener('submit', function(e) {
    e.preventDefault();
    if (!fileInput.files.length) {
      Swal.fire({ icon: 'warning', title: '請先選擇檔案', allowOutsideClick: false, confirmButtonColor: '#2563eb' });
      return;
    }
    
    const ext = fileInput.files[0].name.split('.').pop().toLowerCase();
    if (ext !== 'xls' && ext !== 'xlsx') {
      Swal.fire({ icon: 'error', title: '格式錯誤', text: '僅接受 .xls 或 .xlsx 檔案', allowOutsideClick: false, confirmButtonColor: '#2563eb' });
      return;
    }
    
    const btn = document.getElementById('btnDashUpload');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> 上傳中…';
    
    fetch('/dashboard/upload', { method: 'POST', body: new FormData(form) })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          Swal.fire({ icon: 'success', title: '上傳成功', text: `${data.filename} 已儲存`, allowOutsideClick: false, confirmButtonColor: '#2563eb' })
            .then(() => location.reload());
        } else {
          Swal.fire({ icon: 'error', title: '上傳失敗', text: data.error || '未知錯誤', allowOutsideClick: false, confirmButtonColor: '#2563eb' });
        }
      })
      .catch(() => {
        Swal.fire({ icon: 'error', title: '上傳失敗', allowOutsideClick: false, confirmButtonColor: '#2563eb' });
      })
      .finally(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-upload"></i> 上傳檔案';
      });
  });

  /* Delete file */
  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-del-file');
    if (!btn) return;
    
    const name = btn.dataset.name;
    Swal.fire({
      title: '確定刪除？',
      text: `將刪除 ${name}`,
      icon: 'warning',
      showCancelButton: true,
      allowOutsideClick: false,
      confirmButtonColor: '#dc2626',
      cancelButtonText: '取消',
      confirmButtonText: '刪除'
    }).then(result => {
      if (!result.isConfirmed) return;
      
      fetch('/dashboard/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: name })
      })
      .then(r => r.json())
      .then(data => {
        if (data.ok) {
          Swal.fire({ icon: 'success', title: '已刪除', confirmButtonColor: '#2563eb' })
            .then(() => location.reload());
        } else {
          Swal.fire({ icon: 'error', title: '刪除失敗', text: data.error, confirmButtonColor: '#2563eb' });
        }
      });
    });
  });
})();

/* ── Analysis Items Checkbox Logic ── */
(function() {
  const table = document.getElementById('analysisItemsTable');
  if (!table) return;

  // Handle Group Checkbox (Check all items under it)
  table.querySelectorAll('.group-checkbox').forEach(groupChk => {
    groupChk.addEventListener('change', function() {
      const groupName = this.dataset.group;
      const isChecked = this.checked;
      
      // Toggle selected class on group checkbox
      const groupChip = this.closest('.field-chip') || this.closest('.naming-chip');
      if (groupChip) groupChip.classList.toggle('selected', isChecked);
      
      // Select all item checkboxes belonging to this group
      const items = table.querySelectorAll(`.item-checkbox[data-parent="${groupName}"]`);
      items.forEach(item => {
        item.checked = isChecked;
        const chip = item.closest('.field-chip') || item.closest('.naming-chip');
        if (chip) chip.classList.toggle('selected', isChecked);
      });

      // Toggle visibility of sub-items container
      const subItemsContainer = document.getElementById(`subItems-${groupName}`);
      if (subItemsContainer) {
        if (isChecked) {
          subItemsContainer.classList.remove('d-none');
        } else {
          subItemsContainer.classList.add('d-none');
        }
      }
    });
  });

  // Handle Item Checkbox (Update parent group)
  table.querySelectorAll('.item-checkbox').forEach(itemChk => {
    itemChk.addEventListener('change', function() {
      const chip = this.closest('.field-chip') || this.closest('.naming-chip');
      if (chip) chip.classList.toggle('selected', this.checked);

      const parentGroup = this.dataset.parent;
      updateGroupCheckbox(parentGroup);
    });
  });

  function updateGroupCheckbox(groupName) {
    const groupChk = table.querySelector(`.group-checkbox[data-group="${groupName}"]`);
    if (!groupChk) return;
    
    const items = table.querySelectorAll(`.item-checkbox[data-parent="${groupName}"]`);
    const allChecked = items.length > 0 && Array.from(items).every(item => item.checked);
    const someChecked = items.length > 0 && Array.from(items).some(item => item.checked);
    
    groupChk.checked = allChecked;
    groupChk.indeterminate = someChecked && !allChecked;
    
    const chip = groupChk.closest('.field-chip') || groupChk.closest('.naming-chip');
    if (chip) chip.classList.toggle('selected', someChecked);

    // Toggle visibility of sub-items container
    const subItemsContainer = document.getElementById(`subItems-${groupName}`);
    if (subItemsContainer) {
      if (someChecked) {
        subItemsContainer.classList.remove('d-none');
      } else {
        subItemsContainer.classList.add('d-none');
      }
    }
  }
})();
// ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------