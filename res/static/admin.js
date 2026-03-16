const tableSchema = {
    mapping_base: ['id', 'element_name', 'element_name_en', 'element_description', 'element_category', 'weight', 'ast_example_input', 'ast_example_output', 'element_regex_rule', 'element_handler_name'],
    mapping_style: ['id', 'style_name', 'is_active', 'is_deletable', 'remark'],
    mapping_rule: ['id', 'style_id', 'style_rule_name', 'ast_input', 'matching_rule', 'html_output', 'render_name', 'weight']
};

let currentTable = 'mapping_base';
let currentData = [];
let isEditing = false;
let editIndex = -1;
let visibleColumns = [...tableSchema.mapping_base];
let currentSort = { column: null, order: null };
let isSqlMode = false;

const tableSelect = document.getElementById('tableSelect');
const columnChecklist = document.getElementById('columnChecklist');
const tableContainer = document.getElementById('tableContainer');
const editModal = document.getElementById('editModal');
const modalTitle = document.getElementById('modalTitle');
const modalForm = document.getElementById('modalForm');
const sqlInput = document.getElementById('sqlInput');

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function loadTableData() {
    isSqlMode = false;
    const sortBy = currentSort.column;
    const order = currentSort.order;
    const query = sortBy && order
        ? `?sort_by=${encodeURIComponent(sortBy)}&order=${encodeURIComponent(order)}`
        : '';
    const response = await fetch(`/api/db/${currentTable}${query}`);
    const data = await response.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    currentData = data;
    if (!visibleColumns.length) {
        visibleColumns = [...tableSchema[currentTable]];
    }
    renderTable();
}

function renderTable() {
    const columns = isSqlMode
        ? visibleColumns
        : visibleColumns.filter(col => tableSchema[currentTable].includes(col));
    if (!columns.length) {
        tableContainer.innerHTML = '<div style="padding:12px;">请先选择至少一列用于展示</div>';
        return;
    }
    if (!currentData.length) {
        tableContainer.innerHTML = '<div style="padding:12px;">暂无数据</div>';
        return;
    }
    const header = columns.map(col => {
        let icon = '↕';
        if (currentSort.column === col && currentSort.order === 'desc') icon = '▼';
        if (currentSort.column === col && currentSort.order === 'asc') icon = '▲';
        return `<th class="sortable-th" data-sort-col="${col}">${col} <span class="sort-icon">${icon}</span></th>`;
    }).join('');
    const rows = currentData.map((row, index) => {
        const tds = columns.map(col => {
            let value = row[col];
            if (value === null || value === undefined) value = '';
            value = String(value);
            if (value.length > 140) value = `${value.slice(0, 140)}...`;
            return `<td>${escapeHtml(value)}</td>`;
        }).join('');
        return `<tr>${tds}<td class="operation-col"><div class="action-row"><button class="btn btn-primary" data-edit="${index}">编辑</button><button class="btn btn-danger" data-del="${index}">删除</button></div></td></tr>`;
    }).join('');
    tableContainer.innerHTML = `<table class="data-table styles-table admin-scroll-table"><thead><tr>${header}<th class="operation-col">操作</th></tr></thead><tbody>${rows}</tbody></table>`;
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
    html += '</div><div class="rule-modal-actions"><button class="btn btn-success" id="saveBtn">保存</button><button class="btn btn-danger" id="cancelEditBtn">取消编辑</button></div>';
    modalForm.innerHTML = html;
    editModal.style.display = 'block';
}

function closeModal() {
    editModal.style.display = 'none';
    modalForm.innerHTML = '';
}

function refreshColumnOptions() {
    const columns = tableSchema[currentTable];
    columnChecklist.innerHTML = columns.map(col => {
        const checked = visibleColumns.includes(col) ? 'checked' : '';
        return `<label class="check-item"><input type="checkbox" value="${col}" ${checked}> ${col}</label>`;
    }).join('');
}

function applySelectedColumns() {
    const selected = Array.from(columnChecklist.querySelectorAll('input[type="checkbox"]:checked')).map(x => x.value);
    visibleColumns = selected;
    renderTable();
}

