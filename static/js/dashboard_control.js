(function() {
  /* ── 狀態管理與介面更新邏輯 ── */
  window.selectedCancers = new Set();
  
  function updateStatus() {
    const status = document.getElementById('cancerPickerStatus');
    const leafNodes = document.querySelectorAll('.cancer-cb-leaf:not([value="All_Cancers"])');
    const allCancersNode = document.querySelector('.cancer-cb-leaf[value="All_Cancers"]');
    const lungHistologyChildChecks = document.querySelectorAll('.lung-histology-child input[type="checkbox"]');
    const hasCheckedLungHistologyChild = Array.from(lungHistologyChildChecks).some(cb => cb.checked);
    const lungTopGroup = document.getElementById('chk_group_Lung_and_Bronchus_Trachea');
    const isDisplayOnlyLungParent = (node) => (
        node &&
        node.value === 'Lung_and_Bronchus' &&
        hasCheckedLungHistologyChild &&
        !(lungTopGroup && lungTopGroup.checked)
    );
    
    let specificSelectedCount = 0;
    const selectedValues = [];
    const selectedNames = [];
    
    const isAllSelected = allCancersNode && allCancersNode.checked;
    
    if (isAllSelected) {
        leafNodes.forEach(node => {
            selectedValues.push(node.value);
            specificSelectedCount++;
        });
        selectedValues.push('All_Cancers');
        window.dashboardSelectedCancerTitle = '全癌別';
    } else {
        leafNodes.forEach(node => {
            if (node.checked && !isDisplayOnlyLungParent(node)) {
                selectedValues.push(node.value);
                specificSelectedCount++;
            }
        });
        
        if (specificSelectedCount === leafNodes.length && leafNodes.length > 0) {
            window.dashboardSelectedCancerTitle = '全癌別';
            selectedValues.push('All_Cancers');
        } else if (specificSelectedCount > 0) {
            const groupNodes = document.querySelectorAll('.cancer-cb-group:not([data-group="All_Cancers"])');
            const groupedNames = [];
            groupNodes.forEach(group => {
               if(group.checked) {
                   const label = group.nextElementSibling.textContent.replace('(全選)', '').trim();
                   groupedNames.push(label.replace(/\s*\([^)]*\)/g, '').replace(/\s+[A-Za-z][A-Za-z0-9\s,./&+-]*$/g, '').trim());
               } 
            });
            
            const independentLeaves = [];
            leafNodes.forEach(node => {
               if(node.checked && !isDisplayOnlyLungParent(node)) {
                   const parentGrp = document.getElementById('chk_group_' + node.getAttribute('data-parent')) || 
                                     document.getElementById('chk_group_' + node.getAttribute('data-grandparent'));
                   if(!parentGrp || !parentGrp.checked) {
                       const label = node.nextElementSibling.textContent.trim();
                       independentLeaves.push(label.replace(/\s*\([^)]*\)/g, '').replace(/\s+[A-Za-z][A-Za-z0-9\s,./&+-]*$/g, '').trim());
                   }
               }
            });
            window.dashboardSelectedCancerTitle = [...groupedNames, ...independentLeaves].join('、');
        } else {
            window.dashboardSelectedCancerTitle = 'XX';
        }
    }
    
    window.selectedCancers = new Set(selectedValues);
    window.dashboardSelectedCancerIds = selectedValues;
    const displayCancerKeys = [];
    if (isAllSelected || (specificSelectedCount === leafNodes.length && leafNodes.length > 0)) {
        displayCancerKeys.push('All_Cancers');
    } else {
        const selectedGroups = new Set();
        document.querySelectorAll('.cancer-cb-group:not([data-group="All_Cancers"])').forEach(group => {
            if (group.checked) {
                selectedGroups.add(group.dataset.group);
                displayCancerKeys.push(group.dataset.group);
            }
        });
        leafNodes.forEach(node => {
            if (!node.checked || isDisplayOnlyLungParent(node)) return;
            const parentKey = node.dataset.parent;
            const grandparentKey = node.dataset.grandparent;
            if (!selectedGroups.has(parentKey) && !selectedGroups.has(grandparentKey)) {
                displayCancerKeys.push(node.value);
            }
        });
    }
    window.dashboardSelectedCancerDisplayKeys = [...new Set(displayCancerKeys)];
    
    const totalSpecificCount = leafNodes.length;
    
    if (status) {
      status.innerHTML = `<i class="bi bi-info-circle me-1"></i>已選取：<span class="fw-bold text-primary">${specificSelectedCount}</span> / ${totalSpecificCount} 項癌別`;
    }
    
    const btnText = document.getElementById('btnCancerPickerText');
    if (btnText) {
      if (isAllSelected || (specificSelectedCount === totalSpecificCount && totalSpecificCount > 0)) {
        btnText.textContent = '不分癌別 全癌別(C00-C80)';
      } else if (specificSelectedCount === 0) {
        btnText.textContent = '— 尚未選擇癌別 —';
      } else {
        btnText.innerHTML = `<span class="text-primary fw-bold">已選取 ${specificSelectedCount} 項</span>`;
      }
    }
    
    if (typeof updateSummary === 'function') {
      updateSummary();
    }
  }

  function updateLungHistologyChildrenVisibility() {
      const lungParent = document.getElementById('chk_Lung_and_Bronchus');
      const childRows = document.querySelectorAll('.lung-histology-child');
      const childChecks = document.querySelectorAll('.lung-histology-child input[type="checkbox"]');
      if (!lungParent || childRows.length === 0) return;

      const hasCheckedChild = Array.from(childChecks).some(cb => cb.checked);
      const shouldShow = lungParent.checked || hasCheckedChild;

      childRows.forEach(row => {
          row.classList.toggle('d-none', !shouldShow);
          row.classList.toggle('d-flex', shouldShow);
      });

      if (!shouldShow) {
          childChecks.forEach(cb => { cb.checked = false; });
      }
  }

  /* ── 癌別選擇事件綁定 ── */
  function updateParentCheckboxes() {
      document.querySelectorAll('.cancer-cb-subgroup').forEach(subgroup => {
          const groupId = subgroup.getAttribute('data-group');
          const leaves = document.querySelectorAll(`.cancer-cb-leaf[data-parent="${groupId}"]`);
          const checkedLeaves = Array.from(leaves).filter(l => l.checked);
          subgroup.checked = leaves.length > 0 && checkedLeaves.length === leaves.length;
          subgroup.indeterminate = checkedLeaves.length > 0 && checkedLeaves.length < leaves.length;
      });
      
      document.querySelectorAll('.cancer-cb-group').forEach(group => {
          const groupId = group.getAttribute('data-group');
          if (groupId === 'All_Cancers') return;
          
          const leavesAndSubgroups = document.querySelectorAll(`.cancer-cb-leaf[data-parent="${groupId}"], .cancer-cb-leaf[data-grandparent="${groupId}"]`);
          const checkedItems = Array.from(leavesAndSubgroups).filter(l => l.checked);
          group.checked = leavesAndSubgroups.length > 0 && checkedItems.length === leavesAndSubgroups.length;
          group.indeterminate = checkedItems.length > 0 && checkedItems.length < leavesAndSubgroups.length;
      });
      
      const allCancersGroup = document.querySelector('.cancer-cb-group[data-group="All_Cancers"]');
      const allCancersLeaf = document.querySelector('.cancer-cb-leaf[value="All_Cancers"]');
      const allLeaves = document.querySelectorAll('.cancer-cb-leaf:not([value="All_Cancers"])');
      const allCheckedLeaves = Array.from(allLeaves).filter(l => l.checked);
      
      if (allCancersGroup && allCancersLeaf) {
          if (allCheckedLeaves.length === allLeaves.length && allLeaves.length > 0) {
              allCancersGroup.checked = true;
              allCancersLeaf.checked = true;
              allCancersGroup.indeterminate = false;
          } else {
              allCancersGroup.checked = false;
              allCancersLeaf.checked = false;
              allCancersGroup.indeterminate = allCheckedLeaves.length > 0;
          }
      }

      updateLungHistologyChildrenVisibility();

      document.querySelectorAll('.cat-nav-btn').forEach(navBtn => {
          const targetHref = navBtn.getAttribute('href');
          if (!targetHref) return;
          const targetId = targetHref.substring(6); // e.g. '#list-oral_group' -> 'oral_group'
          const badgeSpan = navBtn.querySelector('.cat-badge');
          if (!badgeSpan) return;
          
          if (targetId === 'All_Cancers') {
              const allLeaf = document.querySelector('.cancer-cb-leaf[value="All_Cancers"]');
              if (allLeaf && allLeaf.checked) {
                  badgeSpan.innerHTML = '<i class="bi bi-check-circle-fill text-success ms-2"></i>';
              } else {
                  badgeSpan.innerHTML = '';
              }
          } else {
              const leaves = document.querySelectorAll(`.cancer-cb-leaf[data-parent="${targetId}"], .cancer-cb-leaf[data-grandparent="${targetId}"]`);
              const checkedCount = Array.from(leaves).filter(l => l.checked).length;
              if (checkedCount === 0) {
                  badgeSpan.innerHTML = '';
              } else if (checkedCount === leaves.length && leaves.length > 0) {
                  badgeSpan.innerHTML = '<i class="bi bi-check-circle-fill text-success ms-2"></i>';
              } else {
                  badgeSpan.innerHTML = `<span class="badge bg-warning text-dark ms-2 rounded-pill">${checkedCount}</span>`;
              }
          }
      });
  }

  document.getElementById('cancerDetailList')?.addEventListener('change', (e) => {
    const target = e.target;
    
    if (target.classList.contains('cancer-cb-group')) {
        const groupId = target.getAttribute('data-group');
        const isChecked = target.checked;
        
        if (groupId === 'All_Cancers') {
            document.querySelectorAll('.cancer-cb-leaf, .cancer-cb-subgroup, .cancer-cb-group').forEach(cb => {
                cb.checked = isChecked;
                cb.indeterminate = false;
            });
        } else {
            document.querySelectorAll(`.cancer-cb-leaf[data-parent="${groupId}"], .cancer-cb-leaf[data-grandparent="${groupId}"], .cancer-cb-subgroup[data-parent="${groupId}"]`).forEach(cb => {
                cb.checked = isChecked;
                cb.indeterminate = false;
            });
        }
    } else if (target.id === 'chk_Lung_and_Bronchus' && !target.checked) {
        document.querySelectorAll('.lung-histology-child input[type="checkbox"]').forEach(cb => {
            cb.checked = false;
        });
    } else if (target.classList.contains('cancer-cb-subgroup')) {
        const groupId = target.getAttribute('data-group');
        const isChecked = target.checked;
        document.querySelectorAll(`.cancer-cb-leaf[data-parent="${groupId}"]`).forEach(cb => {
            cb.checked = isChecked;
        });
    }
    
    updateParentCheckboxes();
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

    document.querySelectorAll('.cancer-cb-leaf, .cancer-cb-group, .cancer-cb-subgroup').forEach(cb => {
      cb.checked = false;
      cb.indeterminate = false;
    });
    
    if (preset.cancers && preset.cancers.length > 0) {
      preset.cancers.forEach(id => {
        let cb = document.querySelector(`.cancer-cb-leaf[value="${id}"]`);
        if (!cb) {
          cb = Array.from(document.querySelectorAll('.cancer-cb-leaf')).find(el => el.value.toLowerCase() === id.toLowerCase());
        }
        if (cb) cb.checked = true;
      });
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

    updateParentCheckboxes();
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

  /* ── 篩選欄位邏輯 ── */
  const yearStartInput = document.getElementById('filterYearStart');
  const yearEndInput = document.getElementById('filterYearEnd');
  const behaviorSelect = document.getElementById('filterBehavior');

  window.dashboardFileYearRange = null;
  window.dashboardYearRangeAlertKey = '';

  const yearSelectUis = new Map();

  function closeYearSelectMenus(exceptUi = null) {
    yearSelectUis.forEach((ui) => {
      if (ui !== exceptUi) {
        ui.classList.remove('is-open');
        ui.querySelector('.year-select-trigger')?.setAttribute('aria-expanded', 'false');
      }
    });
  }

  function syncYearSelectUi(selectEl) {
    if (!selectEl) return;

    let ui = yearSelectUis.get(selectEl);
    if (!ui) {
      selectEl.classList.add('year-select-native');

      ui = document.createElement('div');
      ui.className = 'year-select-ui';
      ui.innerHTML = `
        <button type="button" class="year-select-trigger" aria-haspopup="listbox" aria-expanded="false">
          <span class="year-select-label"></span>
        </button>
        <div class="year-select-menu" role="listbox"></div>
      `;
      selectEl.insertAdjacentElement('afterend', ui);
      yearSelectUis.set(selectEl, ui);

      const trigger = ui.querySelector('.year-select-trigger');
      trigger.addEventListener('click', () => {
        if (selectEl.disabled) return;
        const shouldOpen = !ui.classList.contains('is-open');
        closeYearSelectMenus(ui);
        ui.classList.toggle('is-open', shouldOpen);
        trigger.setAttribute('aria-expanded', String(shouldOpen));
      });
    }

    const trigger = ui.querySelector('.year-select-trigger');
    const label = ui.querySelector('.year-select-label');
    const menu = ui.querySelector('.year-select-menu');
    const selectedOption = selectEl.options[selectEl.selectedIndex] || selectEl.options[0];

    label.textContent = selectedOption ? selectedOption.textContent : '';
    trigger.disabled = selectEl.disabled;
    ui.classList.toggle('is-start', selectEl.id === 'filterYearStart');
    ui.classList.toggle('is-end', selectEl.id === 'filterYearEnd');
    ui.classList.toggle('is-placeholder', !selectedOption || !selectedOption.value);
    ui.classList.toggle('is-disabled', selectEl.disabled);
    if (selectEl.disabled) {
      ui.classList.remove('is-open');
      trigger.setAttribute('aria-expanded', 'false');
    }

    menu.replaceChildren();
    Array.from(selectEl.options).forEach((option) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'year-select-option';
      item.innerHTML = '<span class="year-select-option-label"></span>';
      item.querySelector('.year-select-option-label').textContent = option.textContent;
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', String(option.selected));

      if (!option.value) item.classList.add('is-placeholder');
      if (option.selected) item.classList.add('is-selected');

      item.addEventListener('click', () => {
        if (!option.value) return;
        selectEl.value = option.value;
        ui.classList.remove('is-open');
        trigger.setAttribute('aria-expanded', 'false');
        selectEl.dispatchEvent(new Event('change', { bubbles: true }));
        syncYearSelectUi(selectEl);
      });

      menu.appendChild(item);
    });
  }

  document.addEventListener('click', (e) => {
    if (!e.target.closest('.year-select-ui')) {
      closeYearSelectMenus();
    }
  });

  function setYearSelectPlaceholder(selectEl, text) {
    if (!selectEl) return;
    selectEl.replaceChildren();
    const option = document.createElement('option');
    option.value = '';
    option.textContent = text;
    option.disabled = true;
    option.selected = true;
    selectEl.appendChild(option);
    selectEl.disabled = true;
    syncYearSelectUi(selectEl);
  }

  function fillYearOptions(selectEl, start, end) {
    if (!selectEl) return;
    for (let year = start; year <= end; year += 1) {
      const option = document.createElement('option');
      option.value = String(year);
      option.textContent = String(year);
      selectEl.appendChild(option);
    }
    syncYearSelectUi(selectEl);
  }

  function refreshYearEndOptions() {
    const range = window.dashboardFileYearRange;
    if (!yearEndInput || !range) return;

    const rangeStart = Number(range.year_start);
    const rangeEnd = Number(range.year_end);
    if (!Number.isInteger(rangeStart) || !Number.isInteger(rangeEnd) || rangeStart > rangeEnd) return;

    const selectedEnd = yearEndInput.value;
    const selectedStartValue = yearStartInput?.value || '';
    const selectedStart = Number(selectedStartValue);
    const endStart = selectedStartValue.length === 4 && Number.isInteger(selectedStart) ? selectedStart : rangeStart;

    setYearSelectPlaceholder(yearEndInput, '結束');
    fillYearOptions(yearEndInput, endStart, rangeEnd);
    yearEndInput.disabled = false;

    if (selectedEnd && Number(selectedEnd) >= endStart && Number(selectedEnd) <= rangeEnd) {
      yearEndInput.value = selectedEnd;
    } else {
      yearEndInput.value = '';
    }
    syncYearSelectUi(yearEndInput);
  }

  function populateYearSelects(range) {
    if (!yearStartInput || !yearEndInput) return;
    setYearSelectPlaceholder(yearStartInput, '起始');
    setYearSelectPlaceholder(yearEndInput, '結束');

    const start = Number(range?.year_start);
    const end = Number(range?.year_end);
    if (!Number.isInteger(start) || !Number.isInteger(end) || start > end) return;

    fillYearOptions(yearStartInput, start, end);
    fillYearOptions(yearEndInput, start, end);

    yearStartInput.disabled = false;
    yearEndInput.disabled = false;
    yearStartInput.value = '';
    yearEndInput.value = '';
    syncYearSelectUi(yearStartInput);
    syncYearSelectUi(yearEndInput);
  }

  setYearSelectPlaceholder(yearStartInput, '起始');
  setYearSelectPlaceholder(yearEndInput, '結束');

  window.validateDashboardYearRange = function(showAlert = false) {
    const ys = yearStartInput ? yearStartInput.value.trim() : '';
    const ye = yearEndInput ? yearEndInput.value.trim() : '';
    const range = window.dashboardFileYearRange;
    if (!range || ys.length !== 4 || ye.length !== 4) return true;

    const start = Number(ys);
    const end = Number(ye);
    if (!Number.isFinite(start) || !Number.isFinite(end)) return false;

    const isInvalidOrder = start > end;
    const isOutside = start < Number(range.year_start) || end > Number(range.year_end);
    if (isInvalidOrder || isOutside) {
      return false;
    }

    window.dashboardYearRangeAlertKey = '';
    return true;
  };

  window.loadDashboardFileYearRange = function(fileId) {
    window.dashboardFileYearRange = null;
    window.dashboardYearRangeAlertKey = '';
    setYearSelectPlaceholder(yearStartInput, '起始');
    setYearSelectPlaceholder(yearEndInput, '結束');
    if (!fileId) return Promise.resolve(null);

    return fetch('/api/dashboard/year_range', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_id: fileId })
    })
      .then(res => res.json())
      .then(data => {
        if (data.ok) {
          window.dashboardFileYearRange = {
            year_start: Number(data.year_start),
            year_end: Number(data.year_end)
          };
          populateYearSelects(window.dashboardFileYearRange);
          window.validateDashboardYearRange(false);
        }
        checkFiltersState();
        return window.dashboardFileYearRange;
      })
      .catch(() => {
        window.dashboardFileYearRange = null;
        checkFiltersState();
        return null;
      });
  };

  function resetDashboardFilters() {
    window.DashboardRenderer?.clearInsightCache?.();
    if (window.dashboardFileYearRange) {
      populateYearSelects(window.dashboardFileYearRange);
    } else {
      setYearSelectPlaceholder(yearStartInput, '起始');
      setYearSelectPlaceholder(yearEndInput, '結束');
    }
    if (behaviorSelect) behaviorSelect.value = '';

    document.querySelectorAll('.cancer-cb-leaf, .cancer-cb-subgroup, .cancer-cb-group').forEach(cb => {
      cb.checked = false;
      cb.indeterminate = false;
    });
    document.querySelectorAll('.item-checkbox, input[name="mainCategoryTab"]').forEach(cb => {
      cb.checked = false;
    });
    document.querySelectorAll('.annual-stage-class-checkbox').forEach(cb => {
      cb.checked = false;
    });
    document.querySelectorAll('[id^="subItems-"]').forEach(div => {
      div.classList.add('d-none');
    });

    const favPresetSelect = document.getElementById('favPresetSelect');
    if (favPresetSelect) favPresetSelect.value = '';
    togglePresetActionButtons(false);

    window.selectedCancers = new Set();
    window.dashboardSelectedCancerIds = [];
    window.dashboardSelectedCancerDisplayKeys = [];
    window.dashboardSelectedCancerTitle = 'XX';

    document.querySelectorAll('.chart-pane').forEach(pane => {
      pane.classList.add('d-none');
    });
    document.getElementById('chartTabsArea')?.classList.add('d-none');
    document.getElementById('chartTabsContainer')?.replaceChildren();

    updateParentCheckboxes();
    updateStatus();
    updateAnnualStageState();
    checkFiltersState();
  }

  document.getElementById('btnResetFilters')?.addEventListener('click', resetDashboardFilters);

  window.addEventListener('pageshow', function() {
    if (sessionStorage.getItem('dashboard_reset_filters_on_return') === '1') {
      sessionStorage.removeItem('dashboard_reset_filters_on_return');
      resetDashboardFilters();
    }
  });

  function checkFiltersState() {
    const ys = yearStartInput ? yearStartInput.value.trim() : '';
    const ye = yearEndInput ? yearEndInput.value.trim() : '';
    const isYearValid = ys.length === 4 && ye.length === 4 && window.validateDashboardYearRange(false);

    const isBehaviorValid = isYearValid && behaviorSelect && behaviorSelect.value !== '';

    if (behaviorSelect) {
      behaviorSelect.disabled = !isYearValid;
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
    updateAnnualStageState();
    updateSummary();
  }

  function updateAnnualStageState() {
    const ajccCheckbox = document.getElementById('chkStageAjcc');
    const classOptions = document.getElementById('annualAjccClassOptions');
    if (!ajccCheckbox || !classOptions) return;
    const enabled = ajccCheckbox.checked && !ajccCheckbox.disabled;
    classOptions.classList.toggle('d-none', !ajccCheckbox.checked);
    classOptions.querySelectorAll('.annual-stage-class-checkbox').forEach(checkbox => {
      checkbox.disabled = !enabled;
      if (!ajccCheckbox.checked) checkbox.checked = false;
    });
  }

  function selectedAnnualStageOptions() {
    return {
      systems: Array.from(document.querySelectorAll('.annual-stage-system-checkbox:checked')).map(input => input.nextElementSibling?.textContent?.trim() || input.value),
      class_groups: Array.from(document.querySelectorAll('.annual-stage-class-checkbox:checked')).map(input => input.value)
    };
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
        const itemNames = Array.from(checkedItems)
          .filter(el => !el.classList.contains('annual-stage-system-checkbox'))
          .map(el => el.nextElementSibling.textContent.trim());
        const stageOptions = selectedAnnualStageOptions();
        if (stageOptions.systems.length) {
          itemNames.push(`期別（${stageOptions.systems.join('、')}${stageOptions.class_groups.length ? `；${stageOptions.class_groups.join('、')}` : ''}）`);
        }
        summaryAnalysis.textContent = itemNames.join('、');
      } else {
        summaryAnalysis.innerHTML = '<span class="text-muted">尚未選擇</span>';
      }
      
      document.querySelectorAll('.cat-count-badge').forEach(badge => {
        const group = badge.getAttribute('data-parent-group');
        if (group) {
          const count = document.querySelectorAll(`.item-checkbox:checked[data-parent="${group}"]`).length;
          if (count > 0) {
            badge.textContent = count;
            badge.classList.remove('d-none');
          } else {
            badge.classList.add('d-none');
          }
        }
      });

      const summaryAiStyle = document.getElementById('summaryAiStyle');
      const modeAiSelect = document.getElementById('mode_ai');
      if (summaryAiStyle && modeAiSelect) {
        const selectedOpt = modeAiSelect.options[modeAiSelect.selectedIndex];
        if (modeAiSelect.value) summaryAiStyle.textContent = selectedOpt.text;
        else summaryAiStyle.innerHTML = '<span class="text-muted">尚未選擇</span>';
      }
    }
  }

  if (yearStartInput && yearEndInput) {
    yearStartInput.addEventListener('change', function() {
      refreshYearEndOptions();
      checkFiltersState();
      window.validateDashboardYearRange(false);
    });
    yearEndInput.addEventListener('change', function() {
      checkFiltersState();
      window.validateDashboardYearRange(false);
    });
  }
  
  if (behaviorSelect) {
    behaviorSelect.addEventListener('change', checkFiltersState);
  }

  const modeAiSelect = document.getElementById('mode_ai');
  if (modeAiSelect) {
    modeAiSelect.addEventListener('change', updateSummary);
  }

  document.querySelectorAll('.item-checkbox').forEach(cb => {
    cb.addEventListener('change', updateSummary);
  });

  document.querySelectorAll('.annual-stage-system-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', function() {
      updateAnnualStageState();
      updateSummary();
    });
  });

  document.querySelectorAll('.annual-stage-class-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', updateSummary);
  });

  document.querySelectorAll('input[name="mainCategoryTab"]').forEach(radio => {
    radio.addEventListener('change', function() {
      // Hide all subItems
      document.querySelectorAll('[id^="subItems-"]').forEach(div => {
        div.classList.add('d-none');
      });
      // Show the selected subItems group
      if (this.checked) {
        const group = this.getAttribute('data-group');
        const targetDiv = document.getElementById('subItems-' + group);
        if (targetDiv) {
          targetDiv.classList.remove('d-none');
        }
      }
      updateSummary();
    });
  });

  document.querySelectorAll('.cat-nav-btn').forEach(btn => {
    btn.addEventListener('show.bs.tab', function(e) {
      const oldTab = e.relatedTarget;
      if (oldTab) {
        oldTab.classList.remove('text-primary', 'fw-bold');
        oldTab.classList.add('text-secondary');
        oldTab.style.borderLeft = '4px solid transparent';
      }
      const newTab = e.target;
      if (newTab) {
        newTab.classList.remove('text-secondary');
        newTab.classList.add('text-primary', 'fw-bold');
        newTab.style.borderLeft = '4px solid #0d6efd';
      }
    });
  });

  updateParentCheckboxes();
  updateStatus();
  checkFiltersState();
})();

