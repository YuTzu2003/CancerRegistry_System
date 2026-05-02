const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');
const fileInfo = document.getElementById('fileInfo');
const fileNameDisplay = document.getElementById('fileName');
const configSection = document.getElementById('configSection');
const resultSection = document.getElementById('resultSection');
const actionGroup = document.getElementById('actionGroup');
const loadingOverlay = document.getElementById('loadingOverlay');

uploadArea.onclick = () => fileInput.click();

fileInput.onchange = (e) => {
  if (e.target.files.length > 0) {
    fileNameDisplay.innerText = e.target.files[0].name;
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    configSection.style.display = 'block';
    actionGroup.style.display = 'flex';
    configSection.scrollIntoView({ behavior: 'smooth' });
  }
};

function resetUpload() {
  fileInput.value = '';
  uploadArea.style.display = 'block';
  fileInfo.style.display = 'none';
  configSection.style.display = 'none';
  resultSection.style.display = 'none';
  actionGroup.style.display = 'none';
  document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
    cb.checked = cb.hasAttribute('checked');
    cb.checked ? cb.parentElement.classList.add('selected') : cb.parentElement.classList.remove('selected');
  });
}

function generateMockData() {
  loadingOverlay.style.display = 'flex';
  
  setTimeout(() => {
    loadingOverlay.style.display = 'none';
    
    const tbody = document.getElementById('previewBody');
    let rows = '';
    for(let i=1; i<=20; i++) {
      rows += `
        <tr>
          <td>${i}</td>
          <td><code>M${Math.floor(Math.random()*90000)+10000}</code></td>
          <td>王*${['明','強','玲','美'][Math.floor(Math.random()*4)]}</td>
          <td>A12****${Math.floor(Math.random()*900)+100}</td>
          <td>${1950+Math.floor(Math.random()*50)}/01/01</td>
          <td>2023/${Math.floor(Math.random()*12)+1}/01</td>
          <td>肺部</td>
          <td>T${Math.floor(Math.random()*4)}</td>
          <td>N${Math.floor(Math.random()*3)}</td>
          <td>M${Math.floor(Math.random()*2)}</td>
          <td>Stage ${['I','II','III','IV'][Math.floor(Math.random()*4)]}</td>
          <td>手術</td>
          <td>2024/01/01</td>
        </tr>
      `;
    }
    tbody.innerHTML = rows;
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
  }, 2000);
}

document.querySelectorAll('.field-chip input').forEach(checkbox => {
  if (checkbox.checked) checkbox.parentElement.classList.add('selected');
  checkbox.addEventListener('change', function() {
    this.checked ? this.parentElement.classList.add('selected') : this.parentElement.classList.remove('selected');
  });
});