function cycleSort(col) {
    if (currentSort.column !== col) {
        currentSort = { column: col, order: 'desc' };
        return;
    }
    if (currentSort.order === 'desc') {
        currentSort = { column: col, order: 'asc' };
        return;
    }
    if (currentSort.order === 'asc') {
        currentSort = { column: null, order: null };
        return;
    }
    currentSort = { column: col, order: 'desc' };
}

function applySqlSort() {
    if (!currentSort.column || !currentSort.order) return;
    const col = currentSort.column;
    const order = currentSort.order;
    currentData = [...currentData].sort((a, b) => {
        const va = a?.[col];
        const vb = b?.[col];
        const na = Number(va);
        const nb = Number(vb);
        const bothNumber = !Number.isNaN(na) && !Number.isNaN(nb);
        if (bothNumber) {
            return order === 'desc' ? nb - na : na - nb;
        }
        const sa = String(va ?? '');
        const sb = String(vb ?? '');
        if (order === 'desc') return sb.localeCompare(sa, 'zh-Hans-CN');
        return sa.localeCompare(sb, 'zh-Hans-CN');
    });
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
    const row = currentData[index];
    if (currentTable === 'mapping_style') {
        if (!confirm('删除风格时，对应的所有映射规则也会被同时删除。是否确认继续？')) return;
    } else {
        if (!confirm('确定要删除这条记录吗？')) return;
    }
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

async function runSqlQuery() {
    const sql = sqlInput.value.trim();
    if (!sql) {
        alert('请先输入 SQL 语句');
        return;
    }
    const resp = await fetch('/api/db/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sql })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    const rows = result.rows || [];
    currentData = rows;
    const cols = result.columns || [];
    visibleColumns = cols;
    currentSort = { column: null, order: null };
    isSqlMode = true;
    columnChecklist.innerHTML = cols.map(col => `<label class="check-item"><input type="checkbox" value="${col}" checked> ${col}</label>`).join('');
    if (!rows.length) {
        tableContainer.innerHTML = '<div style="padding:12px;">查询执行成功，返回 0 条记录</div>';
        return;
    }
    renderTable();
}

tableSelect.addEventListener('change', async (e) => {
    currentTable = e.target.value;
    visibleColumns = [...tableSchema[currentTable]];
    currentSort = { column: null, order: null };
    refreshColumnOptions();
    await loadTableData();
});

document.getElementById('runSqlBtn').addEventListener('click', runSqlQuery);
columnChecklist.addEventListener('change', applySelectedColumns);

document.getElementById('addBtn').addEventListener('click', () => {
    if (isSqlMode) {
        alert('SQL 查询模式下不支持新增，请先切回数据表视图');
        return;
    }
    isEditing = false;
    editIndex = -1;
    modalTitle.textContent = '新增记录';
    openModal(null);
});

document.getElementById('closeModalBtn').addEventListener('click', closeModal);

tableContainer.addEventListener('click', async (e) => {
    const sortCol = e.target.closest('[data-sort-col]')?.getAttribute('data-sort-col');
    if (sortCol) {
        cycleSort(sortCol);
        if (isSqlMode) {
            applySqlSort();
            renderTable();
        } else {
            await loadTableData();
        }
        return;
    }
    const editIndexValue = e.target.getAttribute('data-edit');
    const delIndexValue = e.target.getAttribute('data-del');
    if (editIndexValue !== null) {
        if (isSqlMode) {
            alert('SQL 查询模式下不支持编辑，请先切回数据表视图');
            return;
        }
        isEditing = true;
        editIndex = Number(editIndexValue);
        modalTitle.textContent = '编辑记录';
        openModal(currentData[editIndex]);
        return;
    }
    if (delIndexValue !== null) {
        if (isSqlMode) {
            alert('SQL 查询模式下不支持删除，请先切回数据表视图');
            return;
        }
        await deleteRow(Number(delIndexValue));
    }
});

modalForm.addEventListener('click', async (e) => {
    if (e.target.id === 'saveBtn') {
        await saveData();
        return;
    }
    if (e.target.id === 'cancelEditBtn') {
        closeModal();
    }
});

refreshColumnOptions();
loadTableData();
