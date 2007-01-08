/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.provide("tests.data.displayViaDojoDebug");
dojo.require("dojo.data.core.Read");

tests.data.displayViaDojoDebug = function(datastore, query) {
	var displayItem = function(item, result) {
		var string = '{';
		var attributes = datastore.getAttributes(item);
		for (var i in attributes) {
			var attribute = attributes[i];
			var value = datastore.get(item, attribute);
			if (i > 0) {
				string += ',\n ';
			}
			string += attribute + " : " + dojo.json.serialize(value);
		}
		string += '}';
		dojo.debug(string);
		return true;
	};
	dojo.debug("");
	dojo.debug("store contents...");
	var result = datastore.find({query:query, sync:true, onnext:displayItem}); //sync
}

