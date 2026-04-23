let userModal;
document.addEventListener('DOMContentLoaded', () => {
    const userModalEl = document.getElementById('userModal');
    if (userModalEl) userModal = new bootstrap.Modal(userModalEl);

    document.getElementById('userTableBody').addEventListener('click', (e) => {
        const editBtn = e.target.closest('.btn-edit-user');
        if (editBtn) {
            const userData = JSON.parse(editBtn.getAttribute('data-user'));
            prepareEditUser(userData);
        }
    });
});

function filterUsers() {
    const q = document.getElementById('userSearch').value.toLowerCase();
    const rows = document.querySelectorAll('.user-row');
    let visibleCount = 0;

    rows.forEach(row => {
        const searchText = row.getAttribute('data-search');
        if (searchText.includes(q)) {
            row.style.display = '';
            visibleCount++;
        } else {
            row.style.display = 'none';
        }
    });

    document.getElementById('noData').style.display = visibleCount === 0 ? 'block' : 'none';
    document.getElementById('userTable').style.display = visibleCount === 0 ? 'none' : 'table';
}

function prepareAddUser() {
    document.getElementById('userForm').reset();
    document.getElementById('formId').value = '';
    document.getElementById('modalTitle').textContent = '新增管理帳號';
    userModal.show();
}

function prepareEditUser(user) {
    document.getElementById('userForm').reset();
    document.getElementById('modalTitle').textContent = '編輯帳號資訊';
    document.getElementById('formId').value = user.ID;
    document.getElementById('formUserID').value = user.UserID;
    document.getElementById('formPassword').value = user.Password;
    document.getElementById('formName').value = user.Name;
    document.getElementById('formPosition').value = user.Position;
    document.getElementById('formLocation').value = user.Location || '';
    userModal.show();
}