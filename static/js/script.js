// static/js/script.js

/**
 * Initializes or re-initializes OverlayScrollbars on a given element.
 * @param {HTMLElement} element The element to apply the scrollbar to.
 */
function initOverlayScrollbars(element) {
    if (!element || typeof OverlayScrollbars === 'undefined') {
        return; // Exit if library or element is not available
    }

    // The theme manager now adds the 'dark' class to the <html> element
    const isDarkMode = document.documentElement.classList.contains('dark');
    const scrollbarTheme = isDarkMode ? 'os-theme-light' : 'os-theme-dark';

    // If an instance already exists, destroy it before creating a new one
    const existingInstance = OverlayScrollbars.instances().find(inst => inst.target() === element);
    if (existingInstance) {
        existingInstance.destroy();
    }

    OverlayScrollbars(element, {
        scrollbars: {
            theme: scrollbarTheme,
            autoHide: 'scroll',
            autoHideDelay: 500,
        }
    });
}

/**
 * Adds a "Copy" button to code blocks that don't have one.
 * This is safe to run multiple times.
 */
function addCopyButtons() {
    document.querySelectorAll('pre code').forEach((codeBlock) => {
        const pre = codeBlock.parentElement;
        if (pre && pre.parentElement && pre.parentElement.classList.contains('code-container')) {
            return; // Skip if the button is already there
        }

        const container = document.createElement('div');
        container.className = 'code-container';
        pre.replaceWith(container);
        container.appendChild(pre);

        const button = document.createElement('button');
        button.textContent = 'Copy';
        // Note: The .copy-btn styles are now in base_styles.css
        button.className = 'copy-btn'; 

        button.addEventListener('click', () => {
            // Check for clipboard support
            if (!navigator.clipboard) {
                button.textContent = 'N/A';
                return;
            }

            // Clear any existing timeout to prevent the "Copied!" message 
            // from disappearing early if clicked rapidly.
            if (button.dataset.timerId) {
                clearTimeout(parseInt(button.dataset.timerId));
                button.dataset.timerId = '';
            }

            navigator.clipboard.writeText(codeBlock.innerText).then(() => {
                button.textContent = 'Copied!';
                const timerId = setTimeout(() => {
                    button.textContent = 'Copy';
                    button.dataset.timerId = '';
                }, 1500);
                button.dataset.timerId = timerId.toString();
            }).catch((err) => {
                console.error('Copy failed:', err);
                button.textContent = 'Error';
                const timerId = setTimeout(() => {
                    button.textContent = 'Copy';
                    button.dataset.timerId = '';
                }, 1500);
                button.dataset.timerId = timerId.toString();
            });
        });
        container.appendChild(button);
    });
}


// --- GLOBAL EVENT LISTENERS ---

// 1. Listen for our custom themeChanged event to update components like scrollbars.
document.addEventListener('themeChanged', () => {
    // Find all elements with scrollbars and re-initialize them to match the new theme.
    document.querySelectorAll('[data-overlayscrollbars]').forEach(el => {
        initOverlayScrollbars(el);
    });
});


// 2. Re-run scripts that need to be applied to new content loaded by HTMX.
document.body.addEventListener('htmx:afterSwap', (event) => {
    // The syntax is already highlighted by `marked.js`.
    // We only need to add copy buttons to any new code blocks.
    addCopyButtons();
});

// 3. Add copy buttons to any code blocks present on the initial page load.
document.addEventListener('DOMContentLoaded', () => {
    addCopyButtons();
});

// Tab renaming
document.addEventListener('DOMContentLoaded', function () {
    const tabBar = document.getElementById('tab-bar');

    if (tabBar) {
        tabBar.addEventListener('dblclick', function (event) {
            // Find the tab-name span that was clicked
            const tabNameSpan = event.target.closest('.tab-name');
            if (!tabNameSpan) {
                return; // Didn't click on a tab name
            }

            const tabContainer = tabNameSpan.closest('.tab-button-container');
            const instanceId = tabContainer.dataset.instanceId;
            const originalName = tabNameSpan.textContent.trim();

            // Create an input field
            const input = document.createElement('input');
            input.type = 'text';
            input.value = originalName;
            input.className = 'tab-name-input'; // For styling if needed
            input.style.width = `${tabNameSpan.offsetWidth + 10}px`; // Set width to match original

            // Replace the span with the input
            tabNameSpan.style.display = 'none';
            tabNameSpan.parentNode.insertBefore(input, tabNameSpan.nextSibling);
            input.focus();
            input.select();

            // Function to handle saving the name
            const saveName = () => {
                const newName = input.value.trim();

                // Restore the original span
                input.parentNode.removeChild(input);
                tabNameSpan.style.display = '';

                if (newName && newName !== originalName) {
                    // Update the UI immediately
                    tabNameSpan.textContent = newName;

                    // Send the change to the server
                    fetch(`/chat/${instanceId}/rename`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ new_name: newName }),
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status !== 'success') {
                            // Revert on failure
                            tabNameSpan.textContent = originalName;
                            alert(`Error renaming tab: ${data.message}`);
                        }
                    })
                    .catch(error => {
                        // Revert on network error
                        tabNameSpan.textContent = originalName;
                        alert('An error occurred while renaming the tab.');
                        console.error('Rename failed:', error);
                    });
                }
            };

            // Save when the input loses focus
            input.addEventListener('blur', saveName);

            // Save on 'Enter', cancel on 'Escape'
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    input.blur(); // Triggers the blur event handler
                } else if (e.key === 'Escape') {
                    // Just remove the input and show the original span
                    input.parentNode.removeChild(input);
                    tabNameSpan.style.display = '';
                }
            });
        });
    }
});

// --- CHAT INPUT KEYBOARD SHORTCUTS ---
// Ctrl+Enter to Send
// Enter to New Line (default behavior preserved)
document.addEventListener('keydown', function(event) {
    // Check if the target is a chat input textarea
    if (event.target && event.target.tagName === 'TEXTAREA' && event.target.name === 'user_input') {
        
        // Ctrl + Enter (or Cmd + Enter on Mac)
        if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
            event.preventDefault(); // Prevent newline
            
            // Find the form
            const form = event.target.closest('form');
            if (form) {
                // Find and click the submit button to trigger HTMX/form submission properly
                const submitButton = form.querySelector('button[type="submit"]');
                if (submitButton && !submitButton.disabled) {
                    submitButton.click();
                }
            }
        }
        // Enter without modifiers
        else if (event.key === 'Enter' && !event.shiftKey && !event.altKey) {
            // Default behavior is new line. We allow it.
            // No specific action needed, but stopping propagation ensures
            // no parent 'Enter-to-submit' handlers interfere.
            event.stopPropagation();
        }
    }
});
