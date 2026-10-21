// #ERROR DISMISSED#
// Defers an action (e.g. reloading the listing) until the user has dismissed all error messages;
// filerShowError (base.js) fires the event once the last one is gone
'use strict';

export const errorDismissedEvent = 'filer-error-dismissed';

export const whenErrorsDismissed = (callback) => {
    if (!document.querySelector('.js-filer-error')) {
        // nothing (left) to read
        callback();
        return;
    }
    document.addEventListener(errorDismissedEvent, callback, { once: true });
};
