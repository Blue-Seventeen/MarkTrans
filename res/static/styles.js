const stylesTableWrap = document.getElementById('stylesTableWrap');
const baseStyleSelect = document.getElementById('baseStyleSelect');
const newStyleNameInput = document.getElementById('newStyleName');
const styleEditModal = document.getElementById('styleEditModal');
const styleModalTitle = document.getElementById('styleModalTitle');
const styleModalName = document.getElementById('styleModalName');
const styleModalRemark = document.getElementById('styleModalRemark');
const styleRulesWrap = document.getElementById('styleRulesWrap');
const ruleEditorWrap = document.getElementById('ruleEditorWrap');
const ruleEditModal = document.getElementById('ruleEditModal');
const ruleModalTitle = document.getElementById('ruleModalTitle');

let styleData = [];
let currentStyleId = null;
let currentRules = [];
let editingRuleId = null;

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
        const idNum = Number(item.id);
        const isActive = Number(item.is_active) === 1;
        const active = isActive ? '是' : '否';
        const deletable = Number(item.is_deletable) === 1 ? '是' : '否';
        const cannotDeleteReason = idNum === 1
            ? '系统中至少应该保留一款映射规则以应对 Markdown => HTML 的转换'
            : '该风格不允许删除';
        const deleteBtn = (idNum !== 1 && Number(item.is_deletable) === 1)
            ? `<button class="btn btn-danger" data-del="${item.id}">删除</button>`
            : `<button class="btn btn-disabled" type="button" title="${escapeHtml(cannotDeleteReason)}">删除</button>`;
        const activeBtn = isActive
            ? `<button class="btn btn-disabled" type="button" title="该风格当前已启用">启用中</button>`
            : `<button class="btn btn-success" data-active="${item.id}">启用</button>`;
        return `
        <tr>
            <td>${item.id}</td>
            <td>${escapeHtml(item.style_name)}</td>
            <td>${active}</td>
            <td>${deletable}</td>
            <td>${escapeHtml(item.remark ?? '')}</td>
            <td>
                <div class="action-row">
                    <button class="btn btn-primary" data-edit="${item.id}">编辑</button>
                    ${activeBtn}
                    ${deleteBtn}
                </div>
            </td>
        </tr>
        `;
    }).join('');
    stylesTableWrap.innerHTML = `<table class="data-table styles-table"><thead><tr><th>id</th><th>style_name</th><th>is_active</th><th>is_deletable</th><th>remark</th><th>操作</th></tr></thead><tbody>${rows}</tbody></table>`;
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

