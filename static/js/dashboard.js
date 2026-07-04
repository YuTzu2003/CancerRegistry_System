(function() {
  const table = document;

  table.querySelectorAll('.group-checkbox').forEach(groupChk => {
    groupChk.addEventListener('change', function() {
      table.querySelectorAll('.group-checkbox').forEach(chk => {
        const gName = chk.dataset.group;
        const subContainer = document.getElementById(`subItems-${gName}`);
        if (subContainer) {
          if (chk.checked) {
            subContainer.classList.remove('d-none');
            subContainer.style.display = 'flex';
            subContainer.querySelectorAll('.item-checkbox:checked').forEach(item => {item.dispatchEvent(new Event('change'));});
          } 
          else {
            subContainer.classList.add('d-none');
            subContainer.style.display = 'none';
          }
        }
      });
    });
  });

  table.querySelectorAll('.item-checkbox').forEach(itemChk => {
    itemChk.addEventListener('change', function() {
      const chip = this.closest('.field-chip') || this.closest('.naming-chip');
      if (chip) chip.classList.toggle('selected', this.checked);
      updateGroupCheckbox(this.dataset.parent);
    });
  });

  const btnRunQuery = document.getElementById('btnRunQuery');
  if (btnRunQuery) {
    btnRunQuery.addEventListener('click', function() {
      // 這裡原本會將所有勾選的圖表顯示，現在移到 dashboard.html 中的 API 成功後處理
      // 以支援獨立圖表分頁功能。這裡我們只做最初的隱藏。
      document.querySelectorAll('.chart-pane').forEach(pane => {pane.classList.add('d-none');});
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

  function fetchInsight(fieldKey, dataObj, resultDivId, btnId, fields = []) {
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
              data: dataObj,
              fields: fields
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
  }

  document.addEventListener('DOMContentLoaded', function() {
      const btnAiMain = document.getElementById('btnAiMain');
      if (btnAiMain) {
          btnAiMain.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('診斷年齡', window.lastChartData.genderAgeData, 'llmResponseMain', 'btnAiMain', ['性別', '診斷年齡']);
          });
      }

      const btnAiMedian = document.getElementById('btnAiMedian');
      if (btnAiMedian) {
          btnAiMedian.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('年齡中位數', window.lastChartData.ageMedianData, 'llmResponseMedian', 'btnAiMedian', ['性別', '診斷年齡']);
          });
      }
      const btnAiAnalyzable = document.getElementById('btnAiAnalyzable');
      if (btnAiAnalyzable) {
          btnAiAnalyzable.addEventListener('click', function() {
              if (!window.lastChartData) return;
              fetchInsight('可分析個案與確診個案', window.lastChartData.analyzableConfirmedData, 'llmResponseAnalyzable', 'btnAiAnalyzable');
          });
      }
  });
})();
