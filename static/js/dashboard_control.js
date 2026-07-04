/* ==========================================
   癌別選擇與篩選邏輯
   ========================================== */
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
                  {id:'colon',name:'結腸癌 Colon'},
                  {id:'rectum',name:'直腸癌 Rectum'},
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

  /* ── 狀態管理與介面更新邏輯 ── */
  const selectedCancers = new Set();
  window.selectedCancers = selectedCancers;
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

  let currentCategory = cancerData[0];
  
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
    html += `<div class="list-group-item bg-light border-0 py-2 fw-bold text-secondary text-uppercase" style="font-size: 11px; letter-spacing: 0.5px; cursor: default; pointer-events: none; margin-bottom: 5px;">不分癌別</div>`;
    
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
    
    html += `<div class="list-group-item bg-light border-0 py-2 fw-bold text-secondary text-uppercase" style="font-size: 11px; letter-spacing: 0.5px; cursor: default; pointer-events: none; margin-top: 10px; margin-bottom: 5px;">常見癌別</div>`;
    
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
    
    container.querySelectorAll('input[data-indeterminate="true"]').forEach(el => {
      el.indeterminate = true;
    });
  }

  function updateStatus() {
    const status = document.getElementById('cancerPickerStatus');
    const specificSelectedCount = Array.from(selectedCancers).filter(id => id !== 'All_Cancers').length;
    const totalSpecificCount = allLeafIds.filter(id => id !== 'All_Cancers').length;
    window.dashboardSelectedCancerIds = Array.from(selectedCancers);
    
    const getChineseCancerName = (name) => {
      return String(name || '').replace(/\s*\([^)]*\)/g, '').replace(/\s+[A-Za-z][A-Za-z0-9\s,./&+-]*$/g, '').trim();
    };

    const getSelectedCancerTitle = () => {
      if (selectedCancers.has('All_Cancers') || (specificSelectedCount === totalSpecificCount && totalSpecificCount > 0)) {
        return '全癌別';
      }

      const names = [];
      cancerData.forEach(category => {
        if (category.id === 'All_Cancers') return;

        const leafIds = getLeafIds(category);
        const selectedLeafIds = leafIds.filter(id => selectedCancers.has(id));
        if (selectedLeafIds.length === 0) return;

        if (selectedLeafIds.length === leafIds.length && leafIds.length > 1) {
          names.push(getChineseCancerName(category.name));
          return;
        }

        selectedLeafIds.forEach(id => {
          if (idToNode[id]) names.push(getChineseCancerName(idToNode[id].name));
        });
      });

      return names.length ? names.join('、') : 'XX';
    };
    
    if (status) {
      status.innerHTML = `<i class="bi bi-info-circle me-1"></i>已選取：<span class="fw-bold text-primary">${specificSelectedCount}</span> / ${totalSpecificCount} 項癌別`;
    }
    
    const btnText = document.getElementById('btnCancerPickerText');
    if (btnText) {
      if (selectedCancers.has('All_Cancers') || (specificSelectedCount === totalSpecificCount && totalSpecificCount > 0)) {
        btnText.textContent = '不分癌別 全癌別(C00-C80)';
        window.dashboardSelectedCancerTitle = '全癌別';
      } else if (specificSelectedCount === 0) {
        btnText.textContent = '— 尚未選擇癌別 —';
        window.dashboardSelectedCancerTitle = 'XX';
      } else {
        btnText.innerHTML = `<span class="text-primary fw-bold">已選取 ${specificSelectedCount} 項</span>`;
        window.dashboardSelectedCancerTitle = getSelectedCancerTitle();
      }
    }
    
    if (typeof updateSummary === 'function') {
      updateSummary();
    }
  }

  /* ── 癌別選擇事件綁定 ── */
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
      if (isChecked) {
        allLeafIds.forEach(id => selectedCancers.add(id));
      } else {
        selectedCancers.clear();
      }
    } else {
      getLeafIds(node).forEach(id => {
        if (isChecked) selectedCancers.add(id);
        else selectedCancers.delete(id);
      });
      
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
          select.innerHTML = '<option value="">— 載入失敗 —</option>';
        }
      })
      .catch(err => {
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

  document.getElementById('favPresetSelect')?.addEventListener('change', function(e) {
    const presetId = parseInt(e.target.value, 10);
    if (!presetId) {
      togglePresetActionButtons(false);
      return;
    }

    const preset = userPresets.find(p => p.id === presetId);
    if (!preset) return;

    const behaviorSelect = document.getElementById('filterBehavior');
    if (behaviorSelect) {
      behaviorSelect.value = preset.behavior;
    }

    selectedCancers.clear();
    if (preset.cancers && preset.cancers.length > 0) {
      preset.cancers.forEach(id => selectedCancers.add(id));
    }

    document.querySelectorAll('input[name="mainCategoryTab"]:checked').forEach(el => {
      el.checked = false;
      el.dispatchEvent(new Event('change'));
    });
    document.querySelectorAll('.item-checkbox:checked').forEach(el => {
      el.checked = false;
      el.dispatchEvent(new Event('change'));
    });

    if (preset.main_category) {
      const mainCatIds = preset.main_category.split(',');
      mainCatIds.forEach(id => {
        const mainCat = document.getElementById(id);
        if (mainCat) {
          mainCat.checked = true;
          mainCat.dispatchEvent(new Event('change'));
        }
      });
    }
    if (preset.sub_category) {
      const subCatIds = preset.sub_category.split(',');
      subCatIds.forEach(id => {
        const subCat = document.getElementById(id);
        if (subCat) {
          subCat.checked = true;
          subCat.dispatchEvent(new Event('change'));
        }
      });
    }

    renderCategories();
    renderDetails();
    updateStatus();
    togglePresetActionButtons(true);
    checkFiltersState();
  });

  document.getElementById('btnSavePreset')?.addEventListener('click', function() {
    const behaviorSelect = document.getElementById('filterBehavior');
    const behavior = behaviorSelect ? behaviorSelect.value : 'all';
    const cancers = Array.from(selectedCancers);

    let main_category = '';
    let sub_category = '';
    
    const activeMainCats = new Set();
    document.querySelectorAll('.item-checkbox:checked').forEach(el => {
      if (el.dataset.parent) {
        let chkId = '';
        if (el.dataset.parent === 'incidence') chkId = 'chkGroupIncidence';
        else if (el.dataset.parent === 'diagnosis') chkId = 'chkGroupDiagnosis';
        else if (el.dataset.parent === 'stage') chkId = 'chkGroupStage';
        else if (el.dataset.parent === 'treatment') chkId = 'chkGroupTreatment';
        else if (el.dataset.parent === 'cross_year') chkId = 'chkGroupCrossYear';
        if (chkId) activeMainCats.add(chkId);
      }
    });
    
    const currentTab = document.querySelector('input[name="mainCategoryTab"]:checked');
    if (currentTab) activeMainCats.add(currentTab.id);
    
    if (activeMainCats.size > 0) {
      main_category = Array.from(activeMainCats).join(',');
    }
    
    const subCatEls = document.querySelectorAll('.item-checkbox:checked');
    if (subCatEls.length > 0) {
      sub_category = Array.from(subCatEls).map(el => el.id).join(',');
    }

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
          body: JSON.stringify({ name, behavior, cancers, main_category, sub_category })
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
      }
    });
  });

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
      }
    });
  });

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
      }
    });
  });
  loadPresets();

  document.getElementById('btnResetFilters')?.addEventListener('click', function() {
    window.location.reload();
  });

  /* ── 篩選欄位邏輯 ── */
  const yearStartInput = document.getElementById('filterYearStart');
  const yearEndInput = document.getElementById('filterYearEnd');
  const behaviorSelect = document.getElementById('filterBehavior');

  function checkFiltersState() {
    const ys = yearStartInput ? yearStartInput.value.trim() : '';
    const ye = yearEndInput ? yearEndInput.value.trim() : '';
    const isYearValid = ys.length === 4 && ye.length === 4;

    const isBehaviorValid = isYearValid && behaviorSelect && behaviorSelect.value !== '';

    if (behaviorSelect) {
      behaviorSelect.disabled = !isYearValid;
      if (!isYearValid) {
        behaviorSelect.value = '';
      }
    }

    const presetElements = [
      document.getElementById('favPresetSelect'),
      document.getElementById('btnSavePreset')
    ];
    presetElements.forEach(el => {
      if (el) {
        el.disabled = !isYearValid;
      }
    });

    const cancerPickerEl = document.getElementById('btnCancerPicker');
    if (cancerPickerEl) {
      cancerPickerEl.disabled = !isBehaviorValid;
    }

    const categoryRadios = document.querySelectorAll('input[name="mainCategoryTab"]');
    categoryRadios.forEach(radio => {
      radio.disabled = !isBehaviorValid;
    });

    const itemRadios = document.querySelectorAll('.item-checkbox');
    itemRadios.forEach(radio => {
      radio.disabled = !isBehaviorValid;
    });
    updateSummary();
  }

  function updateSummary() {
    const ys = yearStartInput ? yearStartInput.value.trim() : '';
    const ye = yearEndInput ? yearEndInput.value.trim() : '';
    const summaryYear = document.getElementById('summaryYear');
    if (summaryYear) {
      if (ys && ye) summaryYear.textContent = ys === ye ? ys : `${ys} - ${ye}`;
      else if (ys) summaryYear.textContent = `${ys} 起`;
      else if (ye) summaryYear.textContent = `至 ${ye}`;
      else summaryYear.innerHTML = '<span class="text-muted">尚未選擇</span>';
    }

    const summaryBehavior = document.getElementById('summaryBehavior');
    if (summaryBehavior && behaviorSelect) {
      const selectedOpt = behaviorSelect.options[behaviorSelect.selectedIndex];
      if (behaviorSelect.value) summaryBehavior.textContent = selectedOpt.text;
      else summaryBehavior.innerHTML = '<span class="text-muted">尚未選擇</span>';
    }

    const summaryCancer = document.getElementById('summaryCancer');
    if (summaryCancer) {
      const btnText = document.getElementById('btnCancerPickerText')?.textContent.trim();
      if (!btnText || btnText.includes('尚未選擇')) {
        summaryCancer.innerHTML = '<span class="text-muted">尚未選擇</span>';
      } else {
        summaryCancer.textContent = window.dashboardSelectedCancerTitle || btnText.replace(/已選取 \d+ 項/g, '').trim();
      }
    }

    const summaryAnalysis = document.getElementById('summaryAnalysis');
    if (summaryAnalysis) {
      const checkedItems = document.querySelectorAll('.item-checkbox:checked');
      if (checkedItems.length > 0) {
        const itemNames = Array.from(checkedItems).map(el => el.nextElementSibling.textContent.trim());
        summaryAnalysis.textContent = itemNames.join('、');
      } else {
        summaryAnalysis.innerHTML = '<span class="text-muted">尚未選擇</span>';
      }
    }
  }

  if (yearStartInput && yearEndInput) {
    ['input', 'change'].forEach(evtType => {
      yearStartInput.addEventListener(evtType, checkFiltersState);
      yearEndInput.addEventListener(evtType, checkFiltersState);
    });
  }
  
  if (behaviorSelect) {
    behaviorSelect.addEventListener('change', checkFiltersState);
  }

  document.querySelectorAll('.item-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSummary);
  });

  renderCategories();
  renderDetails();
  updateStatus();
  checkFiltersState();
})();

