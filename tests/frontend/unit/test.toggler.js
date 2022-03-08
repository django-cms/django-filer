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

        link = $('#link');
        header = $('#header');
        content = $('#content');
    });

    afterEach(function () {
        toggler.destroy();

        link = null;
        header = null;
        content = null;

        fixture.cleanup();
    });

    it('adds js-expanded class to the header if the content is visible', function () {
        toggler = new Cl.Toggler();

        expect(header).not.toHaveClass('js-collapsed');
        expect(header).toHaveClass('js-expanded');
    });

    it('adds js-collapsed class to the header if the content is hidden', function () {
        content.addClass('hidden');

        toggler = new Cl.Toggler();

        expect(header).not.toHaveClass('js-expanded');
        expect(header).toHaveClass('js-collapsed');
    });

    it('adds js-expanded class to the link if the content is visible and there is no header', function () {
        header.remove();

        toggler = new Cl.Toggler();

        expect(link).not.toHaveClass('js-collapsed');
        expect(link).toHaveClass('js-expanded');
    });

    it('adds js-collapsed class to the link if the content is hidden and there is no header', function () {
        header.remove();

        toggler = new Cl.Toggler();

        expect(link).not.toHaveClass('js-collapsed');
        expect(link).toHaveClass('js-expanded');
    });

    it('toggles the content and header classes if the content was visible', function () {
        toggler = new Cl.Toggler();

        expect(header).not.toHaveClass('js-collapsed');
        expect(header).toHaveClass('js-expanded');

        link.click();

        expect(header).not.toHaveClass('js-expanded');
        expect(header).toHaveClass('js-collapsed');

        link.click();

        expect(header).not.toHaveClass('js-collapsed');
        expect(header).toHaveClass('js-expanded');
    });

    it('toggles the content and header classes if the content was hidden', function () {
        content.addClass('hidden');

        toggler = new Cl.Toggler();

        expect(header).not.toHaveClass('js-expanded');
        expect(header).toHaveClass('js-collapsed');

        link.click();

        expect(header).not.toHaveClass('js-collapsed');
        expect(header).toHaveClass('js-expanded');

        link.click();

        expect(header).not.toHaveClass('js-expanded');
        expect(header).toHaveClass('js-collapsed');
    });
});
