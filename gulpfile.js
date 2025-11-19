'use strict';

var gulp = require('gulp');
var log = require('fancy-log');
var sass = require('gulp-sass')(require('sass'));
var iconfont = require('gulp-iconfont');
var iconfontCss = require('gulp-iconfont-css');
var autoprefixer = require('gulp-autoprefixer').default;
var sourcemaps = require('gulp-sourcemaps');
var eslint = require('gulp-eslint-new');
var Server = require('karma').Server;

var PROJECT_ROOT = __dirname;
var PROJECT_PATH = {
    'sass': PROJECT_ROOT + '/filer/private/sass/',
    'css': PROJECT_ROOT + '/filer/static/filer/css/',
    'js': PROJECT_ROOT + '/filer/static/filer/js/',
    'icons': PROJECT_ROOT + '/filer/static/filer/fonts/',
    'tests': PROJECT_ROOT + '/tests/frontend/'
};

var PROJECT_PATTERNS = {
    'sass': PROJECT_PATH.sass + '**/*.scss',
    icons: [
        PROJECT_PATH.icons + '/src/*.svg'
    ],
    'lint': [
        PROJECT_PATH.js + '**/*.js',
        '!' + PROJECT_PATH.js + '**/*.min.js',
        PROJECT_PATH.tests + 'unit/**/*.js',
        '!' + PROJECT_PATH.tests + 'unit/**/*.min.js',
        PROJECT_ROOT + '/gulpfile.js'
    ]
};

// #############################################################################
// sass
gulp.task('sass', function () {
    return gulp.src(PROJECT_PATTERNS.sass)
        .pipe(sourcemaps.init())
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(autoprefixer())
        .pipe(sourcemaps.write('/maps'))
        .pipe(gulp.dest(PROJECT_PATH.css));
});

gulp.task('sass:watch', function () {
    gulp.watch(PROJECT_PATTERNS.sass, gulp.series('sass'));
});


// #############################################################################
// WEBPACK
gulp.task('bundle', function (done) {
    var webpack = require('webpack');
    var webpackConfigFactory = require('./webpack.config.js');
    var isDebug = process.argv.includes('--debug');
    var webpackConfig = webpackConfigFactory({}, { debug: isDebug });

    webpack(webpackConfig, function(err, stats) {
        if (err) {
            log.error(err);
            done(err);
            return;
        }

        log.info(stats.toString({
            colors: true,
            chunks: false
        }));

        if (isDebug) {
            log.info('Built in DEBUG mode (unminified with source maps)');
        } else {
            log.info('Built in PRODUCTION mode (minified)');
        }

        done();
    });
});

// #############################################################################
// Icons

gulp.task('icons', function () {
    return gulp.src(PROJECT_PATTERNS.icons)
        .pipe(iconfontCss({
            fontName: 'django-filer-iconfont',
            fontPath: '../fonts/',
            path: PROJECT_PATH.sass + '/libs/_iconfont.scss',
            targetPath: '../../../private/sass/components/_iconography.scss'
        }))
        .pipe(iconfont({
            fontName: 'django-filer-iconfont',
            normalize: true,
            formats: ['svg', 'ttf', 'eot', 'woff', 'woff2']
        }))
        .on('glyphs', function (glyphs, options) {
            log.info('Generated', glyphs.length, 'glyphs');
        })
        .pipe(gulp.dest(PROJECT_PATH.icons));
});

// #############################################################################
// LINTING
gulp.task('eslint', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(eslint())
        .pipe(eslint.format())
        .pipe(eslint.failAfterError());
});

gulp.task('eslint:fix', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(eslint({fix: true}))
        .pipe(eslint.format())
        .pipe(gulp.dest(function(file) {
            return file.base;
        }));
});

// #############################################################################
// JS UNIT-TESTS
gulp.task('tests:unit', function (done) {
    new Server({
        configFile: PROJECT_PATH.tests + '/karma.conf.js',
        singleRun: true
    }, done).start();
});
gulp.task('tests:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['tests:unit']);
});

// #############################################################################
// TASKS
gulp.task('build', gulp.series('sass', 'bundle'));
gulp.task('js', gulp.series('eslint' /* ,'tests:unit'*/));
gulp.task('js:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, gulp.series('js'));
});
gulp.task('watch', gulp.parallel('sass:watch', 'js:watch'));
gulp.task('lint', gulp.series('eslint'));
gulp.task('lint:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, gulp.series('lint'));
});
gulp.task('ci', gulp.series('sass', 'bundle', 'eslint', 'lint', 'tests:unit'));
gulp.task('default', gulp.parallel('sass:watch', 'js:watch', 'lint:watch'));
