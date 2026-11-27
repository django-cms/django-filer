// #############################################################################
// #ADMIN FILE WIDGET TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, jasmine */

describe('admin file widget', function () {
    var UPLOAD_RESPONSE = {
        file_id: 42,
        label: 'new_image.png',
        alt_text: '',
        thumbnail_180: '/media/new_image__120x120.png',
        original_image: '/media/new_image.png',
        change_url: '/admin/filer/image/42/change/'
    };

    var dropzone;

    // The widget's file representation, i.e. everything but the upload previews
    // dropzone adds to the same container.
    var fileSelector = function () {
        return dropzone.querySelector('.js-file-selector');
    };

    var previews = function () {
        return Array.prototype.filter.call(
            dropzone.querySelectorAll('.filerFile'),
            function (element) {
                return element !== fileSelector();
            }
        );
    };

    var drop = function () {
        var transfer = new DataTransfer();

        transfer.items.add(new File([new Uint8Array([1, 2, 3, 4])], 'new_image.png', {type: 'image/png'}));
        dropzone.dispatchEvent(new DragEvent('drop', {
            dataTransfer: transfer,
            bubbles: true,
            cancelable: true
        }));
    };

    var stubUpload = function (response) {
        jasmine.Ajax.stubRequest(/upload/).andReturn(response);
    };

    var initWidget = function () {
        // The widget sets itself up when the document is ready
        document.dispatchEvent(new Event('DOMContentLoaded', {bubbles: true}));
        dropzone = document.querySelector('.js-filer-dropzone');
    };

    beforeEach(function () {
        jasmine.Ajax.install();
        window.filerShowError = function () {};
        fixture.setBase('frontend/fixtures');
        fixture.load('file-widget.html');
        initWidget();
    });

    afterEach(function () {
        jasmine.Ajax.uninstall();
        fixture.cleanup();
    });

    it('shows the uploaded file instead of the previous one', function (done) {
        stubUpload({
            status: 200,
            contentType: 'application/json',
            responseText: JSON.stringify(UPLOAD_RESPONSE)
        });

        drop();

        setTimeout(function () {
            var thumbnail = fileSelector().querySelector('.thumbnail_img');

            // The upload preview must not pile up on the widget's own markup
            expect(previews().length).toBe(0);
            expect(fileSelector().style.display).not.toBe('none');

            expect(document.getElementById('id_image').value).toBe('42');
            expect(fileSelector().querySelector('.description_text').textContent).toBe('new_image.png');
            expect(thumbnail.getAttribute('src')).toBe('/media/new_image__120x120.png');
            // The srcset of the previous file would win over the new src
            expect(thumbnail.hasAttribute('srcset')).toBe(false);
            expect(thumbnail.classList.contains('hidden')).toBe(false);
            expect(thumbnail.parentElement.getAttribute('href')).toBe('/media/new_image.png');
            expect(document.getElementById('id_image_change').getAttribute('href'))
                .toBe('/admin/filer/image/42/change/?_edit_from_widget=1');
            expect(fileSelector().querySelector('.filerClearer').classList.contains('hidden')).toBe(false);
            done();
        }, 400);
    });

    it('keeps the previous file if the upload fails', function (done) {
        stubUpload({
            status: 400,
            contentType: 'application/json',
            responseText: JSON.stringify({error: 'File type not supported'})
        });

        drop();

        setTimeout(function () {
            expect(previews().length).toBe(0);
            expect(fileSelector().style.display).not.toBe('none');
            expect(document.getElementById('id_image').value).toBe('1');
            expect(fileSelector().querySelector('.description_text').textContent).toBe('old_image.jpg');
            done();
        }, 400);
    });

    it('keeps the drag state while the pointer moves over its own content', function () {
        var thumbnail = fileSelector().querySelector('.thumbnail_img');
        var description = fileSelector().querySelector('.description_text');
        var dragEvent = function (type) {
            var transfer = new DataTransfer();

            // Dropzone ignores drags that carry no files
            transfer.items.add(new File([''], 'new_image.png', {type: 'image/png'}));
            return new DragEvent(type, {dataTransfer: transfer, bubbles: true, cancelable: true});
        };

        thumbnail.dispatchEvent(dragEvent('dragenter'));
        expect(dropzone.classList.contains('dz-drag-hover')).toBe(true);

        // Moving on to the next element enters it before leaving the previous one
        description.dispatchEvent(dragEvent('dragenter'));
        thumbnail.dispatchEvent(dragEvent('dragleave'));
        expect(dropzone.classList.contains('dz-drag-hover')).toBe(true);

        // Only leaving the dropzone itself ends the drag state
        description.dispatchEvent(dragEvent('dragleave'));
        expect(dropzone.classList.contains('dz-drag-hover')).toBe(false);
    });

    it('empties the widget when the clear button is clicked', function () {
        fileSelector().querySelector('.filerClearer').click();

        expect(document.getElementById('id_image').value).toBe('');
        expect(fileSelector().querySelector('.description_text').textContent).toBe('');
        expect(fileSelector().querySelector('.thumbnail_img').classList.contains('hidden')).toBe(true);
        expect(dropzone.querySelector('.js-filer-dropzone-message').classList.contains('hidden')).toBe(false);
    });

    it('clears widgets added after page load, e.g. by inline formsets', function () {
        var row = document.createElement('div');

        row.innerHTML = document.querySelector('.filer-widget').outerHTML;
        document.body.appendChild(row);

        var clearer = row.querySelector('.js-file-selector .filerClearer');

        clearer.click();

        expect(row.querySelector('input[name="image"]').value).toBe('');
        expect(row.querySelector('.description_text').textContent).toBe('');
        document.body.removeChild(row);
    });
});
