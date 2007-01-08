/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.data.old.*");
dojo.require("dojo.data.old.provider.FlatFile");
dojo.require("dojo.data.old.provider.Delicious");
dojo.require("dojo.lang.type");

function test_data_provider_empty() {
	var dataProvider = new dojo.data.old.provider.FlatFile();
	
	var arrayOfAttributes = dataProvider.getAttributes();
	jum.assertTrue('100', dojo.lang.isOfType(arrayOfAttributes, Array));
	jum.assertTrue('101', (arrayOfAttributes.length == 0));
	
	var attributeFoo = dataProvider.getAttribute("foo");
	jum.assertTrue('102', (attributeFoo === null));

	var resultSet = dataProvider.fetchResultSet();
	jum.assertTrue('103', dojo.lang.isOfType(resultSet, dojo.data.old.ResultSet));
	jum.assertTrue('104', (resultSet.getLength() == 0));
	jum.assertTrue('105', !(resultSet.toString()));
	jum.assertTrue('106', !(resultSet.getItemAt(1)));
	jum.assertTrue('107', (resultSet.indexOf("bar") == -1));
	jum.assertTrue('108', (resultSet.contains("bar") == false));
	var resultArray = dataProvider.fetchArray();
	jum.assertTrue('109', dojo.lang.isOfType(resultArray, Array));
	jum.assertTrue('110', (resultArray.length == 0));
	var iterator = resultSet.getIterator();
	jum.assertTrue('111', iterator.atEnd);
}

function test_data_provider_json_sample1() {
	var arrayOfJsonStates = [
	  { abbr: "WA", population: 5894121, name: "Washington" },
	  { abbr: "WV", population: 1808344, name: "West Virginia" },
	  { abbr: "WI", population: 5453896, name: "Wisconsin" },
	  { abbr: "WY", population:  493782, name: "Wyoming" } ];
	var dataProvider = new dojo.data.old.provider.FlatFile({jsonObjects: arrayOfJsonStates});
	var queryResultSet = dataProvider.fetchResultSet();
	jum.assertTrue('200', (queryResultSet.getLength() == arrayOfJsonStates.length));
	
	var arrayOfStateItems = queryResultSet.toArray();
	jum.assertTrue('201', (arrayOfStateItems.length == arrayOfJsonStates.length));
	
	var abbrAttribute = dataProvider.getAttribute('abbr');
	var popAttribute = dataProvider.getAttribute('population');
	var nameAttribute = dataProvider.getAttribute('name');
	jum.assertTrue('202', (abbrAttribute instanceof dojo.data.old.Attribute));
	jum.assertTrue('203', (popAttribute instanceof dojo.data.old.Attribute));
	jum.assertTrue('204', (nameAttribute instanceof dojo.data.old.Attribute));
	
	var arrayOfAttributes = dataProvider.getAttributes();
	jum.assertTrue('205', (arrayOfAttributes.length == 3));
	
	showQueryResultSet(queryResultSet);
	var iterator = queryResultSet.getIterator();
	while (!iterator.atEnd) {
		var stateItem = iterator.current;
		
		var abbr = stateItem.get('abbr');
		var pop  = stateItem.get('population');
		var name = stateItem.get('name');
		jum.assertTrue('206', (abbr.length == 2));
		jum.assertTrue('207', (dojo.lang.isOfType(pop, "numeric")));
		jum.assertTrue('208', (name.length > 2));

		jum.assertTrue('209', (stateItem.get('abbr') == stateItem.get(abbrAttribute)));
		jum.assertTrue('210', (stateItem.get('population') == stateItem.get(popAttribute)));
		jum.assertTrue('211', (stateItem.get('name') == stateItem.get(nameAttribute)));
		
		var abbrValue = stateItem.getValue('abbr');
		var popValue = stateItem.getValue(popAttribute);
		var nameValue = stateItem.getValue('name');
		jum.assertTrue('212', (abbrValue.getValue() == abbr));
		jum.assertTrue('213', (popValue.getValue()  == pop));
		jum.assertTrue('214', (nameValue.getValue() == name));

		var abbrValueToo = stateItem.getValues(abbrAttribute)[0];
		var popValueToo = stateItem.getValues('population')[0];
		var nameValueToo = stateItem.getValues('name')[0];
		jum.assertTrue('215', (abbrValueToo === abbrValue));
		jum.assertTrue('216', (popValueToo  === popValue));
		jum.assertTrue('217', (nameValueToo === nameValue));
		
		iterator.moveNext();
	}
}

