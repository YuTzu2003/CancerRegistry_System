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
            // Ensure the charts switch to the active sub-items in this group
            subContainer.querySelectorAll('.item-checkbox:checked').forEach(item => {
               item.dispatchEvent(new Event('change'));
            });
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
      updateGroupCheckbox(this.dataset.parent);
    });
  });

  // Apply chart visibility only when Run Query is clicked
  const btnRunQuery = document.getElementById('btnRunQuery');
  if (btnRunQuery) {
    btnRunQuery.addEventListener('click', function() {
      // Hide all chart panes first
      document.querySelectorAll('.chart-pane').forEach(pane => {
        pane.classList.add('d-none');
      });

      let anyChecked = false;

      table.querySelectorAll('.item-checkbox').forEach(itemChk => {
        const targetSelector = itemChk.getAttribute('data-target');
        if (targetSelector && itemChk.checked) {
          const targetPane = document.querySelector(targetSelector);
          if (targetPane) {
            anyChecked = true;
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
      });

      // If no items are checked, show empty pane
      if (!anyChecked) {
          const emptyPane = document.getElementById('chartPane-Empty');
          if (emptyPane) emptyPane.classList.remove('d-none');
      }
    });
  }

  function updateGroupCheckbox(groupName) {
    if (!groupName) return;
    
    let chkId = '';
    if (groupName === 'incidence') chkId = 'chkGroupIncidence';
    else if (groupName === 'diagnosis') chkId = 'chkGroupDiagnosis';
    else if (groupName === 'stage') chkId = 'chkGroupStage';
    else if (groupName === 'treatment') chkId = 'chkGroupTreatment';
    else if (groupName === 'cross_year') chkId = 'chkGroupCrossYear';
    
    if (!chkId) return;
    
    const container = document.getElementById(`subItems-${groupName}`);
    if (!container) return;
    
    const label = document.querySelector(`label[for="${chkId}"]`);
    if (label) {
      const checkedCount = container.querySelectorAll('.item-checkbox:checked').length;
      
      let text = label.innerHTML;
      // Remove existing badge
      text = text.replace(/\s*<span class="badge.*<\/span>$/, '');
      if (checkedCount > 0) {
        text += ` <span class="badge bg-primary rounded-pill ms-1" style="font-size:0.75rem;">${checkedCount}</span>`;
      }
      label.innerHTML = text;
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

      const btnAiMedian = document.getElementById('btnAiMedian');
      if (btnAiMedian) {
          btnAiMedian.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('年齡中位數', window.lastChartData.ageMedianTable, 'llmResponseMedian', 'btnAiMedian');
          });
      }
  });
})();
