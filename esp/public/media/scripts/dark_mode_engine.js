(function() {
    const STORAGE_KEY = 'esp-theme-preference';

    const getPreferredTheme = () => {
        let storedTheme = null;
        try {
            storedTheme = localStorage.getItem(STORAGE_KEY);
        } catch (e) {
            // storage blocked
        }
        if (storedTheme) {
            return storedTheme;
        }
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    };

    const setTheme = (theme) => {
        document.documentElement.setAttribute('data-bs-theme', theme);
    };

    // Apply the theme immediately to avoid FOUC
    setTheme(getPreferredTheme());

    // Listen for OS changes
    if (window.matchMedia) {
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleColorSchemeChange = () => {
            let storedTheme = null;
            try {
                storedTheme = localStorage.getItem(STORAGE_KEY);
            } catch (e) {}
            if (storedTheme !== 'light' && storedTheme !== 'dark') {
                setTheme(getPreferredTheme());
            }
        };
        if (typeof mediaQuery.addEventListener === 'function') {
            mediaQuery.addEventListener('change', handleColorSchemeChange);
        } else if (typeof mediaQuery.addListener === 'function') {
            mediaQuery.addListener(handleColorSchemeChange);
        }
    }
    // Expose engine to other scripts
    window.ESPThemeEngine = {
        toggleTheme: () => {
            const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';

            try {
                localStorage.setItem(STORAGE_KEY, newTheme);
            } catch (e) {
                // ignore
            }
            setTheme(newTheme);
            return newTheme;
        },
        getCurrentTheme: () => document.documentElement.getAttribute('data-bs-theme') || 'light'
    };

    // Bind generic toggles across the DOM when it loads
    document.addEventListener("DOMContentLoaded", () => {
        // Bind clicks for all buttons with class 'dark-mode-toggle'
        document.querySelectorAll('.dark-mode-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const newTheme = window.ESPThemeEngine.toggleTheme();
                document.body.classList.add('theme-transition');
                setTimeout(() => document.body.classList.remove('theme-transition'), 300);
            });
        });
    });
})();
