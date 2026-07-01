/* ── Analysis Items Checkbox Logic ── */
(function() {
  // Use document instead of a specific table container so elements can be placed anywhere
  const table = document;

  // Handle Group Checkbox (Check all items under it)
  table.querySelectorAll('.group-checkbox').forEach(groupChk => {
    groupChk.addEventListener('change', function() {
      
      // For radio buttons, the browser might not fire 'change' on the one that gets unchecked.
      // So we loop through ALL group checkboxes and update their respective sub-items containers.
      table.querySelectorAll('.group-checkbox').forEach(chk => {
        const gName = chk.dataset.group;
        const subContainer = document.getElementById(`subItems-${gName}`);
        if (subContainer) {
          if (chk.checked) {
            subContainer.classList.remove('d-none');
            subContainer.style.display = 'flex';
            // Ensure the chart switches to the active sub-item in this group
            const activeItem = subContainer.querySelector('.item-checkbox:checked');
            if (activeItem) {
               activeItem.dispatchEvent(new Event('change'));
            }
          } else {
            subContainer.classList.add('d-none');
            subContainer.style.display = 'none';
          }
        }
      });

      // (Removed auto-check logic so they can act as independent toolbar options)
    });
  });

  // Handle Item Checkbox (Switching Chart Panes)
  table.querySelectorAll('.item-checkbox').forEach(itemChk => {
    itemChk.addEventListener('change', function() {
      // Toggle selected class on chip (if any remains)
      const chip = this.closest('.field-chip') || this.closest('.naming-chip');
      if (chip) chip.classList.toggle('selected', this.checked);

      if (this.checked) {
        // Hide all chart panes
        table.querySelectorAll('.chart-pane').forEach(pane => {
           pane.classList.add('d-none');
        });
        
        // Find target pane or fallback to empty
        const targetSelector = this.getAttribute('data-target');
        let targetPane = targetSelector ? document.querySelector(targetSelector) : null;
        if (!targetPane) targetPane = document.getElementById('chartPane-Empty');
        if (targetPane) {
            targetPane.classList.remove('d-none');
            
            // Re-render ECharts in the new visible pane to avoid sizing issues
            if (typeof echarts !== 'undefined') {
                setTimeout(() => {
                    const chartDoms = targetPane.querySelectorAll('div[_echarts_instance_], #main, #barChart');
                    chartDoms.forEach(c => {
                       const inst = echarts.getInstanceByDom(c);
                       if (inst) inst.resize();
                    });
                    
                    // Auto-generate AI narrative if data is loaded but narrative is empty
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
      }
      updateGroupCheckbox(this.dataset.parent);
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

/* ── AI Insight Generation Logic ── */
(function() {
  window.lastChartData = null;

  function fetchInsight(fieldKey, dataObj, resultDivId, btnId) {
      const btn = document.getElementById(btnId);
      const resultDiv = document.getElementById(resultDivId);
      if (!btn || !resultDiv) return;
      
      btn.disabled = true;
      resultDiv.innerText = '產生敘述中...';
      
      fetch('/api/chart_insight', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
              field_key: fieldKey,
              data: dataObj
          })
      })
      .then(res => res.json())
      .then(data => {
          btn.disabled = false;
          btn.innerHTML = '重新產生敘述';
          if (data.success) {
              resultDiv.innerText = data.insight;
          } else {
              resultDiv.innerText = '分析失敗: ' + (data.error || '發生錯誤');
          }
      })
      .catch(err => {
          btn.disabled = false;
          btn.innerHTML = '重新產生敘述';
          console.error(err);
          resultDiv.innerText = '系統錯誤，無法取得分析結果。';
      });
  }

  document.addEventListener('DOMContentLoaded', function() {
      const btnAiMain = document.getElementById('btnAiMain');
      if (btnAiMain) {
          btnAiMain.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('診斷年齡', window.lastChartData.genderAgeData, 'llmResponseMain', 'btnAiMain');
          });
      }

      const btnAiBar = document.getElementById('btnAiBar');
      if (btnAiBar) {
          btnAiBar.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('原發部位', window.lastChartData.topCancersData, 'llmResponseBar', 'btnAiBar');
          });
      }
  });
})();