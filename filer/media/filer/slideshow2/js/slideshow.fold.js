/**
Script: Slideshow.Fold.js
	Slideshow.Fold - Flash extension for Slideshow.

License:
	MIT-style license.

Copyright:
	Copyright (c) 2008 [Aeron Glemann](http://www.electricprism.com/aeron/).

Dependencies:
	Slideshow.
*/

Slideshow.Fold = new Class({
	Extends: Slideshow,
	
/**
Constructor: initialize
	Creates an instance of the Slideshow class.

Arguments:
	element - (element) The wrapper element.
	data - (array or object) The images and optional thumbnails, captions and links for the show.
	options - (object) The options below.

Syntax:
	var myShow = new Slideshow.Fold(element, data, options);
*/

	initialize: function(el, data, options){
		this.parent(el, data, options);
	},

/**
Private method: show
	Does the slideshow effect.
*/

	_show: function(fast){
		if (!this.image.retrieve('tween')){
			var options = (this.options.overlap) ? {'duration': this.options.duration} : {'duration': this.options.duration / 2};
			$$(this.a, this.b).set('tween', $merge(options, {'link': 'chain', 'onStart': this._start.bind(this), 'onComplete': this._complete.bind(this), 'property': 'clip', 'transition': this.options.transition}));
		}
		var rect = this._rect(this.image);
		var img = (this.counter % 2) ? this.a : this.b;
		if (fast){			
			img.get('tween').cancel().set('rect(0, 0, 0, 0)');
			this.image.get('tween').cancel().set('rect(auto, auto, auto, auto)'); 			
		} 
		else {
			if (this.options.overlap){	
				img.get('tween').set('rect(auto, auto, auto, auto)');
				var tween = this.image.get('tween').set(rect.top + ' ' + rect.left + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).start(rect.top + ' ' + rect.right + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).start(rect.top + ' ' + rect.right + ' ' + rect.bottom + ' ' + rect.left);
			} 
			else	{
				var fn = function(rect){
					this.image.get('tween').set(rect.top + ' ' + rect.left + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).start(rect.top + ' ' + rect.right + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).start(rect.top + ' ' + rect.right + ' ' + rect.bottom + ' ' + rect.left);
				}.pass(rect, this);
				var rect = this._rect(img);
				img.get('tween').set(rect.top + ' ' + rect.right + ' ' + rect.bottom + ' ' + rect.left).start(rect.top + ' ' + rect.right + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).start(rect.top + ' ' + rect.left + ' ' + Math.ceil(rect.bottom / 2) + ' ' + rect.left).chain(fn);
			}
		}
	},
	
	/**
	Private method: rect
		Calculates the clipping rect
	*/

	_rect: function(img){
		var rect = img.getCoordinates(this.slideshow.retrieve('images'));
		rect.right = (rect.right > this.width) ? this.width - rect.left : rect.width;
		rect.bottom = (rect.bottom > this.height) ? this.height - rect.top : rect.height;
		rect.top = (rect.top < 0) ? Math.abs(rect.top) : 0;
		rect.left = (rect.left < 0) ? Math.abs(rect.left) : 0;
		return rect;		
	}
});