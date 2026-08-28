'use strict';
window.Cl = window.Cl || {};

Cl.filerTooltip = () => {
    const tooltipSelector = '.js-filer-tooltip';
    const tooltips = document.querySelectorAll(tooltipSelector);

    tooltips.forEach((element) => {
        element.addEventListener('mouseover', function () {
            const title = this.getAttribute('title');
            if (!title) {
                return;
            }

            this.dataset.filerTooltip = title;
            this.removeAttribute('title');

            const tooltip = document.createElement('p');
            tooltip.className = 'filer-tooltip';
            tooltip.textContent = title;

            const container = document.querySelector(tooltipSelector);
            if (container) {
                container.appendChild(tooltip);
            }
        });

        element.addEventListener('mouseout', function () {
            const title = this.dataset.filerTooltip;
            if (title) {
                this.setAttribute('title', title);
            }

            const existingTooltips = document.querySelectorAll('.filer-tooltip');
            existingTooltips.forEach((t) => {
                t.remove();
            });
        });
    });
};
