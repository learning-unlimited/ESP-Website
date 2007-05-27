/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.crypto.Blowfish");

function test_Blowfish_encryption(){
	var message = "The rain in Spain falls mainly on the plain.";
	var key = "foobar";
	var base64Encrypted = "WI5J5BPPVBuiTniVcl7KlIyNMmCosmKTU6a/ueyQuoUXyC5dERzwwdzfFsiU4vBw";
	result = dojo.crypto.Blowfish.encrypt(message, key);
	jum.assertEquals("BlowfishEncryption", base64Encrypted, result);
}

function test_Blowfish_decryption(){
	var message = "The rain in Spain falls mainly on the plain.";
	var key = "foobar";
	var base64Encrypted = "WI5J5BPPVBuiTniVcl7KlIyNMmCosmKTU6a/ueyQuoUXyC5dERzwwdzfFsiU4vBw";

	result = dojo.crypto.Blowfish.decrypt(base64Encrypted, key);
	jum.assertEquals("BlowfishDecryption", message, result);
}
