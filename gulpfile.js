'use strict';

var gulp = require('gulp');
var sass = require('gulp-sass');
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
};

var PROJECT_PATTERNS = {
    'sass': PROJECT_PATH.sass + '**/*.scss',
    'lint': [
        PROJECT_PATH.js + '**/*.js',
        PROJECT_ROOT + '/gulpfile.js',
        '!' + PROJECT_PATH.js + '**/*.min.js'
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

gulp.task('jscs:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['jscs']);
});

gulp.task('jshint', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(jshint('.jshintrc'))
        .pipe(jshint.reporter(stylish))
        .pipe(jshint.reporter('fail'));
});

gulp.task('jshint:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['jshint']);
});

gulp.task('js', ['jshint', 'jscs']);

gulp.task('js:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['js']);
});

gulp.task('tests:unit', function (done) {
    new Server({
        configFile: PROJECT_PATH.tests + '/karma.conf.js',
        singleRun: true
    }, done).start();
});

gulp.task('watch', ['sass:watch', 'js:watch']);
gulp.task('lint', ['js']);
gulp.task('ci', ['js', 'tests:unit']);
gulp.task('default', ['js', 'sass', 'js:watch', 'sass:watch']);
