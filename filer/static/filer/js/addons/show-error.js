// #SHOW ERROR#
// Shows error messages that stay until the user dismisses them
'use strict';

import { errorDismissedEvent } from './error-dismissed.js';

const listClass = 'js-filer-messagelist';
const errorSelector = '.js-filer-error';
const dismissSelector = '.js-filer-message-dismiss';

const getList = (container) => {
    if (container) {
        // errors of a widget are shown right below it
        const next = container.nextElementSibling;
        if (next && next.classList.contains(listClass)) {
            return next;
        }
    } else {
        const existing = document.querySelector('.messagelist');
        if (existing) {
            return existing;
        }
    }

    const list = document.createElement('ul');
    list.className = `messagelist ${listClass}`;
    if (container) {
        container.after(list);
    } else {
        const header = document.querySelector('#header');
        if (!header) {
            return null;
        }
        header.after(list);
    }
    return list;
};

/**
 * Errors stay visible until the user dismisses them or the page reloads: removing
 * them after a fixed delay does not leave everyone enough time to read them
 * (WCAG 2.2.1). Several errors (e.g. from one upload batch) are listed together.
 * Once the last error is dismissed, `errorDismissedEvent` is fired on the document.
 *
 * @param {String} message plain text, never parsed as HTML
 * @param {Object} [options]
 * @param {Element} [options.container] show the error right below this element
 *     (e.g. a form widget) instead of in the page's message list
 */
export const showError = (message, { container } = {}) => {
    const translate = window.gettext || ((text) => text);
    const returnFocusTo = document.activeElement;
    const list = getList(container);

    if (!list) {
        return;
    }

    const item = document.createElement('li');
    const text = document.createElement('span');
    const dismiss = document.createElement('button');

    item.className = 'error js-filer-error';
    item.setAttribute('role', 'alert');
    // textContent: file names and server responses must not be parsed as HTML
    text.textContent = message;
    dismiss.type = 'button';
    dismiss.className = 'filer-message-dismiss js-filer-message-dismiss';
    dismiss.setAttribute('aria-label', translate('Dismiss'));
    dismiss.title = translate('Dismiss');
    dismiss.innerHTML = '<span aria-hidden="true">&times;</span>';
    dismiss.addEventListener('click', () => {
        item.remove();
        if (!list.querySelector('li')) {
            list.remove();
        }

        const nextError = document.querySelector(dismissSelector);
        if (nextError) {
            // keep keyboard users on the remaining errors
            nextError.focus();
        } else {
            if (returnFocusTo && returnFocusTo !== document.body && returnFocusTo.isConnected) {
                returnFocusTo.focus();
            }
            if (!document.querySelector(errorSelector)) {
                document.dispatchEvent(new CustomEvent(errorDismissedEvent));
            }
        }
    });

    item.appendChild(text);
    item.appendChild(dismiss);
    list.appendChild(item);
};
