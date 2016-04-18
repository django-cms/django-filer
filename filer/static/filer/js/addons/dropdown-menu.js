'use strict';
/* global django */

django.jQuery(function ($) {
    var dropdownMenu = $('.js-filer-dropdown-menu');
    var closeDropdown = $('.js-close-dropdown-menu-checkboxes');

    dropdownMenu.on('click', function () {
        $(this).parent().toggleClass('open');
    });

    closeDropdown.on('click', function () {
        console.log('close')
        $(this).closest('.dropdown-container').removeClass('open');
    });



});
