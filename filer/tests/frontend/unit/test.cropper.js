// #############################################################################
// #CROPPER TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl, spyOn, jasmine */

describe('Cl.Cropper', function () {
    var cropper;
    var container;
    var image;
    var location;
    var preview;
    var container2;
    var image2;
    var preview2;
    var cropperStub;

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('cropper.html');

        container = $('#container');
        image = $('#image');
        location = $('#location');
        preview = $('#preview');
        container2 = $('#container-2');
        image2 = $('#image-2');
        preview2 = $('#preview-2');

        cropperStub = spyOn($.fn, 'cropper');
        cropper = new Cl.Cropper();
    });

    afterEach(function () {
        cropper.destroy();

        fixture.cleanup();

        container = null;
        image = null;
        location = null;
        preview = null;
        container2 = null;
        image2 = null;
        preview2 = null;
        cropperStub = null;
        cropper = null;
    });

    it('does nothing if image was not loaded', function () {
        cropper = new Cl.Cropper();
        expect(cropperStub).not.toHaveBeenCalled();
    });

    it('cropper is loaded with correct params', function () {
        cropper = new Cl.Cropper();
        image.trigger('load');

        expect(cropperStub).toHaveBeenCalled();
        expect(cropperStub).toHaveBeenCalledWith({
            viewMode: 2,
            dragMode: 'crop',
            autoCropArea: 1,
            preview: preview,
            built: jasmine.any(Function),
            crop: jasmine.any(Function)
        });
    });

    it('cropper plugin loads correctly', function (done) {
        cropperStub.and.callThrough();
        image.attr('src', '/img/blank.png');

        cropper = new Cl.Cropper();

        setTimeout(function () {
            expect(cropperStub).toHaveBeenCalled();
            expect(preview.children('img').length).toBe(1);
            done();
        }, 100);
    });

    it('mediator init works correctly', function () {
        cropper = new Cl.Cropper();

        Cl.mediator.publish('cropper:init', container2[0]);

        image2.trigger('load');

        expect(cropperStub).toHaveBeenCalledWith({
            viewMode: 2,
            dragMode: 'crop',
            autoCropArea: 1,
            preview: preview2,
            built: jasmine.any(Function),
            crop: jasmine.any(Function)
        });
    });
});
