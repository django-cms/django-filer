// #############################################################################
// #TOGGLER TEST#

'use strict';
/* globals fixture, describe, it, expect, beforeEach, afterEach, Cl */

describe('Cl.Toggler', function () {
    var toggler;
    var link;
    var header;
    var content;

    beforeEach(function () {
        fixture.setBase('frontend/fixtures');
        this.markup = fixture.load('toggler.html');

        link = document.getElementById('link');
        header = document.getElementById('header');
        content = document.getElementById('content');
    });

    afterEach(function () {
        if (toggler) {
            toggler.destroy();
            toggler = null;
        }

        link = null;
        header = null;
        content = null;

        fixture.cleanup();
    });

    it('adds js-expanded class to the header if the content is visible', function () {
        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(header.classList.contains('js-collapsed')).toBe(false);
        expect(header.classList.contains('js-expanded')).toBe(true);
    });

    it('adds js-collapsed class to the header if the content is hidden', function () {
        content.classList.add('hidden');

        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(header.classList.contains('js-expanded')).toBe(false);
        expect(header.classList.contains('js-collapsed')).toBe(true);
    });

    it('adds js-expanded class to the link if the content is visible and there is no header', function () {
        header.remove();

        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(link.classList.contains('js-collapsed')).toBe(false);
        expect(link.classList.contains('js-expanded')).toBe(true);
    });

    it('adds js-collapsed class to the link if the content is hidden and there is no header', function () {
        header.remove();
        content.classList.add('hidden');

        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(link.classList.contains('js-expanded')).toBe(false);
        expect(link.classList.contains('js-collapsed')).toBe(true);
    });

    it('toggles the content and header classes if the content was visible', function () {
        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(header.classList.contains('js-collapsed')).toBe(false);
        expect(header.classList.contains('js-expanded')).toBe(true);

        link.click();

        expect(header.classList.contains('js-expanded')).toBe(false);
        expect(header.classList.contains('js-collapsed')).toBe(true);

        link.click();

        expect(header.classList.contains('js-collapsed')).toBe(false);
        expect(header.classList.contains('js-expanded')).toBe(true);
    });

    it('toggles the content and header classes if the content was hidden', function () {
        content.classList.add('hidden');

        toggler = new Cl.TogglerConstructor(link, {
            dataHeaderSelector: 'togglerHeaderSelector',
            dataContentSelector: 'togglerContentSelector',
            collapsedClass: 'js-collapsed',
            expandedClass: 'js-expanded',
            hiddenClass: 'hidden'
        });

        expect(header.classList.contains('js-expanded')).toBe(false);
        expect(header.classList.contains('js-collapsed')).toBe(true);

        link.click();

        expect(header.classList.contains('js-collapsed')).toBe(false);
        expect(header.classList.contains('js-expanded')).toBe(true);

        link.click();

        expect(header.classList.contains('js-expanded')).toBe(false);
        expect(header.classList.contains('js-collapsed')).toBe(true);
    });
});
