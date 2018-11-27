/* ========================================================================
 * Bootstrap: dropdown.js v3.3.6
 * http://getbootstrap.com/javascript/#dropdowns
 * ========================================================================
 * Copyright 2011-2016 Twitter, Inc.
 * Licensed under MIT (https://github.com/twbs/bootstrap/blob/master/LICENSE)
 * ======================================================================== */
'use strict';

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

/* global django */
(function ($) {

    // DROPDOWN CLASS DEFINITION
    // =========================

    var backdrop = '.filer-dropdown-backdrop';
    var toggle   = '[data-toggle="filer-dropdown"]';
    var Dropdown = function (element) {
        $(element).on('click.bs.filer-dropdown', this.toggle);
    };
    var old = $.fn.dropdown;

    function getParent($this) {
        var selector = $this.attr('data-target');
        var $parent = selector && $(selector);

        if (!selector) {
            selector = $this.attr('href');
            selector = selector && /#[A-Za-z]/.test(selector) && selector.replace(/.*(?=#[^\s]*$)/, ''); // strip for ie7
        }

        return $parent && $parent.length ? $parent : $this.parent(); // jshint ignore:line
    }

    function clearMenus(e) {
        if (e && e.which === 3) {
            return;
        }
        $(backdrop).remove();
        $(toggle).each(function () {
            var $this = $(this);
            var $parent = getParent($this);
            var relatedTarget = { relatedTarget: this };

            if (!$parent.hasClass('open')) {
                return;
            }

            if (e && e.type === 'click' && /input|textarea/i.test(e.target.tagName) && $.contains($parent[0], e.target)) { // jshint ignore:line
                return;
            }

            $parent.trigger(e = $.Event('hide.bs.filer-dropdown', relatedTarget));

            if (e.isDefaultPrevented()) {
                return;
            }

            $this.attr('aria-expanded', 'false');
            $parent.removeClass('open').trigger($.Event('hidden.bs.filer-dropdown', relatedTarget));
        });
    }

    Dropdown.prototype.toggle = function (e) {
        var $this = $(this);
        var $parent  = getParent($this);
        var isActive = $parent.hasClass('open');
        var relatedTarget = { relatedTarget: this };

        if ($this.is('.disabled, :disabled')) {
            return;
        }

        clearMenus();

        if (!isActive) {
            if ('ontouchstart' in document.documentElement && !$parent.closest('.navbar-nav').length) {
                // if mobile we use a backdrop because click events don't delegate
                $(document.createElement('div')).addClass('filer-dropdown-backdrop')
                    .insertAfter($(this)).on('click', clearMenus);
            }

            $parent.trigger(e = $.Event('show.bs.filer-dropdown', relatedTarget));

            if (e.isDefaultPrevented()) {
                return;
            }

            $this.trigger('focus').attr('aria-expanded', 'true');

            $parent.toggleClass('open').trigger($.Event('shown.bs.filer-dropdown', relatedTarget));
        }

        return false;
    };

    Dropdown.prototype.keydown = function (e) {
        var $this = $(this);
        var $parent  = getParent($this);
        var isActive = $parent.hasClass('open');
        var desc = ' li:not(.disabled):visible a';
        var $items = $parent.find('.dropdown-menu' + desc);
        var index = $items.index(e.target);

        if (!/(38|40|27|32)/.test(e.which) || /input|textarea/i.test(e.target.tagName)) {
            return;
        }

        e.preventDefault();
        e.stopPropagation();

        if ($this.is('.disabled, :disabled')) {
            return;
        }

        if (!isActive && e.which !== 27 || isActive && e.which === 27) {
            if (e.which === 27) {
                $parent.find(toggle).trigger('focus');
            }
            return $this.trigger('click');
        }

        if (!$items.length) {
            return;
        }

        if (e.which === 38 && index > 0) {
            index--; // up
        }
        if (e.which === 40 && index < $items.length - 1) {
            index++; // down
        }
        if (!~index) { // jshint ignore:line
            index = 0;
        }

        $items.eq(index).trigger('focus');
    };


    // DROPDOWN PLUGIN DEFINITION
    // ==========================

    function Plugin(option) {
        return this.each(function () {
            var $this = $(this);
            var data = $this.data('bs.filer-dropdown');

            if (!data) {
                $this.data('bs.filer-dropdown', (data = new Dropdown(this)));
            }
            if (typeof option === 'string') {
                data[option].call($this);
            }
        });
    }


    $.fn.dropdown = Plugin;
    $.fn.dropdown.Constructor = Dropdown;


    // DROPDOWN NO CONFLICT
    // ====================

    $.fn.dropdown.noConflict = function () {
        $.fn.dropdown = old;
        return this;
    };


    // APPLY TO STANDARD DROPDOWN ELEMENTS
    // ===================================

    $(document)
        .on('click.bs.filer-dropdown.data-api', clearMenus)
        .on('click.bs.filer-dropdown.data-api', '.filer-dropdown form', function (e) {
                e.stopPropagation();
            })
        .on('click.bs.filer-dropdown.data-api', toggle, Dropdown.prototype.toggle)
        .on('keydown.bs.filer-dropdown.data-api', toggle, Dropdown.prototype.keydown)
        .on('keydown.bs.filer-dropdown.data-api', '.filer-dropdown-menu', Dropdown.prototype.keydown);

})(djQuery);
