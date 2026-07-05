(function() {
  /* ── 狀態管理與介面更新邏輯 ── */
  window.selectedCancers = new Set();
  
  function updateStatus() {
    const status = document.getElementById('cancerPickerStatus');
    const leafNodes = document.querySelectorAll('.cancer-cb-leaf:not([value="All_Cancers"])');
    const allCancersNode = document.querySelector('.cancer-cb-leaf[value="All_Cancers"]');
    
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
            if (node.checked) {
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
               if(node.checked) {
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
        const cb = document.querySelector(`.cancer-cb-leaf[value="${id}"]`);
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

  updateParentCheckboxes();
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
              utils.alert('請先輸入四位數的年度！', 'warning');
              return;
          }
          
          const behaviorVal = document.getElementById('filterBehavior')?.value;
          if (!behaviorVal) {
              utils.alert('請先選擇性態碼！', 'warning');
              return;
          }

          if (!selectedFile) {
              utils.alert('請先從上方檔案列表點選要分析的檔案！', 'warning');
              return;
          }

          if (window.utils && window.utils.showLoading) {
              window.utils.showLoading('分析中，請稍候...');
          } else if (window.dashboardChartInstance) {
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
                  


                  const btnAiMain = document.getElementById('btnAiMain');
                  const btnAiMedian = document.getElementById('btnAiMedian');
                  const btnAiAnalyzable = document.getElementById('btnAiAnalyzable');
                  const btnAiHistology = document.getElementById('btnAiHistology');
                  
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
                  if (btnAiHistology) {
                      btnAiHistology.style.display = 'block';
                      btnAiHistology.innerHTML = '重新產生敘述';
                      btnAiHistology.onclick = () => window.DashboardRenderer.fetchLlmInsight('組織型態分佈', window.lastChartData.histologyData, ['組織型態', '個案數'], 'llmResponseHistology', 'btnAiHistology');
                  }

                  const llmResponseMain = document.getElementById('llmResponseMain');
                  if (llmResponseMain) llmResponseMain.innerText = '（系統將自動產生分析敘述）';
                  const llmResponseMedian = document.getElementById('llmResponseMedian');
                  if (llmResponseMedian) llmResponseMedian.innerText = '（系統將自動產生分析敘述）';
                  const llmResponseAnalyzable = document.getElementById('llmResponseAnalyzable');
                  if (llmResponseAnalyzable) llmResponseAnalyzable.innerText = '（系統將自動產生分析敘述）';
                  const llmResponseHistology = document.getElementById('llmResponseHistology');
                  if (llmResponseHistology) llmResponseHistology.innerText = '（系統將自動產生分析敘述）';

                  if (window.DashboardRenderer) {
                      const yearTitle = window.DashboardRenderer.getSelectedYearTitle();
                      const cancerTitle = window.DashboardRenderer.getSelectedCancerTitle();
                      window.DashboardRenderer.renderSexAgeTable(chartData.genderAgeData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAgeMedianTable(chartData.ageMedianData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderAnalyzableConfirmedTable(chartData.analyzableConfirmedData, yearTitle, cancerTitle);
                      window.DashboardRenderer.renderHistologyTable(chartData.histologyData, yearTitle, cancerTitle);
                      window.DashboardRenderer.showAnnualDataContent();
                      const chartCaption = document.getElementById('annualSexAgeChartCaption');
                      if (chartCaption) {
                          chartCaption.innerText = `圖、${yearTitle}年新診斷${window.DashboardRenderer.getCancerTitleForSentence(cancerTitle)}病患性別及年齡分佈圖`;
                      }
                      const histologyChartCaption = document.getElementById('annualHistologyChartCaption');
                      if (histologyChartCaption) {
                          histologyChartCaption.innerText = `圖、${yearTitle}年${window.DashboardRenderer.getCancerTitleForSentence(cancerTitle)}組織型態分佈圖`;
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

                  if (window.dashboardHistologyChartInstance && chartData.histologyData) {
                      const yearTitle = window.DashboardRenderer ? window.DashboardRenderer.getSelectedYearTitle() : '';
                      const cancerTitle = window.DashboardRenderer ? window.DashboardRenderer.getSelectedCancerTitle() : '';
                      const cancerTitleSent = window.DashboardRenderer ? window.DashboardRenderer.getCancerTitleForSentence(cancerTitle) : '';
                      const validData = chartData.histologyData.filter(item => item.name !== 'Unknown / 未對應組織型態');
                      const topData = validData.reverse();
                      const categories = topData.map(item => item.name);
                      const counts = topData.map(item => item.count);

                      // 動態調整圖表高度，防止柱狀圖項目過多時擠壓重疊
                      const chartDom = document.getElementById('histologyChart');
                      if (chartDom) {
                          const computedHeight = Math.max(450, categories.length * 30); // 每筆資料給予 30px 的垂直空間，最低 450px
                          chartDom.style.height = computedHeight + 'px';
                          window.dashboardHistologyChartInstance.resize();
                      }

                      window.dashboardHistologyChartInstance.setOption({
                          title: { 
                              text: `${yearTitle}年${cancerTitleSent}組織型態分佈圖`, 
                              subtext: selectedFile,
                              left: 'center'
                          },
                          yAxis: { data: categories },
                          series: [
                              { data: counts }
                          ]
                      });
                  }
                  
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