/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.logging.Logger");

function test_logging_defaultInstalledHandler(){
	jum.assertTrue((dojo.logging.logQueueHandler instanceof dojo.logging.MemoryLogHandler));
	jum.assertEquals("object", (typeof dojo.logging.logQueueHandler.data));
	jum.assertTrue((dojo.logging.logQueueHandler instanceof dojo.logging.MemoryLogHandler));
	jum.assertTrue((dojo.logging.logQueueHandler.data instanceof Array));
	
	dojo.log.debug("dojo.log.debug() working correctly");
	
	jum.assertTrue((dojo.logging.logQueueHandler.data.length >= 1));
}

function test_logging_debug(){
	var msg = "dojo.log.debug() working correctly";
	dojo.log.debug(msg);
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message);
}

function test_logging_info(){
	var msg = "dojo.log.info() working correctly";
	dojo.log.info(msg);
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message);
}

function test_logging_warn(){
	var msg = "dojo.log.warn() working correctly";
	dojo.log.warn(msg);
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message);
}

function test_logging_err(){
	var msg = "dojo.log.err() working correctly";
	dojo.log.err(msg);
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message);
}

function test_logging_err(){
	var msg = "dojo.log.crit() working correctly";
	dojo.log.crit(msg);
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message);
}

function test_logging_exception(){
	var msg = "dojo.log.exception() working correctly";
	try{
		dojo.raise("a synthetic exception");
	}catch(e){
		// catch and squelch
		dojo.log.exception(msg, e, true);
	}
	var last = dojo.logging.logQueueHandler.data.pop();
	jum.assertEquals(msg, last.message.substr(0, msg.length));
}

function test_logging_log(){
	/*
	for(var x in dojo.logging){
		print(x);
	}
	print(dojo.logging.log.debug);
	*/
	// dojo.logging.log.debug("WTF?");
}
