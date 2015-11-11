'use strict';

var gulp = require('gulp');
var gutil = require('gulp-util');
var sass = require('gulp-sass');
var autoprefixer = require('gulp-autoprefixer');
var sourcemaps = require('gulp-sourcemaps');
var jshint = require('gulp-jshint');
var jscs = require('gulp-jscs');

var PROJECT_ROOT = __dirname;
var PROJECT_PATH = {
    'scss': PROJECT_ROOT + '/filer/private/sass/',
    'css': PROJECT_ROOT + '/filer/static/filer/css/',
    'js': PROJECT_ROOT + '/filer/static/filer/js/'
};

var PROJECT_PATTERNS = {
    'scss': PROJECT_PATH.scss + '**/*.scss',
    'lint': [
        PROJECT_PATH.js + '**/*.js',
        PROJECT_ROOT + '/gulpfile.js'
    ]
};

// #############################################################################
// SCSS
gulp.task('scss', function () {
    gulp.src(PROJECT_PATTERNS.scss)
        .pipe(sourcemaps.init())
        .pipe(sass({outputStyle: 'compressed'}).on('error', sass.logError))
        .pipe(autoprefixer('last 2 version', 'safari 5', 'ie 8', 'ie 9', 'opera 12.1', 'ios 6', 'android 4'))
        .pipe(sourcemaps.write('/maps'))
        .pipe(gulp.dest(PROJECT_PATH.css));
});

gulp.task('scss:watch', function () {
    gulp.watch(PROJECT_PATTERNS.scss, ['scss']);
});

// #############################################################################
// LINTING
gulp.task('lint', function () {
    return gulp.src(PROJECT_PATTERNS.lint)
        .pipe(jshint())
        .pipe(jscs())
        .on('error', function (error) {
            gutil.log('\n' + error.message);
            if (process.env.CI) {
                process.exit(1);
            }
        })
        .pipe(jshint.reporter('jshint-stylish'));
});

gulp.task('lint:watch', function () {
    gulp.watch(PROJECT_PATTERNS.lint, ['lint']);
});

gulp.task('compile', ['scss']);
gulp.task('watch', ['scss:watch', 'lint:watch']);
