const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileNameDisplay = document.getElementById('fileName');
const configSection = document.getElementById('configSection');
const namingSection = document.getElementById('namingSection');
const resultSection = document.getElementById('resultSection');
const actionGroup = document.getElementById('actionGroup');
const loadingOverlay = document.getElementById('loadingOverlay');

let currentColumns = [];
let downloadUrl = '';

uploadArea.onclick = () => fileInput.click();

// 命名選擇邏輯 (優化效能：僅在 radio 改變時觸發，並使用較快的方式渲染)
document.querySelectorAll('input[name="nameScheme"]').forEach(radio => {
    radio.addEventListener('change', function() {
        // 更新 UI 樣式 (selected class)
        document.querySelectorAll('#namingScheme .naming-chip').forEach(c => c.classList.remove('selected'));
        this.closest('.naming-chip').classList.add('selected');

        const newSelected = this.value;
        // 當切換命名格式時，只重新渲染「額外欄位」
        if (currentColumns.length > 0) {
            renderExtraFields(currentColumns, newSelected);
        }
    });
});

// 移除原本標籤上的 click 事件以避免重複觸發
document.querySelectorAll('#namingScheme .naming-chip').forEach(chip => {
    // 這裡我們不再需要綁定 click，因為 radio 的 change 就夠了
});

fileInput.onchange = async (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        fileNameDisplay.innerText = file.name;
        
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
                
                // 初次渲染所有區塊
                renderFixedFields(currentColumns);
                const selectedScheme = document.querySelector('input[name="nameScheme"]:checked')?.value || 'field_name_zh';
                renderExtraFields(currentColumns, selectedScheme);
                
                uploadArea.style.display = 'none';
                fileInfo.style.display = 'flex';
                namingSection.style.display = 'block';
                configSection.style.display = 'block';
                actionGroup.style.display = 'flex';
                namingSection.scrollIntoView({ behavior: 'smooth' });
            } else {
                utils.alert("分析失敗: " + res.error, "error");
            }
        } catch (err) {
            loadingOverlay.style.display = 'none';
            utils.alert("上傳發生錯誤", "error");
        }
    }
};

// 渲染「固定」的區塊 (日期、特殊欄位) - 只有上傳檔案時跑一次
function renderFixedFields(analyzedColumns) {
    const dateGrid = document.getElementById('dateFields');
    const specialGrid = document.getElementById('specialFields');
    
    // 使用陣列組合字串，效能比 innerHTML += 更好
    const dateHtml = analyzedColumns.map(col => `
        <label class="field-chip ${col.is_date ? 'selected' : ''}">
            <input type="checkbox" value="${col.name}" ${col.is_date ? 'checked' : ''}> ${col.name}
        </label>
    `).join('');
    dateGrid.innerHTML = dateHtml;

    // 2. 特殊
    const specialRules = [
        { key: 'cno', label: '病歷號', hint: '轉為TEST+編號' },
        { key: 'name', label: '姓名', hint: '遮罩為姓氏OO' },
        { key: 'id', label: '身分證號', hint: '遮罩為A1********' },
        { key: 'gender', label: '性別', hint: '隨機重置' },
        { key: 'district', label: '戶籍地', hint: '隨機4碼代碼' },
        { key: 'age_calc', label: '年齡重算', hint: '需有生日與診斷日' }
    ];

    const specialHtml = specialRules.map(rule => {
        const matchedCol = analyzedColumns.find(col => col.special_key === rule.key);
        let displayText = rule.label;
        if (matchedCol) {
            displayText += ` <span class="small text-primary fw-bold">[${matchedCol.name}]</span>`;
        }
        displayText += ` <span class="small text-muted">(${rule.hint})</span>`;

        return `
            <label class="field-chip ${matchedCol ? 'selected' : ''}" style="width: 100%; justify-content: flex-start; padding: 10px 15px;">
                <input type="checkbox" data-key="${rule.key}" ${matchedCol ? 'checked' : ''}> 
                <span class="ms-2">${displayText}</span>
            </label>
        `;
    }).join('');
    specialGrid.innerHTML = specialHtml;

    // 綁定樣式事件
    document.querySelectorAll('.config-section .field-chip input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
        });
    });
}

