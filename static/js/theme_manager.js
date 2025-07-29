// static/js/theme_manager.js
console.log("theme_manager.js: Loaded.");

const THEMES = {
    '80s': {
        path: "/static/css/themes/80's_theme.css"
        // No associated JS needed for this theme
    },
    'zen': {
        path: "/static/css/themes/zen_gardens.css"
        // No associated JS needed for this theme
    },
    'hotseat': {
        path: "/static/css/themes/hotseat.css",
        // The effects for this theme are in hotseat_effects.js, which is pre-loaded in base.html
        js_effects: true 
    }
};

const PYGMENTS_THEMES = {
    light: "/static/css/themes/light_default_pygments.css",
    dark: "/static/css/themes/dark_monokai_pygments.css"
};

/**
 * Creates a <link> element for a CSS stylesheet.
 * @param {string} id - The ID for the new link element.
 * @param {string} href - The URL for the stylesheet.
 */
function createStylesheetLink(id, href) {
    const link = document.createElement('link');
    link.id = id;
    link.rel = 'stylesheet';
    link.href = href;
    return link;
}

/**
 * Manages the Pygments (syntax highlighting) theme based on dark mode.
 */
function applyPygmentsTheme() {
    const isDark = document.documentElement.classList.contains('dark');
    const themeToLoad = isDark ? 'dark' : 'light';
    const themeToRemove = isDark ? 'light' : 'dark';

    // Remove the old theme
    const oldLink = document.getElementById(`pygments-${themeToRemove}-theme`);
    if (oldLink) {
        oldLink.remove();
    }

    // Add the new theme if it's not already there
    if (!document.getElementById(`pygments-${themeToLoad}-theme`)) {
        const newLink = createStylesheetLink(`pygments-${themeToLoad}-theme`, PYGMENTS_THEMES[themeToLoad]);
        document.head.appendChild(newLink);
    }
}

/**
 * Sets the active theme for the application.
 * @param {string | null} themeName - The name of the theme to activate (e.g., '80s'), or null to disable.
 */
function setTheme(themeName) {
    // Remove all existing theme stylesheets and classes
    for (const name in THEMES) {
        document.body.classList.remove(`theme-${name}`);
        const link = document.getElementById(`${name}-theme-stylesheet`);
        if (link) {
            link.remove();
        }
    }

    // Deactivate effects from any special themes
    if (window.deactivateHotseatEffects) {
        window.deactivateHotseatEffects();
    }

    // If a theme is selected, apply it
    if (themeName && THEMES[themeName]) {
        const theme = THEMES[themeName];
        document.body.classList.add(`theme-${themeName}`);

        // Add the new stylesheet
        const newLink = createStylesheetLink(`${themeName}-theme-stylesheet`, theme.path);
        document.head.appendChild(newLink);

        // Activate special effects if they exist
        if (theme.js_effects) {
            if (themeName === 'hotseat' && window.activateHotseatEffects) {
                window.activateHotseatEffects();
            }
        }

        localStorage.setItem('activeTheme', themeName);
    } else {
        localStorage.removeItem('activeTheme');
    }

    // Dispatch a general theme changed event
    document.dispatchEvent(new CustomEvent('themeChanged'));
}

/**
 * Toggles dark mode.
 */
function toggleDarkMode() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
    applyPygmentsTheme(); // Re-apply the correct syntax highlighting
    document.dispatchEvent(new CustomEvent('themeChanged'));
}

/**
 * Initializes the themes on page load.
 */
function initializeThemes() {
    // 1. Apply dark mode first
    if (localStorage.getItem('darkMode') === 'enabled') {
        document.documentElement.classList.add('dark');
    }

    // 2. Load the base Pygments theme
    applyPygmentsTheme();

    // 3. Load the active theme from localStorage
    const activeTheme = localStorage.getItem('activeTheme');
    if (activeTheme) {
        setTheme(activeTheme);
    }
}

// Run initialization as soon as the script is loaded.
initializeThemes();
