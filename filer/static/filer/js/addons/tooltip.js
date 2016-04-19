'use strict';
var Cl = window.Cl || {};

Cl.filerTooltip = function ($) {
    var tooltipSelector = '.js-filer-tooltip';
    var that = $(this);

    $(tooltipSelector).on('hover', function () {
        var title = that.attr('title');

        that.data('filerTooltip', title).removeAttr('title');
        $('<p class="filer-tooltip"></p>').text(title).appendTo(tooltipSelector);

    }, function () {
        // Hover out code
        that.attr('title', that.data('filerTooltip'));
        $('.filer-tooltip').remove();
    });
};
