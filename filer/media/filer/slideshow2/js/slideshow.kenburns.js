/**
Script: Slideshow.KenBurns.js
	Slideshow.KenBurns - KenBurns extension for Slideshow, includes zooming and panning effects.

License:
	MIT-style license.

Copyright:
	Copyright (c) 2008 [Aeron Glemann](http://www.electricprism.com/aeron/).
	
Dependencies:
	Slideshow.
*/

Slideshow.KenBurns = new Class({
	Extends: Slideshow,
	
	options: {
		pan: [100, 100],
		zoom: [50, 50]
	},
	
/**
Constructor: initialize
	Creates an instance of the Slideshow class.

Arguments:
	element - (element) The wrapper element.
	data - (array or object) The images and optional thumbnails, captions and links for the show.
	options - (object) The options below.

Syntax:
	var myShow = new Slideshow.KenBurns(element, data, options);
*/

	initialize: function(el, data, options){
		options.overlap = true;
		options.resize = true;
		['pan', 'zoom'].each(function(p){
				if ($chk(this[p])){
					if ($type(this[p]) != 'array') this[p] = [this[p], this[p]];
					this[p].map(function(n){return (n.toInt() || 0).limit(0, 100);});					
				}
		}, options);
		this.parent(el, data, options);
	},

/**
Private method: show
	Does the slideshow effect.
*/

	_show: function(fast){
		if (!this.image.retrieve('morph')){
			['a', 'b'].each(function(image){
				this[image].set('tween', {
					'duration': this.options.duration, 'link': 'cancel', 'onStart': this._start.bind(this), 'onComplete': this._complete.bind(this), 'property': 'opacity'}
				).get('morph', {
					'duration': (this.options.delay + this.options.duration * 2), 'link': 'cancel', 'transition': $arguments(0)}
				);
			}, this);
		}
		this.image.set('styles', {'bottom': 'auto', 'left': 'auto', 'right': 'auto', 'top': 'auto'});
		var props = ['top left', 'top right', 'bottom left', 'bottom right'][this.counter % 4].split(' ');
		props.each(function(prop){this.image.setStyle(prop, 0);}, this);
		dh = this.height / this.preloader.height;
		dw = this.width / this.preloader.width;
		delta = (dw > dh) ? dw : dh;
		var values = {};
		var zoom = ($random.run(this.options.zoom) / 100.0) + 1;
		var pan = Math.abs(($random.run(this.options.pan) / 100.0) - 1);
		['height', 'width'].each(function(prop, i){
			var e = Math.ceil(this.preloader[prop] * delta);
			var s = (e * zoom).toInt();		
			values[prop] = [s, e];
			if (dw > dh || i){
				e = (this[prop] - this.image[prop]);
				s = (e * pan).toInt();			
				values[props[i]] = [s, e];
			}
		}, this);
		var paused = (this.firstrun && this.options.paused);
		if (fast || paused){
			this._center(this.image);
			this.image.get('morph').cancel();
			if (paused)
				this.image.get('tween').cancel().set(0).start(1);
			else
				this.image.get('tween').cancel().set(1);
		} 
		else{
			this.image.get('morph').start(values);
			this.image.get('tween').set(0).start(1);
		}
	}
});