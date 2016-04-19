'use strict';
/* global filerTooltip */

var filerTooltip = function ($) {
    var tooltipSelector = '.js-filer-tooltip';

    $(tooltipSelector).hover(function(){
        var title = $(this).attr('title');

        $(this).data('tipText', title).removeAttr('title');
        $('<p class="filer-tooltip"></p>').text(title).appendTo(tooltipSelector);

    }, function() {
        // Hover out code
        $(this).attr('title', $(this).data('tipText'));
        $('.filer-tooltip').remove();
    });
};
