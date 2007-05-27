/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.validate.creditCard");

function test_validate_isValidLuhn(){
	jum.assertTrue(dojo.validate.isValidLuhn('5105105105105100')); //test string input
	jum.assertTrue(dojo.validate.isValidLuhn('5105-1051 0510-5100')); //test string input with dashes and spaces (commonly used when entering card #'s)
	jum.assertTrue(dojo.validate.isValidLuhn(38520000023237)); //test numerical input as well
	jum.assertFalse(dojo.validate.isValidLuhn(3852000002323)); //testing failures
	jum.assertTrue(dojo.validate.isValidLuhn(18)); //length doesnt matter
	jum.assertFalse(dojo.validate.isValidLuhn(818181)); //short length failure
}

function test_validate_isValidCvv(){
	jum.assertTrue(dojo.validate.isValidCvv('123','mc')); //string is ok
	jum.assertFalse(dojo.validate.isValidCvv('5AA','ec')); //invalid characters are not ok
	jum.assertTrue(dojo.validate.isValidCvv(723,'mc')); //numbers are ok too
	jum.assertFalse(dojo.validate.isValidCvv(7234,'mc')); //too long
	jum.assertTrue(dojo.validate.isValidCvv(612,'ec'));
	jum.assertTrue(dojo.validate.isValidCvv(421,'vi'));
	jum.assertTrue(dojo.validate.isValidCvv(543,'di'));
	jum.assertTrue(dojo.validate.isValidCvv('1234','ax')); 
	jum.assertTrue(dojo.validate.isValidCvv(4321,'ax'));
	jum.assertFalse(dojo.validate.isValidCvv(43215,'ax')); //too long
	jum.assertFalse(dojo.validate.isValidCvv(215,'ax')); //too short
}

function test_validate_isValidCreditCard(){
	//misc checks
	jum.assertTrue("test1", dojo.validate.isValidCreditCard('5105105105105100','mc')); //test string input
	jum.assertTrue("test2", dojo.validate.isValidCreditCard('5105-1051 0510-5100','mc')); //test string input with dashes and spaces (commonly used when entering card #'s)
	jum.assertTrue("test3", dojo.validate.isValidCreditCard(5105105105105100,'mc')); //test numerical input as well
	jum.assertFalse("test4", dojo.validate.isValidCreditCard('5105105105105100','vi')); //fails, wrong card type
	//Mastercard/Eurocard checks
	jum.assertTrue("test5", dojo.validate.isValidCreditCard('5105105105105100','mc'));
	jum.assertTrue("test6", dojo.validate.isValidCreditCard('5204105105105100','ec'));
	jum.assertTrue("test7", dojo.validate.isValidCreditCard('5303105105105100','mc'));
	jum.assertTrue("test8", dojo.validate.isValidCreditCard('5402105105105100','ec'));
	jum.assertTrue("test9", dojo.validate.isValidCreditCard('5501105105105100','mc'));
	//Visa card checks
	jum.assertTrue("test10", dojo.validate.isValidCreditCard('4111111111111111','vi'));
	jum.assertTrue("test11", dojo.validate.isValidCreditCard('4111111111010','vi'));
	//American Express card checks
	jum.assertTrue("test12", dojo.validate.isValidCreditCard('378 2822 4631 0005','ax'));
	jum.assertTrue("test13", dojo.validate.isValidCreditCard('341-1111-1111-1111','ax'));
	//Diners Club/Carte Blanch card checks
	jum.assertTrue("test14", dojo.validate.isValidCreditCard('36400000000000','dc'));
	jum.assertTrue("test15", dojo.validate.isValidCreditCard('38520000023237','bl'));
	jum.assertTrue("test16", dojo.validate.isValidCreditCard('30009009025904','dc'));
	jum.assertTrue("test17", dojo.validate.isValidCreditCard('30108009025904','bl'));
	jum.assertTrue("test18", dojo.validate.isValidCreditCard('30207009025904','dc'));
	jum.assertTrue("test19", dojo.validate.isValidCreditCard('30306009025904','bl'));
	jum.assertTrue("test20", dojo.validate.isValidCreditCard('30405009025904','dc'));
	jum.assertTrue("test21", dojo.validate.isValidCreditCard('30504009025904','bl'));
	//Discover card checks
	jum.assertTrue("test22", dojo.validate.isValidCreditCard('6011111111111117','di'));
	//JCB card checks
	jum.assertTrue("test23", dojo.validate.isValidCreditCard('3530111333300000','jcb'));
	jum.assertTrue("test24", dojo.validate.isValidCreditCard('213100000000001','jcb'));
	jum.assertTrue("test25", dojo.validate.isValidCreditCard('180000000000002','jcb'));
	jum.assertFalse("test26", dojo.validate.isValidCreditCard('1800000000000002','jcb')); //should fail, good checksum, good prefix, but wrong length'
	//Enroute card checks
	jum.assertTrue("test27", dojo.validate.isValidCreditCard('201400000000000','er'));
	jum.assertTrue("test28", dojo.validate.isValidCreditCard('214900000000000','er')); 
}

