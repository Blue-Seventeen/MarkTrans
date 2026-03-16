const THEME_KEY = 'marktrans-theme';
const THEME_TOGGLE_ID = 'activeStyleLabel';

function applyTheme(theme) {
    const targetTheme = theme === 'light' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', targetTheme);
    const themeToggle = document.getElementById(THEME_TOGGLE_ID);
    if (!themeToggle) {
        return;
    }
    themeToggle.textContent = targetTheme === 'dark'
        ? '当前模式：深色（点此切换亮色）'
        : '当前模式：亮色（点此切换暗色）';
}

function switchTheme() {
    const currentTheme = document.body.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
    const targetTheme = currentTheme === 'dark' ? 'light' : 'dark';
    applyTheme(targetTheme);
    localStorage.setItem(THEME_KEY, targetTheme);
}

function initThemeToggle() {
    applyTheme(localStorage.getItem(THEME_KEY) || 'dark');
    const themeToggle = document.getElementById(THEME_TOGGLE_ID);
    if (!themeToggle) {
        return;
    }
    themeToggle.addEventListener('click', switchTheme);
    themeToggle.addEventListener('keydown', (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            switchTheme();
        }
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initThemeToggle);
} else {
    initThemeToggle();
}
