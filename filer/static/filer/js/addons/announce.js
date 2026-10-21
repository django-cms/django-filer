// #ANNOUNCE#
// Sends short status messages to screen readers through a shared live region
'use strict';

const liveRegionClass = 'js-filer-live-region';

const getLiveRegion = () => {
    let region = document.querySelector(`.${liveRegionClass}`);

    if (!region) {
        region = document.createElement('div');
        region.className = `${liveRegionClass} sr-only`;
        region.setAttribute('role', 'status');
        region.setAttribute('aria-live', 'polite');
        document.body.appendChild(region);
    }
    return region;
};

export const announce = (message) => {
    const region = getLiveRegion();
    const text = (message || '').trim();

    // clear first so that repeating the same message is announced again
    region.textContent = '';
    if (text) {
        setTimeout(() => {
            region.textContent = text;
        }, 50);
    }
};
