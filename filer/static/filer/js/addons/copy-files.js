'use strict';
/* global */

jQuery(function ($) {
    var destinationOptions = $('#destination').find('option');
    var destinationOptionLength = destinationOptions.length;
    var submit = $('.js-submit');

    console.log(destinationOptions.prop('disabled'));
    console.log(destinationOptionLength);

    if (destinationOptionLength == 1 && destinationOptions.prop('disabled')) {
        submit.prop('disabled', true);
    }
});
