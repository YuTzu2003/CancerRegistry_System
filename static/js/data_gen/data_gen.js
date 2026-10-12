const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileNameDisplay = document.getElementById('fileName');
const txtHeaderOption = document.getElementById('txtHeaderOption');
const txtHasHeader = document.getElementById('txtHasHeader');
const analyzeFileBtn = document.getElementById('analyzeFileBtn');
const selectAllExtraFieldsBtn = document.getElementById('btnSelectAllDataGenExtras');
const clearAllExtraFieldsBtn = document.getElementById('btnClearAllDataGenExtras');
const configSection = document.getElementById('configSection');
const namingSection = document.getElementById('namingSection');
const resultSection = document.getElementById('resultSection');
const actionGroup = document.getElementById('actionGroup');
const loadingOverlay = document.getElementById('loadingOverlay');

let currentColumns = [];
let downloadUrl = '';
let selectedUploadFile = null;

function extraFieldCheckboxes() {
    return Array.from(document.querySelectorAll('#outputFieldList .extra-field-checkbox'));
}

function syncExtraFieldControls() {
    const checkboxes = extraFieldCheckboxes();
    const selectedCount = checkboxes.filter(checkbox => checkbox.checked).length;
    const hasUnmatchedFields = checkboxes.length > 0;
    if (selectAllExtraFieldsBtn) {
        selectAllExtraFieldsBtn.disabled = !hasUnmatchedFields || selectedCount === checkboxes.length;
    }
    if (clearAllExtraFieldsBtn) {
        clearAllExtraFieldsBtn.disabled = !hasUnmatchedFields || selectedCount === 0;
    }
}

function setExtraFieldsChecked(checked) {
    extraFieldCheckboxes().forEach(checkbox => {
        checkbox.checked = checked;
        checkbox.closest('.field-chip')?.classList.toggle('selected', checked);
    });
    syncExtraFieldControls();
}

selectAllExtraFieldsBtn?.addEventListener('click', () => setExtraFieldsChecked(true));
clearAllExtraFieldsBtn?.addEventListener('click', () => setExtraFieldsChecked(false));

uploadArea.onclick = () => fileInput.click();

document.querySelectorAll('input[name="nameScheme"]').forEach(radio => {
    radio.addEventListener('change', function() {
        document.querySelectorAll('#namingScheme .naming-chip').forEach(c => c.classList.remove('selected'));
        this.closest('.naming-chip').classList.add('selected');

        const newSelected = this.value;
        if (currentColumns.length > 0) {
            renderExtraFields(currentColumns, newSelected);
        }
    });
});

document.querySelectorAll('#namingScheme .naming-chip').forEach(chip => {
});

fileInput.onchange = async (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        const formatSelect = document.getElementById('formatSelect');
        if (!formatSelect?.value) {
            utils.alert('請先選擇參考資料格式', 'warning');
            fileInput.value = '';
            return;
        }

        selectedUploadFile = file;
        fileNameDisplay.innerText = file.name;
        fileInfo.style.display = 'flex';

        const isTxt = file.name.toLowerCase().endsWith('.txt');
        txtHeaderOption.style.display = isTxt ? 'block' : 'none';
        txtHasHeader.checked = false;
        analyzeFileBtn.style.display = isTxt ? 'inline-flex' : 'none';

        if (!isTxt) {
            analyzeSelectedFile();
        }
    }
};

