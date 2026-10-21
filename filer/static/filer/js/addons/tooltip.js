'use strict';
window.Cl = window.Cl || {};

Cl.filerTooltip = () => {
    const tooltipSelector = '.js-filer-tooltip';
    const tooltips = document.querySelectorAll(tooltipSelector);

    const showTooltip = function () {
        const title = this.getAttribute('title');
        if (!title) {
            return;
        }

        this.dataset.filerTooltip = title;
        this.removeAttribute('title');

        const tooltip = document.createElement('p');
        tooltip.className = 'filer-tooltip';
        tooltip.textContent = title;
        // the reason is exposed to assistive technology via aria-describedby on the control
        tooltip.setAttribute('aria-hidden', 'true');
        this.appendChild(tooltip);
    };

    const hideTooltip = function () {
        const title = this.dataset.filerTooltip;
        if (title) {
            this.setAttribute('title', title);
        }

        this.querySelectorAll('.filer-tooltip').forEach((t) => {
            t.remove();
        });
    };

    tooltips.forEach((element) => {
        element.addEventListener('mouseover', showTooltip);
        element.addEventListener('mouseout', hideTooltip);
        // keyboard users get the same hint when the control receives focus
        element.addEventListener('focusin', showTooltip);
        element.addEventListener('focusout', hideTooltip);
    });
};
