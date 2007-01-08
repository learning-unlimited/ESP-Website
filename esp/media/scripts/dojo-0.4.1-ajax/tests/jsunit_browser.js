/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.uri.*");
dj_eval(dojo.hostenv.getText(new dojo.uri.dojoUri("testtools/JsTestManager/jsunit_wrap.js")));
var _jum = jum;

var jum = {
	isBrowser: true, // so dojo can easily differentiate

	debug: function() {
		var dbg = djConfig.isDebug;
		djConfig.isDebug = true;
		dojo.debug.apply(dj_global, arguments);
		djConfig.isDebug = dbg;
	},

	assertTrue: function() {
		try {
			_jum.assertTrue.apply(_jum, arguments);
		} catch(e) {
			var str='';
			if(e["fileName"]){str+=e.fileName+':';}
			if (e["lineNumber"]){str+=e.lineNumber+' ';}
			str+=e.message;
			jum.debug(str);
		}
	},

	assertFalse: function() {
		try {
			_jum.assertFalse.apply(_jum, arguments);
		} catch(e) {
			var str='';
			if(e["fileName"]){str+=e.fileName+':';}
			if (e["lineNumber"]){str+=e.lineNumber+' ';}
			str+=e.message;
			jum.debug(str);
		}
	},

	assertEquals: function() {
		try {
			_jum.assertEquals.apply(_jum, arguments);
		} catch(e) {
			var str='';
			if(e["fileName"]){str+=e.fileName+':';}
			if (e["lineNumber"]){str+=e.lineNumber+' ';}
			str+=e.message;
			jum.debug(str);
		}
	}
};