/* ==========================================
   檔案管理與查詢執行邏輯
   ========================================== */
function initDashboardControl() {
  /* ── 檔案列表選擇邏輯 ── */
  document.addEventListener('click', function(e) {
      const row = e.target.closest('#dashFileListBody tr');
      if (!row) return;
      if (!row.querySelector('a')) return;
      if (e.target.closest('.btn-del-file')) return;                 
      
      e.preventDefault();
      const fileRows = document.querySelectorAll('#dashFileListBody tr');
      fileRows.forEach(r => {
          r.classList.remove('table-active');
          const link = r.querySelector('a');
          if(link) link.classList.replace('text-primary', 'text-dark');
          const badge = r.querySelector('.status-badge-selected');
          if(badge) badge.style.display = 'none';
      });
      
      row.classList.add('table-active');
      const activeLink = row.querySelector('a');
      if(activeLink) activeLink.classList.replace('text-dark', 'text-primary');
      const activeBadge = row.querySelector('.status-badge-selected');
      if(activeBadge) activeBadge.style.display = 'inline-block';
      const selectedFileId = row.dataset.fileId || '';
      if (window.loadDashboardFileYearRange) {
          window.loadDashboardFileYearRange(selectedFileId);
      }
  });

  /* ── 查詢按鈕執行邏輯 ── */
  const btnRunQuery = document.getElementById('btnRunQuery');
  if (btnRunQuery) {
      btnRunQuery.addEventListener('click', async function() {
          await window.DashboardI18n?.setLanguage('zh-TW');
          window.DashboardRenderer?.clearInsightCache?.();
          document.querySelectorAll('.chart-pane').forEach(pane => {pane.classList.add('d-none');});

          let selectedFileId = '';
          const activeRow = document.querySelector('#dashFileListBody tr.table-active');
          if (activeRow) {
              const link = activeRow.querySelector('a');
              selectedFileId = activeRow.dataset.fileId || '';
          }

          const yearStartVal = document.getElementById('filterYearStart')?.value.trim();
          const yearEndVal = document.getElementById('filterYearEnd')?.value.trim();
          if (!yearStartVal || !yearEndVal || yearStartVal.length !== 4 || yearEndVal.length !== 4) {
              utils.alert('請先輸入四位數的年度！', 'warning');
              return;
          }

          const yearStartNum = Number(yearStartVal);
          const yearEndNum = Number(yearEndVal);
          window.dashboardYearRangeAlertKey = '';
          if (yearStartNum > yearEndNum || !window.validateDashboardYearRange(true)) {
              return;
          }
          
          const behaviorVal = document.getElementById('filterBehavior')?.value;
          if (!behaviorVal) {
              utils.alert('請先選擇性態碼！', 'warning');
              return;
          }

          if (!selectedFileId) {
              utils.alert('請先從上方檔案列表點選要分析的檔案！', 'warning');
              return;
          }
          window.dashboardAnalysisFileId = selectedFileId;

          if (window.utils && window.utils.showLoading) {
              window.utils.showLoading('分析中，請稍候...');
          } else if (window.dashboardChartInstance) {
              window.dashboardChartInstance.showLoading({ text: '資料載入中...', color: '#2563eb', textColor: '#212529', maskColor: 'rgba(255, 255, 255, 0.8)', zlevel: 0 });
          }

          const dashboardAnalyzePayload = {
              file_id: selectedFileId,
              cancers: Array.from(window.selectedCancers || []),
              year_start: yearStartVal,
              year_end: yearEndVal,
              behavior: behaviorVal
          };
          fetch('/api/dashboard/analyze_file', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(dashboardAnalyzePayload)
          })
          .then(res => res.json())
          .then(data => {
              if (data.ok) {
                  const chartData = data.data;
                  if (chartData && chartData.noDataWarning) {
                      if (window.utils && window.utils.hideLoading) {
                          window.utils.hideLoading();
                      } else if (window.dashboardChartInstance) {
                          window.dashboardChartInstance.hideLoading();
                      }
                      utils.alert(chartData.noDataWarning, 'warning');
                      return;
                  }
                  window.lastChartData = chartData;

                  const histologyWarnings = Array.isArray(chartData.histologyWarnings) ? chartData.histologyWarnings : [];
                  const histologyChecked = Boolean(document.getElementById('chkDiagnosisHistology')?.checked);

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
                                              if (targetPane.id === 'chartPane-CrossYearSurvival') {
                                                  window.DashboardRenderer?.updateSurvivalChartLayout?.();
                                              }
                                              
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
                  


                  const llmConfigs = [
                      { btnId: 'btnAiMain', title: '性別與年齡分佈', dataKey: 'genderAgeData', fields: ['性別', '年齡'], respId: 'llmResponseMain' },
                      { btnId: 'btnAiMedian', title: '年齡中位數', dataKey: 'ageMedianData', fields: ['年齡', '性別'], respId: 'llmResponseMedian' },
                      { btnId: 'btnAiAnalyzable', title: '癌症登記可分析個案與確診個案', dataKey: 'analyzableConfirmedData', fields: ['可分析個案', '確診個案'], respId: 'llmResponseAnalyzable' },
                      { btnId: 'btnAiHistology', title: '組織型態分佈', dataKey: 'histologyData', fields: ['組織型態', '個案數'], respId: 'llmResponseHistology' },
                      { btnId: 'btnAiDiagnosisClassification', title: '個案分類', dataKey: 'diagnosisClassificationData', fields: ['個案分類'], respId: 'llmResponseDiagnosisClassification' }
                  ];

                  llmConfigs.forEach(cfg => {
                      const btn = document.getElementById(cfg.btnId);
                      if (btn) {
                          btn.style.display = 'block';
                          btn.innerHTML = window.DashboardRenderer.t('regenerateInsight');
                          btn.dataset.insightFieldKey = cfg.title;
                          btn.onclick = (event) => {
                              let dataToSend = window.lastChartData[cfg.dataKey];
                              if (cfg.btnId === 'btnAiHistology' && dataToSend) {
                                  // 過濾掉 Unknown / 未對應組織型態，並重新計算百分比以與表格配平
                                  const validHist = dataToSend.filter(item => item.name !== 'Unknown / 未對應組織型態');
                                  const totalValid = validHist.reduce((sum, item) => sum + item.count, 0);
                                  dataToSend = validHist.map(item => {
                                      const pct = totalValid > 0 ? ((item.count / totalValid) * 100).toFixed(1) + '%' : '0.0%';
                                      return {
                                          code: item.code,
                                          name: item.name,
                                          count: item.count,
                                          percentage: pct
                                      };
                                  });
                              }
                              const currentRequest = window.DashboardRenderer.fetchLlmInsight(
                                  cfg.title, dataToSend, cfg.fields, cfg.respId, cfg.btnId,
                                  { forceRefresh: event?.isTrusted === true }
                              );
                              return currentRequest;
                          };
                      }
                  });

                  document.querySelectorAll('[id^="llmResponse"]').forEach(el => {
                      el.innerText = window.DashboardRenderer.t('autoInsight');
                  });

                  if (window.DashboardRenderer) {
                      const yearTitle = window.DashboardRenderer.getSelectedYearTitle();
                      const cancerTitle = window.DashboardRenderer.getSelectedCancerTitle();
                      window.DashboardRenderer.renderSexAgeTable(chartData.genderAgeData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAgeMedianTable(chartData.ageMedianData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAnalyzableConfirmedTable(chartData.analyzableConfirmedData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderHistologyTable(chartData.histologyData, yearTitle, cancerTitle, chartData.histologyNoDataReason);
                      window.DashboardRenderer.renderColonHistologyTableNote(chartData.histologyWarnings);
                      window.DashboardRenderer.renderHistologyWarningButton(histologyChecked ? histologyWarnings : []);
                      window.DashboardRenderer.renderDiagnosisClassificationTable(chartData.diagnosisClassificationData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderDiagnosisClassificationChart(chartData.diagnosisClassificationData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderSurvivalTable(chartData.survivalData, yearTitle, cancerTitle);
                      window.DashboardRenderer.showAnnualDataContent();
                      window.DashboardRenderer.updateChartCaptions(yearTitle, cancerTitle);
                  }

                  if (window.dashboardChartInstance) {
                      const genderAgeOption = window.DashboardRenderer && window.DashboardRenderer.getGenderAgeChartOption
                          ? window.DashboardRenderer.getGenderAgeChartOption(chartData.genderAgeData)
                          : {
                              xAxis: [{ data: chartData.genderAgeData.categories }],
                              series: [
                                  { name: '男性', data: chartData.genderAgeData.male },
                                  { name: '女性', data: chartData.genderAgeData.female },
                                  { name: '總計', data: chartData.genderAgeData.total }
                              ]
                          };
                      window.dashboardChartInstance.setOption(genderAgeOption, true);
                  }

                  if (window.DashboardRenderer) window.DashboardRenderer.updateHistologyChart(chartData.histologyData, chartData.histologyNoDataReason);
                  
                  // Collect all AI promises before showing the charts
                  let aiPromises = [];
                  document.querySelectorAll('.item-checkbox').forEach(itemChk => {
                      if (itemChk.checked) {
                          const targetSelector = itemChk.getAttribute('data-target');
                          if (targetSelector) {
                              const targetPane = document.querySelector(targetSelector);
                              if (targetPane) {
                                  const aiBtn = targetPane.querySelector('button[id^="btnAi"]');
                                  const llmDiv = targetPane.querySelector('div[id^="llmResponse"]');
                                  if (aiBtn && llmDiv && llmDiv.innerText.includes('自動產生')) {
                                      if (typeof aiBtn.onclick === 'function') {
                                          const prom = aiBtn.onclick();
                                          if (prom instanceof Promise) aiPromises.push(prom);
                                      }
                                  }
                              }
                          }
                      }
                  });

                  Promise.all(aiPromises).then(() => {
                      if (window.utils && window.utils.hideLoading) {
                          window.utils.hideLoading();
                      } else if (window.dashboardChartInstance) {
                          window.dashboardChartInstance.hideLoading();
                      }
                      
                      if (chartTabsArea) {
                          if (anyChecked) {
                              chartTabsArea.classList.remove('d-none');
                              setTimeout(() => {
                                  if (firstBtn) firstBtn.click();
                                  else if (window.dashboardChartInstance) window.dashboardChartInstance.resize();
                              }, 50);
                          } else {
                              chartTabsArea.classList.add('d-none');
                              const emptyPane = document.getElementById('chartPane-Empty');
                              if (emptyPane) emptyPane.classList.remove('d-none');
                          }
                      }
                  }).catch(() => {
                      if (window.utils && window.utils.hideLoading) {
                          window.utils.hideLoading();
                      } else if (window.dashboardChartInstance) {
                          window.dashboardChartInstance.hideLoading();
                      }
                  });
              } else {
                  if (window.utils && window.utils.hideLoading) window.utils.hideLoading();
                  utils.alert('資料分析失敗: ' + data.error, 'error');
              }
          })
          .catch(err => {
              if (window.utils && window.utils.hideLoading) {
                  window.utils.hideLoading();
              } else if (window.dashboardChartInstance) {
                  window.dashboardChartInstance.hideLoading();
              }
              utils.alert('發生系統錯誤，請稍後再試。', 'error');
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
      const fileId = btn.dataset.fileId;
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
              body: JSON.stringify({ file_id: fileId })
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

}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboardControl);
} else {
  initDashboardControl();
}
