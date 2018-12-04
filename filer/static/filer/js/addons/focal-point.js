// #FOCAL POINT#
// This script implements the image focal point setting
'use strict';

var Cl = window.Cl || {};
/* globals Class, django */

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

(function ($) {
    Cl.FocalPoint = new Class({
        options: {
            containerSelector: '.js-focal-point',
            imageSelector: '.js-focal-point-image',
            circleSelector: '.js-focal-point-circle',
            locationSelector: '.js-focal-point-location',
            draggableClass: 'ui-draggable',
            hiddenClass: 'hidden',
            dataLocation: 'location-selector'
        },
        _init: function (container) {
            var focalPointInstance = new Cl.FocalPointConstructor(container, this.options);
            this.focalPointInstances.push(focalPointInstance);
        },
        initialize: function (options) {
            var that = this;

            this.options = $.extend({}, this.options, options);
            this.focalPointInstances = [];

            $(this.options.containerSelector).each(function () {
                that._init(this);
            });

            Cl.mediator.subscribe('focal-point:init', this._init);
        },
        destroy: function () {
            Cl.mediator.remove('focal-point:init', this._init);

            this.focalPointInstances.forEach(function (focalPointInstance) {
                focalPointInstance.destroy();
            });

            this.focalPointInstances = [];
        }
    });

    Cl.FocalPointConstructor = new Class({
        _updateLocationValue: function (x, y) {
            var locationValue;

            locationValue = Math.round(x * this.ratio) + ',' + Math.round(y * this.ratio);

            this.location.val(locationValue);
        },
        _onImageLoaded: function () {
            var that = this;
            var x = null;
            var y = null;
            var locationValue = this.location.val();
            var imageWidth = this.image.width();
            var imageHeight = this.image.height();

            if (this.image[0].naturalWidth === 0) {
                return;
            }

            this.circle.removeClass(this.options.hiddenClass);

            if (locationValue.length) {
                x = Math.round(Number(locationValue.split(',')[0]) / this.ratio);
                y = Math.round(Number(locationValue.split(',')[1]) / this.ratio);
            } else {
                y = imageHeight / 2;
                x = imageWidth / 2;
            }

            if (isNaN(x) || isNaN(y)) {
                return;
            }

            this.circle.css({
                top: y,
                left: x
            });

            this.circle.draggable({
                containment: 'parent',
                drag: function (event, ui) {
                    that._updateLocationValue(ui.position.left, ui.position.top);
                }
            });

            this._updateLocationValue(x, y);
        },
        _getLocation: function () {
            var newLocationSelector = this.container.data(this.options.dataLocation);
            var newLocation = $(newLocationSelector);
            if (newLocation.length) {
                return newLocation;
            } else {
                return this.container.find(this.options.locationSelector);
            }
        },
        initialize: function (container, options) {
            this.options = $.extend({}, this.options, options);

            this.container = $(container);
            this.containerOffset = this.container.offset();
            this.image = this.container.find(this.options.imageSelector);
            this.circle = this.container.find(this.options.circleSelector);
            this.ratio = parseFloat(this.image.data('ratio'));
            this.location = this._getLocation();
            this._onImageLoaded = $.proxy(this._onImageLoaded, this);

            if (this.image.prop('complete')) {
                this._onImageLoaded();
            } else {
                this.image.on('load', this._onImageLoaded);
            }

        },
        destroy: function () {
            if (this.circle.hasClass(this.options.draggableClass)) {
                this.circle.draggable('disable');
            }

            this.options = null;

            this.container = null;
            this.containerOffset = null;
            this.image = null;
            this.circle = null;
            this.location = null;
            this.ratio = null;
        }
    });
})(djQuery);
