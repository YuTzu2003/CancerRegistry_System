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
                alert((res.error));
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('系統連線發生錯誤，請稍後再試。');
        });
}

document.addEventListener('DOMContentLoaded', () => {
    const filterFormat = document.getElementById('filterFormat');
    const historyTable = document.getElementById('historyTable');
    if (!historyTable) return;

    const tbody = historyTable.querySelector('tbody');

    // 格式篩選邏輯
    if (filterFormat) {
        filterFormat.addEventListener('change', () => {
            const val = filterFormat.value;
            const rows = tbody.querySelectorAll('.history-row');
            rows.forEach(row => {
                if (val === 'all' || row.dataset.format === val) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});