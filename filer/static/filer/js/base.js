// #####################################################################################################################
// #BASE#
// Basic logic django filer
'use strict';

var Cl = window.Cl || {};
/* global Mediator */

(function ($) {

    $(function () {
        // mediator init
        Cl.mediator = new Mediator();

        // Focal point logic init
        if (Cl.FocalPoint) {
            new Cl.FocalPoint();
        }

        // Toggler init
        if (Cl.Toggler) {
            new Cl.Toggler();
        }
    });
})(jQuery);
