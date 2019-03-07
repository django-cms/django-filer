'use strict';
/* global django, Cl */

/*
    This functionality is used in folder/choose_copy_destination.html template
    to disable submit if there is only one folder to copy
*/

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

djQuery(function ($) {
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