function test_validate_isValidCreditCardNumber(){
	//misc checks
	jum.assertTrue("test1", dojo.validate.isValidCreditCardNumber('5105105105105100','mc')); //test string input
	jum.assertTrue("test2", dojo.validate.isValidCreditCardNumber('5105-1051 0510-5100','mc')); //test string input with dashes and spaces (commonly used when entering card #'s)
	jum.assertTrue("test3", dojo.validate.isValidCreditCardNumber(5105105105105100,'mc')); //test numerical input as well
	jum.assertFalse("test4", dojo.validate.isValidCreditCardNumber('5105105105105100','vi')); //fails, wrong card type
	//Mastercard/Eurocard checks
	jum.assertEquals("test5", "mc|ec", dojo.validate.isValidCreditCardNumber('5100000000000000')); //should match 'mc|ec'
	jum.assertEquals("test6", "mc|ec", dojo.validate.isValidCreditCardNumber('5200000000000000')); //should match 'mc|ec'
	jum.assertEquals("test7", "mc|ec", dojo.validate.isValidCreditCardNumber('5300000000000000')); //should match 'mc|ec'
	jum.assertEquals("test8", "mc|ec", dojo.validate.isValidCreditCardNumber('5400000000000000')); //should match 'mc|ec'
	jum.assertEquals("test9", "mc|ec", dojo.validate.isValidCreditCardNumber('5500000000000000')); //should match 'mc|ec'
	jum.assertFalse("test10", dojo.validate.isValidCreditCardNumber('55000000000000000')); //should fail, too long
	//Visa card checks
	jum.assertEquals("test11", "vi", dojo.validate.isValidCreditCardNumber('4111111111111111')); //should match 'vi'
	jum.assertEquals("test12", "vi", dojo.validate.isValidCreditCardNumber('4111111111010')); //should match 'vi'
	//American Express card checks
	jum.assertEquals("test13", "ax", dojo.validate.isValidCreditCardNumber('378 2822 4631 0005')); //should match 'ax'
	jum.assertEquals("test14", "ax", dojo.validate.isValidCreditCardNumber('341-1111-1111-1111')); //should match 'ax'
	//Diners Club/Carte Blanch card checks
	jum.assertEquals("test15", "dc|bl", dojo.validate.isValidCreditCardNumber('36400000000000')); //should match 'dc|bl'
	jum.assertEquals("test16", "dc|bl", dojo.validate.isValidCreditCardNumber('38520000023237')); //should match 'dc|bl'
	jum.assertEquals("test17", "dc|bl", dojo.validate.isValidCreditCardNumber('30009009025904')); //should match 'di|bl'
	jum.assertEquals("test18", "dc|bl", dojo.validate.isValidCreditCardNumber('30108009025904')); //should match 'di|bl'
	jum.assertEquals("test19", "dc|bl", dojo.validate.isValidCreditCardNumber('30207009025904')); //should match 'di|bl'
	jum.assertEquals("test20", "dc|bl", dojo.validate.isValidCreditCardNumber('30306009025904')); //should match 'di|bl'
	jum.assertEquals("test21", "dc|bl", dojo.validate.isValidCreditCardNumber('30405009025904')); //should match 'di|bl'
	jum.assertEquals("test22", "dc|bl", dojo.validate.isValidCreditCardNumber('30504009025904')); //should match 'di|bl'
	//Discover card checks
	jum.assertEquals("test23", "di", dojo.validate.isValidCreditCardNumber('6011111111111117')); //should match 'di'
	//JCB card checks
	jum.assertEquals("test24", "jcb", dojo.validate.isValidCreditCardNumber('3530111333300000')); //should match 'jcb'
	jum.assertEquals("test25", "jcb", dojo.validate.isValidCreditCardNumber('213100000000001')); //should match 'jcb'
	jum.assertEquals("test26", "jcb", dojo.validate.isValidCreditCardNumber('180000000000002')); //should match 'jcb'
	jum.assertFalse("test27", dojo.validate.isValidCreditCardNumber('1800000000000002')); //should fail, good checksum, good prefix, but wrong length'
	//Enroute card checks
	jum.assertEquals("test28", "er", dojo.validate.isValidCreditCardNumber('201400000000000')); //should match 'er'
	jum.assertEquals("test29", "er", dojo.validate.isValidCreditCardNumber('214900000000000')); //should match 'er'
}
