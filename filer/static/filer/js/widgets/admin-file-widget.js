// Admin File Widget JavaScript
'use strict';

document.addEventListener('DOMContentLoaded', () => {
    // Find all file widgets and clean up "add new" buttons
    const cleanupAddButtons = () => {
        document.querySelectorAll('.filer-widget').forEach((widget) => {
            const hiddenInput = widget.querySelector('input[type="text"][id]');
            if (hiddenInput) {
                const widgetId = hiddenInput.id;
                const addButton = document.querySelector(`#add_${widgetId}`);
                if (addButton) {
                    addButton.remove();
                }
            }
        });
    };

    cleanupAddButtons();

    // Also handle dynamically added widgets (e.g., in inline formsets)
    const observer = new MutationObserver(() => {
        cleanupAddButtons();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
