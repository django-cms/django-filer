'use strict';
/* global django */

django.jQuery(function ($) {
    var dropdownMenu = $('.js-filer-dropdown-menu');
    var containerSelector = '.js-filter-files-container';
    var closeDropdown = $('.js-close-dropdown-menu-checkboxes');
    var navigatorTable = $('.navigator-table').find('tr');
    var dropdownContainer = '.dropdown-container';

    dropdownMenu.on('click', function (e) {
        dropdownMenu.not(this).parent(dropdownContainer).removeClass('open');
        if (!navigatorTable.hasClass('selected') && $(this).parent(dropdownContainer).hasClass('js-actions-menu')) {
            $('.js-actions-menu').removeClass('open');
        } else {
            $(this).parent(dropdownContainer).toggleClass('open');
        }
        if ($(containerSelector).find(dropdownContainer).hasClass('open')) {
            $(containerSelector).addClass('is-focused');
        } else {
            $(containerSelector).removeClass('is-focused');
        }
    });

    closeDropdown.on('click', function () {
        $(containerSelector).find(dropdownContainer).removeClass('open');
        $(containerSelector).removeClass('is-focused');
    });



});
