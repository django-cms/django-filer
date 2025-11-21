'use strict';

var Cl = window.Cl || {};

window.gettext = function (text) {
    return text;
};
window.django = {
    jQuery: window.jQuery
};

// Mediator is loaded from the bundle, so Cl.mediator should already exist
// If not, we need to wait for the bundle to load
if (!Cl.mediator) {
    console.warn('Cl.mediator not found - bundle may not be loaded yet');
}
