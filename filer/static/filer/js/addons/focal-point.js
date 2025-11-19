// #FOCAL POINT#
// This script implements the image focal point setting
'use strict';

window.Cl = window.Cl || {};

(() => {
    class FocalPoint {
        constructor(options = {}) {
            this.options = {
                containerSelector: '.js-focal-point',
                imageSelector: '.js-focal-point-image',
                circleSelector: '.js-focal-point-circle',
                locationSelector: '.js-focal-point-location',
                draggableClass: 'draggable',
                hiddenClass: 'hidden',
                dataLocation: 'location-selector',
                ...options
            };
            this.focalPointInstances = [];
            this._init = this._init.bind(this);
        }

        _init(container) {
            const focalPointInstance = new FocalPointConstructor(container, this.options);
            this.focalPointInstances.push(focalPointInstance);
        }

        initialize() {
            const containers = document.querySelectorAll(this.options.containerSelector);
            containers.forEach((container) => {
                this._init(container);
            });

            if (window.Cl.mediator) {
                window.Cl.mediator.subscribe('focal-point:init', this._init);
            }
        }

        destroy() {
            if (window.Cl.mediator) {
                window.Cl.mediator.remove('focal-point:init', this._init);
            }

            this.focalPointInstances.forEach((focalPointInstance) => {
                focalPointInstance.destroy();
            });

            this.focalPointInstances = [];
        }
    }

    class FocalPointConstructor {
        constructor(container, options = {}) {
            this.options = {
                imageSelector: '.js-focal-point-image',
                circleSelector: '.js-focal-point-circle',
                locationSelector: '.js-focal-point-location',
                draggableClass: 'draggable',
                hiddenClass: 'hidden',
                dataLocation: 'location-selector',
                ...options
            };

            this.container = container;
            this.image = this.container.querySelector(this.options.imageSelector);
            this.circle = this.container.querySelector(this.options.circleSelector);
            this.ratio = parseFloat(this.image?.dataset.ratio || 1);
            this.location = this._getLocation();
            this.isDragging = false;
            this.dragStartX = 0;
            this.dragStartY = 0;
            this.circleStartX = 0;
            this.circleStartY = 0;

            this._onImageLoaded = this._onImageLoaded.bind(this);
            this._onMouseDown = this._onMouseDown.bind(this);
            this._onMouseMove = this._onMouseMove.bind(this);
            this._onMouseUp = this._onMouseUp.bind(this);

            if (this.image?.complete) {
                this._onImageLoaded();
            } else if (this.image) {
                this.image.addEventListener('load', this._onImageLoaded);
            }
        }

        _updateLocationValue(x, y) {
            const locationValue = `${Math.round(x * this.ratio)},${Math.round(y * this.ratio)}`;
            if (this.location) {
                this.location.value = locationValue;
            }
        }

        _getLocation() {
            const locationSelector = this.container.dataset[this.options.dataLocation];
            if (locationSelector) {
                const newLocation = document.querySelector(locationSelector);
                if (newLocation) {
                    return newLocation;
                }
            }
            return this.container.querySelector(this.options.locationSelector);
        }

        _makeDraggable() {
            if (!this.circle) return;

            this.circle.classList.add(this.options.draggableClass);
            this.circle.addEventListener('mousedown', this._onMouseDown);
            this.circle.addEventListener('touchstart', this._onMouseDown, { passive: false });
        }

        _onMouseDown(event) {
            event.preventDefault();
            this.isDragging = true;

            const clientX = event.type === 'touchstart' ? event.touches[0].clientX : event.clientX;
            const clientY = event.type === 'touchstart' ? event.touches[0].clientY : event.clientY;

            this.dragStartX = clientX;
            this.dragStartY = clientY;

            const rect = this.circle.getBoundingClientRect();
            this.circleStartX = rect.left;
            this.circleStartY = rect.top;

            document.addEventListener('mousemove', this._onMouseMove);
            document.addEventListener('mouseup', this._onMouseUp);
            document.addEventListener('touchmove', this._onMouseMove, { passive: false });
            document.addEventListener('touchend', this._onMouseUp);
        }

        _onMouseMove(event) {
            if (!this.isDragging) return;

            event.preventDefault();

            const clientX = event.type === 'touchmove' ? event.touches[0].clientX : event.clientX;
            const clientY = event.type === 'touchmove' ? event.touches[0].clientY : event.clientY;

            const deltaX = clientX - this.dragStartX;
            const deltaY = clientY - this.dragStartY;

            const containerRect = this.container.getBoundingClientRect();
            const circleRect = this.circle.getBoundingClientRect();

            let newX = this.circleStartX - containerRect.left + deltaX;
            let newY = this.circleStartY - containerRect.top + deltaY;

            // Constrain to container bounds
            const minX = 0;
            const minY = 0;
            const maxX = containerRect.width - circleRect.width;
            const maxY = containerRect.height - circleRect.height;

            newX = Math.max(minX, Math.min(maxX, newX));
            newY = Math.max(minY, Math.min(maxY, newY));

            this.circle.style.left = `${newX}px`;
            this.circle.style.top = `${newY}px`;

            // Update location value (center of circle)
            const centerX = newX + circleRect.width / 2;
            const centerY = newY + circleRect.height / 2;
            this._updateLocationValue(centerX, centerY);
        }

        _onMouseUp() {
            this.isDragging = false;
            document.removeEventListener('mousemove', this._onMouseMove);
            document.removeEventListener('mouseup', this._onMouseUp);
            document.removeEventListener('touchmove', this._onMouseMove);
            document.removeEventListener('touchend', this._onMouseUp);
        }

        _onImageLoaded() {
            if (!this.image || this.image.naturalWidth === 0) {
                return;
            }

            this.circle?.classList.remove(this.options.hiddenClass);

            const locationValue = this.location?.value || '';
            const imageWidth = this.image.offsetWidth;
            const imageHeight = this.image.offsetHeight;

            let x, y;

            if (locationValue.length) {
                const coords = locationValue.split(',');
                x = Math.round(Number(coords[0]) / this.ratio);
                y = Math.round(Number(coords[1]) / this.ratio);
            } else {
                x = imageWidth / 2;
                y = imageHeight / 2;
            }

            if (isNaN(x) || isNaN(y)) {
                return;
            }

            // Position circle (accounting for circle size)
            if (this.circle) {
                const circleRect = this.circle.getBoundingClientRect();
                this.circle.style.left = `${x - circleRect.width / 2}px`;
                this.circle.style.top = `${y - circleRect.height / 2}px`;
            }

            this._makeDraggable();
            this._updateLocationValue(x, y);
        }

        destroy() {
            if (this.circle?.classList.contains(this.options.draggableClass)) {
                this.circle.removeEventListener('mousedown', this._onMouseDown);
                this.circle.removeEventListener('touchstart', this._onMouseDown);
            }

            document.removeEventListener('mousemove', this._onMouseMove);
            document.removeEventListener('mouseup', this._onMouseUp);
            document.removeEventListener('touchmove', this._onMouseMove);
            document.removeEventListener('touchend', this._onMouseUp);

            if (this.image) {
                this.image.removeEventListener('load', this._onImageLoaded);
            }

            this.options = null;
            this.container = null;
            this.image = null;
            this.circle = null;
            this.location = null;
            this.ratio = null;
        }
    }

    window.Cl.FocalPoint = FocalPoint;
    window.Cl.FocalPointConstructor = FocalPointConstructor;
})();
