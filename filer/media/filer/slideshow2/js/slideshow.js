/**
Script: Slideshow.js
	Slideshow - A javascript class for Mootools to stream and animate the presentation of images on your website.

License:
	MIT-style license.

Copyright:
	Copyright (c) 2008 [Aeron Glemann](http://www.electricprism.com/aeron/).

Dependencies:
	Mootools 1.2 Core: Fx.Morph, Fx.Tween, Selectors, Element.Dimensions.
	Mootools 1.2 More: Assets.
*/

Slideshow = new Class({
	Implements: [Chain, Events, Options],
	
	options: {/*
		onComplete: $empty,
		onEnd: $empty,
		onStart: $empty,*/
		captions: false,
		center: true,
		classes: [],
		controller: false,
		delay: 2000,
		duration: 750,
		fast: false,
		height: false,
		href: '',
		hu: '',
		linked: false,
		loader: {'animate': ['css/loader-#.png', 12]},
		loop: true,
		match: /\?slide=(\d+)$/,
		overlap: true,
		paused: false,
		properties: ['href', 'rel', 'rev', 'title'],
		random: false,
		replace: [/(\.[^\.]+)$/, 't$1'],
		resize: 'width',
		slide: 0,
		thumbnails: false,
		titles: true,
		transition: function(p){return -(Math.cos(Math.PI * p) - 1) / 2;},
		width: false
	},
	
/**
Constructor: initialize
	Creates an instance of the Slideshow class.
	
Arguments:
	element - (element) The wrapper element.
	data - (array or object) The images and optional thumbnails, captions and links for the show.
	options - (object) The options below.
	
Syntax:
	var myShow = new Slideshow(element, data, options);
*/

	initialize: function(el, data, options){	
		this.setOptions(options);
		this.slideshow = $(el);
		if (!this.slideshow) 
			return;
		this.slideshow.set('styles', {'display': 'block', 'position': 'relative', 'z-index': 0});
		var match = window.location.href.match(this.options.match);
		this.slide = (this.options.match && match) ? match[1].toInt() : this.options.slide;
		this.counter = this.delay = this.transition = 0;
		this.direction = 'left';
		this.paused = false;
		if (!this.options.overlap)
			this.options.duration *= 2;
		var anchor = this.slideshow.getElement('a') || new Element('a');
		if (!this.options.href)
			this.options.href = anchor.get('href') || '';
		if (this.options.hu.length && !this.options.hu.test(/\/$/)) 
			this.options.hu += '/';
		if (this.options.fast === true)
			this.options.fast = 2;
			
		// styles
		
		var keys = ['slideshow', 'first', 'prev', 'play', 'pause', 'next', 'last', 'images', 'captions', 'controller', 'thumbnails', 'hidden', 'visible', 'inactive', 'active', 'loader'];
		var values = keys.map(function(key, i){
			return this.options.classes[i] || key;
		}, this);
		this.classes = values.associate(keys);
		this.classes.get = function(){
			var str = '.' + this.slideshow;
			for (var i = 0, l = arguments.length; i < l; i++)
				str += ('-' + this[arguments[i]]);
			return str;
		}.bind(this.classes);
			
		// data	
			
		if (!data){
			this.options.hu = '';
			data = {};
			var thumbnails = this.slideshow.getElements(this.classes.get('thumbnails') + ' img');
			this.slideshow.getElements(this.classes.get('images') + ' img').each(function(img, i){
				var src = img.get('src');
				var caption = $pick(img.get('alt'), img.get('title'), '');
				var parent = img.getParent();
				var properties = (parent.get('tag') == 'a') ? parent.getProperties : {};
				var href = img.getParent().get('href') || '';
				var thumbnail = (thumbnails[i]) ? thumbnails[i].get('src') : '';
				data[src] = {'caption': caption, 'href': href, 'thumbnail': thumbnail};
			});
		}
		var loaded = this.load(data);
		if (!loaded)
			return; 
		
		// events
		
		this.events = $H({'keydown': [], 'keyup': [], 'mousemove': []});
		var keyup = function(e){
			switch(e.key){
				case 'left': 
					this.prev(e.shift); break;
				case 'right': 
					this.next(e.shift); break;
				case 'p': 
					this.pause(); break;
			}
		}.bind(this);		
		this.events.keyup.push(keyup);
		document.addEvent('keyup', keyup);

		// required elements
			
		var el = this.slideshow.getElement(this.classes.get('images'));
		var images = (el) ? el.empty() : new Element('div', {'class': this.classes.get('images').substr(1)}).inject(this.slideshow);
		var div = images.getSize();
		this.height = this.options.height || div.y;		
		this.width = this.options.width || div.x;
		images.set({'styles': {'display': 'block', 'height': this.height, 'overflow': 'hidden', 'position': 'relative', 'width': this.width}});
		this.slideshow.store('images', images);
		this.a = this.image = this.slideshow.getElement('img') || new Element('img');
		if (Browser.Engine.trident && Browser.Engine.version > 4)
			this.a.style.msInterpolationMode = 'bicubic';
		this.a.set('styles', {'display': 'none', 'position': 'absolute', 'zIndex': 1});
		this.b = this.a.clone();
		[this.a, this.b].each(function(img){
			anchor.clone().cloneEvents(anchor).grab(img).inject(images);
		});
		
		// optional elements
		
		if (this.options.captions)
 			this._captions();
		if (this.options.controller)
			this._controller();
		if (this.options.loader)
 			this._loader();
		if (this.options.thumbnails)
			this._thumbnails();
			
		// begin show
		
		this._preload();
	},
	
/**
Public method: go
	Jump directly to a slide in the show.

Arguments:
	n - (integer) The index number of the image to jump to, 0 being the first image in the show.
	
Syntax:
	myShow.go(n);	
*/

	go: function(n, direction){
		if ((this.slide - 1 + this.data.images.length) % this.data.images.length == n || $time() < this.transition)
			return;		
		$clear(this.timer);
		this.delay = 0;		
		this.direction = (direction) ? direction : ((n < this.slide) ? 'right' : 'left');
		this.slide = n;
		if (this.preloader) 
			this.preloader = this.preloader.destroy();
		this._preload(this.options.fast == 2 || (this.options.fast == 1 && this.paused));
	},

/**
Public method: first
	Goes to the first image in the show.

Syntax:
	myShow.first();	
*/

	first: function(){
		this.prev(true); 
	},

/**
Public method: prev
	Goes to the previous image in the show.

Syntax:
	myShow.prev();	
*/

	prev: function(first){
		var n = 0;
		if (!first){
			if (this.options.random){
				
				// if it's a random show get the previous slide from the showed array

				if (this.showed.i < 2)
					return;
				this.showed.i -= 2;
				n = this.showed.array[this.showed.i];
			}
			else
				n = (this.slide - 2 + this.data.images.length) % this.data.images.length;									
		}
		this.go(n, 'right');
	},

/**
Public method: pause
	Toggles play / pause state of the show.

Arguments:
	p - (undefined, 1 or 0) Call pause with no arguments to toggle the pause state. Call pause(1) to force pause, or pause(0) to force play.

Syntax:
	myShow.pause(p);	
*/

	pause: function(p){
		if ($chk(p))
			this.paused = (p) ? false : true;
		if (this.paused){
			this.paused = false;
			this.delay = this.transition = 0;		
			this.timer = this._preload.delay(100, this);
			[this.a, this.b].each(function(img){
				['morph', 'tween'].each(function(p){
					if (this.retrieve(p)) this.get(p).resume();
				}, img);
			});
			if (this.options.controller)
				this.slideshow.getElement('.' + this.classes.pause).removeClass(this.classes.play);
		} 
		else {
			this.paused = true;
			this.delay = Number.MAX_VALUE;
			this.transition = 0;
			$clear(this.timer);
			[this.a, this.b].each(function(img){
				['morph', 'tween'].each(function(p){
					if (this.retrieve(p)) this.get(p).pause();
				}, img);
			});
			if (this.options.controller)
				this.slideshow.getElement('.' + this.classes.pause).addClass(this.classes.play);
		}
	},
	
/**
Public method: next
	Goes to the next image in the show.

Syntax:
	myShow.next();	
*/

	next: function(last){
		var n = (last) ? this.data.images.length - 1 : this.slide;
		this.go(n, 'left');
	},

/**
Public method: last
	Goes to the last image in the show.

Syntax:
	myShow.last();	
*/

	last: function(){
		this.next(true); 
	},

/**
Public method: load
	Loads a new data set into the show: will stop the current show, rewind and rebuild thumbnails if applicable.

Arguments:
	data - (array or object) The images and optional thumbnails, captions and links for the show.

Syntax:
	myShow.load(data);
*/

	load: function(data){
		this.firstrun = true;
		this.showed = {'array': [], 'i': 0};
		if ($type(data) == 'array'){
			this.options.captions = false;			
			data = new Array(data.length).associate(data.map(function(image, i){ return image + '?' + i })); 
		}
		this.data = {'images': [], 'captions': [], 'hrefs': [], 'thumbnails': []};
		for (var image in data){
			var obj = data[image] || {};
			var caption = (obj.caption) ? obj.caption.trim() : '';
			var href = (obj.href) ? obj.href.trim() : ((this.options.linked) ? this.options.hu + image : this.options.href);
			var thumbnail = (obj.thumbnail) ? obj.thumbnail.trim() : image.replace(this.options.replace[0], this.options.replace[1]);
			this.data.images.push(image);
			this.data.captions.push(caption);
			this.data.hrefs.push(href);
			this.data.thumbnails.push(thumbnail);
		}
		if (this.options.random)
			this.slide = $random(0, this.data.images.length - 1);
		
		// only run when data is loaded dynamically into an existing slideshow instance
		
		if (this.options.thumbnails && this.slideshow.retrieve('thumbnails'))
			this._thumbnails();
		if (this.slideshow.retrieve('images')){
			[this.a, this.b].each(function(img){
				['morph', 'tween'].each(function(p){
					if (this.retrieve(p)) this.get(p).cancel();
				}, img);
			});
			this.slide = this.transition = 0;
			this.go(0);		
		}
		return this.data.images.length;
	},
	
/**
Public method: destroy
	Destroys a Slideshow instance.

Arguments:
	p - (string) The images and optional thumbnails, captions and links for the show.

Syntax:
	myShow.destroy(p);
*/

	destroy: function(p){
		this.events.each(function(array, e){
			array.each(function(fn){ document.removeEvent(e, fn); });
		});
		this.pause(1);
		if (this.options.loader)
			$clear(this.slideshow.retrieve('loader').retrieve('timer'));		
		if (this.options.thumbnails)
			$clear(this.slideshow.retrieve('thumbnails').retrieve('timer'));
		this.slideshow.uid = Native.UID++;
		if (p)
			this.slideshow[p]();
	},
	
/**
Private method: preload
	Preloads the next slide in the show, once loaded triggers the show, updates captions, thumbnails, etc.
*/

	_preload: function(fast){
		if (!this.preloader)
		 	this.preloader = new Asset.image(this.options.hu + this.data.images[this.slide], {'onload': function(){
				this.store('loaded', true);
			}});	
		if (this.preloader.retrieve('loaded') && $time() > this.delay && $time() > this.transition){
			if (this.stopped){
				if (this.options.captions)
					this.slideshow.retrieve('captions').get('morph').cancel().start(this.classes.get('captions', 'hidden'));
				this.pause(1);
				if (this.end)
					this.fireEvent('end');
				this.stopped = this.end = false;
				return;				
			}					
			this.image = (this.counter % 2) ? this.b : this.a;
			this.image.set('styles', {'display': 'block', 'height': 'auto', 'visibility': 'hidden', 'width': 'auto', 'zIndex': this.counter});
			['src', 'height', 'width'].each(function(prop){
				this.image.set(prop, this.preloader.get(prop));
			}, this);
			this._resize(this.image);
			this._center(this.image);
			var anchor = this.image.getParent();
			if (this.data.hrefs[this.slide])
				anchor.set('href', this.data.hrefs[this.slide]);			
			else
				anchor.erase('href');
			var text = (this.data.captions[this.slide])
				? this.data.captions[this.slide].replace(/<.+?>/gm, '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, "'") 
				: '';
			this.image.set('alt', text);		
			if (this.options.titles)
				anchor.set('title', text);
			if (this.options.loader)
				this.slideshow.retrieve('loader').fireEvent('hide');
			if (this.options.captions)
				this.slideshow.retrieve('captions').fireEvent('update', fast);				
			if (this.options.thumbnails)
				this.slideshow.retrieve('thumbnails').fireEvent('update', fast); 			
			this._show(fast);
			this._loaded();
		} 
		else {
			if ($time() > this.delay && this.options.loader)
				this.slideshow.retrieve('loader').fireEvent('show');
			this.timer = (this.paused && this.preloader.retrieve('loaded')) ? null : this._preload.delay(100, this, fast); 
		}
	},

/**
Private method: show
	Does the slideshow effect.
*/

	_show: function(fast){
		if (!this.image.retrieve('morph')){
			var options = (this.options.overlap) ? {'duration': this.options.duration, 'link': 'cancel'} : {'duration': this.options.duration / 2, 'link': 'chain'};
			$$(this.a, this.b).set('morph', $merge(options, {'onStart': this._start.bind(this), 'onComplete': this._complete.bind(this), 'transition': this.options.transition}));
		}
		var hidden = this.classes.get('images', ((this.direction == 'left') ? 'next' : 'prev'));
		var visible = this.classes.get('images', 'visible');
		var img = (this.counter % 2) ? this.a : this.b;
		if (fast){			
			img.get('morph').cancel().set(hidden);
			this.image.get('morph').cancel().set(visible); 			
		} 
		else {
			if (this.options.overlap){
				img.get('morph').set(visible);
				this.image.get('morph').set(hidden).start(visible);
			} 
			else	{
				var fn = function(hidden, visible){
					this.image.get('morph').set(hidden).start(visible);
				}.pass([hidden, visible], this);
				hidden = this.classes.get('images', ((this.direction == 'left') ? 'prev' : 'next'));
				img.get('morph').set(visible).start(hidden).chain(fn);
			}
		}
	},
	
/**
Private method: loaded
	Run after the current image has been loaded, sets up the next image to be shown.
*/

	_loaded: function(){
		this.counter++;
		this.delay = (this.paused) ? Number.MAX_VALUE : $time() + this.options.duration + this.options.delay;
		this.direction = 'left';
		this.transition = (this.options.fast == 2 || (this.options.fast == 1 && this.paused)) ? 0 : $time() + this.options.duration;			
		if (this.slide + 1 == this.data.images.length && !this.options.loop && !this.options.random)
			this.stopped = this.end = true;			
		if (this.options.random){
			this.showed.i++;
			if (this.showed.i >= this.showed.array.length){
				var n = this.slide;
				if (this.showed.array.getLast() != n) this.showed.array.push(n);
				while (this.slide == n)
					this.slide = $random(0, this.data.images.length - 1);				
			}
			else
				this.slide = this.showed.array[this.showed.i];
		}
		else
			this.slide = (this.slide + 1) % this.data.images.length;
		if (this.image.getStyle('visibility') != 'visible')
			(function(){ this.image.setStyle('visibility', 'visible'); }).delay(1, this);			
		if (this.preloader) 
			this.preloader = this.preloader.destroy();
		this._preload();
	},

/**
Private method: center
	Center an image.
*/

	_center: function(img){
		if (this.options.center){
			var size = img.getSize();
			img.set('styles', {'left': (size.x - this.width) / -2, 'top': (size.y - this.height) / -2});
		}
	},

/**
Private method: resize
	Resizes an image.
*/

	_resize: function(img){
		if (this.options.resize){
			var h = this.preloader.get('height'), w = this.preloader.get('width');
			var dh = this.height / h, dw = this.width / w, d;
			if (this.options.resize == 'length')
				d = (dh > dw) ? dw : dh;
			else
				d = (dh > dw) ? dh : dw;
			img.set('styles', {height: Math.ceil(h * d), width: Math.ceil(w * d)});
		}	
	},

/**
Private method: start
	Callback on start of slide change.
*/

	_start: function(){		
		this.fireEvent('start');
	},

/**
Private method: complete
	Callback on start of slide change.
*/

	_complete: function(){
		if (this.firstrun && this.options.paused){
			this.firstrun = false;
			this.pause(1);
		}
		this.fireEvent('complete');
	},

/**
Private method: captions
	Builds the optional caption element, adds interactivity.
	This method can safely be removed if the captions option is not enabled.
*/

	_captions: function(){
 		if (this.options.captions === true) 
 			this.options.captions = {};
		var el = this.slideshow.getElement(this.classes.get('captions'));
		var captions = (el) ? el.empty() : new Element('div', {'class': this.classes.get('captions').substr(1)}).inject(this.slideshow);
		captions.set({
			'events': {
				'update': function(fast){	
					var captions = this.slideshow.retrieve('captions');
					var empty = (this.data.captions[this.slide] === '');
					if (fast){
						var p = (empty) ? 'hidden' : 'visible';
						captions.set('html', this.data.captions[this.slide]).get('morph').cancel().set(this.classes.get('captions', p));
					}
					else {
						var fn = (empty) ? $empty : function(n){
							this.slideshow.retrieve('captions').set('html', this.data.captions[n]).morph(this.classes.get('captions', 'visible'))
						}.pass(this.slide, this);		
						captions.get('morph').cancel().start(this.classes.get('captions', 'hidden')).chain(fn);
					}
				}.bind(this)
			},
			'morph': $merge(this.options.captions, {'link': 'chain'})
		});
		this.slideshow.store('captions', captions);
	},

/**
Private method: controller
	Builds the optional controller element, adds interactivity.
	This method can safely be removed if the controller option is not enabled.
*/

	_controller: function(){
 		if (this.options.controller === true)
 			this.options.controller = {};
		var el = this.slideshow.getElement(this.classes.get('controller'));
		var controller = (el) ? el.empty() : new Element('div', {'class': this.classes.get('controller').substr(1)}).inject(this.slideshow);
		var ul = new Element('ul').inject(controller);
		$H({'first': 'Shift + Leftwards Arrow', 'prev': 'Leftwards Arrow', 'pause': 'P', 'next': 'Rightwards Arrow', 'last': 'Shift + Rightwards Arrow'}).each(function(accesskey, action){
			var li = new Element('li', {
				'class': (action == 'pause' && this.options.paused) ? this.classes.play + ' ' + this.classes[action] : this.classes[action]
			}).inject(ul);
			var a = this.slideshow.retrieve(action, new Element('a', {
				'title': ((action == 'pause') ? this.classes.play.capitalize() + ' / ' : '') + this.classes[action].capitalize() + ' [' + accesskey + ']'				
			}).inject(li));
			a.set('events', {
				'click': function(action){this[action]();}.pass(action, this),
				'mouseenter': function(active){this.addClass(active);}.pass(this.classes.active, a),
				'mouseleave': function(active){this.removeClass(active);}.pass(this.classes.active, a)
			});		
		}, this);
		controller.set({
			'events': {
				'hide': function(hidden){  
					if (!this.retrieve('hidden'))
						this.store('hidden', true).morph(hidden);
				}.pass(this.classes.get('controller', 'hidden'), controller),
				'show': function(visible){  
					if (this.retrieve('hidden'))
						this.store('hidden', false).morph(visible);
				}.pass(this.classes.get('controller', 'visible'), controller)
			},
			'morph': $merge(this.options.controller, {'link': 'cancel'})
		}).store('hidden', false);
		var keydown = function(e){
			if (['left', 'right', 'p'].contains(e.key)){
				var controller = this.slideshow.retrieve('controller');
				if (controller.retrieve('hidden'))
					controller.get('morph').set(this.classes.get('controller', 'visible')); 			
				switch(e.key){
					case 'left': 
						this.slideshow.retrieve((e.shift) ? 'first' : 'prev').fireEvent('mouseenter'); break;
					case 'right':
						this.slideshow.retrieve((e.shift) ? 'last' : 'next').fireEvent('mouseenter'); break;
					default:
						this.slideshow.retrieve('pause').fireEvent('mouseenter'); break;
				}
			}
		}.bind(this);
		this.events.keydown.push(keydown);
		var keyup = function(e){
			if (['left', 'right', 'p'].contains(e.key)){
				var controller = this.slideshow.retrieve('controller');
				if (controller.retrieve('hidden'))
					controller.store('hidden', false).fireEvent('hide'); 
				switch(e.key){
					case 'left': 
						this.slideshow.retrieve((e.shift) ? 'first' : 'prev').fireEvent('mouseleave'); break;
					case 'right': 
						this.slideshow.retrieve((e.shift) ? 'last' : 'next').fireEvent('mouseleave'); break;
					default:
						this.slideshow.retrieve('pause').fireEvent('mouseleave'); break;
				}
			}
		}.bind(this);
		this.events.keyup.push(keyup);
		var mousemove = function(e){
			var images = this.slideshow.retrieve('images').getCoordinates();
			if (e.page.x > images.left && e.page.x < images.right && e.page.y > images.top && e.page.y < images.bottom)
				this.slideshow.retrieve('controller').fireEvent('show');
			else
				this.slideshow.retrieve('controller').fireEvent('hide');
		}.bind(this);
		this.events.mousemove.push(mousemove);
		document.addEvents({'keydown': keydown, 'keyup': keyup, 'mousemove': mousemove});
		this.slideshow.retrieve('controller', controller).fireEvent('hide');
	},

/**
Private method: loader
	Builds the optional loader element, adds interactivity.
	This method can safely be removed if the loader option is not enabled.
*/

	_loader: function(){
 		if (this.options.loader === true) 
 			this.options.loader = {};
		var loader = new Element('div', {
			'class': this.classes.get('loader').substr(1),				
			'morph': $merge(this.options.loader, {'link': 'cancel'})
		}).store('hidden', false).store('i', 1).inject(this.slideshow.retrieve('images'));
		if (this.options.loader.animate){
			for (var i = 0; i < this.options.loader.animate[1]; i++)
				img = new Asset.image(this.options.loader.animate[0].replace(/#/, i));
			if (Browser.Engine.trident4 && this.options.loader.animate[0].contains('png'))
				loader.setStyle('backgroundImage', 'none');					
		}
		loader.set('events', {
			'animate': function(){  
				var loader = this.slideshow.retrieve('loader');				
				var i = (loader.retrieve('i').toInt() + 1) % this.options.loader.animate[1];
				loader.store('i', i);
				var img = this.options.loader.animate[0].replace(/#/, i);
				if (Browser.Engine.trident4 && this.options.loader.animate[0].contains('png'))
					loader.style.filter = 'progid:DXImageTransform.Microsoft.AlphaImageLoader(src="' + img + '", sizingMethod="scale")';
				else 
					loader.setStyle('backgroundImage', 'url(' + img + ')');
			}.bind(this),
			'hide': function(){  
				var loader = this.slideshow.retrieve('loader');
				if (!loader.retrieve('hidden')){
					loader.store('hidden', true).morph(this.classes.get('loader', 'hidden'));
					if (this.options.loader.animate)
						$clear(loader.retrieve('timer'));					
				}
			}.bind(this),
			'show': function(){  
				var loader = this.slideshow.retrieve('loader');
				if (loader.retrieve('hidden')){
					loader.store('hidden', false).morph(this.classes.get('loader', 'visible'));
					if (this.options.loader.animate)
						loader.store('timer', function(){this.fireEvent('animate');}.periodical(50, loader));
				}
			}.bind(this)
		});
		this.slideshow.retrieve('loader', loader).fireEvent('hide');
	},
	
/**
Private method: thumbnails
	Builds the optional thumbnails element, adds interactivity.
	This method can safely be removed if the thumbnails option is not enabled.
*/

	_thumbnails: function(){
 		if (this.options.thumbnails === true) 
 			this.options.thumbnails = {}; 
		var el = this.slideshow.getElement(this.classes.get('thumbnails'));
		var thumbnails = (el) ? el.empty() : new Element('div', {'class': this.classes.get('thumbnails').substr(1)}).inject(this.slideshow);
		thumbnails.setStyle('overflow', 'hidden');
		var ul = new Element('ul', {'tween': {'link': 'cancel'}}).inject(thumbnails);
		this.data.thumbnails.each(function(thumbnail, i){
			var li = new Element('li').inject(ul);
			var a = new Element('a', {
				'events': {
					'click': function(i){
						this.go(i); 
						return false; 
					}.pass(i, this),
					'loaded': function(){
						this.data.thumbnails.pop();
						if (!this.data.thumbnails.length){
							var div = thumbnails.getCoordinates();
							var props = thumbnails.retrieve('props');			
							var limit = 0, pos = props[1], size = props[2];		
							thumbnails.getElements('li').each(function(li){			
								var li = li.getCoordinates();		
								if (li[pos] > limit) limit = li[pos];
							}, this);			
							thumbnails.store('limit', div[size] + div[props[0]] - limit);
						}
					}.bind(this)
				},
				'href': this.options.hu + this.data.images[i],
				'morph': $merge(this.options.thumbnails, {'link': 'cancel'})
			}).inject(li);
			if (this.data.captions[i] && this.options.titles)
				a.set('title', this.data.captions[i].replace(/<.+?>/gm, '').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, "'"));
			var img = new Asset.image(this.options.hu + thumbnail, {
				'onload': function(){this.fireEvent('loaded');}.bind(a) 
			}).inject(a);
		}, this);
		thumbnails.set('events', {
			'scroll': function(n, fast){
				var div = this.getCoordinates();
				var ul = this.getElement('ul').getPosition();
				var props = this.retrieve('props');
				var axis = props[3], delta, pos = props[0], size = props[2], value;				
				var tween = this.getElement('ul').get('tween', {'property': pos});	
				if ($chk(n)){
					var li = this.getElements('li')[n].getCoordinates();
					delta = div[pos] + (div[size] / 2) - (li[size] / 2) - li[pos]	
					value = (ul[axis] - div[pos] + delta).limit(this.retrieve('limit'), 0);
					if (fast)	
						tween.set(value);
					else						 
						tween.start(value);
				}
				else{
					var area = div[props[2]] / 3, page = this.retrieve('page'), velocity = -0.2;			
					if (page[axis] < (div[pos] + area))
						delta = (page[axis] - div[pos] - area) * velocity;
					else if (page[axis] > (div[pos] + div[size] - area))
						delta = (page[axis] - div[pos] - div[size] + area) * velocity;			
					if (delta){			
						value = (ul[axis] - div[pos] + delta).limit(this.retrieve('limit'), 0);
						tween.set(value);
					}
				}				
			}.bind(thumbnails),
			'update': function(fast){
				var thumbnails = this.slideshow.retrieve('thumbnails');
				thumbnails.getElements('a').each(function(a, i){	
					if (i == this.slide){
						if (!a.retrieve('active', false)){
							a.store('active', true);
							var active = this.classes.get('thumbnails', 'active');							
							if (fast) a.get('morph').set(active);
							else a.morph(active);
						}
					} 
					else {
						if (a.retrieve('active', true)){
							a.store('active', false);
							var inactive = this.classes.get('thumbnails', 'inactive');						
							if (fast) a.get('morph').set(inactive);
							else a.morph(inactive);
						}
					}
				}, this);
				if (!thumbnails.retrieve('mouseover'))
					thumbnails.fireEvent('scroll', [this.slide, fast]);
			}.bind(this)
		})
		var div = thumbnails.getCoordinates();
		thumbnails.store('props', (div.height > div.width) ? ['top', 'bottom', 'height', 'y'] : ['left', 'right', 'width', 'x']);
		var mousemove = function(e){
			var div = this.getCoordinates();
			if (e.page.x > div.left && e.page.x < div.right && e.page.y > div.top && e.page.y < div.bottom){
				this.store('page', e.page);			
				if (!this.retrieve('mouseover')){
					this.store('mouseover', true);
					this.store('timer', function(){this.fireEvent('scroll');}.periodical(50, this));
				}
			}
			else {
				if (this.retrieve('mouseover')){
					this.store('mouseover', false);				
					$clear(this.retrieve('timer'));
				}
			}
		}.bind(thumbnails);
		this.events.mousemove.push(mousemove);
		document.addEvent('mousemove', mousemove);
		this.slideshow.store('thumbnails', thumbnails);
	}
});