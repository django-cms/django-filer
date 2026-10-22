'use strict';
/* globals spyOn */

describe('Copy URL tooltip', function () {
    var button;

    beforeEach(function () {
        jasmine.clock().install();
        spyOn(navigator.clipboard, 'writeText').and.returnValue(Promise.resolve());
        button = document.createElement('a');
        button.className = 'js-copy-url';
        button.href = '#';
        button.dataset.url = '/media/test.png';
        button.dataset.msg = '<b>Copied</b> & ready';
        document.body.appendChild(button);
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    afterEach(function () {
        button.remove();
        document.querySelectorAll('.js-filer-live-region').forEach(function (region) {
            region.remove();
        });
        jasmine.clock().uninstall();
    });

    it('copies the URL and shows and announces the message as plain text', function () {
        button.click();

        var tooltip = button.querySelector('.info.filer-tooltip');

        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
            new URL('/media/test.png', window.location.href).href
        );
        expect(tooltip.textContent).toBe(button.dataset.msg);
        expect(tooltip.childElementCount).toBe(0);
        expect(tooltip.getAttribute('aria-hidden')).toBe('true');

        jasmine.clock().tick(50);
        var announcement = document.querySelector('.js-filer-live-region');

        expect(announcement.textContent).toBe(button.dataset.msg);
        expect(announcement.childElementCount).toBe(0);

        jasmine.clock().tick(1150);
        expect(button.querySelector('.info.filer-tooltip')).toBe(null);
    });
});
