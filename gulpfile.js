'use strict';

var gulp = require('gulp');
var gulpsync = require('gulp-sync')(gulp);
var gutil = require('gulp-util');
var sass = require('gulp-sass');
var iconfont = require('gulp-iconfont');
var iconfontCss = require('gulp-iconfont-css');
var autoprefixer = require('gulp-autoprefixer');
var sourcemaps = require('gulp-sourcemaps');
var jshint = require('gulp-jshint');
var jscs = require('gulp-jscs');
var stylish = require('jshint-stylish');
var Server = require('karma').Server;

var PROJECT_ROOT = __dirname;
var PROJECT_PATH = {
    'sass': PROJECT_ROOT + '/filer/private/sass/',
    'css': PROJECT_ROOT + '/filer/static/filer/css/',
    'js': PROJECT_ROOT + '/filer/static/filer/js/',
    'tests': PROJECT_ROOT + '/filer/tests/frontend/',
    'icons': PROJECT_ROOT + '/filer/static/filer/fonts/'
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
    gulp.src(PROJECT_PATTERNS.sass)
        .pipe(sourcemaps.init())
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(autoprefixer('last 2 version', 'safari 5', 'ie 8', 'ie 9', 'opera 12.1', 'ios 6', 'android 4'))
        .pipe(sourcemaps.write('/maps'))
        .pipe(gulp.dest(PROJECT_PATH.css));
});

gulp.task('sass:watch', function () {
    gulp.watch(PROJECT_PATTERNS.sass, ['sass']);
});

// #############################################################################
// Icons

gulp.task('icons', function () {
    gulp.src(PROJECT_PATTERNS.icons)
    .pipe(iconfontCss({
        fontName: 'django-filer-iconfont',
        fontPath: '../fonts/',
        path: PROJECT_PATH.sass + '/libs/_iconfont.scss',
        targetPath: '../../../private/sass/layout/_iconography.scss'
    }))
    .pipe(iconfont({
        fontName: 'django-filer-iconfont',
        normalize: true
    }))
    .on('glyphs', function (glyphs, options) {
        gutil.log.bind(glyphs, options);
    })
    .pipe(gulp.dest(PROJECT_PATH.icons));
});

// #############################################################################
// LINTING
gulp.task('jscs', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(jscs())
        .pipe(jscs.reporter())
        .pipe(jscs.reporter('fail'));
});

gulp.task('jscs:fix', function () {
    return gulp.src([PROJECT_PATH.js + '**/*.js', '!' + PROJECT_PATH.js + '**/*.min.js'])
        .pipe(jscs({fix: true}))
        .pipe(gulp.dest(PROJECT_PATH.js));
});

gulp.task('jshint', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(jshint('.jshintrc'))
        .pipe(jshint.reporter(stylish))
        .pipe(jshint.reporter('fail'));
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
gulp.task('js', gulpsync.sync(['jshint', 'jscs', 'tests:unit']));
gulp.task('js:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['js']);
});
gulp.task('watch', ['sass:watch', 'js:watch']);
gulp.task('lint', ['jscs', 'jshint']);
gulp.task('lint:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['lint']);
});
gulp.task('ci', ['js']);
gulp.task('default', ['sass', 'sass:watch', 'js', 'js:watch']);
