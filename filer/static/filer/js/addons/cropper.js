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
            locationSelector: '.js-cropper-location',
            dataLocation: 'location-selector',
            hiddenClass: 'hidden'
        },
        _init: function (container) {
            var cropperInstance = new Cl.CropperConstructor(container, this.options);
            this.cropperInstances.push(cropperInstance);
        },
        initialize: function (options) {
            var that = this;

            this.options = $.extend({}, this.options, options);
            this.cropperInstances = [];
            this._init = $.proxy(this._init, this);

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
        _getLocationValue: function () {
            var that = this;
            var currentLocation;

            if (that.ratio === 0) {
                throw new Error('cropper: no aspect ratio specified');
            }

            if (!this.location || !this.location.length) {
                return false;
            }

            currentLocation = this.location.val();

            if (currentLocation) {
                currentLocation = $.parseJSON(currentLocation);

                $.each(currentLocation, function (index, value) {
                    currentLocation[index] = Math.floor(value / that.ratio);
                });

                currentLocation.x = currentLocation.left;
                currentLocation.y = currentLocation.top;

                return currentLocation;
            }

            return false;
        },
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
            this._getLocationValue = $.proxy(this._getLocationValue, this);

            this.image.cropper({
                viewMode: 2,
                dragMode: 'crop',
                autoCropArea: 0.1,
                data: that._getLocationValue,
                crop: that._updateLocationValue
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
            this.image.off('load', this._onImageLoaded);
            this.image.cropper('destroy');
            this.image.off('load', this._onImageLoaded);

            this.options = null;

            this.container = null;
            this.image = null;
            this.ratio = null;
            this.location = null;
        }
    });
})(jQuery);
