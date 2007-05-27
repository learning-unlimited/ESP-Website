/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

import DojoExternalInterface;

class HelloWorld{
	public function HelloWorld(){
		DojoExternalInterface.initialize();
		DojoExternalInterface.addCallback("sayHello", this, sayHello);
		DojoExternalInterface.loaded();
	}
	
	public function sayHello(msg){
		return "FLASH: Message received from JavaScript was: " + msg;
	}
	
	static function main(mc){
		//getURL("javascript:dojo.debug('FLASH:main method of flash')");
		_root.helloWorld = new HelloWorld();
	}
}
