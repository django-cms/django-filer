// #####################################################################################################################
// #BASE#
// Basic logic django filer
var Cl = window.Cl || {};
/* global django, Mediator */

(function ($) {
    'use strict';

    $(function () {
        // mediator init
        Cl.mediator = new Mediator();

        // Focal point logic init
        if (Cl.FocalPoint) {
            new Cl.FocalPoint();
        }
    });
})(django.jQuery);
