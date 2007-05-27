/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.registerModulePath("tests", "tests");
dojo.require("tests.MockXMLHttpRequest");
dojo.require("dojo.data.RdfStore");
dojo.require("dojo.lang.type");

function test_data_rdf_newStore() {
	//RhizomeStore is a working subclass of RDFStore
	return new dojo.data.RhizomeStore({ baseUrl : "http://localhost:8000/" });
}

var rdfTestData = {
	testJson: '{"_:1": {"http://rx4rdf.sf.net/ns/wiki#name" : [{"type":"bnode","value":"1"}, {"type":"bnode","value":"2"}]}'+
	 	',"urn:sha:ndKxl8RGTmr3uomnJxVdGnWgXuA=": {"http://rx4rdf.sf.net/ns/archive#content-length" : ' +
		'[{"type":"typed-literal","datatype":"http://www.w3.org/2001/XMLSchema#int","value":"5"}], ' +
		'"http://rx4rdf.sf.net/ns/archive#hasContent" : [{"type":"literal","value":" llll","xml:lang":"en-US"}],' +
		' "http://rx4rdf.sf.net/ns/archive#sha1-digest" : [{"type":"literal","value":"ndKxl8RGTmr3u\/omnJxVdGnWgXuA="}],' +
		' "http://www.w3.org/1999/02/22-rdf-syntax-ns#type" : [{"type":"uri","value":"http://rx4rdf.sf.net/ns/archive#Contents"}]}}',
	testId: "urn:sha:ndKxl8RGTmr3uomnJxVdGnWgXuA=",
	testAttr: "http://rx4rdf.sf.net/ns/archive#content-length",
	testValue: 5
};

function run_all_data_rdf_tests() {
	test_data_rdf_empty();
	test_data_rdf_sync();
	test_data_rdf_async();
	test_data_rdf_revert();
	test_data_rdf_save();
}

function test_data_rdf_empty() {
	var rhizomeStore = test_data_rdf_newStore();
	tests.MockXMLHttpRequest.wrap(rhizomeStore, 'find', '{}', 100);
	
	// These are not items
	jum.assertTrue("100", !rhizomeStore.isItem("foo"));
	jum.assertTrue("101", !rhizomeStore.isItem());
	jum.assertTrue("102", !rhizomeStore.isItem(rhizomeStore));
	jum.assertTrue("103", !rhizomeStore.isItem(103));
	
	// find() returns a Result
	
	var oncompleted = function(result) { 
		jum.assertTrue("121", result.length == 0);
		//jum.assertTrue("122", result.inProgress() == false);
	};
	
	var callback = function(item, result) { 
		// always fail if we get called
		jum.assertTrue("130", false);
	};
	
	var result = rhizomeStore.find({
			query: "/*",
			onnext: callback,
			oncompleted: oncompleted
	}) || null;

	jum.assertTrue("120", result != null);
	jum.assertTrue("123", result.store == rhizomeStore);
}

function _load_rdf_data(rhizomeStore, sync, kwArgs) {
	tests.MockXMLHttpRequest.wrap(rhizomeStore, 'find', rdfTestData.testJson, 200);
	
	var args = kwArgs || {};
	args.sync = sync;
	args.query = "/*";
	var result = rhizomeStore.find(args);
	//dojo.debug('result ' + dojo.json.serialize(result) );
	jum.assertTrue("result not null", result);
	return result;
}


function test_data_rdf_sync() {
	_test_rdf_data(true);
}

function test_data_rdf_async() {
	_test_rdf_data(false);
}
	
