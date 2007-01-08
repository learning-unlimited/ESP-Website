/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.lang.type");


function test_lang_isNumeric() {
	var number365 = new Number(365);
	var numberFoo = new Number("foo");
	var string365 = new String("365");
	var stringFoo = new String("foo");
	var booleanFalse = new Boolean(false);
	var error = new Error();
	var undef; // undefined

	jum.assertTrue("100", dojo.lang.isNumeric(12345));
	jum.assertTrue("101", dojo.lang.isNumeric("12345"));
	jum.assertTrue("102", dojo.lang.isNumeric(number365));
	jum.assertTrue("103", dojo.lang.isNumeric(string365));

	jum.assertFalse("110", dojo.lang.isNumeric(3/0));
	jum.assertFalse("111", dojo.lang.isNumeric("foo"));
	jum.assertFalse("112", dojo.lang.isNumeric(numberFoo));
	jum.assertFalse("113", dojo.lang.isNumeric(false));
	jum.assertFalse("114", dojo.lang.isNumeric(true));
	jum.assertFalse("115", dojo.lang.isNumeric(stringFoo));
	jum.assertFalse("116", dojo.lang.isNumeric(null));
	jum.assertFalse("117", dojo.lang.isNumeric(undef));
	jum.assertFalse("118", dojo.lang.isNumeric([]));
	jum.assertFalse("119", dojo.lang.isNumeric(error));
	jum.assertFalse("120", dojo.lang.isNumeric(""));
	jum.assertFalse("121", dojo.lang.isNumeric("  "));
}

function test_lang_isPureObject() {
	var undef; // undefined

	jum.assertTrue("130", dojo.lang.isPureObject(new Object()));
	jum.assertTrue("131", dojo.lang.isPureObject({a: 1, b: 2}));

	jum.assertFalse("141", dojo.lang.isPureObject([1, 2]));
	jum.assertFalse("142", dojo.lang.isPureObject(new Number(365)));
	jum.assertFalse("143", dojo.lang.isPureObject(new String("foo")));
	jum.assertFalse("144", dojo.lang.isPureObject(test_lang_isPureObject));
	jum.assertFalse("145", dojo.lang.isPureObject(new Boolean(true)));
	jum.assertFalse("146", dojo.lang.isPureObject(365));
	jum.assertFalse("147", dojo.lang.isPureObject("foo"));
	jum.assertFalse("148", dojo.lang.isPureObject(true));
	jum.assertFalse("149", dojo.lang.isPureObject(null));
	jum.assertFalse("140", dojo.lang.isPureObject(undef));
	jum.assertFalse("141", dojo.lang.isPureObject(new Error()));
}

function test_lang_isOfType() {
	var number365 = new Number(365);
	var stringFoo = new String("foo");
	var booleanFalse = new Boolean(false);
	var undef; // undefined

	jum.assertTrue("200", dojo.lang.isOfType("foo", String));
	jum.assertTrue("201", dojo.lang.isOfType(12345, Number));
	jum.assertTrue("202", dojo.lang.isOfType(false, Boolean));
	jum.assertTrue("203", dojo.lang.isOfType([6, 8], Array));
	jum.assertTrue("204", dojo.lang.isOfType(dojo.lang.isOfType, Function));
	jum.assertTrue("205", dojo.lang.isOfType({foo: "bar"}, Object));
	jum.assertTrue("206", dojo.lang.isOfType(new Date(), Date));
	jum.assertTrue("207", dojo.lang.isOfType(number365, Number));
	jum.assertTrue("208", dojo.lang.isOfType(stringFoo, String));
	jum.assertTrue("209", dojo.lang.isOfType(booleanFalse, Boolean));

	jum.assertTrue("210", dojo.lang.isOfType("foo", "string"));
	jum.assertTrue("211", dojo.lang.isOfType(12345, "number"));
	jum.assertTrue("212", dojo.lang.isOfType(false, "boolean"));
	jum.assertTrue("213", dojo.lang.isOfType([6, 8], "array"));
	jum.assertTrue("214", dojo.lang.isOfType(dojo.lang.isOfType, "function"));
	jum.assertTrue("215", dojo.lang.isOfType({foo: "bar"}, "object"));
	jum.assertTrue("216", dojo.lang.isOfType(undef, "undefined"));
	jum.assertTrue("217", dojo.lang.isOfType(number365, "number"));
	jum.assertTrue("218", dojo.lang.isOfType(stringFoo, "string"));
	jum.assertTrue("219", dojo.lang.isOfType(booleanFalse, "boolean"));

	jum.assertTrue("220", dojo.lang.isOfType("foo", [Number, String, Boolean]));
	jum.assertTrue("221", dojo.lang.isOfType(12345, [Number, String, Boolean]));
	jum.assertTrue("222", dojo.lang.isOfType(false, [Number, String, Boolean]));

	jum.assertTrue("223", dojo.lang.isOfType("foo", ["number", String, "boolean"]));
	jum.assertTrue("224", dojo.lang.isOfType(12345, ["number", String, Boolean]));
	jum.assertTrue("225", dojo.lang.isOfType(false, ["number", "string", "boolean"]));

	jum.assertTrue("226", dojo.lang.isOfType(undef, ["number", "undefined"]));
	jum.assertTrue("227", dojo.lang.isOfType(undef, "number", {optional: true}));
	jum.assertTrue("228", dojo.lang.isOfType(12345, "number", {optional: true}));

	jum.assertFalse("230", dojo.lang.isOfType(undef, String));
	jum.assertFalse("231", dojo.lang.isOfType(undef, Number));
	jum.assertFalse("232", dojo.lang.isOfType(undef, [Boolean]));
	jum.assertFalse("233", dojo.lang.isOfType(undef, Array));
	jum.assertFalse("234", dojo.lang.isOfType(undef, Function));
	jum.assertFalse("235", dojo.lang.isOfType(undef, Object));
	jum.assertFalse("236", dojo.lang.isOfType(undef, Date));
	jum.assertFalse("237", dojo.lang.isOfType(undef, [String, Number, Boolean]));
	jum.assertFalse("238", dojo.lang.isOfType(undef, "string"));
	jum.assertFalse("239", dojo.lang.isOfType(undef, ["string", "number"]));

	jum.assertFalse("240", dojo.lang.isOfType(12345, String));
	jum.assertFalse("241", dojo.lang.isOfType("foo", "numeric"));
	jum.assertFalse("242", dojo.lang.isOfType(12345, Boolean));
	jum.assertFalse("243", dojo.lang.isOfType(false, [Array]));
	jum.assertFalse("244", dojo.lang.isOfType(new Date(), Function));
	jum.assertFalse("245", dojo.lang.isOfType("foo", Object));
	jum.assertFalse("246", dojo.lang.isOfType([6, 8], Date));
	jum.assertFalse("247", dojo.lang.isOfType([6, 8], [String, Number, Boolean]));
	jum.assertFalse("248", dojo.lang.isOfType(12345, "string"));
	jum.assertFalse("249", dojo.lang.isOfType(true, "string"));
	jum.assertFalse("250", dojo.lang.isOfType({foo: "bar"}, ["string", "number"]));
	jum.assertFalse("251", dojo.lang.isOfType(number365, "pureobject"));
	jum.assertFalse("252", dojo.lang.isOfType(stringFoo, "pureobject"));
	jum.assertFalse("253", dojo.lang.isOfType(booleanFalse, "pureobject"));
	jum.assertFalse("254", dojo.lang.isOfType([], "numeric"));

	// dojo.log.debug("leaving test_lang_isOfType()");
}

