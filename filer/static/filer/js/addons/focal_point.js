'use strict';
/* globals Raphael, django */

(function ($) {
    $(function () {
        var paperWidth, pagerHeight;
        var paper, ratio;
        var isDrag = false;
        var image_loaded = false;
        var dragger = function (e) {
            this.dx = e.clientX;
            this.dy = e.clientY;
            isDrag = this;
            this.animate({'fill-opacity': 0.3, 'fill': '#fffccc'}, 500);
        };
        var imageContainerImage = $('#image_container img');
        var focalPoint;

        document.onmousemove = function (e) {
            e = e || window.event;
            if (isDrag) {
                isDrag.translate(e.clientX - isDrag.dx, e.clientY - isDrag.dy);
                paper.safari();
                isDrag.dx = e.clientX;
                isDrag.dy = e.clientY;
            }
        };

        document.onmouseup = function () {
            if (isDrag) {
                isDrag.animate({'fill-opacity': 0.2, 'fill': '#fff'}, 500);
                if (isDrag.type === 'circle') {
                    updatePosition(isDrag.attrs.cx, isDrag.attrs.cy);
                }
            }
            isDrag = false;
        };

        function add(x, y) {
            var el;

            if (isNaN(x)) {
                x = paperWidth / 2;
                y = pagerHeight / 2;
            }
            el = paper.circle(x, y, 15);
            el.attr('fill', '#fff');
            el.attr('fill-opacity', 0.2);
            el.attr('stroke', '#c00');
            el.attr('stroke-width', 2);


            el.mousedown(dragger);
            el.node.style.cursor = 'move';
            focalPoint = el;
        }

        window.remove = function () {
            focalPoint.remove();
            focalPoint = null;
        };

        function updatePosition(x, y) {
            $('#id_subject_location')
                .val(x === undefined ? '' : parseInt(parseInt(x) * ratio) + ',' + parseInt(parseInt(y) * ratio));
        }

        function imageInit() {
            var location = $('#id_subject_location').val();
            var x, y;

            paperWidth = imageContainerImage.width();
            pagerHeight = imageContainerImage.height();
            $('#image_container').height(pagerHeight + 'px');

            // interface
            ratio = parseFloat(imageContainerImage.attr('rel'));
            paper = new Raphael(document.getElementById('paper'), paperWidth, pagerHeight);

            // read location from form
            if (location) {
                x = parseInt(parseInt(location.split(',')[0]) / ratio);
                y = parseInt(parseInt(location.split(',')[1]) / ratio);
            }
            add(x, y);
            image_loaded = true;
        }

        imageContainerImage.load(imageInit);
        // If image has not been loaded after 250ms after pageload,
        // assume it's allready loaded and try initializing.
        window.setTimeout(function () {
            if (!image_loaded) {
                imageInit();
            }
        }, 250);
    });
})(django.jQuery);
