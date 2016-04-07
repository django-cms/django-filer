'use strict';
/* global django */

/*
    This functionality is used in folder/choose_copy_destination.html template
    to disable submit if there is only one folder to copy
*/

django.jQuery(function ($) {
    var destinationOptions = $('#destination').find('option');
    var destinationOptionLength = destinationOptions.length;
    var submit = $('.js-submit-copy');
    var tooltip = $('.js-disabled-btn-tooltip');
    var tooltipText = tooltip.data('tooltip-text');

    if (destinationOptionLength === 1 && destinationOptions.prop('disabled')) {
        submit.prop('disabled', true);
        tooltip.prop('title', tooltipText);
        tooltip.attr('data-toggle', 'tooltip');
        tooltip.attr('data-placement', 'bottom');
debugger;
        tooltip.tooltip();
    }
});
