// #############################################################################
// #ERROR MESSAGE TEST#

'use strict';
/* globals describe, it, expect, beforeEach, afterEach */

describe('window.filerShowError', function () {
    var header;

    beforeEach(function () {
        header = document.createElement('div');
        header.id = 'header';
        document.body.appendChild(header);
    });

    afterEach(function () {
        document.querySelectorAll('.messagelist').forEach(function (el) {
            el.remove();
        });
        header.remove();
        header = null;
    });

    it('shows the message as an alert without parsing it as HTML', function () {
        window.filerShowError('<b>bad.png</b>: too large');

        var error = document.querySelector('.messagelist .js-filer-error');

        expect(error.getAttribute('role')).toBe('alert');
        expect(error.querySelector('b')).toBe(null);
        expect(error.textContent).toContain('<b>bad.png</b>: too large');
    });

    it('can be dismissed by the user', function () {
        window.filerShowError('upload failed');

        var dismiss = document.querySelector('.js-filer-message-dismiss');

        expect(dismiss.getAttribute('aria-label')).toBeTruthy();
        dismiss.click();
        expect(document.querySelector('.js-filer-error')).toBe(null);
    });

    it('lists several errors and fires the dismissed event after the last one', function () {
        var dismissed = 0;
        var onDismissed = function () {
            dismissed++;
        };

        document.addEventListener('filer-error-dismissed', onDismissed);
        window.filerShowError('a.png: failed');
        window.filerShowError('b.png: failed');

        expect(document.querySelectorAll('.js-filer-error').length).toBe(2);

        document.querySelector('.js-filer-message-dismiss').click();
        expect(document.querySelectorAll('.js-filer-error').length).toBe(1);
        expect(dismissed).toBe(0);

        document.querySelector('.js-filer-message-dismiss').click();
        expect(document.querySelector('.messagelist')).toBe(null);
        expect(dismissed).toBe(1);

        document.removeEventListener('filer-error-dismissed', onDismissed);
    });
});
