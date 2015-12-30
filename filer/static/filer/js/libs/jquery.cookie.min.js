/**
 * Cookie plugin
 *
 * Copyright (c) 2006 Klaus Hartl (stilbuero.de)
 * Dual licensed under the MIT and GPL licenses:
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.gnu.org/licenses/gpl.html
 *
 */

/**
 * Create a cookie with the given name and value and other optional parameters.
 *
 * @example $.cookie('the_cookie', 'the_value');
 * @desc Set the value of a cookie.
 * @example $.cookie('the_cookie', 'the_value', { expires: 7, path: '/', domain: 'jquery.com', secure: true });
 * @desc Create a cookie with all available options.
 * @example $.cookie('the_cookie', 'the_value');
 * @desc Create a session cookie.
 * @example $.cookie('the_cookie', null);
 * @desc Delete a cookie by passing null as value. Keep in mind that you have to use the same path and domain
 *       used when the cookie was set.
 *
 * @param String name The name of the cookie.
 * @param String value The value of the cookie.
 * @param Object options An object literal containing key/value pairs to provide optional cookie attributes.
 * @option Number|Date expires Either an integer specifying the expiration date from now on in days or a Date object.
 *                             If a negative value is specified (e.g. a date in the past), the cookie will be deleted.
 *                             If set to null or omitted, the cookie will be a session cookie and will not be retained
 *                             when the the browser exits.
 * @option String path The value of the path atribute of the cookie (default: path of page that created the cookie).
 * @option String domain The value of the domain attribute of the cookie (default: domain of page that created the cookie).
 * @option Boolean secure If true, the secure attribute of the cookie will be set and the cookie transmission will
 *                        require a secure protocol (like HTTPS).
 * @type undefined
 *
 * @name $.cookie
 * @cat Plugins/Cookie
 * @author Klaus Hartl/klaus.hartl@stilbuero.de
 */

!function(e){e.cookie=function(n,o,i){if("undefined"==typeof o){var t=null;if(document.cookie&&""!=document.cookie)for(var r=document.cookie.split(";"),p=0;p<r.length;p++){var u=e.trim(r[p]);if(u.substring(0,n.length+1)==n+"="){t=decodeURIComponent(u.substring(n.length+1));break}}return t}i=i||{},null===o&&(o="",i=$.extend({},i),i.expires=-1);var s="";if(i.expires&&("number"==typeof i.expires||i.expires.toUTCString)){var a;"number"==typeof i.expires?(a=new Date,a.setTime(a.getTime()+24*i.expires*60*60*1e3)):a=i.expires,s="; expires="+a.toUTCString()}var c=i.path?"; path="+i.path:"",d=i.domain?"; domain="+i.domain:"",m=i.secure?"; secure":"";document.cookie=[n,"=",encodeURIComponent(o),s,c,d,m].join("")}}(jQuery);
