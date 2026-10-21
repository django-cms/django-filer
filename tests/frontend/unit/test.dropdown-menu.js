// #############################################################################
// #DROPDOWN MENU TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, KeyboardEvent */

describe('Filer dropdown menu keyboard handling', function () {
    var container;
    var toggle;

    var pressKey = function (element, keyCode) {
        var event = new KeyboardEvent('keydown', { bubbles: true, cancelable: true });

        Object.defineProperty(event, 'which', { value: keyCode });
        element.dispatchEvent(event);
        return event;
    };

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        fixture.load('dropdown-menu.html');

        container = document.getElementById('container');
        toggle = document.getElementById('toggle');
    });

    afterEach(function () {
        container = null;
        toggle = null;
        fixture.cleanup();
    });

    it('opens the menu with the space key', function () {
        toggle.focus();
        pressKey(toggle, 32);

        expect(container.classList.contains('open')).toBe(true);
        expect(toggle.getAttribute('aria-expanded')).toBe('true');
    });

    it('moves focus through the menu items with the arrow keys', function () {
        pressKey(toggle, 32);
        pressKey(toggle, 40);
        expect(document.activeElement.id).toBe('first');

        pressKey(document.activeElement, 40);
        expect(document.activeElement.id).toBe('second');

        pressKey(document.activeElement, 38);
        expect(document.activeElement.id).toBe('first');
    });

    it('closes the menu with the escape key and returns focus to the toggle', function () {
        pressKey(toggle, 32);
        pressKey(toggle, 40);
        pressKey(document.activeElement, 27);

        expect(container.classList.contains('open')).toBe(false);
        expect(toggle.getAttribute('aria-expanded')).toBe('false');
        expect(document.activeElement).toBe(toggle);
    });

    it('closes an open menu when its toggle is clicked again', function () {
        toggle.click();
        expect(container.classList.contains('open')).toBe(true);

        toggle.click();
        expect(container.classList.contains('open')).toBe(false);
        expect(toggle.getAttribute('aria-expanded')).toBe('false');
    });
});
