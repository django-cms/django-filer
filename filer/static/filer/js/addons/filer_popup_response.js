/*global opener */
(function () {
    'use strict';
    var dataElement = document.getElementById('django-admin-popup-response-constants');
    var initData;

    if (dataElement) {
        initData = JSON.parse(dataElement.dataset.popupResponse);
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
    }
})();
