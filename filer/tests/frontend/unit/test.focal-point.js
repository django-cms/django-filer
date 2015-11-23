// #############################################################################
// #FOCAL POINT TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl */

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

    it('tests something', function () {
        // Tests will go here soon
        expect(true).toBeTruthy();
    });
});
