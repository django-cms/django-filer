'use strict';

// #############################################################################
// CONFIGURATION

// rake spec:javascript loads specs relative to the tmp/jasmine/runner.html, need to override:
module.exports = function (config) {
    var browsers = {
        'PhantomJS': 'used for local testing'
    };

    var settings = {
        // base path that will be used to resolve all patterns (eg. files, exclude)
        basePath: '..',

        // frameworks to use
        // available frameworks: https://npmjs.org/browse/keyword/karma-adapter
        frameworks: ['jasmine', 'fixture'],

        // list of files / patterns to load in the browser
        // tests/${path}
        files: [
            // the current order meets the dependency requirements
            // dependency loading is not handled yet
            '../static/filer/js/libs/jquery.min.js',
            '../static/filer/js/libs/!(jquery.min)*.js',

            'frontend/unit/mocks.js',
            'frontend/unit/mock-ajax.min.js',

            '../static/filer/js/addons/*.js',

            // tests themselves
            'frontend/unit/*.js',

            // fixture patterns
            {
                pattern: 'frontend/fixtures/**/*',
            },
            {
                pattern: 'frontend/img/*', watched: false, included: false, served: true, nocache: false
            }
        ],
        proxies: {
            '/img/': 'http://localhost:9876/base/frontend/img/'
        },


        // list of files to exclude
        exclude: [],

        // preprocess matching files before serving them to the browser
        // available preprocessors: https://npmjs.org/browse/keyword/karma-preprocessor
        preprocessors: {
            // for fixtures
            '**/*.html': ['html2js'],
            '**/*.json': ['json_fixtures']
        },

        // fixtures dependency
        // https://github.com/billtrik/karma-fixture
        jsonFixturesPreprocessor: {
            variableName: '__json__'
        },

        // web server port
        port: 9876,

        // enable / disable colors in the output (reporters and logs)
        colors: true,

        // level of logging
        // possible values:
        // config.LOG_DISABLE || config.LOG_ERROR || config.LOG_WARN || config.LOG_INFO || config.LOG_DEBUG
        logLevel: config.LOG_INFO,

        // enable / disable watching file and executing tests whenever any file changes
        autoWatch: true,

        // start these browsers
        // available browser launchers: https://npmjs.org/browse/keyword/karma-launcher
        browsers: Object.keys(browsers),

        // Continuous Integration mode
        // if true, Karma captures browsers, runs the tests and exits
        singleRun: false
    };

    config.set(settings);
};
