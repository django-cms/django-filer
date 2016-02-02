// #####################################################################################################################
// #BASE#
// Basic logic django filer
'use strict';

var Cl = window.Cl || {};

/* global Mediator */

// mediator init
Cl.mediator = new Mediator();

(function ($) {
    $(function () {
        var showErrorTimeout;

        window.showError = function (message) {
            var messages = $('.messagelist');
            var header = $('#header');
            var filerErrorClass = 'js-filer-error';
            var tpl = '<ul class="messagelist"><li class="error ' + filerErrorClass + '">{msg}</li></ul>';
            var msg = tpl.replace('{msg}', message);

            messages.length ? messages.replaceWith(msg) : header.after(msg);

            if (showErrorTimeout) {
                clearTimeout(showErrorTimeout);
            }

            showErrorTimeout = setTimeout(function () {
                $('.' + filerErrorClass).remove();
            }, 3000);
        };

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

        // show counter if file is selected
        (function () {
            var table = $('.navigator-table').find('tr');
            var actionCounter = $('.actions');
            var actionSelect = $('.action-select, #action-toggle, .actions .clear a');

            actionSelect.on('change click', function () {
                actionCounter.toggleClass('action-selected', table.hasClass('selected'));
            });
        }());

        (function () {
            var dropdown = $('.js-actions-menu .dropdown-menu');
            var actionsSelect = $('.actions select[name="action"]');
            var actionsSelectOptions = actionsSelect.find('option');
            var actionsGo = $('.actions button[type="submit"]');
            var html = '';
            var actionDelete = $('.js-action-delete');
            var actionCopy = $('.js-action-copy');
            var actionMove = $('.js-action-move');
            var valueDelete = 'delete_files_or_folders';
            var valueCopy = 'copy_files_and_folders';
            var valueMove = 'move_files_and_folders';

            // triggers delete copy and move actions on separate buttons
            function actionsButton(optionValue, actionButton) {
                actionsSelectOptions.each(function () {
                    if (this.value === optionValue) {
                        actionButton.show();

                        actionButton.on('click', function (e) {
                            e.preventDefault();
                            actionsSelect.val(optionValue).prop('selected', true);
                            actionsGo.trigger('click');
                        });
                    }
                });
            }

            actionsButton(valueDelete, actionDelete);
            actionsButton(valueCopy, actionCopy);
            actionsButton(valueMove, actionMove);

            // mocking the action buttons to work in frontend UI
            actionsSelectOptions.each(function (index) {
                var className = '';
                if (index !== 0) {
                    if (this.value === valueDelete || this.value === valueCopy || this.value === valueMove) {
                        className = 'class="hidden"';
                    }
                    html += '<li><a href="#"' + className + '>' + $(this).text() + '</a></li>';

                }
            });
            dropdown.append(html);

            dropdown.on('click', 'a', function (clickEvent) {
                var targetIndex = $(this).closest('li').index() + 1;

                clickEvent.preventDefault();

                actionsSelect.find('option').eq(targetIndex).prop('selected', true);
                actionsGo.trigger('click');
            });
        }());
    });
})(jQuery);
