function openDetail(jobId) {
    fetch(`/history/detail/${jobId}`)
        .then(response => response.json())
        .then(res => {
            if (res.ok && res.data) {
                const data = res.data;
                document.getElementById('detail-jobId').innerText = data.JobID || '無資料';
                document.getElementById('detail-createdAt').innerText = data.CreatedAt || '-';
                
                // 格式名稱
                const fmtDisplay = (data.FmtName && data.Version) ? `${data.FmtName}欄位(${data.Version})`:(data.FmtName || '未指定');
                document.getElementById('detail-fmtName').innerText = fmtDisplay;
                
                // 數值(%)
                document.getElementById('detail-totalCount').innerText = data.TotalCount ? data.TotalCount.toLocaleString() + ' 筆' : '0 筆';
                document.getElementById('detail-compScore').innerText = data.CompletenessScore ? (data.CompletenessScore * 100).toFixed(2) + '%' : '-';
                document.getElementById('detail-corrScore').innerText = data.CorrectScore ? (data.CorrectScore * 100).toFixed(2) + '%' : '-';
                document.getElementById('detail-consScore').innerText = data.ConsistencyScore ? (data.ConsistencyScore * 100).toFixed(2) + '%' : '-';
                document.getElementById('detail-dqi').innerText = data.DQI ? data.DQI.toFixed(2) + '%' : '-';
                
                // 設定下載連結
                document.getElementById('btnDownloadLink').href = `/history/download/${jobId}`;
                
                const detailModal = new bootstrap.Modal(document.getElementById('jobDetailModal'));
                detailModal.show();
            } 
            else {
                utils.alert(res.error, "error");
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

document.addEventListener('DOMContentLoaded', () => {
    const filterFormat = document.getElementById('filterFormat');
    const historyTable = document.getElementById('historyTable');
    if (!historyTable) return;

    const tbody = historyTable.querySelector('tbody');
    const selectAll = document.getElementById('selectAll');

    // 全選
    if (selectAll) {
        selectAll.addEventListener('change', () => {
            const checkboxes = tbody.querySelectorAll('.row-checkbox');
            checkboxes.forEach(cb => {
                if (cb.closest('tr').style.display !== 'none') {
                    cb.checked = selectAll.checked;
                }
            });
        });
    }

    // 格式篩選
    if (filterFormat) {
        filterFormat.addEventListener('change', () => {
            const val = filterFormat.value;
            const rows = tbody.querySelectorAll('.history-row');
            rows.forEach(row => {
                if (val === 'all' || row.dataset.format === val) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                    const cb = row.querySelector('.row-checkbox');
                    if (cb) cb.checked = false;
                }
            });
            if (selectAll) selectAll.checked = false;
        });
    }
});

// 取得選取的 JobID
function getSelectedIds() {
    const checkboxes = document.querySelectorAll('.row-checkbox:checked');
    return Array.from(checkboxes).map(cb => cb.value);
}

// 批次刪除
async function batchDelete() {
    const ids = getSelectedIds();
    if (ids.length === 0) {
        utils.alert('請先勾選欲刪除的項目。', 'warning');
        return;
    }

    const confirmed = await utils.confirm(`確定要刪除這 ${ids.length} 筆紀錄嗎？此動作無法復原。`);
    if (!confirmed.isConfirmed) return;

    fetch('/history/batch_delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_ids: ids })
    })
    .then(r => r.json())
    .then(res => {
        if (res.ok) {
            location.reload();
        } else {
            utils.alert(res.error || '刪除失敗', 'error');
        }
    })
    .catch(err => {
        console.error(err);
    });
}

// 批次下載
async function batchDownload() {
    const ids = getSelectedIds();
    if (ids.length === 0) {
        utils.alert('請先勾選欲下載的項目。', 'warning');
        return;
    }
    
    const confirmed = await utils.confirm(`確定要下載這 ${ids.length} 筆選取的紀錄嗎？`, '確認下載');
    if (!confirmed.isConfirmed) return;
    
    try {
        const response = await fetch('/history/batch_download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ job_ids: ids })
        });

        if (!response.ok) {
            const res = await response.json();
            throw new Error(res.error || '下載失敗');
        }

        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Batch_Download_${new Date().getTime()}.zip`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        console.error(err);
        utils.alert(err.message || '下載發生錯誤', 'error');
    }
}