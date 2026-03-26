/**
 * Dynamic Dark Mode Accessibility Engine
 * Zero-config setup leveraging data-bs-theme
 */
(function() {
    const STORAGE_KEY = 'esp-theme-preference';

    const getPreferredTheme = () => {
        const storedTheme = localStorage.getItem(STORAGE_KEY);
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
            const storedTheme = localStorage.getItem(STORAGE_KEY);
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
                // If persistence fails (e.g., quota exceeded or storage disabled),
                // continue applying the theme without storing the preference.
            }
            setTheme(newTheme);
            return newTheme;
        },
        getCurrentTheme: () => document.documentElement.getAttribute('data-bs-theme') || 'light'
    };

    // Bind generic toggles across the DOM when it loads
    document.addEventListener("DOMContentLoaded", () => {
        const updateIcons = (theme) => {
            document.querySelectorAll('.theme-icon-sun').forEach(el => el.style.display = theme === 'dark' ? 'inline-block' : 'none');
            document.querySelectorAll('.theme-icon-moon').forEach(el => el.style.display = theme === 'dark' ? 'none' : 'inline-block');
        };

        // Set initial icon visibility
        updateIcons(window.ESPThemeEngine.getCurrentTheme());

        // Watch for programmatic theme changes, if supported
        if (typeof MutationObserver !== 'undefined') {
            const observer = new MutationObserver(() => {
                updateIcons(window.ESPThemeEngine.getCurrentTheme());
            });
            observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-bs-theme'] });
        }

        // Bind clicks for all buttons with class 'dark-mode-toggle'
        document.querySelectorAll('.dark-mode-toggle').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const newTheme = window.ESPThemeEngine.toggleTheme();
                updateIcons(newTheme);
                document.body.classList.add('theme-transition');
                setTimeout(() => document.body.classList.remove('theme-transition'), 300);
            });
        });
    });
})();
