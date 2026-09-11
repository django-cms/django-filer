'use strict';

// #############################################################################
// CONFIGURATION
//
// The admin file widget lives in its own bundle and is the only dropzone on a
// change form. It therefore gets its own karma run: loading filer-base.bundle.js
// alongside would let the directory listing's dropzone claim the widget's
// .js-filer-dropzone element, which never happens in the admin.

module.exports = function (config) {
    config.set({
        basePath: '..',

        frameworks: ['jasmine', 'fixture'],

        files: [
            'frontend/unit/mock-ajax.min.js',

            '../filer/static/filer/js/dist/admin-file-widget.bundle.js',

            'frontend/unit/test.file-widget.js',

            {
                pattern: 'frontend/fixtures/file-widget.html',
            }
        ],

        preprocessors: {
            '**/*.html': ['html2js']
        },

        port: 9877,

        colors: true,

        logLevel: config.LOG_INFO,

        autoWatch: false,

        browsers: ['ChromeHeadless'],

        customLaunchers: {
            ChromeHeadlessNoSandbox: {
                base: 'ChromeHeadless',
                flags: ['--no-sandbox', '--disable-web-security']
            }
        },

        singleRun: true
    });
};
