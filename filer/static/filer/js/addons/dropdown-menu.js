'use strict';
/* global django */

django.jQuery(function ($) {
    var dropdownMenu = $('.js-filer-dropdown-menu');
    var containerSelector = '.js-filter-files-container';
    var closeDropdown = $('.js-close-dropdown-menu-checkboxes');

    dropdownMenu.on('click', function () {
        $(this).parent().toggleClass('open');
        if ($(containerSelector).find('.dropdown-container').hasClass('open')) {
            $(containerSelector).addClass('is-focused');
        } else {
            $(containerSelector).removeClass('is-focused');
        }
    });

    closeDropdown.on('click', function () {
        $(containerSelector).find('.dropdown-container').removeClass('open');
        $(containerSelector).removeClass('is-focused');
    });



});