async function saveStyleMeta(id) {
    const value = styleModalName.value.trim();
    const remarkValue = styleModalRemark.value.trim();
    if (!value || !id) {
        alert('style_name 不能为空');
        return;
    }
    const resp = await fetch('/api/db/mapping_style/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id, updates: { style_name: value, remark: remarkValue } })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadStyles();
    await loadRulesForStyle(id);
}

async function deleteStyle(id) {
    if (!confirm('删除风格时，对应的所有映射规则也会被同时删除。是否确认继续？')) return;
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
    if (currentStyleId === id) {
        closeStyleModal();
    }
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

function closeStyleModal() {
    styleEditModal.style.display = 'none';
    currentStyleId = null;
    currentRules = [];
    editingRuleId = null;
    styleRulesWrap.innerHTML = '';
    ruleEditorWrap.innerHTML = '';
    closeRuleModal();
}

function showRuleEditor(rule = null) {
    editingRuleId = rule ? Number(rule.id) : null;
    const values = {
        style_rule_name: rule?.style_rule_name ?? '',
        ast_input: rule?.ast_input ?? '',
        matching_rule: rule?.matching_rule ?? '',
        html_output: rule?.html_output ?? '',
        render_name: rule?.render_name ?? '',
        weight: rule?.weight ?? 0
    };
    ruleModalTitle.textContent = editingRuleId ? '编辑规则' : '新增规则';
    ruleEditorWrap.innerHTML = `
        <div class="form-grid">
            <div class="field"><label>style_rule_name</label><input id="rule_style_rule_name" type="text" value="${escapeHtml(values.style_rule_name)}"></div>
            <div class="field"><label>render_name</label><input id="rule_render_name" type="text" value="${escapeHtml(values.render_name)}"></div>
            <div class="field"><label>weight</label><input id="rule_weight" type="text" value="${escapeHtml(values.weight)}"></div>
            <div class="field"><label>ast_input</label><textarea id="rule_ast_input" rows="3">${escapeHtml(values.ast_input)}</textarea></div>
            <div class="field"><label>matching_rule</label><textarea id="rule_matching_rule" rows="3">${escapeHtml(values.matching_rule)}</textarea></div>
            <div class="field"><label>html_output</label><textarea id="rule_html_output" rows="3">${escapeHtml(values.html_output)}</textarea></div>
        </div>
    `;
    ruleEditModal.style.display = 'block';
}

function closeRuleModal() {
    ruleEditModal.style.display = 'none';
    editingRuleId = null;
    ruleEditorWrap.innerHTML = '';
}

async function loadRulesForStyle(styleId) {
    const resp = await fetch('/api/db/mapping_rule?sort_by=weight&order=desc');
    const rows = await resp.json();
    if (rows.error) {
        alert(rows.error);
        return;
    }
    currentRules = rows.filter(x => Number(x.style_id) === Number(styleId));
    renderRuleTable();
}

function renderRuleTable() {
    if (!currentRules.length) {
        styleRulesWrap.innerHTML = '<div style="padding:10px;">当前风格暂无映射规则</div>';
        return;
    }
    const body = currentRules.map(rule => `
        <tr>
            <td>${rule.id}</td>
            <td>${escapeHtml(rule.style_rule_name ?? '')}</td>
            <td>${escapeHtml(rule.render_name ?? '')}</td>
            <td>${escapeHtml(rule.weight ?? '')}</td>
            <td>${escapeHtml((rule.matching_rule ?? '').slice(0, 80))}</td>
            <td>
                <div class="action-row">
                    <button class="btn btn-primary" data-rule-edit="${rule.id}">编辑</button>
                    <button class="btn btn-danger" data-rule-del="${rule.id}">删除</button>
                </div>
            </td>
        </tr>
    `).join('');
    styleRulesWrap.innerHTML = `<table class="data-table styles-table rules-scroll-table"><thead><tr><th>id</th><th>style_rule_name</th><th>render_name</th><th>weight</th><th>matching_rule</th><th>操作</th></tr></thead><tbody>${body}</tbody></table>`;
}

async function saveRule() {
    if (!currentStyleId) return;
    const payload = {
        style_id: Number(currentStyleId),
        style_rule_name: document.getElementById('rule_style_rule_name').value.trim(),
        ast_input: document.getElementById('rule_ast_input').value.trim(),
        matching_rule: document.getElementById('rule_matching_rule').value.trim(),
        html_output: document.getElementById('rule_html_output').value.trim(),
        render_name: document.getElementById('rule_render_name').value.trim(),
        weight: Number(document.getElementById('rule_weight').value || 0)
    };
    if (!payload.style_rule_name) {
        alert('style_rule_name 不能为空');
        return;
    }
    let url = '/api/db/mapping_rule';
    let body = payload;
    if (editingRuleId) {
        url = '/api/db/mapping_rule/update';
        body = { id: editingRuleId, updates: payload };
    }
    const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    closeRuleModal();
    await loadRulesForStyle(currentStyleId);
}

async function deleteRule(id) {
    if (!confirm('确定删除该映射规则吗？')) return;
    const resp = await fetch('/api/db/mapping_rule/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id })
    });
    const result = await resp.json();
    if (result.error) {
        alert(result.error);
        return;
    }
    await loadRulesForStyle(currentStyleId);
}

async function openStyleModal(id) {
    const style = styleData.find(x => Number(x.id) === Number(id));
    if (!style) return;
    currentStyleId = Number(id);
    styleModalTitle.textContent = `编辑风格 #${style.id}`;
    styleModalName.value = style.style_name ?? '';
    styleModalRemark.value = style.remark ?? '';
    styleEditModal.style.display = 'block';
    await loadRulesForStyle(currentStyleId);
}

stylesTableWrap.addEventListener('click', async (e) => {
    const editId = e.target.getAttribute('data-edit');
    const activeId = e.target.getAttribute('data-active');
    const delId = e.target.getAttribute('data-del');
    if (editId) await openStyleModal(Number(editId));
    if (activeId) await activateStyle(Number(activeId));
    if (delId) await deleteStyle(Number(delId));
});

document.getElementById('cloneStyleBtn').addEventListener('click', cloneStyle);
document.getElementById('closeStyleModalBtn').addEventListener('click', closeStyleModal);
document.getElementById('saveStyleMetaBtn').addEventListener('click', async () => {
    await saveStyleMeta(currentStyleId);
});
document.getElementById('addRuleBtn').addEventListener('click', () => {
    showRuleEditor();
});

document.getElementById('saveRuleBtn').addEventListener('click', async () => {
    await saveRule();
});

document.getElementById('cancelRuleBtn').addEventListener('click', closeRuleModal);
document.getElementById('closeRuleModalBtn').addEventListener('click', closeRuleModal);

styleRulesWrap.addEventListener('click', async (e) => {
    const ruleEditId = e.target.getAttribute('data-rule-edit');
    const ruleDelId = e.target.getAttribute('data-rule-del');
    if (ruleEditId) {
        const rule = currentRules.find(x => Number(x.id) === Number(ruleEditId));
        if (rule) showRuleEditor(rule);
        return;
    }
    if (ruleDelId) {
        await deleteRule(Number(ruleDelId));
    }
});

loadStyles();
