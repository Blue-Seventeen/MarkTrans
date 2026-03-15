const tableSchema = {
    mapping_base: ['id', 'element_name', 'element_name_en', 'element_description', 'element_category', 'weight', 'ast_example_input', 'ast_example_output', 'element_regex_rule', 'element_handler_name'],
    mapping_style: ['id', 'style_name', 'is_active', 'is_deletable', 'remark'],
    mapping_rule: ['id', 'style_id', 'style_rule_name', 'ast_input', 'matching_rule', 'html_output', 'render_name', 'weight']
};

let currentTable = 'mapping_base';
let currentData = [];
let isEditing = false;
let editIndex = -1;

const tableSelect = document.getElementById('tableSelect');
const sortColumnSelect = document.getElementById('sortColumnSelect');
const sortOrderSelect = document.getElementById('sortOrderSelect');
const tableContainer = document.getElementById('tableContainer');
const editModal = document.getElementById('editModal');
const modalTitle = document.getElementById('modalTitle');
const modalForm = document.getElementById('modalForm');

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function refreshSortColumns() {
    const columns = tableSchema[currentTable];
    sortColumnSelect.innerHTML = columns.map(col => `<option value="${col}">${col}</option>`).join('');
}

async function loadTableData() {
    const sortBy = sortColumnSelect.value || tableSchema[currentTable][0];
    const order = sortOrderSelect.value || 'asc';
    const response = await fetch(`/api/db/${currentTable}?sort_by=${encodeURIComponent(sortBy)}&order=${encodeURIComponent(order)}`);
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    currentData = data;
    renderTable();
}

function renderTable() {
    const columns = tableSchema[currentTable];
    if (!currentData.length) {
        tableContainer.innerHTML = '<div style="padding:12px;">暂无数据</div>';
        return;
    }
    const header = columns.map(col => `<th>${col}</th>`).join('');
    const rows = currentData.map((row, index) => {
        const tds = columns.map(col => {
            let value = row[col];
            if (value === null || value === undefined) value = '';
            value = String(value);
            if (value.length > 140) value = `${value.slice(0, 140)}...`;
            return `<td>${escapeHtml(value)}</td>`;
        }).join('');
        return `<tr>${tds}<td><button class="btn btn-primary" data-edit="${index}">编辑</button> <button class="btn btn-danger" data-del="${index}">删除</button></td></tr>`;
    }).join('');
    tableContainer.innerHTML = `<table class="data-table"><thead><tr>${header}<th>操作</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function nextId() {
    const ids = currentData.map(x => Number(x.id) || 0);
    return ids.length ? Math.max(...ids) + 1 : 1;
}

function openModal(rowData = null) {
    const fields = tableSchema[currentTable];
    let html = '<div class="form-grid">';
    fields.forEach(field => {
        const value = rowData ? rowData[field] ?? '' : (field === 'id' ? nextId() : '');
        const readonly = field === 'id' ? 'readonly' : '';
        const isLong = ['element_description', 'ast_example_input', 'ast_example_output', 'element_regex_rule', 'ast_input', 'matching_rule', 'html_output', 'remark'].includes(field);
        const input = isLong
            ? `<textarea name="${field}" rows="4" ${readonly}>${escapeHtml(value)}</textarea>`
            : `<input type="text" name="${field}" value="${escapeHtml(value)}" ${readonly}>`;
        html += `<div class="field"><label>${field}</label>${input}</div>`;
    });
    html += '</div><div style="margin-top:10px;"><button class="btn btn-success" id="saveBtn">保存</button></div>';
    modalForm.innerHTML = html;
    editModal.style.display = 'block';
}

function closeModal() {
    editModal.style.display = 'none';
    modalForm.innerHTML = '';
}

async function saveData() {
    const formFields = modalForm.querySelectorAll('input[name], textarea[name]');
    const data = {};
    formFields.forEach(el => { data[el.name] = el.value; });
    let url = `/api/db/${currentTable}`;
    let payload = data;
    if (isEditing) {
        url += '/update';
        payload = { id: data.id, updates: data };
    }
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    closeModal();
    await loadTableData();
}

async function deleteRow(index) {
    if (!confirm('确定要删除这条记录吗？')) return;
    const row = currentData[index];
    const resp = await fetch(`/api/db/${currentTable}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: row.id })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadTableData();
}

tableSelect.addEventListener('change', async (e) => {
    currentTable = e.target.value;
    refreshSortColumns();
    await loadTableData();
});

document.getElementById('sortBtn').addEventListener('click', loadTableData);

document.getElementById('addBtn').addEventListener('click', () => {
    isEditing = false;
    editIndex = -1;
    modalTitle.textContent = '新增记录';
    openModal(null);
});

document.getElementById('closeModalBtn').addEventListener('click', closeModal);

tableContainer.addEventListener('click', async (e) => {
    const editIndexValue = e.target.getAttribute('data-edit');
    const delIndexValue = e.target.getAttribute('data-del');
    if (editIndexValue !== null) {
        isEditing = true;
        editIndex = Number(editIndexValue);
        modalTitle.textContent = '编辑记录';
        openModal(currentData[editIndex]);
        return;
    }
    if (delIndexValue !== null) {
        await deleteRow(Number(delIndexValue));
    }
});

modalForm.addEventListener('click', async (e) => {
    if (e.target.id === 'saveBtn') {
        await saveData();
    }
});

refreshSortColumns();
loadTableData();
