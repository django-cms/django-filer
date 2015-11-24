// #############################################################################
// #FOCAL POINT TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl, spyOn */

describe('Cl.FocalPoint', function () {
    var focalPoint;
    var container;
    var image;
    var circle;
    var location;

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('focal-point.html');

        container = $('#container');
        image = $('#image');
        circle = $('#circle');
        location = $('#location');

        focalPoint = new Cl.FocalPoint();
    });

    afterEach(function () {
        focalPoint.destroy();

        fixture.cleanup();

        container = null;
        image = null;
        circle = null;
        location = null;
    });

    it('shows circle on image load', function () {
        image.trigger('load');
        expect(circle).not.toHaveClass('hidden');

        expect(location.val()).toBe('');
    });

    it('sets the location value to center and updates location value according to the ratio', function () {
        var updateLocationValueStub = spyOn(Cl.FocalPointConstructor.prototype, '_updateLocationValue').and.callThrough();

        image.trigger('load');

        circle.simulate('drag', {
            moves: 1,
            dx: 1,
            dy: 1
        });

        expect(updateLocationValueStub).toHaveBeenCalled();
        expect(updateLocationValueStub.calls.count()).toBe(2);
        expect(updateLocationValueStub).toHaveBeenCalledWith(51, 101);

        expect(location.val()).toBe('102,202');
    });

    it('updates location value according to the ratio and latest position', function () {
        var updateLocationValueStub = spyOn(Cl.FocalPointConstructor.prototype, '_updateLocationValue').and.callThrough();

        image.trigger('load');

        circle.simulate('drag', {
            moves: 2,
            dx: -20,
            dy: -30
        });

        expect(updateLocationValueStub).toHaveBeenCalled();
        expect(updateLocationValueStub.calls.count()).toBe(3);
        expect(updateLocationValueStub).toHaveBeenCalledWith(40, 85);
        expect(updateLocationValueStub).toHaveBeenCalledWith(30, 70);

        expect(location.val()).toBe('60,140');
    });
});