function test_data_observersable() {
	var arrayOfJsonStates = [
	  { abbr: "WA", population: 5894121, name: "Washington" },
	  { abbr: "WV", population: 1808344, name: "West Virginia" },
	  { abbr: "WI", population: 5453896, name: "Wisconsin" },
	  { abbr: "WY", population:  493782, name: "Wyoming" } ];
	var dataProvider = new dojo.data.old.provider.FlatFile({jsonObjects: arrayOfJsonStates});
	var queryResultSet = dataProvider.fetchResultSet();
	
	var observationCount = 0;
	var Observer = function() {
		this.observedObjectHasChanged = function() {
			observationCount += 1;
			// dojo.debug("Observer.observedObjectHasChanged()");
		}
	}
	
	var itemObserver = new Observer();
	var itemUnderObservation = queryResultSet.getItemAt(0);
	itemUnderObservation.addObserver(itemObserver);

	var itemNotUnderObservation = queryResultSet.getItemAt(2);
	itemNotUnderObservation.set("abbr", "CA");
	jum.assertTrue('300', (observationCount === 0)); // no observers called
	
	itemUnderObservation.set("abbr", "ME");
	jum.assertTrue('301', (observationCount === 1)); // called just the item observer
	
	observationCount = 0;
	var resultSetObserver = new Observer();
	queryResultSet.addObserver(resultSetObserver);
	itemNotUnderObservation.set("abbr", "KS");
	jum.assertTrue('302', (observationCount === 1)); // called just the result set observer 

	observationCount = 0;
	itemUnderObservation.set("abbr", "OR");
	jum.assertTrue('303', (observationCount === 2)); // called both observers
}

function test_data_provider_json_sample2() {
	var arrayOfJsonStates = [
		{ abbr: "WA", name: "Washington" },
		{ abbr: "WV", name: "West Virginia" },
		{ abbr: "WI", name: "Wisconsin", song: "On, Wisconsin!" },
		{ abbr: "WY", name: "Wyoming", cities: ["Lander", "Cheyenne", "Laramie"] } ];
		
	var dataProvider = new dojo.data.old.provider.FlatFile({jsonObjects: arrayOfJsonStates});
	var queryResultSet = dataProvider.fetchResultSet();
	jum.assertTrue('400', (queryResultSet.getLength() == arrayOfJsonStates.length));
	showQueryResultSet(queryResultSet);
}

function test_data_provider_json_sample3() {
	var arrayOfJsonStates = [
		[ "abbr",  "population",  "name" ],
		[  "WA",     5894121,      "Washington"    ],
		[  "WV",     1808344,      "West Virginia" ],
		[  "WI",     5453896,      "Wisconsin"     ],
		[  "WY",      493782,      "Wyoming"       ] ];
		
	var dataProvider = new dojo.data.old.provider.FlatFile({jsonObjects: arrayOfJsonStates});
	var queryResultSet = dataProvider.fetchResultSet();
	jum.assertTrue('500', (queryResultSet.getLength() == (arrayOfJsonStates.length - 1)));
	showQueryResultSet(queryResultSet);
}

function BROKEN_test_data_provider_json_file() {
	var dataProvider = new dojo.data.old.provider.FlatFile({url: "states_with_keywords.json"});
	var queryResultSet = dataProvider.fetchResultSet();
	showQueryResultSet(queryResultSet);

	dataProvider = new dojo.data.old.provider.FlatFile({url: "states_with_header_row.json"});
	queryResultSet = dataProvider.fetchResultSet();
	showQueryResultSet(queryResultSet);
}

function BROKEN_test_data_provider_csv_file() {
	var dataProvider = new dojo.data.old.provider.FlatFile({url: "movies.csv"});
	var queryResultSet = dataProvider.fetchResultSet();
	showQueryResultSet(queryResultSet);
}

function BROKEN_test_data_provider_delicious() {
	/*
	var scriptElement = document.createElement('script');
	scriptElement.type = 'text/javascript';
	// scriptElement.src = '...' + '&output=json&callback=myFunction';
	scriptElement.src = 'http://del.icio.us/feeds/json/gumption?count=8';
	document.getElementsByTagName('body')[0].appendChild(scriptElement);
	*/
	var dataProvider = new dojo.data.old.provider.Delicious();
	var queryResultSet = dataProvider.fetchResultSet();
	showQueryResultSet(queryResultSet);
}

function NOTYET_test_data_item() {
	jum.assertTrue('600', true);
}

// -------------------------------------------------------------------
// Helper functions
// -------------------------------------------------------------------
function showQueryResultSet(queryResultSet) {
	dojo.debug('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~');
	var iterator = queryResultSet.getIterator();
	while (!iterator.atEnd) {
		var item = iterator.current;
		dojo.debug(item.toString());
		iterator.moveNext();
	}
}