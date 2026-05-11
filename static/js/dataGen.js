const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileNameDisplay = document.getElementById('fileName');
const configSection = document.getElementById('configSection');
const resultSection = document.getElementById('resultSection');
const actionGroup = document.getElementById('actionGroup');
const loadingOverlay = document.getElementById('loadingOverlay');

let currentColumns = [];
let downloadUrl = '';

uploadArea.onclick = () => fileInput.click();

fileInput.onchange = async (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        fileNameDisplay.innerText = file.name;
        
        // 1. 上傳並分析欄位
        const formData = new FormData();
        formData.append('file', file);
        
        loadingOverlay.querySelector('.h5').innerText = "分析檔案欄位中...";
        loadingOverlay.style.display = 'flex';
        
        try {
            const resp = await fetch('/api/data_gen/analyze', { method: 'POST', body: formData });
            const res = await resp.json();
            loadingOverlay.style.display = 'none';
            
            if (res.ok) {
                currentColumns = res.analyzed_columns;
                renderColumnSelectors(res.analyzed_columns);
                
                uploadArea.style.display = 'none';
                fileInfo.style.display = 'flex';
                configSection.style.display = 'block';
                actionGroup.style.display = 'flex';
                configSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                utils.alert("分析失敗: " + res.error, "error");
            }
        } catch (err) {
            loadingOverlay.style.display = 'none';
            utils.alert("上傳發生錯誤", "error");
        }
    }
};

function renderColumnSelectors(analyzedColumns) {
    const dateGrid = document.getElementById('dateFields');
    const specialGrid = document.getElementById('specialFields');
    
    // 清空
    dateGrid.innerHTML = '';
    specialGrid.innerHTML = '';
    
    // 1. 渲染日期欄位
    analyzedColumns.forEach(col => {
        dateGrid.innerHTML += `
            <label class="field-chip ${col.is_date ? 'selected' : ''}">
                <input type="checkbox" value="${col.name}" ${col.is_date ? 'checked' : ''}> ${col.name}
            </label>
        `;
    });

    // 2. 渲染特殊欄位 (動態顯示匹配到的原始欄位名稱)
    const specialRules = [
        { key: 'cno', label: '病歷號', hint: '轉為TEST+編號' },
        { key: 'name', label: '姓名', hint: '遮罩為姓氏OO' },
        { key: 'id', label: '身分證號', hint: '遮罩為A1********' },
        { key: 'gender', label: '性別', hint: '隨機重置' },
        { key: 'district', label: '戶籍地', hint: '隨機4碼代碼' },
        { key: 'age_calc', label: '年齡重算', hint: '需有生日與診斷日' }
    ];

    specialRules.forEach(rule => {
        // 尋找對應的原始欄位
        const matchedCol = analyzedColumns.find(col => col.special_key === rule.key);
        
        // 組合標籤文字： 標準名稱 + [原始名稱] + 功能說明
        let displayText = rule.label;
        if (matchedCol) {
            displayText += ` <span class="small text-primary fw-bold">[${matchedCol.name}]</span>`;
        }
        displayText += ` <span class="small text-muted">(${rule.hint})</span>`;

        specialGrid.innerHTML += `
            <label class="field-chip ${matchedCol ? 'selected' : ''}" style="width: 100%; justify-content: flex-start; padding: 10px 15px;">
                <input type="checkbox" data-key="${rule.key}" ${matchedCol ? 'checked' : ''}> 
                <span class="ms-2">${displayText}</span>
            </label>
        `;
    });

    // 重新綁定事件
    document.querySelectorAll('.field-chip input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
        });
    });
}

async function generateMockData() {
    const dateCols = Array.from(document.querySelectorAll('#dateFields input:checked')).map(i => i.value);
    const specialConfigs = {};
    document.querySelectorAll('#specialFields input').forEach(i => {
        specialConfigs[i.dataset.key] = i.checked;
    });

    loadingOverlay.querySelector('.h5').innerText = "虛擬資料建置生成中...";
    loadingOverlay.style.display = 'flex';
    
    try {
        const resp = await fetch('/api/data_gen/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ date_cols: dateCols, special_configs: specialConfigs })
        });
        const res = await resp.json();
        loadingOverlay.style.display = 'none';

        if (res.ok) {
            downloadUrl = res.download_url;
            renderPreview(res.preview);
            resultSection.style.display = 'block';
            resultSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            utils.alert("生成失敗: " + res.error, "error");
        }
    } catch (err) {
        loadingOverlay.style.display = 'none';
        utils.alert("執行發生錯誤", "error");
    }
}

function renderPreview(data) {
    const tbody = document.getElementById('previewBody');
    const thead = document.querySelector('#resultSection thead tr');
    
    if (data.length === 0) return;
    
    // 動態標頭
    const headers = Object.keys(data[0]);
    thead.innerHTML = '<th>#</th>' + headers.map(h => `<th>${h}</th>`).join('');
    
    // 資料列
    tbody.innerHTML = data.map((row, idx) => {
        return `<tr>
            <td>${idx + 1}</td>
            ${headers.map(h => `<td>${row[h]}</td>`).join('')}
        </tr>`;
    }).join('');
}

function downloadResult() {
    if (downloadUrl) {
        window.location.href = downloadUrl;
    }
}

function resetUpload() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    configSection.style.display = 'none';
    resultSection.style.display = 'none';
    actionGroup.style.display = 'none';
}
