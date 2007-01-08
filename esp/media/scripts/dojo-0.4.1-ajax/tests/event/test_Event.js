/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.event.*");

function testObjectClass(){
	this.funcCallCount = 0;
	this.lastReturn =  null;
	this.secondLastReturn = null;

	this.func1 = function(arg1, arg2){
		this.funcCallCount++;
		this.secondLastReturn = this.lastReturn;
		this.lastReturn = "func1, arg1: "+arg1+", arg2: "+arg2;
		jum.debug(this.lastReturn);
		return this.lastReturn;
	}

	this.func2 = function(arg1, arg2){
		this.funcCallCount++;
		this.secondLastReturn = this.lastReturn;
		this.lastReturn = "func2, arg1: "+arg1+", arg2: "+arg2;
		jum.debug(this.lastReturn);
		return this.lastReturn;
	}

	this.argSwapAroundAdvice =  function(miObj){
		// dojo.hostenv.println("in adviceFromFunc1ToFunc2");
		var tmp = miObj.args[1];
		miObj.args[1] = miObj.args[0];
		miObj.args[0] = tmp;
		// dojo.hostenv.println(miObj.args.length);

		// return obj[funcName].apply(obj, argsArr);
		ret = miObj.proceed();
		return ret;
	}
}

function test_event_callPrecedence(){
	// from bug #70
	var obj1 = new testObjectClass();
	obj1.ctr = 0;
	obj1.increment = function(){ this.ctr++; }
	dojo.event.connect(obj1, "func1", function(){
		obj1.increment();
		dojo.event.connect(obj1, "func1", obj1, "increment");
	});
	obj1.func1();
	jum.assertEquals("test", obj1.ctr, 1);
}

