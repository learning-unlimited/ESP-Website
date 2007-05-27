/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

function test_hostenv_getText () {
	if (dojo.hostenv.getName() == "browser") {
		var text;
		
		// first test
		text = dojo.hostenv.getText('test_hostenv_browser.js');
		var numberOfCharactersInThisFile = 100; 
		jum.assertTrue("10", (typeof text == "string"));
		jum.assertTrue("11", (text.length > numberOfCharactersInThisFile));
		
		// second test
		var exceptionCaught = false;
		try {
			text = dojo.hostenv.getText('this_file_does_not_exist.txt');
		} catch (e) {
			exceptionCaught = true;
		}
		jum.assertTrue("12", exceptionCaught);
		
		// third test
		exceptionCaught = false;
		try {
			var callbackFunction = null;
			var fail_ok = true;
			text = dojo.hostenv.getText('this_file_does_not_exist.txt', callbackFunction, fail_ok);
		} catch (e) {
			exceptionCaught = true;
		}
		jum.assertTrue("13", !exceptionCaught);	
		jum.assertTrue("14", (text === null));
	}
}

