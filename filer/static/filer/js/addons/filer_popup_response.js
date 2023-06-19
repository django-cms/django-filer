/*global opener */
(function () {
    'use strict';
    var initData = JSON.parse(document.getElementById('django-admin-popup-response-constants').dataset.popupResponse);
    switch (initData.action) {
        case 'change':
            // Specific function for file editing popup opened from widget
            opener.dismissRelatedImageLookupPopup(window, initData.new_value, null, initData.obj, null);
            break;
        case 'delete':
            opener.dismissDeleteRelatedObjectPopup(window, initData.value);
            break;
        default:
            opener.dismissAddRelatedObjectPopup(window, initData.value, initData.obj);
            break;
    }
})();
