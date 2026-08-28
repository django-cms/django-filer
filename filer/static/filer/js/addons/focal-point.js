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
                dataLocation: 'locationSelector',
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
                dataLocation: 'locationSelector',
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
            if (!this.circle) {
                return;
            }

            this.circle.classList.add(this.options.draggableClass);
            this.circle.addEventListener('mousedown', this._onMouseDown);
            this.circle.addEventListener('touchstart', this._onMouseDown, { passive: false });
        }

        _onMouseDown(event) {
            event.preventDefault();
            this.isDragging = true;

            const touch = event.type === 'touchstart' ? event.touches[0] : event;

            // Get container bounds
            const containerRect = this.container.getBoundingClientRect();

            // Calculate mouse position relative to container
            this.dragStartX = touch.clientX - containerRect.left;
            this.dragStartY = touch.clientY - containerRect.top;

            // Get current circle position (center)
            const circleRect = this.circle.getBoundingClientRect();
            this.circleStartX = circleRect.left - containerRect.left + circleRect.width / 2;
            this.circleStartY = circleRect.top - containerRect.top + circleRect.height / 2;

            document.addEventListener('mousemove', this._onMouseMove);
            document.addEventListener('mouseup', this._onMouseUp);
            document.addEventListener('touchmove', this._onMouseMove, { passive: false });
            document.addEventListener('touchend', this._onMouseUp);
        }

        _onMouseMove(event) {
            if (!this.isDragging) {
                return;
            }

            event.preventDefault();

            const touch = event.type === 'touchmove' ? event.touches[0] : event;

            // Get container bounds
            const containerRect = this.container.getBoundingClientRect();

            // Calculate current mouse position relative to container
            const currentX = touch.clientX - containerRect.left;
            const currentY = touch.clientY - containerRect.top;

            // Calculate how much the mouse moved
            const deltaX = currentX - this.dragStartX;
            const deltaY = currentY - this.dragStartY;

            // Calculate new center position
            let centerX = this.circleStartX + deltaX;
            let centerY = this.circleStartY + deltaY;

            // Constrain center to container bounds
            centerX = Math.max(0, Math.min(containerRect.width - 1, centerX));
            centerY = Math.max(0, Math.min(containerRect.height - 1, centerY));

            // Position circle by its top-left corner (center - radius)
            this.circle.style.left = `${centerX}px`;
            this.circle.style.top = `${centerY}px`;

            // Update location value with center coordinates
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
                this.circle.style.left = `${x}px`;
                this.circle.style.top = `${y}px`;
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

    // Export for ES6 module usage
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = FocalPoint;
    }
})();

export default window.Cl.FocalPoint;
