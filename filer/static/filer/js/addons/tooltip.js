'use strict';
var Cl = window.Cl || {};

Cl.filerTooltip = function ($) {
    var tooltipSelector = '.js-filer-tooltip';

    $(tooltipSelector).on('mouseover', function () {
        var that = $(this);
        var title = that.attr('title');

        that.data('filerTooltip', title).removeAttr('title');
        $('<p class="filer-tooltip"></p>').text(title).appendTo(tooltipSelector);

    }).on('mouseout', function () {
        var that = $(this);

        that.attr('title', that.data('filerTooltip'));
        $('.filer-tooltip').remove();
    });
};
