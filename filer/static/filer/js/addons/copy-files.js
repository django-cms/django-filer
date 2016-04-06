'use strict';

jQuery(function ($) {
    var destinationOptions = $('#destination').find('option');
    var destinationOptionLength = destinationOptions.length;
    var submit = $('.js-submit-copy');

    if (destinationOptionLength === 1 && destinationOptions.prop('disabled')) {
        submit.prop('disabled', true);
    }
});
