// #CROPPER#
// This script implements the image cropper settings
'use strict';

var Cl = window.Cl || {};
/* global Class */
(function ($) {
    Cl.Cropper = new Class({
        options: {
            containerSelector: '.js-cropper',
            imageSelector: '.js-cropper-image',
            circleSelector: '.js-cropper-circle',
            locationSelector: '.js-cropper-location',
            draggableClass: 'ui-draggable',
            hiddenClass: 'hidden',
            dataLocation: 'location-selector'
        },
        _init: function (container) {
            var cropperInstance = new Cl.CropperConstructor(container, this.options);
            this.cropperInstances.push(cropperInstance);
        },
        initialize: function (options) {
            var that = this;

            this.options = $.extend({}, this.options, options);
            this.cropperInstances = [];

            $(this.options.containerSelector).each(function () {
                that._init(this);
            });

            Cl.mediator.subscribe('cropper:init', this._init);
        },
        destroy: function () {
            Cl.mediator.remove('cropper:init', this._init);

            this.cropperInstances.forEach(function (CropperInstance) {
                CropperInstance.destroy();
            });

            this.cropperInstances = [];
        }
    });

    Cl.CropperConstructor = new Class({
        _updateLocationValue: function () {
            var that = this;
            var cropData = this.image.cropper('getCropBoxData');

            $.each(cropData, function (index, value) {
                cropData[index] = Math.floor(value * that.ratio);
            });

            this.location.val(JSON.stringify(cropData));
        },
        _onImageLoaded: function () {
            var that = this;

            this._updateLocationValue = $.proxy(this._updateLocationValue, this);

            this.image.cropper({
                viewMode: 2,
                dragMode: 'crop',
                autoCropArea: 1,
                crop: that._updateLocationValue,
                preview: that.container.find('.js-cropper-preview')
            });
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
            this.image = this.container.find(this.options.imageSelector);
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
            this.image = null;
            this.location = null;
            this.ratio = null;
        }
    });
})(jQuery);
