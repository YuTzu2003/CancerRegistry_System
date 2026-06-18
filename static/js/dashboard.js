(function() {
  const cancerData = [
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
  allLeafIds.forEach(id => selectedCancers.add(id));
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
    
    list.innerHTML = cancerData.map(cat => {
      const isActive = currentCategory.id === cat.id;
      const cls = isActive ? 'active fw-bold text-primary bg-white' : 'text-secondary';
      const border = isActive ? '4px solid #0d6efd' : '4px solid transparent';
      
      return `
        <a href="#" class="list-group-item list-group-item-action bg-transparent border-0 py-3 cat-nav-btn ${cls}" 
           style="border-left: ${border};" data-cat-id="${cat.id}">
          <div class="d-flex justify-content-between align-items-center">
            <span>${cat.name}</span>
            ${getBadgeHtml(cat)}
          </div>
        </a>
      `;
    }).join('');
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
    if (status) {
      status.innerHTML = `<i class="bi bi-info-circle me-1"></i>已選取：<span class="fw-bold text-primary">${selectedCancers.size}</span> / ${allLeafIds.length} 項癌別`;
    }
    
    const btnText = document.getElementById('btnCancerPickerText');
    if (btnText) {
      if (selectedCancers.size === allLeafIds.length) {
        btnText.textContent = '預設：全選 (所有癌別)';
      } else if (selectedCancers.size === 0) {
        btnText.textContent = '— 尚未選擇癌別 —';
      } else {
        btnText.innerHTML = `<span class="text-primary fw-bold">已選取 ${selectedCancers.size} 項</span>`;
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
    
    getLeafIds(node).forEach(id => {
      if (isChecked) selectedCancers.add(id);
      else selectedCancers.delete(id);
    });
    
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
        Swal.fire({ icon: 'error', title: '上傳失敗', text: '網路錯誤', allowOutsideClick: false, confirmButtonColor: '#2563eb' });
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
