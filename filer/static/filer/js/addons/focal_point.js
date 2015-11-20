// #FOCAL POINT#
// This script implements the

var Cl = window.Cl || {};
/* global Class */

(function ($) {
    'use strict';

    Cl.FocalPoint = new Class({
        options: {
            containerSelector: '.js-focal-point',
            imageSelector: '.js-focal-point-image',
            circleSelector: '.js-focal-point-circle',
            locationSelector: '.js-focal-point-location',
            hiddenClass: 'hidden'
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

            if (isNaN(x) && isNaN(y)) {
                locationValue = '';
            } else {
                locationValue = parseInt(x * this.ratio) + ',' + parseInt(y * this.ratio);
            }
            this.location
                .val(locationValue);
        },
        _onImageLoaded: function () {
            var that = this;
            var x = null;
            var y = null;
            var locationValue = this.location.val();

            this.circle.removeClass(this.options.hiddenClass);

            this.imageWidth = this.image.width();
            this.imageHeight = this.image.height();
            this.ratio = parseFloat(this.image.data('ratio'));
            this.circleWidth = this.circle.outerWidth();
            this.circleHeight = this.circle.outerHeight();

            if (locationValue.length) {
                x = parseInt(parseInt(locationValue.split(',')[0]) / this.ratio);
                y = parseInt(parseInt(locationValue.split(',')[1]) / this.ratio);
            } else {
                y = this.imageHeight / 2;
                x = this.imageWidth / 2;
            }

            this.circle.css({
                'top': y,
                'left': x
            });

            this.circle.draggable({
                containment : [
                    this.containerOffset.left,
                    this.containerOffset.top,
                    this.containerOffset.left + this.imageWidth,
                    this.containerOffset.top + this.imageHeight
                ],
                drag: function (event, ui) {
                    that._updateLocationValue(ui.position.left, ui.position.top);
                }
            });

            this._updateLocationValue();

            this.isImageLoaded = true;
        },
        initialize: function (container, options) {
            this.options = $.extend({}, this.options, options);

            this.container = $(container);
            this.containerOffset = this.container.offset();
            this.image = this.container.find(this.options.imageSelector);
            this.circle = this.container.find(this.options.circleSelector);
            this.location = this.container.find(this.options.locationSelector);

            this.isDrag = null;
            this.isImageLoaded = false;

            this._onImageLoaded = $.proxy(this._onImageLoaded, this);

            this.image.on('load', this._onImageLoaded);
        },
        destroy: function () {
            this.circle.draggable('disable');

            this.focalPoint.remove();
            this.focalPoint = null;

            this.options = null;

            this.container = null;
            this.image = null;
            this.paper = null;
            this.location = null;

            this.isDrag = null;
            this.isImageLoaded = null;
        }
    });
})(jQuery);
