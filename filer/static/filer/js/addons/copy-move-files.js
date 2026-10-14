'use strict';
/* global Cl */

/*
    This functionality is used in folder/choose_copy_destination.html template
    to disable submit if there is only one folder to copy
*/

document.addEventListener('DOMContentLoaded', () => {
    const destination = document.getElementById('destination');
    if (!destination) {
        return;
    }

    const destinationOptions = destination.querySelectorAll('option');
    const destinationOptionLength = destinationOptions.length;
    const submit = document.querySelector('.js-submit-copy-move');
    const tooltip = document.querySelector('.js-disabled-btn-tooltip');

    if (destinationOptionLength === 1 && destinationOptions[0].disabled) {
        if (submit) {
            submit.style.display = 'none';
        }
        if (tooltip) {
            tooltip.style.display = 'inline-block';
        }
    }

    if (Cl.filerTooltip) {
        Cl.filerTooltip();
    }
});
