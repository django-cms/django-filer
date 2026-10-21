// #####################################################################################################################
// #BASE#
// Basic logic django filer
'use strict';

import Mediator from 'mediator-js/lib/mediator';
import FocalPoint from './addons/focal-point';
import Toggler from './addons/toggler';

window.Cl = window.Cl || {};
Cl.mediator = new Mediator();  // mediator init
Cl.FocalPoint = FocalPoint;
Cl.Toggler = Toggler;


document.addEventListener('DOMContentLoaded', () => {
    let showErrorTimeout;

    window.filerShowError = (message) => {
        const messages = document.querySelector('.messagelist');
        const header = document.querySelector('#header');
        const filerErrorClass = 'js-filer-error';
        const tpl = `<ul class="messagelist"><li class="error ${filerErrorClass}">{msg}</li></ul>`;
        const msg = tpl.replace('{msg}', message);

        if (messages) {
            messages.outerHTML = msg;
        } else if (header) {
            header.insertAdjacentHTML('afterend', msg);
        }

        if (showErrorTimeout) {
            clearTimeout(showErrorTimeout);
        }

        showErrorTimeout = setTimeout(() => {
            const errorEl = document.querySelector(`.${filerErrorClass}`);
            if (errorEl) {
                errorEl.remove();
            }
        }, 5000);
    };

    const filterFiles = document.querySelector('.js-filter-files');
    if (filterFiles) {
        filterFiles.addEventListener('focus', (event) => {
            const container = event.target.closest('.navigator-top-nav');
            if (container) {
                container.classList.add('search-is-focused');
            }
        });

        filterFiles.addEventListener('blur', (event) => {
            const container = event.target.closest('.navigator-top-nav');
            if (container) {
                const dropdownTrigger = container.querySelector('.dropdown-container a');
                if (!dropdownTrigger || event.relatedTarget !== dropdownTrigger) {
                    container.classList.remove('search-is-focused');
                }
            }
        });
    }

    // Focus on the search field on page load
    (() => {
        const filter = document.querySelector('.js-filter-files');
        const containerSelector = '.navigator-top-nav';
        const container = document.querySelector(containerSelector);
        const searchDropdown = container?.querySelector('.filter-search-wrapper .filer-dropdown-container');

        if (filter) {
            filter.addEventListener('keydown', function () {
                const navContainer = this.closest(containerSelector);
                if (navContainer) {
                    navContainer.classList.add('search-is-focused');
                }
            });

            if (searchDropdown) {
                searchDropdown.addEventListener('show.bs.filer-dropdown', () => {
                    if (container) {
                        container.classList.add('search-is-focused');
                    }
                });
                searchDropdown.addEventListener('hide.bs.filer-dropdown', () => {
                    if (container) {
                        container.classList.remove('search-is-focused');
                    }
                });
            }
        }
    })();

    // show counter if file is selected
    (() => {
        const navigatorTable = document.querySelectorAll('.navigator-table tr, .navigator-list .list-item');
        const actionList = document.querySelector('.actions-wrapper');
        const actionSelect = document.querySelectorAll(
            '.action-select, #action-toggle, #files-action-toggle, #folders-action-toggle, .actions .clear a'
        );

        // timeout is needed to wait until table row has class selected.
        setTimeout(() => {
            // Set classes for checked items
            actionSelect.forEach((el) => {
                if (el.checked) {
                    const listItem = el.closest('.list-item');
                    if (listItem) {
                        listItem.classList.add('selected');
                    }
                }
            });
            const hasSelected = Array.from(navigatorTable).some((el) =>
                el.classList.contains('selected')
            );
            if (hasSelected && actionList) {
                actionList.classList.add('action-selected');
            }
        }, 100);

        actionSelect.forEach((el) => {
            el.addEventListener('change', function () {
                // Mark element selected (for table view this is done by Django admin js - we do it ourselves
                const listItem = this.closest('.list-item');
                if (listItem) {
                    if (this.checked) {
                        listItem.classList.add('selected');
                    } else {
                        listItem.classList.remove('selected');
                    }
                }
                // setTimeout makes sure that change event fires before click event which is reliable to admin
                setTimeout(() => {
                    const hasSelected = Array.from(navigatorTable).some((el) =>
                        el.classList.contains('selected')
                    );
                    if (actionList) {
                        if (hasSelected) {
                            actionList.classList.add('action-selected');
                        } else {
                            actionList.classList.remove('action-selected');
                        }
                    }
                }, 0);
            });
        });
    })();

    (() => {
        const actionsMenu = document.querySelector('.js-actions-menu');
        if (!actionsMenu) {
            return;
        }

        const dropdown = actionsMenu.querySelector('.filer-dropdown-menu');
        const actionsSelect = document.querySelector('.actions select[name="action"]');
        const actionsSelectOptions = actionsSelect?.querySelectorAll('option') || [];
        const actionsGo = document.querySelector('.actions button[type="submit"]');
        const actionDelete = document.querySelector('.js-action-delete');
        const actionCopy = document.querySelector('.js-action-copy');
        const actionMove = document.querySelector('.js-action-move');
        const valueDelete = 'delete_files_or_folders';
        const valueCopy = 'copy_files_and_folders';
        const valueMove = 'move_files_and_folders';
        const navigatorTable = document.querySelectorAll('.navigator-table tr, .navigator-list .list-item');

        // triggers delete copy and move actions on separate buttons
        const actionsButton = (optionValue, actionButton) => {
            if (!actionButton) {
                return;
            }
            actionsSelectOptions.forEach((option) => {
                if (option.value === optionValue) {
                    actionButton.style.display = '';
                    actionButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        const hasSelected = Array.from(navigatorTable).some((el) =>
                            el.classList.contains('selected')
                        );
                        if (hasSelected && actionsSelect && actionsGo) {
                            actionsSelect.value = optionValue;
                            const targetOption = actionsSelect.querySelector(`option[value="${optionValue}"]`);
                            if (targetOption) {
                                targetOption.selected = true;
                            }
                            actionsGo.click();
                        }
                    });
                }
            });
        };
        actionsButton(valueDelete, actionDelete);
        actionsButton(valueCopy, actionCopy);
        actionsButton(valueMove, actionMove);

        // mocking the action buttons to work in frontend UI
        actionsSelectOptions.forEach((option, index) => {
            if (index !== 0) {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = '#';
                a.textContent = option.textContent;

                if (option.value === valueDelete || option.value === valueCopy || option.value === valueMove) {
                    a.classList.add('hidden');
                }

                li.appendChild(a);
                if (dropdown) {
                    dropdown.appendChild(li);
                }
            }
        });
        if (dropdown) {

            dropdown.addEventListener('click', (clickEvent) => {
                if (clickEvent.target.tagName === 'A') {
                    const li = clickEvent.target.closest('li');
                    const targetIndex = Array.from(dropdown.querySelectorAll('li')).indexOf(li) + 1;

                    clickEvent.preventDefault();

                    if (actionsSelect && actionsGo) {
                        const options = actionsSelect.querySelectorAll('option');
                        if (options[targetIndex]) {
                            options[targetIndex].selected = true;
                        }
                        actionsGo.click();
                    }
                }
            });
        }

        actionsMenu.addEventListener('click', (e) => {
            const hasSelected = Array.from(navigatorTable).some((el) =>
                el.classList.contains('selected')
            );
            if (!hasSelected) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    })();

    // breaks header if breadcrumbs name reaches a width of 80px
    (() => {
        const minBreadcrumbWidth = 80;
        const header = document.querySelector('.navigator-top-nav');

        if (!header) {
            return;
        }

        const breadcrumbContainer = document.querySelector('.breadcrumbs-container');
        if (!breadcrumbContainer) {
            return;
        }

        const breadcrumbFolder = breadcrumbContainer.querySelector('.navigator-breadcrumbs');
        const breadcrumbDropdown = breadcrumbContainer.querySelector('.filer-dropdown-container');
        const filterFilesContainer = document.querySelector('.filter-files-container');
        const actionsWrapper = document.querySelector('.actions-wrapper');
        const navigatorButtonWrapper = document.querySelector('.navigator-button-wrapper');

        const breadcrumbFolderWidth = breadcrumbFolder?.offsetWidth || 0;
        const breadcrumbDropdownWidth = breadcrumbDropdown?.offsetWidth || 0;
        const searchWidth = filterFilesContainer?.offsetWidth || 0;
        const actionsWidth = actionsWrapper?.offsetWidth || 0;
        const buttonsWidth = navigatorButtonWrapper?.offsetWidth || 0;

        const headerStyles = window.getComputedStyle(header);
        const headerPadding = parseInt(headerStyles.paddingLeft, 10) + parseInt(headerStyles.paddingRight, 10);

        let headerWidth = header.offsetWidth;
        const fullHeaderWidth = minBreadcrumbWidth + breadcrumbFolderWidth +
            breadcrumbDropdownWidth + searchWidth + actionsWidth + buttonsWidth + headerPadding;

        const breadcrumbSizeHandlerClassName = 'breadcrumb-min-width';

        const breadcrumbSizeHandler = () => {
            if (headerWidth < fullHeaderWidth) {
                header.classList.add(breadcrumbSizeHandlerClassName);
            } else {
                header.classList.remove(breadcrumbSizeHandlerClassName);
            }
        };

        breadcrumbSizeHandler();

        window.addEventListener('resize', () => {
            headerWidth = header.offsetWidth;
            breadcrumbSizeHandler();
        });
    })();
    // thumbnail folder admin view
    (() => {
        const actionEls = document.querySelectorAll('.navigator-list .list-item input.action-select');
        const foldersActionCheckboxes = '.navigator-list .navigator-folders-body .list-item input.action-select';
        const filesActionCheckboxes = '.navigator-list .navigator-files-body .list-item input.action-select';
        const allFilesToggle = document.querySelector('#files-action-toggle');
        const allFoldersToggle = document.querySelector('#folders-action-toggle');

        if (allFoldersToggle) {
            allFoldersToggle.addEventListener('click', function () {
                const checkboxes = document.querySelectorAll(foldersActionCheckboxes);
                if (this.checked) {
                    checkboxes.forEach((cb) => {
                        if (!cb.checked) {
                            cb.click();
                        }
                    });
                } else {
                    checkboxes.forEach((cb) => {
                        if (cb.checked) {
                            cb.click();
                        }
                    });
                }
            });
        }

        if (allFilesToggle) {
            allFilesToggle.addEventListener('click', function () {
                const checkboxes = document.querySelectorAll(filesActionCheckboxes);
                if (this.checked) {
                    checkboxes.forEach((cb) => {
                        if (!cb.checked) {
                            cb.click();
                        }
                    });
                } else {
                    checkboxes.forEach((cb) => {
                        if (cb.checked) {
                            cb.click();
                        }
                    });
                }
            });
        }

        actionEls.forEach((el) => {
            el.addEventListener('click', function () {
                const filesCheckboxes = document.querySelectorAll(filesActionCheckboxes);
                const foldersCheckboxes = document.querySelectorAll(foldersActionCheckboxes);

                if (!this.checked) {
                    const hasUncheckedFiles = Array.from(filesCheckboxes).some((cb) => !cb.checked);
                    const hasUncheckedFolders = Array.from(foldersCheckboxes).some((cb) => !cb.checked);

                    if (hasUncheckedFiles && allFilesToggle) {
                        allFilesToggle.checked = false;
                    }
                    if (hasUncheckedFolders && allFoldersToggle) {
                        allFoldersToggle.checked = false;
                    }
                } else {
                    const allFilesChecked = Array.from(filesCheckboxes).every((cb) => cb.checked);
                    const allFoldersChecked = Array.from(foldersCheckboxes).every((cb) => cb.checked);

                    if (allFilesChecked && allFilesToggle) {
                        allFilesToggle.checked = true;
                    }
                    if (allFoldersChecked && allFoldersToggle) {
                        allFoldersToggle.checked = true;
                    }
                }
            });
        });

        const clearLink = document.querySelector('.navigator .actions .clear a');
        if (clearLink) {
            clearLink.addEventListener('click', () => {
                if (allFoldersToggle) {
                    allFoldersToggle.checked = false;
                }
                if (allFilesToggle) {
                    allFilesToggle.checked = false;
                }
            });
        }
    })();

    const copyUrlButtons = document.querySelectorAll('.js-copy-url');
    copyUrlButtons.forEach((button) => {
        button.addEventListener('click', function (e) {
            const url = new URL(this.dataset.url, document.location.href);
            const msg = this.dataset.msg || 'URL copied to clipboard';
            const infobox = document.createElement('template');
            e.preventDefault();

            const existingTooltips = document.querySelectorAll('.info.filer-tooltip');
            existingTooltips.forEach((el) => {
                el.remove();
            });

            navigator.clipboard.writeText(url.href);
            infobox.innerHTML = `<div class="info filer-tooltip">${msg}</div>`;
            this.classList.add('filer-tooltip-wrapper');
            this.appendChild(infobox.content.firstChild);

            const self = this;
            setTimeout(() => {
                const tooltip = self.querySelector('.info');
                if (tooltip) {
                    tooltip.remove();
                }
            }, 1200);
        });
    });

    // Initialize FocalPoint
    const focalPoint = new FocalPoint();
    focalPoint.initialize();

    // Initialize Toggler (auto-initializes in constructor)
    new Toggler();
});