/* ==========================================
   檔案管理與查詢執行邏輯
   ========================================== */
document.addEventListener('DOMContentLoaded', function() {

  /* ── 檔案列表選擇邏輯 ── */
  const fileRows = document.querySelectorAll('#dashFileListBody tr');
  fileRows.forEach(row => {
      if (row.querySelector('a')) {
          row.addEventListener('click', function(e) {
              if (e.target.closest('.btn-del-file')) return;                 
              e.preventDefault();
              fileRows.forEach(r => {
                  r.classList.remove('table-active');
                  const link = r.querySelector('a');
                  if(link) link.classList.replace('text-primary', 'text-dark');
              });
              this.classList.add('table-active');
              const activeLink = this.querySelector('a');
              if(activeLink) activeLink.classList.replace('text-dark', 'text-primary');
          });
      }
  });

  /* ── 查詢按鈕執行邏輯 ── */
  const btnRunQuery = document.getElementById('btnRunQuery');
  if (btnRunQuery) {
      btnRunQuery.addEventListener('click', function() {
          document.querySelectorAll('.chart-pane').forEach(pane => {pane.classList.add('d-none');});

          let selectedFile = '';
          const activeRow = document.querySelector('#dashFileListBody tr.table-active');
          if (activeRow) {
              const link = activeRow.querySelector('a');
              if (link) selectedFile = link.innerText.trim();
          }

          const yearStartVal = document.getElementById('filterYearStart')?.value.trim();
          const yearEndVal = document.getElementById('filterYearEnd')?.value.trim();
          if (!yearStartVal || !yearEndVal || yearStartVal.length !== 4 || yearEndVal.length !== 4) {
              alert('請先輸入四位數的年度！');
              return;
          }
          
          const behaviorVal = document.getElementById('filterBehavior')?.value;
          if (!behaviorVal) {
              alert('請先選擇性態碼！');
              return;
          }

          if (!selectedFile) {
              alert('請先從上方檔案列表點選要分析的檔案！');
              return;
          }

          if (window.dashboardChartInstance) {
              window.dashboardChartInstance.showLoading({ text: '資料載入中...', color: '#2563eb', textColor: '#212529', maskColor: 'rgba(255, 255, 255, 0.8)', zlevel: 0 });
          }

          fetch('/api/dashboard/analyze_file', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ 
                  filename: selectedFile,
                  cancers: Array.from(window.selectedCancers || []),
                  year_start: yearStartVal,
                  year_end: yearEndVal,
                  behavior: behaviorVal
              })
          })
          .then(res => res.json())
          .then(data => {
              if (window.dashboardChartInstance) window.dashboardChartInstance.hideLoading();
              if (data.ok) {
                  const chartData = data.data;
                  window.lastChartData = chartData;

                  const chartTabsArea = document.getElementById('chartTabsArea');
                  const chartTabsContainer = document.getElementById('chartTabsContainer');
                  if (chartTabsContainer) chartTabsContainer.innerHTML = '';
                  
                  let anyChecked = false;
                  let firstBtn = null;
                  
                  document.querySelectorAll('.item-checkbox').forEach(itemChk => {
                      const targetSelector = itemChk.getAttribute('data-target');
                      if (targetSelector && itemChk.checked) {
                          anyChecked = true;
                          if (chartTabsContainer) {
                              const btn = document.createElement('button');
                              btn.className = 'btn btn-outline-primary chart-tab-btn';
                              btn.type = 'button';
                              btn.innerText = itemChk.value;
                              btn.dataset.target = targetSelector;
                              
                              btn.addEventListener('click', function() {
                                  chartTabsContainer.querySelectorAll('.chart-tab-btn').forEach(b => b.classList.remove('active'));
                                  this.classList.add('active');
                                  document.querySelectorAll('.chart-pane').forEach(pane => pane.classList.add('d-none'));
                                  const targetPane = document.querySelector(this.dataset.target);
                                  if (targetPane) {
                                      targetPane.classList.remove('d-none');
                                      if (typeof echarts !== 'undefined') {
                                          setTimeout(() => {
                                              const chartDoms = targetPane.querySelectorAll('div[_echarts_instance_], #main');
                                              chartDoms.forEach(c => {
                                                  const inst = echarts.getInstanceByDom(c);
                                                  if (inst) inst.resize();
                                              });
                                              
                                              if (window.lastChartData) {
                                                  const aiBtn = targetPane.querySelector('button[id^="btnAi"]');
                                                  const llmDiv = targetPane.querySelector('div[id^="llmResponse"]');
                                                  if (aiBtn && llmDiv && llmDiv.innerText.includes('自動產生')) {
                                                      aiBtn.click();
                                                  }
                                              }
                                          }, 50);
                                      }
                                  }
                              });
                              
                              chartTabsContainer.appendChild(btn);
                              if (!firstBtn) firstBtn = btn;
                          }
                      }
                  });
                  
                  if (chartTabsArea) {
                      if (anyChecked) chartTabsArea.classList.remove('d-none');
                      else {
                          chartTabsArea.classList.add('d-none');
                          const emptyPane = document.getElementById('chartPane-Empty');
                          if (emptyPane) emptyPane.classList.remove('d-none');
                      }
                  }

                  const btnAiMain = document.getElementById('btnAiMain');
                  const btnAiMedian = document.getElementById('btnAiMedian');
                  const btnAiAnalyzable = document.getElementById('btnAiAnalyzable');
                  
                  if (btnAiMain) {
                      btnAiMain.style.display = 'block';
                      btnAiMain.innerHTML = '重新產生敘述';
                      btnAiMain.onclick = () => window.DashboardRenderer.fetchLlmInsight('性別與年齡分佈', window.lastChartData.genderAgeData, ['性別', '年齡'], 'llmResponseMain', 'btnAiMain');
                  }
                  if (btnAiMedian) {
                      btnAiMedian.style.display = 'block';
                      btnAiMedian.innerHTML = '重新產生敘述';
                      btnAiMedian.onclick = () => window.DashboardRenderer.fetchLlmInsight('年齡中位數', window.lastChartData.ageMedianData, ['年齡', '性別'], 'llmResponseMedian', 'btnAiMedian');
                  }
                  if (btnAiAnalyzable) {
                      btnAiAnalyzable.style.display = 'block';
                      btnAiAnalyzable.innerHTML = '重新產生敘述';
                      btnAiAnalyzable.onclick = () => window.DashboardRenderer.fetchLlmInsight('癌症登記可分析個案與確診個案', window.lastChartData.analyzableConfirmedData, ['可分析個案', '確診個案'], 'llmResponseAnalyzable', 'btnAiAnalyzable');
                  }

                  const llmResponseMain = document.getElementById('llmResponseMain');
                  if (llmResponseMain) llmResponseMain.innerText = '（系統將自動產生分析敘述）';
                  const llmResponseMedian = document.getElementById('llmResponseMedian');
                  if (llmResponseMedian) llmResponseMedian.innerText = '（系統將自動產生分析敘述）';
                  const llmResponseAnalyzable = document.getElementById('llmResponseAnalyzable');
                  if (llmResponseAnalyzable) llmResponseAnalyzable.innerText = '（系統將自動產生分析敘述）';

                  if (window.DashboardRenderer) {
                      const yearTitle = window.DashboardRenderer.getSelectedYearTitle();
                      const cancerTitle = window.DashboardRenderer.getSelectedCancerTitle();
                      window.DashboardRenderer.renderSexAgeTable(chartData.genderAgeData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAgeMedianTable(chartData.ageMedianData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAnalyzableConfirmedTable(chartData.analyzableConfirmedData, yearTitle, cancerTitle);
                      window.DashboardRenderer.showAnnualDataContent();
                      const chartCaption = document.getElementById('annualSexAgeChartCaption');
                      if (chartCaption) {
                          chartCaption.innerText = `圖、${yearTitle}年新診斷${window.DashboardRenderer.getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈圖`;
                      }
                  }

                  if (window.dashboardChartInstance) {
                      window.dashboardChartInstance.setOption({
                          title: { text: '性別與年齡分佈', subtext: selectedFile },
                          xAxis: [{ data: chartData.genderAgeData.categories }],
                          series: [
                              { name: '男性', data: chartData.genderAgeData.male },
                              { name: '女性', data: chartData.genderAgeData.female },
                              { name: '總計', data: chartData.genderAgeData.total }
                          ]
                      });
                  }
                  
                  setTimeout(() => {
                      if (firstBtn) firstBtn.click();
                      else if (window.dashboardChartInstance) window.dashboardChartInstance.resize();
                  }, 50);
              } else {
                  alert('資料分析失敗: ' + data.error);
              }
          })
          .catch(err => {
              if (window.dashboardChartInstance) window.dashboardChartInstance.hideLoading();
              alert('發生系統錯誤，請稍後再試。');
          });
      });
  }

  /* ── 檔案上傳邏輯 ── */
  const form = document.getElementById('dashUploadForm');
  const fileInput = document.getElementById('dashFileInput');
  
  if (form && fileInput) {
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
  }

  /* ── 檔案刪除邏輯 ── */
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

});