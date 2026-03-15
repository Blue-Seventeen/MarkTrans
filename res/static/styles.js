const stylesTableWrap = document.getElementById('stylesTableWrap');
const baseStyleSelect = document.getElementById('baseStyleSelect');
const newStyleNameInput = document.getElementById('newStyleName');

let styleData = [];

function escapeHtml(text) {
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

async function loadStyles() {
    const resp = await fetch('/api/style/list');
    const data = await resp.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    styleData = data;
    renderStyles();
    baseStyleSelect.innerHTML = styleData.map(item => `<option value="${item.id}">${escapeHtml(item.style_name)} (#${item.id})</option>`).join('');
}

function renderStyles() {
    if (!styleData.length) {
        stylesTableWrap.innerHTML = '<div style="padding:12px;">暂无风格</div>';
        return;
    }
    const rows = styleData.map(item => {
        const active = Number(item.is_active) === 1 ? '是' : '否';
        const deletable = Number(item.is_deletable) === 1 ? '是' : '否';
        const deleteBtn = Number(item.is_deletable) === 1
            ? `<button class="btn btn-danger" data-del="${item.id}">删除</button>`
            : `<button class="btn btn-danger" disabled>删除</button>`;
        return `
        <tr>
            <td>${item.id}</td>
            <td><input type="text" value="${escapeHtml(item.style_name)}" data-name="${item.id}"></td>
            <td>${active}</td>
            <td>${deletable}</td>
            <td>${escapeHtml(item.remark ?? '')}</td>
            <td>
                <button class="btn btn-primary" data-save="${item.id}">保存名称</button>
                <button class="btn btn-success" data-active="${item.id}">设为启用</button>
                ${deleteBtn}
            </td>
        </tr>
        `;
    }).join('');
    stylesTableWrap.innerHTML = `<table class="data-table"><thead><tr><th>id</th><th>style_name</th><th>is_active</th><th>is_deletable</th><th>remark</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table>`;
}

async function activateStyle(id) {
    const resp = await fetch('/api/style/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadStyles();
}

async function saveStyleName(id) {
    const input = document.querySelector(`input[data-name="${id}"]`);
    const value = input ? input.value.trim() : '';
    if (!value) {
        alert('style_name 不能为空');
        return;
    }
    const resp = await fetch('/api/db/mapping_style/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, updates: { style_name: value } })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadStyles();
}

async function deleteStyle(id) {
    if (!confirm('确定删除该风格吗？')) return;
    const resp = await fetch('/api/db/mapping_style/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadStyles();
}

async function cloneStyle() {
    const base_style_id = Number(baseStyleSelect.value);
    const style_name = newStyleNameInput.value.trim();
    if (!base_style_id || !style_name) {
        alert('请选择基础风格并填写新名称');
        return;
    }
    const resp = await fetch('/api/style/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ base_style_id, style_name })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    newStyleNameInput.value = '';
    await loadStyles();
}

stylesTableWrap.addEventListener('click', async (e) => {
    const activeId = e.target.getAttribute('data-active');
    const saveId = e.target.getAttribute('data-save');
    const delId = e.target.getAttribute('data-del');
    if (activeId) await activateStyle(Number(activeId));
    if (saveId) await saveStyleName(Number(saveId));
    if (delId) await deleteStyle(Number(delId));
});

document.getElementById('cloneStyleBtn').addEventListener('click', cloneStyle);

loadStyles();
