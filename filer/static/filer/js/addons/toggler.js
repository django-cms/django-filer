// #TOGGLER#
// This script implements the simple element toggle
'use strict';

window.Cl = window.Cl || {};

class Toggler {
    constructor(options = {}) {
        this.options = {
            linksSelector: '.js-toggler-link',
            dataHeaderSelector: 'toggler-header-selector',
            dataContentSelector: 'toggler-content-selector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden',
            ...options
        };

        this.togglerInstances = [];

        const links = document.querySelectorAll(this.options.linksSelector);
        links.forEach(link => {
            const togglerInstance = new TogglerConstructor(link, this.options);
            this.togglerInstances.push(togglerInstance);
        });
    }

    destroy() {
        this.links = null;
        this.togglerInstances.forEach(togglerInstance => togglerInstance.destroy());
        this.togglerInstances = [];
    }
}

class TogglerConstructor {
    constructor(link, options = {}) {
        this.options = { ...options };
        this.link = link;
        this.headerSelector = this.link.dataset[this.options.dataHeaderSelector];
        this.contentSelector = this.link.dataset[this.options.dataContentSelector];
        this.header = document.querySelector(this.headerSelector);
        this.header = this.header || this.link;
        this.content = document.querySelector(this.contentSelector);

        if (!this.content) {
            return;
        }

        this._initLink();
    }

    _updateClasses() {
        if (this.content.classList.contains(this.options.hiddenClass)) {
            this.header.classList.remove(this.options.expandedClass);
            this.header.classList.add(this.options.collapsedClass);
        } else {
            this.header.classList.add(this.options.expandedClass);
            this.header.classList.remove(this.options.collapsedClass);
        }
    }

    _onTogglerClick(clickEvent) {
        this.content.classList.toggle(this.options.hiddenClass);
        this._updateClasses();
        clickEvent.preventDefault();
    }

    _initLink() {
        this._updateClasses();
        this.link.addEventListener('click', e => this._onTogglerClick(e));
    }

    destroy() {
        this.options = null;
        this.link = null;
    }
}

Cl.Toggler = Toggler;
Cl.TogglerConstructor = TogglerConstructor;

export default Toggler;
