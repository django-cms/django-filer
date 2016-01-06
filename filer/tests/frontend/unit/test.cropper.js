// #############################################################################
// #CROPPER TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl, spyOn, jasmine */

describe('Cl.Cropper', function () {
    var cropper;
    var container;
    var image;
    var location;
    var container2;
    var image2;
    var cropperStub;

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('cropper.html');

        container = $('#container');
        image = $('#image');
        location = $('#location');
        container2 = $('#container-2');
        image2 = $('#image-2');

        cropperStub = spyOn($.fn, 'cropper');
        cropper = new Cl.Cropper();
    });

    afterEach(function () {
        cropper.destroy();

        fixture.cleanup();

        container = null;
        image = null;
        location = null;
        container2 = null;
        image2 = null;
        cropperStub = null;
        cropper = null;
    });

    it('does nothing if image was not loaded', function () {
        expect(cropperStub).not.toHaveBeenCalled();
    });

    it('cropper is loaded with correct params', function () {
        cropper = new Cl.Cropper();
        image.trigger('load');

        expect(cropperStub).toHaveBeenCalled();
        expect(cropperStub).toHaveBeenCalledWith({
            viewMode: 2,
            dragMode: 'crop',
            autoCropArea: 0.1,
            data: jasmine.any(Function),
            crop: jasmine.any(Function)
        });
    });

    it('mediator init works correctly', function () {
        cropper = new Cl.Cropper();

        Cl.mediator.publish('cropper:init', container2[0]);

        image2.trigger('load');

        expect(cropperStub).toHaveBeenCalledWith({
            viewMode: 2,
            dragMode: 'crop',
            autoCropArea: 0.1,
            data: jasmine.any(Function),
            crop: jasmine.any(Function)
        });
    });
});
