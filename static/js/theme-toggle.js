// 立即初始化主题，防止白闪
(function() {
    initTheme();
})();

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme) {
        setTheme(savedTheme, false);
    } else if (prefersDark) {
        setTheme('dark', false);
    } else {
        setTheme('light', false);
    }
}

function setTheme(theme, animate = true) {
    if (!animate) {
        document.documentElement.classList.add('no-transition');
    }
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
    
    if (!animate) {
        // 强制重绘后恢复过渡
        requestAnimationFrame(() => {
            requestAnimationFrame(() => {
                document.documentElement.classList.remove('no-transition');
            });
        });
    }
    
    updateThemeButton(theme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function updateThemeButton(theme) {
    const buttons = document.querySelectorAll('.theme-toggle-btn');
    buttons.forEach(button => {
        const sunIcon = button.querySelector('.fa-sun');
        const moonIcon = button.querySelector('.fa-moon');
        if (sunIcon && moonIcon) {
            if (theme === 'dark') {
                sunIcon.style.display = 'block';
                moonIcon.style.display = 'none';
            } else {
                sunIcon.style.display = 'none';
                moonIcon.style.display = 'block';
            }
        }
    });
}

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (!localStorage.getItem('theme')) {
        setTheme(e.matches ? 'dark' : 'light');
    }
});