// 渲染「動態」區塊 (額外欄位) - 優化效能與預設勾選
function renderExtraFields(analyzedColumns, selectedScheme) {
    const outputFieldList = document.getElementById('outputFieldList');

    const extraCols = analyzedColumns.filter(col => {
        if (!col.seq) return true;
        const targetName = col.mappings[selectedScheme];
        return !targetName || targetName.trim() === '';
    });

    if (extraCols.length === 0) {
        outputFieldList.innerHTML = '<span class="text-muted small">所有欄位皆已正確匹配，無額外欄位。</span>';
    } else {
        const extraHtml = extraCols.map(col => `
            <label class="field-chip selected">
                <input type="checkbox" class="extra-field-checkbox" value="${col.name}" checked> ${col.name}
            </label>
        `).join('');
        outputFieldList.innerHTML = extraHtml;
    }

    // 綁定額外欄位的樣式事件
    outputFieldList.querySelectorAll('input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
        });
    });
}

async function generateMockData() {
    const dateCols = Array.from(document.querySelectorAll('#dateFields input:checked')).map(i => i.value);
    const extraCols = Array.from(document.querySelectorAll('.extra-field-checkbox:checked')).map(i => i.value);
    const specialConfigs = {};
    document.querySelectorAll('#specialFields input').forEach(i => {
        specialConfigs[i.dataset.key] = i.checked;
    });

    const namingScheme = document.querySelector('input[name="nameScheme"]:checked').value;

    loadingOverlay.querySelector('.h5').innerText = "虛擬資料建置生成中...";
    loadingOverlay.style.display = 'flex';
    
    try {
        const resp = await fetch('/api/data_gen/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                date_cols: dateCols, 
                extra_cols: extraCols,
                special_configs: specialConfigs,
                naming_scheme: namingScheme
            })
        });
        const res = await resp.json();
        loadingOverlay.style.display = 'none';

        if (res.ok) {
            downloadUrl = res.download_url;
            renderPreview(res.preview, res.headers);
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

function renderPreview(data, headers) {
    const tbody = document.getElementById('previewBody');
    const thead = document.querySelector('#resultSection thead tr');
    
    if (data.length === 0) return;
    
    // 動態標頭：優先使用後端傳來的嚴格排序 headers
    if (!headers) {
        headers = Object.keys(data[0]);
    }
    thead.innerHTML = '<th>#</th>' + headers.map(h => `<th>${h}</th>`).join('');
    
    // 資料列
    tbody.innerHTML = data.map((row, idx) => {
        return `<tr>
            <td>${idx + 1}</td>
            ${headers.map(h => `<td>${row[h] || ''}</td>`).join('')}
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
    namingSection.style.display = 'none';
    configSection.style.display = 'none';
    resultSection.style.display = 'none';
    actionGroup.style.display = 'none';
    
    // 重置狀態與內容
    currentColumns = [];
    downloadUrl = '';
    document.getElementById('dateFields').innerHTML = '';
    document.getElementById('specialFields').innerHTML = '';
    document.getElementById('outputFieldList').innerHTML = '<span class="field-chip disabled"><i class="bi bi-asterisk"></i> 尚未載入欄位，請先上傳檔案</span>';
    document.getElementById('previewBody').innerHTML = '';

    // 重置命名選擇為預設
    document.querySelectorAll('#namingScheme .naming-chip').forEach(c => c.classList.remove('selected'));
    const defaultRadio = document.querySelector('input[name="nameScheme"][value="field_name_zh"]');
    if (defaultRadio) {
        defaultRadio.checked = true;
        defaultRadio.closest('.naming-chip').classList.add('selected');
    }
}