async function analyzeSelectedFile() {
    const file = selectedUploadFile || fileInput.files?.[0];
    if (!file) {
        utils.alert('請先選擇檔案', 'warning');
        return;
    }

    const isTxt = file.name.toLowerCase().endsWith('.txt');
    if (isTxt && !txtHasHeader.checked && !document.getElementById('formatSelect')?.value) {
        utils.alert('無標頭 TXT 請先選擇參考資料格式', 'warning');
        return;
    }

        const formData = new FormData();
        formData.append('file', file);
        formData.append('format_id', document.getElementById('formatSelect')?.value || '');
        formData.append('txt_has_header', isTxt && txtHasHeader.checked ? 'true' : 'false');
        
        loadingOverlay.querySelector('.h5').innerText = "分析檔案欄位中...";
        loadingOverlay.style.display = 'flex';
        
        try {
            const resp = await fetch('/api/data_gen/analyze', { method: 'POST', body: formData });
            const res = await resp.json();
            loadingOverlay.style.display = 'none';
            
            if (res.ok) {
                currentColumns = res.analyzed_columns;
                
                renderFixedFields(currentColumns);
                const selectedScheme = document.querySelector('input[name="nameScheme"]:checked')?.value || 'field_name_zh';
                renderExtraFields(currentColumns, selectedScheme);
                
                uploadArea.style.display = 'none';
                fileInfo.style.display = 'flex';
                txtHeaderOption.style.display = 'none';
                analyzeFileBtn.style.display = 'none';
                document.getElementById('formatSelect').disabled = true;
                namingSection.style.display = 'block';
                configSection.style.display = 'block';
                actionGroup.style.display = 'flex';
                namingSection.scrollIntoView({ behavior: 'smooth' });
            } else if (res.has_length_error) {
                showFixedWidthLengthError(res);
            } else {
                utils.alert("分析失敗: " + res.error, "error");
            }
        } catch (err) {
            loadingOverlay.style.display = 'none';
            utils.alert("上傳發生錯誤", "error");
        }
}

function downloadBase64File(base64Data, filename, mimeType) {
    const binary = atob(base64Data);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
        bytes[index] = binary.charCodeAt(index);
    }

    const url = URL.createObjectURL(new Blob([bytes], { type: mimeType }));
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
}

function showFixedWidthLengthError(result) {
    const sourceName = result.filename || 'uploaded_file.txt';
    const baseName = sourceName.includes('.')
        ? sourceName.slice(0, sourceName.lastIndexOf('.'))
        : sourceName;

    Swal.fire({
        icon: 'warning',
        title: '固定欄位長度不符',
        confirmButtonText: '關閉',
        confirmButtonColor: '#2563eb',
        html: `
            <div class="text-start px-1">
                <div class="rounded-3 border bg-light p-3 text-secondary small lh-base">
                    <div class="fw-semibold text-dark mb-1">檢查結果</div>
                    <div data-length-error-detail></div>
                </div>
                <div class="small text-muted mt-3 mb-2">可下載下列檔案協助確認問題：</div>
                <div class="d-grid gap-2">
                    <button type="button" class="btn btn-outline-primary" data-length-download="xlsx">
                        <i class="bi bi-file-earmark-excel me-1"></i>下載欄位拆解檢視 XLSX
                    </button>
                    <button type="button" class="btn btn-outline-secondary" data-length-download="log">
                        <i class="bi bi-file-earmark-text me-1"></i>下載完整錯誤 Log
                    </button>
                </div>
            </div>`,
        didOpen: (popup) => {
            const detail = popup.querySelector('[data-length-error-detail]');
            if (detail) detail.textContent = result.error || '固定欄位資料長度不符。';
            popup.querySelector('[data-length-download="xlsx"]')?.addEventListener('click', () => {
                if (result.xlsx_data) {
                    downloadBase64File(
                        result.xlsx_data,
                        `欄位拆解檢視_${baseName}.xlsx`,
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    );
                }
            });
            popup.querySelector('[data-length-download="log"]')?.addEventListener('click', () => {
                if (result.log_data) {
                    downloadBase64File(result.log_data, `長度錯誤_${baseName}.log`, 'text/plain');
                }
            });
        },
    });
}

function renderFixedFields(analyzedColumns) {
    const dateGrid = document.getElementById('dateFields');
    const specialGrid = document.getElementById('specialFields');

    dateGrid.replaceChildren(...analyzedColumns.map(col => {
        const label = document.createElement('label');
        label.className = `field-chip${col.is_date ? ' selected' : ''}`;
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.value = col.name;
        input.checked = col.is_date;
        label.append(input, document.createTextNode(` ${col.name}`));
        return label;
    }));

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

    document.querySelectorAll('.config-section .field-chip input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
        });
    });
}

