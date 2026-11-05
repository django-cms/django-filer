/* ========================================================================
 * Bootstrap: dropdown.js v3.3.6
 * http://getbootstrap.com/javascript/#dropdowns
 * ========================================================================
 * Copyright 2011-2016 Twitter, Inc.
 * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
 * ======================================================================== */
'use strict';

(() => {
    // DROPDOWN CLASS DEFINITION
    // =========================

    const backdropClass = 'filer-dropdown-backdrop';
    const toggleSelector = '[data-toggle="filer-dropdown"]';

    class Dropdown {
        constructor(element) {
            this.element = element;
            element.addEventListener('click', () => this.toggle());
        }

        toggle() {
            const element = this.element;
            const parent = getParent(element);
            const isActive = parent.classList.contains('open');
            const relatedTarget = { relatedTarget: element };

            if (element.disabled || element.classList.contains('disabled')) {
                return false;
            }

            clearMenus();

            if (!isActive) {
                if ('ontouchstart' in document.documentElement && !parent.closest('.navbar-nav')) {
                    // if mobile we use a backdrop because click events don't delegate
                    const backdrop = document.createElement('div');
                    backdrop.className = backdropClass;
                    element.parentNode.insertBefore(backdrop, element.nextSibling);
                    backdrop.addEventListener('click', clearMenus);
                }

                const showEvent = new CustomEvent('show.bs.filer-dropdown', {
                    bubbles: true,
                    cancelable: true,
                    detail: relatedTarget
                });
                parent.dispatchEvent(showEvent);

                if (showEvent.defaultPrevented) {
                    return false;
                }

                element.focus();
                element.setAttribute('aria-expanded', 'true');
                parent.classList.add('open');

                const shownEvent = new CustomEvent('shown.bs.filer-dropdown', {
                    bubbles: true,
                    detail: relatedTarget
                });
                parent.dispatchEvent(shownEvent);
            }

            return false;
        }

        keydown(e) {
            const element = this.element;
            const parent = getParent(element);
            const isActive = parent.classList.contains('open');
            const desc = ' li:not(.disabled):visible a';
            const items = Array.from(parent.querySelectorAll(`.filer-dropdown-menu${desc}`))
                .filter(item => item.offsetParent !== null); // visible check
            const index = items.indexOf(e.target);

            if (!/(38|40|27|32)/.test(e.which) || /input|textarea/i.test(e.target.tagName)) {
                return;
            }

            e.preventDefault();
            e.stopPropagation();

            if (element.disabled || element.classList.contains('disabled')) {
                return;
            }

            if ((!isActive && e.which !== 27) || (isActive && e.which === 27)) {
                if (e.which === 27) {
                    parent.querySelector(toggleSelector)?.focus();
                }
                return element.click();
            }

            if (!items.length) {
                return;
            }

            let newIndex = index;
            if (e.which === 38 && index > 0) {
                newIndex--; // up
            }
            if (e.which === 40 && index < items.length - 1) {
                newIndex++; // down
            }
            if (newIndex === -1) {
                newIndex = 0;
            }

            items[newIndex]?.focus();
        }
    }

    function getParent(element) {
        let selector = element.getAttribute('data-target');
        let parent = selector ? document.querySelector(selector) : null;

        if (!selector) {
            selector = element.getAttribute('href');
            selector = selector && /#[A-Za-z]/.test(selector) && selector.replace(/.*(?=#[^\s]*$)/, ''); // strip for ie7
            parent = selector ? document.querySelector(selector) : null;
        }

        return parent && parent.parentNode ? parent : element.parentNode;
    }

    function clearMenus(e) {
        if (e && e.which === 3) {
            return;
        }

        // Remove all backdrops
        document.querySelectorAll(`.${backdropClass}`).forEach(el => el.remove());

        document.querySelectorAll(toggleSelector).forEach((toggle) => {
            const parent = getParent(toggle);
            const relatedTarget = { relatedTarget: toggle };

            if (!parent.classList.contains('open')) {
                return;
            }

            if (e && e.type === 'click' && /input|textarea/i.test(e.target.tagName) && parent.contains(e.target)) {
                return;
            }

            const hideEvent = new CustomEvent('hide.bs.filer-dropdown', {
                bubbles: true,
                cancelable: true,
                detail: relatedTarget
            });
            parent.dispatchEvent(hideEvent);

            if (hideEvent.defaultPrevented) {
                return;
            }

            toggle.setAttribute('aria-expanded', 'false');
            parent.classList.remove('open');

            const hiddenEvent = new CustomEvent('hidden.bs.filer-dropdown', {
                bubbles: true,
                detail: relatedTarget
            });
            parent.dispatchEvent(hiddenEvent);
        });
    }

    // DROPDOWN PLUGIN DEFINITION
    // ==========================

    function Plugin(option) {
        this.forEach((element) => {
            let data = element._filerDropdownInstance;

            if (!data) {
                data = new Dropdown(element);
                element._filerDropdownInstance = data;
            }
            if (typeof option === 'string') {
                data[option].call(element);
            }
        });
        return this;
    }

    // Extend NodeList and HTMLCollection with dropdown method
    if (!NodeList.prototype.dropdown) {
        NodeList.prototype.dropdown = function(option) {
            return Plugin.call(this, option);
        };
    }
    if (!HTMLCollection.prototype.dropdown) {
        HTMLCollection.prototype.dropdown = function(option) {
            return Plugin.call(this, option);
        };
    }

    // APPLY TO STANDARD DROPDOWN ELEMENTS
    // ===================================

    document.addEventListener('click', clearMenus);

    document.addEventListener('click', (e) => {
        if (e.target.closest('.filer-dropdown form')) {
            e.stopPropagation();
        }
    });

    document.addEventListener('click', (e) => {
        const toggle = e.target.closest(toggleSelector);
        if (toggle) {
            const instance = toggle._filerDropdownInstance || new Dropdown(toggle);
            if (!toggle._filerDropdownInstance) {
                toggle._filerDropdownInstance = instance;
            }
            instance.toggle(e);
        }
    });

    document.addEventListener('keydown', (e) => {
        const toggle = e.target.closest(toggleSelector);
        if (toggle) {
            const instance = toggle._filerDropdownInstance || new Dropdown(toggle);
            if (!toggle._filerDropdownInstance) {
                toggle._filerDropdownInstance = instance;
            }
            instance.keydown(e);
        }
    });

    document.addEventListener('keydown', (e) => {
        const menu = e.target.closest('.filer-dropdown-menu');
        if (menu) {
            const toggle = menu.parentNode.querySelector(toggleSelector);
            if (toggle) {
                const instance = toggle._filerDropdownInstance || new Dropdown(toggle);
                if (!toggle._filerDropdownInstance) {
                    toggle._filerDropdownInstance = instance;
                }
                instance.keydown(e);
            }
        }
    });

    // Export for compatibility
    window.FilerDropdown = Dropdown;
})();
