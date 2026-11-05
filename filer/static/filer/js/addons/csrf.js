// #CSRF#
// Helper to look up Django's CSRF token for AJAX uploads.
'use strict';

/**
 * Returns the CSRF token to send as X-CSRFToken header.
 *
 * Prefers the hidden input rendered by {% csrf_token %} (which also works when
 * CSRF_USE_SESSIONS is enabled or the cookie name has been customized) and falls
 * back to the default csrftoken cookie.
 *
 * @returns {string} the token, or an empty string if none was found
 */
export const getCsrfToken = () => {
    const input = document.querySelector('input[name="csrfmiddlewaretoken"]');

    if (input && input.value) {
        return input.value;
    }

    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);

    return match ? decodeURIComponent(match[1]) : '';
};
