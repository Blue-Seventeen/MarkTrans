const styleSelect = document.getElementById('styleSelect');
const markdownInput = document.getElementById('markdownInput');
const filePathInput = document.getElementById('filePath');
const imageDirInput = document.getElementById('imageDir');
const astOutput = document.getElementById('astOutput');
const htmlPreview = document.getElementById('htmlPreview');
const htmlSource = document.getElementById('htmlSource');
const htmlViewToggleBtn = document.getElementById('htmlViewToggleBtn');
const statusBar = document.getElementById('statusBar');
let htmlViewMode = 'preview';

function setStatus(text) {
    statusBar.textContent = `状态：${text}`;
}

async function fetchStyles() {
    const resp = await fetch('/api/style/list');
    const data = await resp.json();
    styleSelect.innerHTML = '';
    data.forEach(item => {
        const option = document.createElement('option');
        option.value = item.id;
        option.textContent = `${item.style_name} (#${item.id})`;
        if (item.is_active === 1) {
            option.selected = true;
        }
        styleSelect.appendChild(option);
    });
}

async function runTranslate() {
    const payload = {
        content: markdownInput.value,
        filePath: filePathInput.value.trim(),
        imageDir: imageDirInput.value.trim(),
        styleId: Number(styleSelect.value || 1)
    };
    setStatus('正在执行转换...');
    const start = performance.now();
    const resp = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await resp.json();
    if (data.error) {
        setStatus(`失败：${data.error}`);
        alert(data.error);
        return;
    }
    if (data.loadedContent) {
        markdownInput.value = data.loadedContent;
    }
    astOutput.value = JSON.stringify(data.ast || [], null, 2);
    htmlPreview.innerHTML = data.html || '';
    htmlSource.value = data.html || '';
    const cost = Math.round(performance.now() - start);
    setStatus(`完成，耗时 ${cost} ms，AST 节点 ${(data.ast || []).length} 个`);
}

document.getElementById('pickPathBtn').addEventListener('click', async () => {
    setStatus('正在打开本地选择窗口...');
    const resp = await fetch('/api/path/pick', { method: 'POST' });
    const data = await resp.json();
    if (data.error) {
        setStatus(`失败：${data.error}`);
        alert(data.error);
        return;
    }
    if (!data.path) {
        setStatus('未选择路径');
        return;
    }
    if (data.kind === 'file') {
        filePathInput.value = data.path;
        setStatus('已选择 Markdown 文件路径');
        return;
    }
    imageDirInput.value = data.path;
    setStatus('已选择附件目录路径');
});
document.getElementById('convertBtn').addEventListener('click', () => runTranslate());
document.getElementById('loadByPathBtn').addEventListener('click', () => runTranslate());

document.getElementById('copyAstBtn').addEventListener('click', async () => {
    await navigator.clipboard.writeText(astOutput.value || '');
    setStatus('AST 已复制');
});

document.getElementById('copyHtmlBtn').addEventListener('click', async () => {
    if (htmlViewMode === 'preview') {
        await navigator.clipboard.writeText(htmlPreview.innerText || '');
        setStatus('HTML 预览文本已复制');
    } else {
        await navigator.clipboard.writeText(htmlSource.value || '');
        setStatus('HTML 源码已复制');
    }
});

htmlViewToggleBtn.addEventListener('click', () => {
    htmlViewMode = htmlViewMode === 'preview' ? 'source' : 'preview';
    if (htmlViewMode === 'source') {
        htmlPreview.classList.add('hidden');
        htmlSource.classList.remove('hidden');
        htmlViewToggleBtn.textContent = '切换到预览';
        setStatus('已切换到 HTML 源码视图');
        return;
    }
    htmlSource.classList.add('hidden');
    htmlPreview.classList.remove('hidden');
    htmlViewToggleBtn.textContent = '切换到源码';
    setStatus('已切换到 HTML 预览视图');
});

styleSelect.addEventListener('change', async () => {
    const styleId = Number(styleSelect.value);
    const resp = await fetch('/api/style/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: styleId })
    });
    const data = await resp.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    const name = styleSelect.options[styleSelect.selectedIndex].textContent.split(' (#')[0];
    setStatus(`已切换样式：${name}`);
});

fetchStyles().then(() => setStatus('就绪'));
