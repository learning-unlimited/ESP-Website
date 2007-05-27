/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.registerModulePath("tests", "tests");
dojo.require("tests.MockXMLHttpRequest");
dojo.require("dojo.data.core.RemoteStore");
dojo.require("dojo.lang.type");

function _test_data_core_newStore() {
	return new dojo.data.core.RemoteStore({ queryUrl : "http://ignored/?query=", saveUrl : "http://ignored/save" });
}

function run_all_tests() {
	test_data_core_empty();
	test_data_core_movies_sync();
	test_data_core_movies_async();
	test_data_core_movies_revert();
	test_data_core_movies_save();
}

function test_data_core_empty() {
	var remoteStore = _test_data_core_newStore();
	tests.MockXMLHttpRequest.wrap(remoteStore, 'find','{}', 100);

	// These are not items
	jum.assertTrue("100", !remoteStore.isItem("foo"));
	jum.assertTrue("101", !remoteStore.isItem());
	jum.assertTrue("102", !remoteStore.isItem(remoteStore));
	jum.assertTrue("103", !remoteStore.isItem(103));
	
	// find() returns a Result
	var oncompleted = function(result) { 
		jum.assertTrue("121", result.length == 0);
		//jum.assertTrue("122", result.inProgress() == false); 
	};
	
	var callback = function(item, result) { 
		// always fail if we get called
		jum.assertTrue("130", false);
	};
	
	var result = remoteStore.find({}, {
		onnext : callback,
		oncompleted : oncompleted
		}) || null;
	
	jum.assertTrue("120", result != null);
	jum.assertTrue("123", result.store == remoteStore);	
}

function _test_data_core_load_movies(remoteStore, sync, kwArgs) {
	var dataString = '{ "data" : { "1" :{ "Title": ["City of God"],	 "Year" : [2002], "Producer" : ["Katia Lund"] }, "2" :{ "Title" : ["Rain"], "Year" : [2001],	"Producer" : ["Christine Jeffs"] } } }';
	tests.MockXMLHttpRequest.wrap(remoteStore, 'find', dataString, 200);
		
	var args = kwArgs || {};
	args.sync = sync;
	args.query = '*';
	var result = remoteStore.find(args) || null;
	return result;	  
}

function test_data_core_movies_sync() {
	_test_data_core_movies(true);
}

function test_data_core_movies_async() {
	_test_data_core_movies(false);
}

function _test_data_core_movies(sync) {
	var remoteStore = _test_data_core_newStore();
	var numItems = 2;
	var callbackCalled = false;
	var callback = function(result)	 {  
		jum.assertTrue("200", result != null);
		jum.assertTrue("201 " + result.length, result.length == numItems);
		//jum.assertTrue("202", result.inProgress() == false);
		jum.assertTrue("203", result.store == remoteStore);
		callbackCalled = true;
	};
	
	var forEachCallbackCalled = 0;
	var foreachCallback = function(item, result) {
		jum.assertTrue("210", remoteStore.isItem(item) );
		//var identity = remoteStore.getIdentity(item);
		//jum.assertTrue("211", identity != null);
		
		//var itemToo = remoteStore.getByIdentity(identity);
		//jum.assertTrue("212", item === itemToo);
		jum.assertTrue("212", remoteStore.get('1', 'Year') == 2002);
		
		var attributes = remoteStore.getAttributes(item);
		for (var i in attributes) {
			var attribute = attributes[i];
			var value = remoteStore.get(item, attribute);
			var values = remoteStore.getValues(item, attribute);
			var valueToo = values[0];
			jum.assertTrue("213", value == valueToo);
			jum.assertTrue("214", remoteStore.hasAttribute(item, attribute));	
			jum.assertTrue("215", remoteStore.containsValue(item, attribute, value));
			// dojo.debug(attribute + ": " + value);
		}
		
		//jum.assertTrue("216", result.inProgress()); 
		forEachCallbackCalled++;
	};

	var result = _test_data_core_load_movies(remoteStore, sync, 
					{ oncompleted : callback,
					  onnext : foreachCallback });

	jum.assertTrue('204 ' + sync + ' ' + callbackCalled, sync == callbackCalled);
	
	jum.assertTrue('217 ' + sync, forEachCallbackCalled == (sync ? numItems : 0));
	
	var onlyOnce = 0;
	var anotherCallback = function(item, result) {
		jum.assertTrue("220 " + sync, onlyOnce == 0);
		onlyOnce++;
		result.abort();
	};
	
	var result = _test_data_core_load_movies(remoteStore, sync, 
				{ onnext : anotherCallback });
	
	if (sync) jum.assertTrue("221 " + sync, onlyOnce == 1);
	//dojo.debug('onlyonce ' + onlyOnce);
}

function test_data_core_movies_revert() {
	var remoteStore = _test_data_core_newStore();
	var result = _test_data_core_load_movies(remoteStore, true, {}); //sync
	jum.assertTrue(remoteStore.get('1', 'Year') == 2002);
	jum.assertTrue(remoteStore.set('1', 'Year',	 2001));
	jum.assertTrue(remoteStore.get('1', 'Year') ==	2001);
	jum.assertTrue(remoteStore.isDirty() );
	jum.assertTrue(remoteStore.isDirty('1') );

	remoteStore.revert();

	jum.assertFalse(remoteStore.isDirty() );
	jum.assertFalse(remoteStore.isDirty('1') );

	jum.assertTrue(remoteStore.get('1', 'Year') == 2002);
}

function test_data_core_movies_save() {
	var remoteStore = _test_data_core_newStore();
	tests.MockXMLHttpRequest.wrap(remoteStore, 'save', "save succeded", 100);	

	var result = _test_data_core_load_movies(remoteStore, true, {}); //sync
	jum.assertTrue(remoteStore.get('1', 'Year') == 2002);
	jum.assertTrue(remoteStore.set('1', 'Year',	 2001));
	jum.assertTrue(remoteStore.get('1', 'Year') ==	2001);

	jum.assertTrue(remoteStore.isDirty() );
	jum.assertTrue(remoteStore.isDirty('1') );

	var result = remoteStore.save({sync : true} ); 

	jum.assertFalse('306', remoteStore.isDirty() );
	jum.assertFalse('307', remoteStore.isDirty('1') );
			
	jum.assertTrue('308', remoteStore.get('1', 'Year') == 2001);
}