function renderExtraFields(analyzedColumns, selectedScheme) {
    const outputFieldList = document.getElementById('outputFieldList');

    const extraCols = analyzedColumns.filter(col => {
        if (!col.seq) return true;
        if (selectedScheme === 'original') return false;
        const targetName = col.mappings[selectedScheme];
        return !targetName || targetName.trim() === '';
    }).sort((left, right) => (left.source_index ?? Number.MAX_SAFE_INTEGER) - (right.source_index ?? Number.MAX_SAFE_INTEGER));

    const matchedSummary = document.createElement('span');
    matchedSummary.className = 'field-chip disabled';
    matchedSummary.innerHTML = `<i class="bi bi-check-circle text-success"></i> 已匹配 ${analyzedColumns.length - extraCols.length}／${analyzedColumns.length} 個欄位`;
    outputFieldList.replaceChildren(matchedSummary);

    if (extraCols.length === 0) {
        const noUnmatched = document.createElement('span');
        noUnmatched.className = 'field-chip disabled';
        noUnmatched.innerHTML = '<i class="bi bi-check2 text-success"></i> 無未匹配欄位';
        outputFieldList.appendChild(noUnmatched);
    } else {
        outputFieldList.append(...extraCols.map(col => {
            const label = document.createElement('label');
            label.className = 'field-chip selected';
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.className = 'extra-field-checkbox';
            input.value = col.name;
            input.checked = true;
            label.append(input, document.createTextNode(` ${col.name}`));
            return label;
        }));
    }

    outputFieldList.querySelectorAll('input').forEach(cb => {
        cb.addEventListener('change', function() {
            this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
            syncExtraFieldControls();
        });
    });
    syncExtraFieldControls();
}

async function generateMockData() {
    const formatSelect = document.getElementById('formatSelect');
    const formatId = formatSelect ? formatSelect.value : '';

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
                format_id: formatId,
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
    const previewContainer = document.querySelector('.table-preview-container');
    
    if (data.length === 0) return;
    
    if (!headers) {
        headers = Object.keys(data[0]);
    }
    const headerRow = document.createDocumentFragment();
    const indexHeader = document.createElement('th');
    indexHeader.textContent = '#';
    headerRow.append(indexHeader);
    headers.forEach(header => {
        const cell = document.createElement('th');
        cell.textContent = header;
        headerRow.append(cell);
    });
    thead.replaceChildren(headerRow);

    const rows = document.createDocumentFragment();
    data.forEach((row, idx) => {
        const tr = document.createElement('tr');
        const indexCell = document.createElement('td');
        indexCell.textContent = idx + 1;
        tr.append(indexCell);
        headers.forEach(header => {
            const cell = document.createElement('td');
            cell.textContent = row[header] ?? '';
            tr.append(cell);
        });
        rows.append(tr);
    });
    tbody.replaceChildren(rows);
    if (previewContainer) {
        previewContainer.scrollLeft = 0;
        previewContainer.scrollTop = 0;
    }
}

function downloadResult() {
    if (downloadUrl) {
        window.location.href = downloadUrl;
    }
}

function resetUpload() {
    fileInput.value = '';
    const formatSelect = document.getElementById('formatSelect');
    if (formatSelect) {
        formatSelect.value = '';
        formatSelect.disabled = false;
    }
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    namingSection.style.display = 'none';
    configSection.style.display = 'none';
    resultSection.style.display = 'none';
    actionGroup.style.display = 'none';
    txtHeaderOption.style.display = 'none';
    if (txtHasHeader) txtHasHeader.checked = false;
    if (analyzeFileBtn) analyzeFileBtn.style.display = 'none';
    
    currentColumns = [];
    downloadUrl = '';
    selectedUploadFile = null;
    document.getElementById('dateFields').innerHTML = '';
    document.getElementById('specialFields').innerHTML = '';
    document.getElementById('outputFieldList').innerHTML = '<span class="field-chip disabled"><i class="bi bi-asterisk"></i> 尚未載入欄位，請先上傳檔案</span>';
    syncExtraFieldControls();
    document.getElementById('previewBody').innerHTML = '';
    const previewContainer = document.querySelector('.table-preview-container');
    if (previewContainer) {
        previewContainer.scrollLeft = 0;
        previewContainer.scrollTop = 0;
    }

    document.querySelectorAll('#namingScheme .naming-chip').forEach(c => c.classList.remove('selected'));
    const defaultRadio = document.querySelector('input[name="nameScheme"][value="field_name_zh"]');
    if (defaultRadio) {
        defaultRadio.checked = true;
        defaultRadio.closest('.naming-chip').classList.add('selected');
    }
}
