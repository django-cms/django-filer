// Admin Folder Widget JavaScript
'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const initFolderWidget = (widget) => {
        const clearButton = widget.querySelector('.filerClearer');
        const input = widget.querySelector('input[type="text"]');
        const folderName = widget.querySelector('.description_text');
        const thumbnailImg = widget.querySelector('.thumbnail_img');
        const addFolderButton = widget.querySelector('.related-lookup');

        if (!clearButton || !input) {
            return;
        }

        // Avoid duplicate initialization
        if (clearButton.dataset.initialized) {
            return;
        }
        clearButton.dataset.initialized = 'true';

        clearButton.addEventListener('click', (e) => {
            e.preventDefault();

            if (folderName) {
                folderName.textContent = '';
            }
            if (input) {
                input.removeAttribute('value');
                input.value = '';
            }
            if (thumbnailImg) {
                thumbnailImg.classList.add('hidden');
            }
            clearButton.classList.add('hidden');
            if (addFolderButton) {
                addFolderButton.classList.remove('hidden');
            }
        });
    };

    // Initialize all folder widgets
    document.querySelectorAll('.filer-dropzone-folder').forEach(initFolderWidget);

    // Handle dynamically added widgets (e.g., in inline formsets)
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === 1) { // Element node
                    if (node.classList?.contains('filer-dropzone-folder')) {
                        initFolderWidget(node);
                    }
                    // Also check child nodes
                    node.querySelectorAll?.('.filer-dropzone-folder').forEach(initFolderWidget);
                }
            });
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});