function test_lang_isOfTypeToo() {
	var allTypes = [
		String, Number, Boolean, Array, Function, Object, null,
		"string", "number", "boolean", "array", "function", "object", "null",
		"numeric", "pureobject", "undefined", Date, Error];
	var number365 = new Number(365);
	var string365 = new String("365");
	var numberFoo = new Number("foo");
	var stringFoo = new String("foo");
	var booleanTrue = new Boolean(true);
	var booleanFalse = new Boolean(false);
	var error = new Error();
	var IggyClass = function() {};
	IggyClass.prototype.valueOf = function() { return 3; };
	var obj = {a: 1, b: 2}; // obj.undef is undefined
	var iggyInstace = new IggyClass();

	var examples = [
		{value: "foo",             types: [String, "string"]},
		{value: stringFoo,         types: [String, "string", Object, "object"]},
		{value: numberFoo,         types: [Number, "number", Object, "object"]},
		{value: number365,         types: [Number, "number", "numeric", Object, "object"]},
		{value: 365,               types: [Number, "number", "numeric"]},
		{value: "365",             types: [String, "string", "numeric"]},
		{value: string365,         types: [String, "string", "numeric", Object, "object"]},
		{value: true,              types: [Boolean, "boolean"]},
		{value: false,             types: [Boolean, "boolean"]},
		{value: booleanTrue,       types: [Boolean, "boolean", Object, "object"]},
		{value: booleanFalse,      types: [Boolean, "boolean", Object, "object"]},
		{value: [],                types: [Array, "array", Object, "object"]},
		{value: [1, 2, obj],       types: [Array, "array", Object, "object"]},
		{value: dojo.lang.indexOf, types: [Function, "function", Object, "object"]},
		{value: parseInt,          types: [Function, "function", Object, "object"]},
		{value: Math.sin,          types: [Function, "function", Object, "object"]},
		{value: obj,               types: [Object, "object", "pureobject"]},
		{value: dojo.lang,         types: [Object, "object", "pureobject"]},
		{value: Math,              types: [Object, "object", "pureobject"]},
		{value: null,              types: [null, "null", Object, "object"]},
		{value: error,             types: [Error, Object, "object"]},
		{value: obj.undef,         types: ["undefined"]},
		{value: iggyInstace,       types: [Object, "object", "numeric"]}
	];
	
	for (var i in examples) {
		var example = examples[i];
		var value = example.value;
		var matchingTypes = example.types;
		
		var getTypeResult = dojo.lang.getType(value);
		jum.assertTrue("300: " + i, dojo.lang.isOfType(value, getTypeResult));
		
		for (var j in matchingTypes) {
			var matchingType = matchingTypes[j];
			jum.assertTrue("301", dojo.lang.isOfType(value, matchingType));
			jum.assertTrue("302", dojo.lang.isOfType(value, [Number, matchingType, String]));
			jum.assertTrue("303", dojo.lang.isOfType(value, matchingType, {optional: true}));
			jum.assertTrue("304", dojo.lang.isOfType(null, matchingType, {optional: true}));
			jum.assertTrue("305", dojo.lang.isOfType(obj.undef, matchingType, {optional: true}));
		}
		for (var k in allTypes) {
			var possibleType = allTypes[k];
			if (!dojo.lang.inArray(matchingTypes, possibleType)) {
				var nonMatchingType = possibleType;
				jum.assertFalse("310:" + i + " " + k, dojo.lang.isOfType(value, nonMatchingType));
			}
		}
	}
	
	
	// dojo.log.debug("leaving test_lang_isOfTypeToo()");
}

function test_lang_type(){
	jum.assertEquals("dojo.lang.getObject", dojo.lang.getObject, dojo.lang.getObject("dojo.lang.getObject")); 
	jum.assertEquals("dojo.lang.doesObjectExist", true, dojo.lang.doesObjectExist("dojo.lang.doesObjectExist"));
}
