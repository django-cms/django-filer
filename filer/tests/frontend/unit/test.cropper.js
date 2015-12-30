// #############################################################################
// #CROPPER TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl */

describe('Cl.Cropper', function () {
    var cropper;
    var container;
    var image;
    var location;

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('cropper.html');

        container = $('#container');
        image = $('#image');
        location = $('#location');

        cropper = new Cl.Cropper();
    });

    afterEach(function () {
        cropper.destroy();

        fixture.cleanup();

        container = null;
        image = null;
        location = null;
    });

    it('fake test', function () {
        // TODO
        expect('a').toBe('a');
    });
});
