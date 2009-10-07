/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.collections.Store");
dojo.require("dojo.logging.Logger");

function test_simple_getters(){
	var data=[
		{Id:1, val1:"testval", simpleNum:1.2, getName:function(){return "Bob Smith";}},
		{Id:2, val1:null, simpleNum:56, getName:function(){return "Jane";}},
		{Id:3, val1:"value", simpleNum:1, getName:function(){return "Bam bam";}, nested:{name:"value"}}
	];
	
	var store=new dojo.collections.Store(data);
	
	jum.assertTrue("store data length", store.getData().length == 3);
	jum.assertEquals("store getByKey", store.getByKey(1)["src"], data[0]);
	jum.assertEquals("store dataByKey", store.getDataByKey("3"), data[2]);
}

function test_nullexpression_values(){
	var data=[
		{Id:1, val1:"testval", simpleNum:1.2, getName:function(){return "Bob Smith";}},
		{Id:2, val1:null, simpleNum:56, getName:function(){return "Jane";}},
		{Id:3, val1:"value", simpleNum:1, getName:function(){return "Bam bam";}, nested:{name:"value"}}
	];
	
	var store=new dojo.collections.Store(data);
	
	jum.assertEquals("getFunctionValue", store.getField(data[2], "nested.name"), "value");
	jum.assertEquals("getNullField", store.getField(data[1], "val1"), null);
	
	jum.assertEquals("store null expr ref", store.getField(data[0], "val1.missing"), null);
	
	try {
		store.getField(data[0], "val1.getMissing()");
	} catch (e) { jum.assertTrue(e instanceof Error);return;}
	throw new JUMAssertFailure("Previous store.getField test should have failed.");
}

function test_null_field_values(){
	var data=[
		{Id:2, val1:null, simpleNum:56, getName:function(){return "Jane";}}
	];
	
	var store=new dojo.collections.Store(data);
	jum.assertEquals("store null value", null, store.getField(data[0], "val1"));
}