function _test_rdf_data(sync) {
	var rhizomeStore = test_data_rdf_newStore();

	var numItems = 2;
	var callbackCalled = false;
	var callback = function(result) {
		jum.assertTrue("200", result != null);
		jum.assertTrue("201", result.length == numItems);
	
		jum.assertTrue("212", rhizomeStore.get(rdfTestData.testId, rdfTestData.testAttr) == rdfTestData.testValue);
		//jum.assertTrue("202", result.inProgress() == false);
		jum.assertTrue("203", result.store == rhizomeStore);
		callbackCalled = true;
	};
	
	var forEachCallbackCalled = 0;
	var foreachCallback = function(item, result) {
		jum.assertTrue("210", rhizomeStore.isItem(item) );
		//var identity = rhizomeStore.getIdentity(item);
		//jum.assertTrue("211", identity != null);
		
		//var itemToo = rhizomeStore.getByIdentity(identity);
		//jum.assertTrue("212", item === itemToo);
		
		var attributes = rhizomeStore.getAttributes(item);
		for (var i in attributes) {
			var attribute = attributes[i];
			var value = rhizomeStore.get(item, attribute);
			var values = rhizomeStore.getValues(item, attribute);
			var valueToo = values[0];
			jum.assertTrue("213", value == valueToo);
			jum.assertTrue("214", rhizomeStore.hasAttribute(item, attribute));
			jum.assertTrue("215", rhizomeStore.containsValue(item, attribute, value));
			//dojo.debug(attribute + ": " + value + ' ' + valueToo);
		}
		
		//jum.assertTrue("216", result.inProgress()); 
		forEachCallbackCalled++;
		
		return;
	};

	var result = _load_rdf_data(rhizomeStore, sync, {
		oncompleted : callback,
		onnext : foreachCallback });

	jum.assertTrue('204', sync == callbackCalled);
		
	jum.assertTrue('217', forEachCallbackCalled == (sync ? numItems : 0));
		
	var onlyOnce = 0;
	var anotherCallback = function(item, result) {
		jum.assertTrue("220", onlyOnce == 0);
		onlyOnce++;
		result.abort(); 
	};
	
	var result = _load_rdf_data(rhizomeStore, sync, { 
		onnext : anotherCallback });
	
	if (sync) jum.assertTrue("221", onlyOnce == 1);
	//dojo.debug('onlyonce ' + onlyOnce);
}

function test_data_rdf_revert() {
	var rhizomeStore = test_data_rdf_newStore();
	var testId = rdfTestData.testId;
	var testAttr = rdfTestData.testAttr;
	
	var result = _load_rdf_data(rhizomeStore, true, {}); //sync
	jum.assertTrue('isItem check for ' + testId, rhizomeStore.isItem(testId));
	jum.assertTrue('310',rhizomeStore.get(testId, testAttr) == rdfTestData.testValue);
	jum.assertTrue('311',rhizomeStore.set(testId, testAttr, 2001));
	jum.assertTrue('312',rhizomeStore.get(testId, testAttr) ==	 2001);
	jum.assertTrue('313',rhizomeStore.isDirty() );
	jum.assertTrue('314',rhizomeStore.isDirty(testId) );

	rhizomeStore.revert();

	jum.assertFalse('315',rhizomeStore.isDirty() );
	jum.assertFalse('316',rhizomeStore.isDirty(testId) );

	jum.assertTrue('317',rhizomeStore.get(testId, testAttr) == rdfTestData.testValue);
}

function test_data_rdf_save() {
	var rhizomeStore = test_data_rdf_newStore();
	tests.MockXMLHttpRequest.wrap(rhizomeStore, 'save', function(xhr) { 
		//dojo.debug(xhr.data); 
		return xhr.data;
		}, 100); 
	var testId = rdfTestData.testId;
	var testAttr = rdfTestData.testAttr;
	
	var result = _load_rdf_data(rhizomeStore, true, {}); //sync
	jum.assertTrue('isItem check for ' + testId, rhizomeStore.isItem(testId));
	jum.assertTrue('301',rhizomeStore.get(testId, testAttr) == rdfTestData.testValue);
	jum.assertTrue('302',rhizomeStore.set(testId, testAttr, 2001));
	jum.assertTrue('303',rhizomeStore.get(testId, testAttr) ==	 2001);

	jum.assertTrue('304',rhizomeStore.isDirty() );
	jum.assertTrue('305',rhizomeStore.isDirty(testId) );

	 var result = rhizomeStore.save({sync : true} ); 

	jum.assertFalse('306', rhizomeStore.isDirty() );
	jum.assertFalse('307', rhizomeStore.isDirty(testId) );

	jum.assertTrue('308', rhizomeStore.get(testId, testAttr) == 2001);
}
