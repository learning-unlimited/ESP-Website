/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.data.old.*");
dojo.require("dojo.lang.type");
dojo.require("dojo.data.old.provider.Delicious");

function data_binding_init() {
	loadFirstTable();
	// loadSecondTable();
}

function loadFirstTable() {
	var tableDiv = dojo.byId('putFirstQueryTableHere');
	var dataProvider = new dojo.data.old.provider.Delicious();	
	queryResultSet = dataProvider.fetchResultSet("gumption");
	var tableBinding = new TableBindingHack(tableDiv, queryResultSet, ["u", "d", "t"]);	
}

function loadSecondTable() {
	var tableDiv = dojo.byId('putSecondQueryTableHere');
	var dataProvider = new dojo.data.old.provider.Delicious();	
	queryResultSet = dataProvider.fetchResultSet("ben");
	var tableBinding = new TableBindingHack(tableDiv, queryResultSet, ["u", "d", "t"]);	
}