function test_event_beforeAround(){
	var obj1 = new testObjectClass();

	dojo.event.connect("before", obj1, "func1", obj1, "func2", obj1, "argSwapAroundAdvice");

	jum.assertTrue("test1", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test2", obj1.secondLastReturn, "func2, arg1: 2, arg2: 1");
	jum.assertEquals("test3", obj1.lastReturn, "func1, arg1: 1, arg2: 2");
}

function test_event_before(){
	var obj1 = new testObjectClass();

	dojo.event.connect("before", obj1, "func1", obj1, "func2");

	jum.assertTrue("test4", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	// we expected func2 to fire before func1 and neither to mangle arguments
	jum.assertEquals("test5", obj1.secondLastReturn, "func2, arg1: 1, arg2: 2");
	// so the most recent return should be from func1
	jum.assertEquals("test6", obj1.lastReturn, "func1, arg1: 1, arg2: 2");
}

function test_event_connectBefore(){
	var obj1 = new testObjectClass();
	var obj2 = new testObjectClass();

	dj_global._testConnectBeforeFunc = function(arg1, arg2){
		obj2.funcCallCount++;
		obj2.secondLastReturn = obj2.lastReturn;
		obj2.lastReturn = "func1, arg1: "+arg1+", arg2: "+arg2;
		return obj2.lastReturn;
	}

	dojo.event.connectBefore(obj1, "func1", obj1, "func2");

	jum.assertTrue("test7", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	// we expected func2 to fire before func1 and neither to mangle arguments
	jum.assertEquals("test8", obj1.secondLastReturn, "func2, arg1: 1, arg2: 2");
	// so the most recent return should be from func1
	jum.assertEquals("test9", obj1.lastReturn, "func1, arg1: 1, arg2: 2");

	dojo.event.connectBefore("_testConnectBeforeFunc", obj2, "func2");
	jum.assertTrue("test10", _testConnectBeforeFunc("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test11", obj2.funcCallCount, 2);
}

function test_event_afterAround(){
	var obj1 = new testObjectClass();

	dojo.event.connect("after", obj1, "func1", obj1, "func2", obj1, "argSwapAroundAdvice");

	jum.assertTrue("test7", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test8", obj1.lastReturn, "func2, arg1: 2, arg2: 1");
	jum.assertEquals("test9", obj1.secondLastReturn, "func1, arg1: 1, arg2: 2");
}

function test_event_after(){
	var obj1 = new testObjectClass();

	dojo.event.connect("after", obj1, "func1", obj1, "func2");

	jum.assertTrue("test10", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test11", obj1.secondLastReturn, "func1, arg1: 1, arg2: 2");
	jum.assertEquals("test12", obj1.lastReturn, "func2, arg1: 1, arg2: 2");
}

function test_event_around(){
	var obj1 = new testObjectClass();
	dojo.event.connect("around", obj1, "func1", obj1, "argSwapAroundAdvice");
	jum.assertTrue("test13", obj1.func1("1", "2")=="func1, arg1: 2, arg2: 1");
	jum.assertEquals("test14", obj1.lastReturn, "func1, arg1: 2, arg2: 1");
	jum.assertEquals("test15", obj1.secondLastReturn, null);
}

function test_event_connectAround(){
	var obj1 = new testObjectClass();

	dojo.event.connectAround(obj1, "func1", obj1, "argSwapAroundAdvice");

	jum.assertTrue("test13", obj1.func1("1", "2")=="func1, arg1: 2, arg2: 1");
	jum.assertEquals("test14", obj1.lastReturn, "func1, arg1: 2, arg2: 1");
	jum.assertEquals("test15", obj1.secondLastReturn, null);
}

function test_event_kwConnect(){
	var obj1 = new testObjectClass();

	// test to see if "after" gets set as the default type
	dojo.event.kwConnect({
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func2"
	});

	jum.assertTrue("test16", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test17", obj1.secondLastReturn, "func1, arg1: 1, arg2: 2");
	jum.assertEquals("test18", obj1.lastReturn, "func2, arg1: 1, arg2: 2");
}

function test_event_connectOnce(){
	var obj1 = new testObjectClass();

	// connect once via kwConnect()
	dojo.event.kwConnect({
		once: true,
		type: "after",
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func2"
	});

	// and then through connect()
	dojo.event.connect("after", obj1, "func1", obj1, "func2", null, null, true);

	jum.assertTrue("test19", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test20", obj1.funcCallCount, 2);
}

function test_event_disconnect(){
	var obj1 = new testObjectClass();

	dojo.event.connect("after", obj1, "func1", obj1, "func2");
	dojo.event.disconnect("after", obj1, "func1", obj1, "func2");


	jum.assertTrue("test21", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test22", obj1.funcCallCount, 1);
	jum.assertEquals("test23", obj1.secondLastReturn, null);
}

function test_event_disconnectOnce(){
	var obj1 = new testObjectClass();

	dojo.event.connect("after", obj1, "func1", obj1, "func2");
	dojo.event.connect("after", obj1, "func1", obj1, "func2");
	dojo.event.disconnect("after", obj1, "func1", obj1, "func2", null, null, true);


	jum.assertTrue("test24", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test25", obj1.funcCallCount, 2);
	jum.assertTrue("test26", obj1.secondLastReturn != null);
}

function test_event_kwDisconnect(){
	var obj1 = new testObjectClass();

	// dojo.event.connect("after", obj1, "func1", obj1, "func2");
	dojo.event.kwConnect({
		type: "after",
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func2"
	});

	dojo.event.kwDisconnect({
		type: "after",
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func2"
	});


	jum.assertTrue("test27", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test28", obj1.funcCallCount, 1);
	jum.assertEquals("test29", obj1.secondLastReturn, null);
}

function test_event_kwDisconnectOnce(){
	var obj1 = new testObjectClass();

	dojo.event.connect("after", obj1, "func1", obj1, "func2");
	dojo.event.connect("after", obj1, "func1", obj1, "func2");

	dojo.event.kwDisconnect({
		type: "after",
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func2",
		once: true
	});


	jum.assertTrue("test30", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test31", obj1.funcCallCount, 2);
}

function test_event_implicitAfter(){
	var obj1 = new testObjectClass();

	dojo.event.connect(obj1, "func1", obj1, "func2");
	jum.assertTrue("test32", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test33", obj1.funcCallCount, 2);
	jum.assertEquals("test34", obj1.secondLastReturn, "func1, arg1: 1, arg2: 2");
}

function test_event_anonymous(){
	var obj1 = new testObjectClass();

	dojo.event.connect(obj1, "func1", function(){
		obj1.funcCallCount++;
	});
	obj1.func1("1", "2");
	jum.assertEquals("test35", 2, obj1.funcCallCount);
}

function test_event_adviceMsg(){
	var obj1 = new testObjectClass();

	obj1.func3 = function(kwa){
		this.argsLen = arguments.length;
		this.miArgsLen = kwa.args.length;
		this.srcObj = kwa.object;
	}

	dojo.event.kwConnect({
		type: "after",
		srcObj: obj1, 
		srcFunc: "func1", 
		adviceObj: obj1, 
		adviceFunc: "func3",
		adviceMsg: true
	});

	obj1.func1("1", "2", "3", "4", "5");
	jum.assertEquals("test36", 1, obj1.argsLen);
	jum.assertEquals("test37", 5, obj1.miArgsLen);
	jum.assertEquals("test38", obj1, obj1.srcObj);

	var obj2 = {
		foo: function(){
		}
	};

	var obj3 = {
		bar: function(mi){
			this.srcObj = mi.object;
		}
	};

	dojo.event.kwConnect({
		srcObj: obj2, 
		srcFunc: "foo", 
		adviceObj: obj3, 
		adviceFunc: "bar",
		adviceMsg: true
	});

	obj2.foo();
	jum.assertTrue("test39", obj2 === obj3.srcObj);
}

function test_event_disconnectFP(){
	var obj1 = new testObjectClass();

	dojo.event.connect(obj1, "func1", obj1, obj1.func2);
	dojo.event.disconnect(obj1, "func1", obj1, obj1.func2);

	jum.assertTrue("test40", obj1.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test41", obj1.funcCallCount, 1);

	var obj2 = new testObjectClass();
	dojo.event.connect("after", obj2, obj2.func1, obj2, obj2.func2);
	dojo.event.disconnect("after", obj2, obj2.func1, obj2, obj2.func2);

	jum.assertTrue("test42", obj2.func1("1", "2")=="func1, arg1: 1, arg2: 2");
	jum.assertEquals("test43", obj2.funcCallCount, 1);
}

