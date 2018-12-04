// #TOGGLER#
// This script implements the simple element toggle
'use strict';

var Cl = window.Cl || {};
/* global Class, django */

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

(function ($) {
    Cl.Toggler = new Class({
        options: {
            linksSelector: '.js-toggler-link',
            dataHeaderSelector: 'toggler-header-selector',
            dataContentSelector: 'toggler-content-selector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        },
        initialize: function (options) {
            var that = this;

            this.options = $.extend({}, this.options, options);
            this.togglerInstances = [];

            $(this.options.linksSelector).each(function () {
                var togglerInstance = new Cl.TogglerConstructor(this, that.options);
                that.togglerInstances.push(togglerInstance);
            });
        },
        destroy: function () {
            this.links = null;

            this.togglerInstances.forEach(function (togglerInstance) {
                togglerInstance.destroy();
            });

            this.togglerInstances = [];
        }
    });

    Cl.TogglerConstructor = new Class({
        _updateClasses: function () {
            if (this.content.hasClass(this.options.hiddenClass)) {
                this.header.removeClass(this.options.expandedClass);
                this.header.addClass(this.options.collapsedClass);
            } else {
                this.header.addClass(this.options.expandedClass);
                this.header.removeClass(this.options.collapsedClass);
            }
        },
        _onTogglerClick: function (clickEvent) {
            this.content.toggleClass(this.options.hiddenClass);
            this._updateClasses();

            clickEvent.preventDefault();
        },
        _initLink: function () {
            this._updateClasses();

            this._onTogglerClick = $.proxy(this._onTogglerClick, this);
            this.link.on('click', this._onTogglerClick);
        },
        initialize: function (link, options) {
            this.options = $.extend({}, this.options, options);

            this.link = $(link);
            this.headerSelector = this.link.data(this.options.dataHeaderSelector);
            this.contentSelector = this.link.data(this.options.dataContentSelector);
            this.header = $(this.headerSelector);
            this.header = this.header.length ? this.header : this.link;
            this.content = $(this.contentSelector);

            if (this.content.length === 0) {
                return;
            }

            this._initLink();
        },
        destroy: function () {
            this.options = null;
            this.link = null;
        }
    });
})(djQuery);
