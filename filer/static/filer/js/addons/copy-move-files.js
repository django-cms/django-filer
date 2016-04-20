'use strict';
/* global django, Cl */

/*
    This functionality is used in folder/choose_copy_destination.html template
    to disable submit if there is only one folder to copy
*/

django.jQuery(function ($) {
    var destinationOptions = $('#destination').find('option');
    var destinationOptionLength = destinationOptions.length;
    var submit = $('.js-submit-copy-move');
    var tooltip = $('.js-disabled-btn-tooltip');

    if (destinationOptionLength === 1 && destinationOptions.prop('disabled')) {
        submit.hide();
        tooltip.show().css('display', 'inline-block');
    }

    Cl.filerTooltip($);
});
