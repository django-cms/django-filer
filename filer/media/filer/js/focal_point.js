(function($) {
$(function(){
	var PAPER_WIDTH, PAPER_HEIGTH;
	var paper, ratio;
	var isDrag = false;
    var dragger = function (e) {
		this.dx = e.clientX;
        this.dy = e.clientY;
		isDrag = this;
        this.animate({"fill-opacity": .3, "fill": "#fffccc"}, 500);
    };
	
	document.onmousemove = function (e) {
        e = e || window.event;
        if (isDrag) {
            isDrag.translate(e.clientX - isDrag.dx, e.clientY - isDrag.dy);
			paper.safari();
            isDrag.dx = e.clientX;
            isDrag.dy = e.clientY;
        }
    };
    
	document.onmouseup = function (e) {
        if (isDrag) {
			isDrag.animate({"fill-opacity": .2, "fill": "#fff"}, 500);
			if (isDrag.type == "circle") {
				updatePosition(isDrag.attrs.cx, isDrag.attrs.cy);
			} 
		}
		isDrag = false;
    };
	
	var focalPoint; 
	
	function add(x, y) {
		if (isNaN(x)) {
			x = PAPER_WIDTH / 2;
			y = PAPER_HEIGTH / 2;
		}
		var el = paper.circle(x, y, 15);
		el.attr("fill", "#fff");
		el.attr("fill-opacity", .2);
		el.attr("stroke", "#c00");
		el.attr('stroke-width', 2);
		
		 
		el.mousedown(dragger);
		el.node.style.cursor = "move";
		focalPoint = el;
	}
	
	function remove(id){
		focalPoint.remove();
		focalPoint = null;
	}
	
	function updatePosition(x, y) {
		$("#id_subject_location").val(x === undefined ? '' : parseInt(parseInt(x)*ratio) + ',' + parseInt(parseInt(y)*ratio) );
	}
	
	
	$('#image_container img').load(function(){
		PAPER_WIDTH = $('#image_container img').width();
		PAPER_HEIGTH = $('#image_container img').height();
		$('#image_container').height(PAPER_HEIGTH + 'px');
		
		//  interface
		ratio = parseFloat($('#image_container img').attr('rel'));
		paper = Raphael(document.getElementById("paper"), PAPER_WIDTH, PAPER_HEIGTH);	
		// read location from form
		var location = $("#id_subject_location").val();
		var x, y;
		if (location){
			x = parseInt(parseInt(location.split(',')[0])/ratio);
			y = parseInt(parseInt(location.split(',')[1])/ratio);		
		}
		add(x, y);
	});
});
})(django.jQuery);


	
    
        
    