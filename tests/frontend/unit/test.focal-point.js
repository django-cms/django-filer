// #############################################################################
// #FOCAL POINT TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl, spyOn */

describe('Cl.FocalPoint', function () {
    var focalPoint;
    var image;
    var circle;
    var location;

    var simulateDrag = function (deltaX, deltaY) {
        var rect = circle.getBoundingClientRect();
        var startX = rect.left + rect.width / 2;
        var startY = rect.top + rect.height / 2;

        circle.dispatchEvent(new MouseEvent('mousedown', {
            bubbles: true,
            cancelable: true,
            clientX: startX,
            clientY: startY
        }));
        document.dispatchEvent(new MouseEvent('mousemove', {
            bubbles: true,
            cancelable: true,
            clientX: startX + deltaX,
            clientY: startY + deltaY
        }));
        document.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
    };

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('focal-point.html');

        image = document.getElementById('image');
        circle = document.getElementById('circle');
        location = document.getElementById('location');

        focalPoint = new Cl.FocalPoint();
        focalPoint.initialize();
    });

    afterEach(function () {
        if (focalPoint) {
            focalPoint.destroy();
            focalPoint = null;
        }

        fixture.cleanup();

        image = null;
        circle = null;
        location = null;
    });

    it('shows circle on image load', function (done) {
        image.setAttribute('src', '/img/blank.png');

        setTimeout(function () {
            expect(circle.classList.contains('hidden')).toBe(false);
            expect(location.value).toBe('100,200');
            done();
        }, 200);
    });

    it('sets the location value to center and updates location value according to the ratio', function (done) {
        var updateLocationValueStub = spyOn(
            Cl.FocalPointConstructor.prototype,
            '_updateLocationValue'
        ).and.callThrough();

        image.setAttribute('src', '/img/blank.png');

        setTimeout(function () {
            // Simulate drag by triggering mousedown, mousemove, mouseup
            var rect = circle.getBoundingClientRect();
            var startX = rect.left + rect.width / 2;
            var startY = rect.top + rect.height / 2;

            // Trigger mousedown
            var mouseDownEvent = new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                clientX: startX,
                clientY: startY
            });
            circle.dispatchEvent(mouseDownEvent);

            // Trigger mousemove
            var mouseMoveEvent = new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true,
                clientX: startX + 1,
                clientY: startY + 1
            });
            document.dispatchEvent(mouseMoveEvent);

            // Trigger mouseup
            var mouseUpEvent = new MouseEvent('mouseup', {
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(mouseUpEvent);

            setTimeout(function () {
                expect(updateLocationValueStub).toHaveBeenCalled();
                done();
            }, 100);
        }, 200);
    });

    it('updates location value according to the ratio and latest position', function (done) {
        var updateLocationValueStub = spyOn(
            Cl.FocalPointConstructor.prototype,
            '_updateLocationValue'
        ).and.callThrough();

        image.setAttribute('src', '/img/blank.png');

        setTimeout(function () {
            // Simulate drag
            var rect = circle.getBoundingClientRect();
            var startX = rect.left + rect.width / 2;
            var startY = rect.top + rect.height / 2;

            // Trigger mousedown
            var mouseDownEvent = new MouseEvent('mousedown', {
                bubbles: true,
                cancelable: true,
                clientX: startX,
                clientY: startY
            });
            circle.dispatchEvent(mouseDownEvent);

            // Trigger mousemove
            var mouseMoveEvent = new MouseEvent('mousemove', {
                bubbles: true,
                cancelable: true,
                clientX: startX - 20,
                clientY: startY - 30
            });
            document.dispatchEvent(mouseMoveEvent);

            // Trigger mouseup
            var mouseUpEvent = new MouseEvent('mouseup', {
                bubbles: true,
                cancelable: true
            });
            document.dispatchEvent(mouseUpEvent);

            setTimeout(function () {
                expect(updateLocationValueStub).toHaveBeenCalled();
                done();
            }, 100);
        }, 200);
    });
    it('stays inactive when the form has no location field', function (done) {
        // The file admin renders the same preview but has no subject location
        // field to write to: the circle must not pretend to be draggable (#1579)
        focalPoint.destroy();
        location.remove();
        focalPoint = new Cl.FocalPoint();
        focalPoint.initialize();

        image.setAttribute('src', '/img/blank.png');

        setTimeout(function () {
            expect(circle.classList.contains('hidden')).toBe(true);
            expect(circle.classList.contains('draggable')).toBe(false);
            done();
        }, 200);
    });

    it('writes to the location field after its node has been replaced', function (done) {
        image.setAttribute('src', '/img/blank.png');

        setTimeout(function () {
            // An admin theme re-rendering the fieldset leaves the focal point
            // holding a detached node - it has to resolve the field again (#1579)
            var replacement = location.cloneNode(true);

            location.replaceWith(replacement);
            replacement.value = 'not written yet';

            simulateDrag(-20, -30);

            setTimeout(function () {
                expect(replacement.value).toMatch(/^-?\d+,-?\d+$/);
                // The detached node keeps its old value, the drag did not go there
                expect(location.value).toBe('100,200');
                done();
            }, 100);
        }, 200);
    });
});
