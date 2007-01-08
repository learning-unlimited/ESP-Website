/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.provide("tests.data.displayFilteringTable");
dojo.require("dojo.data.core.Read");
dojo.require("dojo.widget.FilteringTable");

tests.data.displayFilteringTable = function(datastore, query, tableElement) {
	var dataInSimpleStoreFormat = [];
	var columnsInFilteringTableFormat = null;
	var addRow = function(item, result) {
		var object = {};
		var attributes = datastore.getAttributes(item);
		object["Identity"] = item;
		for (var i in attributes) {
			var attribute = attributes[i];
			var value = datastore.get(item, attribute);
			object[attribute] = value;
		}
		dataInSimpleStoreFormat.push(object);
		if (!columnsInFilteringTableFormat) {
			columnsInFilteringTableFormat = [];
			for (var i in attributes) {
				var attribute = attributes[i];
				columnsInFilteringTableFormat.push({field: attribute});
			}
		}
	};

	var result = datastore.find({query:query, sync:true, onnext:addRow});
	
	var filteringTable = dojo.widget.createWidget("dojo:FilteringTable", {valueField:"Identity"}, tableElement);

	for (var i in columnsInFilteringTableFormat) {
		var column = columnsInFilteringTableFormat[i];
		filteringTable.columns.push(filteringTable.createMetaData(column));
	}

	filteringTable.store.setData(dataInSimpleStoreFormat);
}
