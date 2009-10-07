/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.lang.declare");

function test_lang_declare() {
	dojo.declare('my.classes.foo', null, {
		instanceId: [ 'bad' ], // make sure we test a non-primitive									 
		initializer: function(arg) {
			this.instanceId = [ 'foo' ]; // this will supercede the prototype in every instance
		},
		getId: function() {
			return "I am a foo";
		}
	});
	jum.assertEquals("30", "function", typeof my.classes.foo);

	dojo.declare('my.classes.bar', my.classes.foo, {
		initializer: function(arg) {
			this.instanceId = [ 'bar' ]; // this will supercede the prototype in every instance
		},
		getId: function() {
			return "I am a bar and " + my.classes.bar.superclass.getId.apply(this, arguments);
		}
	});
	jum.assertEquals("31", "function", typeof my.classes.bar);
	
	b = new my.classes.bar();
	jum.assertEquals("32", "object", typeof b);
	
	dojo.declare('my.classes.zot', my.classes.bar, {
		initializer: function(arg) {
			this.instanceId = [ 'zot' ]; // this will supercede the prototype in every instance
		},
		getId: function() {
			return "I am a zot and " + my.classes.zot.superclass.getId.apply(this, arguments);
		}
	});
	jum.assertEquals("33", "function", typeof my.classes.zot);
	
	f = new my.classes.foo();
	jum.assertEquals("34", "object", typeof f);
	
	z = new my.classes.zot("with an argument");
	jum.assertEquals("35", "object", typeof z);
	
	jum.assertEquals("36", "I am a foo", f.getId());
	jum.assertEquals("37", "I am a bar and I am a foo", b.getId());
	jum.assertEquals("38", "I am a zot and I am a bar and I am a foo", z.getId());
}