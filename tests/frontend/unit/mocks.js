'use strict';

var Cl = window.Cl || {};
/* global Mediator */

window.gettext = function (text) {
    return text;
};
window.django = {
    jQuery: window.jQuery
};

Cl.mediator = new Mediator();
