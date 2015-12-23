// #####################################################################################################################
// #BASE#
// Basic logic django filer
'use strict';

var Cl = window.Cl || {};
/* global Mediator */

(function ($) {
    $(function () {
        window.showError = function (message) {
            var messages = $('.messagelist');
            var header = $('#header');
            var tpl = '<ul class="messagelist"><li class="error">{msg}</li></ul>';
            var msg = tpl.replace('{msg}', message);

            messages.length ? messages.replaceWith(msg) : header.after(msg);
        };

        // mediator init
        Cl.mediator = new Mediator();

        // Focal point logic init
        if (Cl.FocalPoint) {
            new Cl.FocalPoint();
        }

        // Toggler init
        if (Cl.Toggler) {
            new Cl.Toggler();
        }

        $(document).on('click', '.dropdown-menu-checkboxes', function (clickEvent) {
            clickEvent.stopPropagation();
        });

        // Focus on the search field on page load
        (function () {
            var filter = $('.js-filter-files');

            if (filter.length) {
                filter.focus();
            }
        }());

        // mocking the action buttons to work in frontend UI, please do not review
        (function () {
            var dropdown = $('.js-actions-menu .dropdown-menu');
            var actionsSelect = $('.actions select[name="action"]');
            var actionsSelectOptions = actionsSelect.find('option');
            var actionsGo = $('.actions button[type="submit"]');
            var html = '';
            var i = 0;

            $.each(actionsSelectOptions, function () {
                if (i !== 0) {
                    html += '<li><a href="#">' + $(this).text() + '</a></li>';
                }
                i++;
            });
            dropdown.append(html);

            dropdown.on('click', function (clickEvent) {
                var targetIndex = $(clickEvent.target).closest('li').index() + 1;

                clickEvent.preventDefault();

                actionsSelect.find('option').eq(targetIndex).attr('selected', 'selected');
                actionsGo.trigger('click');
            });
        }());
    });
})(jQuery);
