// #####################################################################################################################
// #BASE#
// Basic logic django filer
'use strict';

var Cl = window.Cl || {};

/* globals Mediator, django */

// mediator init
Cl.mediator = new Mediator();

(function ($) {
    $(function () {
        var showErrorTimeout;

        window.filerShowError = function (message) {
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

        $('.js-filter-files').on('focus blur', function (event) {
            var container = $(this).closest('.navigator-top-nav');
            var dropdownTrigger = container.find('.dropdown-container a');

            if (event.type === 'focus') {
                container.addClass('search-is-focused');
            } else {
                if (!dropdownTrigger.is(event.relatedTarget)) {
                    container.removeClass('search-is-focused');
                }
            }
        });

        // Focus on the search field on page load
        (function () {
            var filter = $('.js-filter-files');
            var containerSelector = '.navigator-top-nav';
            var searchDropdown = $(containerSelector).find('.filter-search-wrapper').find('.filer-dropdown-container');

            if (filter.length) {
                filter.on('keydown', function () {
                    $(this).closest(containerSelector).addClass('search-is-focused');
                });

                searchDropdown.on('show.bs.filer-dropdown', function () {
                    $(containerSelector).addClass('search-is-focused');
                }).on('hide.bs.filer-dropdown', function () {
                    $(containerSelector).removeClass('search-is-focused');
                });
            }
        }());

        // show counter if file is selected
        (function () {
            var navigatorTable = $('.navigator-table').find('tr');
            var actionList = $('.actions-wrapper');
            var actionSelect = $('.action-select, #action-toggle, .actions .clear a');

            // timeout is needed to wait until table row has class selected.
            setTimeout(function () {
                if (navigatorTable.hasClass('selected')) {
                    actionList.addClass('action-selected');
                }
            }, 100);

            actionSelect.on('change', function () {
                // setTimeout makes sure that change event fires before click event which is reliable to admin
                setTimeout(function () {
                    if (navigatorTable.hasClass('selected')) {
                        actionList.addClass('action-selected');
                    } else {
                        actionList.removeClass('action-selected');
                    }
                }, 0);

            });
        }());

        (function () {
            var actionsMenu = $('.js-actions-menu');
            var dropdown = actionsMenu.find('.filer-dropdown-menu');
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
            var navigatorTable = $('.navigator-table').find('tr');

            // triggers delete copy and move actions on separate buttons
            function actionsButton(optionValue, actionButton) {
                actionsSelectOptions.each(function () {
                    if (this.value === optionValue) {
                        actionButton.show();
                        actionButton.on('click', function (e) {
                            e.preventDefault();
                            if (navigatorTable.hasClass('selected')) {
                                actionsSelect.val(optionValue).prop('selected', true);
                                actionsGo.trigger('click');
                            }
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

            actionsMenu.on('click', function (e) {
                if (!navigatorTable.hasClass('selected')) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });
        }());

        // breaks header if breadcrumbs name reaches a width of 80px
        (function () {
            var minBreadcrumbWidth = 80;
            var header = $('.navigator-top-nav');

            var breadcrumbContainer = $('.breadcrumbs-container');
            var breadcrumbFolderWidth = breadcrumbContainer.find('.navigator-breadcrumbs').outerWidth();
            var breadcrumbDropdownWidth = breadcrumbContainer.find('.filer-dropdown-container').outerWidth();
            var searchWidth = $('.filter-files-container').outerWidth();
            var actionsWidth = $('.actions-wrapper').outerWidth();
            var buttonsWidth = $('.navigator-button-wrapper').outerWidth();
            var headerPadding = parseInt(header.css('padding-left'), 10) + parseInt(header.css('padding-right'), 10);

            var headerWidth = header.outerWidth();
            var fullHeaderWidth = minBreadcrumbWidth + breadcrumbFolderWidth +
                breadcrumbDropdownWidth + searchWidth + actionsWidth + buttonsWidth + headerPadding;

            var breadcrumbSizeHandlerClassName = 'breadcrumb-min-width';

            var breadcrumbSizeHandler = function () {
                if (headerWidth < fullHeaderWidth) {
                    header.addClass(breadcrumbSizeHandlerClassName);
                } else {
                    header.removeClass(breadcrumbSizeHandlerClassName);
                }
            };

            breadcrumbSizeHandler();

            $(window).on('resize', function () {
                headerWidth = header.outerWidth();
                breadcrumbSizeHandler();
            });

        }());
    });
})(django.jQuery);
