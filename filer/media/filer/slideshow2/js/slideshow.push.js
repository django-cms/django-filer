/**
Script: Slideshow.Push.js
	Slideshow.Push - Push extension for Slideshow.

License:
	MIT-style license.

Copyright:
	Copyright (c) 2008 [Aeron Glemann](http://www.electricprism.com/aeron/).
	
Dependencies:
	Slideshow.
	Mootools 1.2 More: Fx.Elements.
*/

Slideshow.Push = new Class({
	Extends: Slideshow,
	
/**
Constructor: initialize
	Creates an instance of the Slideshow class.

Arguments:
	element - (element) The wrapper element.
	data - (array or object) The images and optional thumbnails, captions and links for the show.
	options - (object) The options below.

Syntax:
	var myShow = new Slideshow.Push(element, data, options);
*/
	
	initialize: function(el, data, options){
		options.overlap = true;		
		this.parent(el, data, options);
	},

/**
Private method: show
	Does the slideshow effect.
*/

	_show: function(fast){
		var images = [this.image, ((this.counter % 2) ? this.a : this.b)];
		if (!this.image.retrieve('fx'))
			this.image.store('fx', new Fx.Elements(images, {'duration': this.options.duration, 'link': 'cancel', 'onStart': this._start.bind(this), 'onComplete': this._complete.bind(this), 'transition': this.options.transition }));
		this.image.set('styles', {'left': 'auto', 'right': 'auto' }).setStyle(this.direction, this.width);
		var values = {'0': {}, '1': {} };
		values['0'][this.direction] = [this.width, 0];
		values['1'][this.direction] = [0, -this.width];
		if (images[1].getStyle(this.direction) == 'auto'){
			var width = this.width - images[1].width;	
			images[1].set('styles', {'left': 'auto', 'right': 'auto' }).setStyle(this.direction, width);		 
			values['1'][this.direction] = [width, -this.width];
		}
		if (fast){
		 	for (var prop in values)
		 		values[prop][this.direction] = values[prop][this.direction][1];			
			this.image.retrieve('fx').cancel().set(values);
		} 
		else
			this.image.retrieve('fx').start(values);
	}
});