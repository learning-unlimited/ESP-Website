/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.validate");
dojo.require("dojo.validate.check");
dojo.require("dojo.validate.datetime");
dojo.require("dojo.validate.de");
dojo.require("dojo.validate.jp");
dojo.require("dojo.validate.us");
dojo.require("dojo.validate.web");

function test_validate_isText(){
	jum.assertTrue("test1", dojo.validate.isText('            x'));
	jum.assertTrue("test2", dojo.validate.isText('x             '));
	jum.assertTrue("test3", dojo.validate.isText('        x     '));
	jum.assertFalse("test4", dojo.validate.isText('   '));
	jum.assertFalse("test5", dojo.validate.isText(''));

	// test lengths
	jum.assertTrue("test6", dojo.validate.isText('123456', {length: 6} ));
	jum.assertFalse("test7", dojo.validate.isText('1234567', {length: 6} ));
	jum.assertTrue("test8", dojo.validate.isText('1234567', {minlength: 6} ));
	jum.assertTrue("test9", dojo.validate.isText('123456', {minlength: 6} ));
	jum.assertFalse("test10", dojo.validate.isText('12345', {minlength: 6} ));
	jum.assertFalse("test11", dojo.validate.isText('1234567', {maxlength: 6} ));
	jum.assertTrue("test12", dojo.validate.isText('123456', {maxlength: 6} ));
}

function test_validate_web_isIpAddress(){
	jum.assertTrue("test1", dojo.validate.isIpAddress('24.17.155.40'));
	jum.assertFalse("test2", dojo.validate.isIpAddress('024.17.155.040'));
	jum.assertTrue("test3", dojo.validate.isIpAddress('255.255.255.255'));
	jum.assertFalse("test4", dojo.validate.isIpAddress('256.255.255.255'));
	jum.assertFalse("test5", dojo.validate.isIpAddress('255.256.255.255'));
	jum.assertFalse("test6", dojo.validate.isIpAddress('255.255.256.255'));
	jum.assertFalse("test7", dojo.validate.isIpAddress('255.255.255.256'));

	// test dotted hex
	jum.assertTrue("test8", dojo.validate.isIpAddress('0x18.0x11.0x9b.0x28'));
	jum.assertFalse("test9", dojo.validate.isIpAddress('0x18.0x11.0x9b.0x28', {allowDottedHex: false}) );
	jum.assertTrue("test10", dojo.validate.isIpAddress('0x18.0x000000011.0x9b.0x28'));
	jum.assertTrue("test11", dojo.validate.isIpAddress('0xff.0xff.0xff.0xff'));
	jum.assertFalse("test12", dojo.validate.isIpAddress('0x100.0xff.0xff.0xff'));

	// test dotted octal
	jum.assertTrue("test13", dojo.validate.isIpAddress('0030.0021.0233.0050'));
	jum.assertFalse("test14", dojo.validate.isIpAddress('0030.0021.0233.0050', {allowDottedOctal: false}) );
	jum.assertTrue("test15", dojo.validate.isIpAddress('0030.0000021.0233.00000050'));
	jum.assertTrue("test16", dojo.validate.isIpAddress('0377.0377.0377.0377'));
	jum.assertFalse("test17", dojo.validate.isIpAddress('0400.0377.0377.0377'));
	jum.assertFalse("test18", dojo.validate.isIpAddress('0377.0378.0377.0377'));
	jum.assertFalse("test19", dojo.validate.isIpAddress('0377.0377.0380.0377'));
	jum.assertFalse("test20", dojo.validate.isIpAddress('0377.0377.0377.377'));

	// test decimal
	jum.assertTrue("test21", dojo.validate.isIpAddress('3482223595'));
	jum.assertTrue("test22", dojo.validate.isIpAddress('0'));
	jum.assertTrue("test23", dojo.validate.isIpAddress('4294967295'));
	jum.assertFalse("test24", dojo.validate.isIpAddress('4294967296'));
	jum.assertFalse("test25", dojo.validate.isIpAddress('3482223595', {allowDecimal: false}));

	// test hex
	jum.assertTrue("test26", dojo.validate.isIpAddress('0xCF8E83EB'));
	jum.assertTrue("test27", dojo.validate.isIpAddress('0x0'));
	jum.assertTrue("test28", dojo.validate.isIpAddress('0x00ffffffff'));
	jum.assertFalse("test29", dojo.validate.isIpAddress('0x100000000'));
	jum.assertFalse("test30", dojo.validate.isIpAddress('0xCF8E83EB', {allowHex: false}));

	// IPv6
	jum.assertTrue("test31", dojo.validate.isIpAddress('fedc:BA98:7654:3210:FEDC:BA98:7654:3210'));
	jum.assertTrue("test32", dojo.validate.isIpAddress('1080:0:0:0:8:800:200C:417A'));
	jum.assertFalse("test33", dojo.validate.isIpAddress('1080:0:0:0:8:800:200C:417A', {allowIPv6: false}));

	// Hybrid of IPv6 and IPv4
	jum.assertTrue("test34", dojo.validate.isIpAddress('0:0:0:0:0:0:13.1.68.3'));
	jum.assertTrue("test35", dojo.validate.isIpAddress('0:0:0:0:0:FFFF:129.144.52.38'));
	jum.assertFalse("test36", dojo.validate.isIpAddress('0:0:0:0:0:FFFF:129.144.52.38', {allowHybrid: false}));
}

function test_validate_web_isUrl(){
	jum.assertTrue("test1", dojo.validate.isUrl('www.yahoo.com'));
	jum.assertTrue("test2", dojo.validate.isUrl('http://www.yahoo.com'));
	jum.assertTrue("test3", dojo.validate.isUrl('https://www.yahoo.com'));
	jum.assertFalse("test4", dojo.validate.isUrl('http://.yahoo.com'));
	jum.assertFalse("test5", dojo.validate.isUrl('http://www.-yahoo.com'));
	jum.assertFalse("test6", dojo.validate.isUrl('http://www.yahoo-.com'));
	jum.assertTrue("test7", dojo.validate.isUrl('http://y-a---h-o-o.com'));
	jum.assertTrue("test8", dojo.validate.isUrl('http://www.y.com'));
	jum.assertTrue("test9", dojo.validate.isUrl('http://www.yahoo.museum'));
	jum.assertTrue("test10", dojo.validate.isUrl('http://www.yahoo.co.uk'));
	jum.assertFalse("test11", dojo.validate.isUrl('http://www.micro$oft.com'));

	jum.assertTrue("test12", dojo.validate.isUrl('http://www.y.museum:8080'));
	jum.assertTrue("test13", dojo.validate.isUrl('http://12.24.36.128:8080'));
	jum.assertFalse("test14", dojo.validate.isUrl('http://12.24.36.128:8080', {allowIP: false} ));
	jum.assertTrue("test15", dojo.validate.isUrl('www.y.museum:8080'));
	jum.assertFalse("test16", dojo.validate.isUrl('www.y.museum:8080', {scheme: true} ));
	jum.assertTrue("test17", dojo.validate.isUrl('localhost:8080', {allowLocal: true} ));
	jum.assertFalse("test18", dojo.validate.isUrl('localhost:8080', {} ));
	jum.assertTrue("test19", dojo.validate.isUrl('http://www.yahoo.com/index.html?a=12&b=hello%20world#anchor'));
	jum.assertFalse("test20", dojo.validate.isUrl('http://www.yahoo.xyz'));
	jum.assertTrue("test21", dojo.validate.isUrl('http://www.yahoo.com/index.html#anchor'));
	jum.assertTrue("test22", dojo.validate.isUrl('http://cocoon.apache.org/2.1/'));
}

function test_validate_web_isEmailAddress(){
	jum.assertTrue("test1", dojo.validate.isEmailAddress('x@yahoo.com'));
	jum.assertTrue("test2", dojo.validate.isEmailAddress('x.y.z.w@yahoo.com'));
	jum.assertFalse("test3", dojo.validate.isEmailAddress('x..y.z.w@yahoo.com'));
	jum.assertFalse("test4", dojo.validate.isEmailAddress('x.@yahoo.com'));
	jum.assertTrue("test5", dojo.validate.isEmailAddress('x@z.com'));
	jum.assertFalse("test6", dojo.validate.isEmailAddress('x@yahoo.x'));
	jum.assertTrue("test7", dojo.validate.isEmailAddress('x@yahoo.museum'));
	jum.assertTrue("test8", dojo.validate.isEmailAddress("o'mally@yahoo.com"));
	jum.assertFalse("test9", dojo.validate.isEmailAddress("'mally@yahoo.com"));
	jum.assertTrue("test10", dojo.validate.isEmailAddress("fred&barney@stonehenge.com"));
	jum.assertFalse("test11", dojo.validate.isEmailAddress("fred&&barney@stonehenge.com"));

	// local addresses
	jum.assertTrue("test12", dojo.validate.isEmailAddress("fred&barney@localhost", {allowLocal: true} ));
	jum.assertFalse("test13", dojo.validate.isEmailAddress("fred&barney@localhost"));

	// addresses with cruft
	jum.assertTrue("test14", dojo.validate.isEmailAddress("mailto:fred&barney@stonehenge.com", {allowCruft: true} ));
	jum.assertTrue("test15", dojo.validate.isEmailAddress("<fred&barney@stonehenge.com>", {allowCruft: true} ));
	jum.assertFalse("test16", dojo.validate.isEmailAddress("mailto:fred&barney@stonehenge.com"));
	jum.assertFalse("test17", dojo.validate.isEmailAddress("<fred&barney@stonehenge.com>"));

	// local addresses with cruft
	jum.assertTrue("test18", dojo.validate.isEmailAddress("<mailto:fred&barney@localhost>", {allowLocal: true, allowCruft: true} ));
	jum.assertFalse("test19", dojo.validate.isEmailAddress("<mailto:fred&barney@localhost>", {allowCruft: true} ));
	jum.assertFalse("test20", dojo.validate.isEmailAddress("<mailto:fred&barney@localhost>", {allowLocal: true} ));
}

function test_validate_web_isEmailAddressList(){
	jum.assertTrue("test1", dojo.validate.isEmailAddressList(
		"x@yahoo.com \n x.y.z.w@yahoo.com ; o'mally@yahoo.com , fred&barney@stonehenge.com \n" )
	);
	jum.assertTrue("test2", dojo.validate.isEmailAddressList(
		"x@yahoo.com \n x.y.z.w@localhost \n o'mally@yahoo.com \n fred&barney@localhost", 
		{allowLocal: true} )
	);
	jum.assertFalse("test3", dojo.validate.isEmailAddressList(
		"x@yahoo.com; x.y.z.w@localhost; o'mally@yahoo.com; fred&barney@localhost", {listSeparator: ";"} )
	);
	jum.assertTrue("test4", dojo.validate.isEmailAddressList(
			"mailto:x@yahoo.com; <x.y.z.w@yahoo.com>; <mailto:o'mally@yahoo.com>; fred&barney@stonehenge.com", 
			{allowCruft: true, listSeparator: ";"} )
	);
	jum.assertFalse("test5", dojo.validate.isEmailAddressList(
			"mailto:x@yahoo.com; <x.y.z.w@yahoo.com>; <mailto:o'mally@yahoo.com>; fred&barney@stonehenge.com", 
			{listSeparator: ";"} )
	);
	jum.assertTrue("test6", dojo.validate.isEmailAddressList(
			"mailto:x@yahoo.com; <x.y.z.w@localhost>; <mailto:o'mally@localhost>; fred&barney@localhost", 
			{allowLocal: true, allowCruft: true, listSeparator: ";"} )
	);
}

function test_validate_web_getEmailAddressList(){
	var list = "x@yahoo.com \n x.y.z.w@yahoo.com ; o'mally@yahoo.com , fred&barney@stonehenge.com";
	jum.assertEquals("test1", 4, dojo.validate.getEmailAddressList(list).length);

	var localhostList = "x@yahoo.com; x.y.z.w@localhost; o'mally@yahoo.com; fred&barney@localhost";
	jum.assertEquals("test2", 0, dojo.validate.getEmailAddressList(localhostList).length);
	jum.assertEquals("test3", 4, dojo.validate.getEmailAddressList(localhostList, {allowLocal: true} ).length);
}

function test_validate_isInRange(){
	// test integers
	jum.assertFalse("test1", dojo.validate.isInRange( '0', {min: 1, max: 100} ));
	jum.assertTrue("test2", dojo.validate.isInRange( '1', {min: 1, max: 100} ));
	jum.assertFalse("test3", dojo.validate.isInRange( '-50', {min: 1, max: 100} ));
	jum.assertTrue("test4", dojo.validate.isInRange( '+50', {min: 1, max: 100} ));
	jum.assertTrue("test5", dojo.validate.isInRange( '100', {min: 1, max: 100} ));
	jum.assertFalse("test6", dojo.validate.isInRange( '101', {min: 1, max: 100} ));

	//test real numbers
	jum.assertFalse("test7", dojo.validate.isInRange( '0.9', {min: 1.0, max: 10.0} ));
	jum.assertTrue("test8", dojo.validate.isInRange( '1.0', {min: 1.0, max: 10.0} ));
	jum.assertFalse("test9", dojo.validate.isInRange( '-5.0', {min: 1.0, max: 10.0} ));
	jum.assertTrue("test10", dojo.validate.isInRange( '+5.50', {min: 1.0, max: 10.0} ));
	jum.assertTrue("test11", dojo.validate.isInRange( '10.0', {min: 1.0, max: 10.0} ));
	jum.assertFalse("test12", dojo.validate.isInRange( '10.1', {min: 1.0, max: 10.0} ));
	jum.assertFalse("test13", dojo.validate.isInRange( '5.566e28', {min: 5.567e28, max: 6.000e28} ));
	jum.assertTrue("test14", dojo.validate.isInRange( '5.7e28', {min: 5.567e28, max: 6.000e28} ));
	jum.assertFalse("test15", dojo.validate.isInRange( '6.00000001e28', {min: 5.567e28, max: 6.000e28} ));
	jum.assertFalse("test16", dojo.validate.isInRange( '10.000.000,12345e-5', {decimal: ",", max: 10000000.1e-5} ));
	jum.assertFalse("test17", dojo.validate.isInRange( '10.000.000,12345e-5', {decimal: ",", min: 10000000.2e-5} ));
	jum.assertTrue("test18", dojo.validate.isInRange('1,500,000', {separator: ',', min: 0}));

	// test currency
	jum.assertFalse("test19", dojo.validate.isInRange('\u20AC123,456,789', {max: 123456788, symbol: '\u20AC'} ));
	jum.assertFalse("test20", dojo.validate.isInRange('\u20AC123,456,789', { min: 123456790, symbol: '\u20AC'} ));
	jum.assertFalse("test21", dojo.validate.isInRange('$123,456,789.07', { max: 123456789.06} ));
	jum.assertFalse("test22", dojo.validate.isInRange('$123,456,789.07', { min: 123456789.08} ));
	jum.assertFalse("test23", dojo.validate.isInRange('123.456.789,00 \u20AC',  {max: 123456788, decimal: ",", symbol: '\u20AC'} ));
	jum.assertFalse("test24", dojo.validate.isInRange('123.456.789,00 \u20AC',  {min: 123456790, decimal: ",", symbol: '\u20AC'} ));
	jum.assertFalse("test25", dojo.validate.isInRange('- T123 456 789-00', {decimal: "-", min:0} ));
	jum.assertTrue("test26", dojo.validate.isInRange('\u20AC123,456,789', { max: 123456790, symbol: '\u20AC'} ));
	jum.assertTrue("test27", dojo.validate.isInRange('$123,456,789.07', { min: 123456789.06} ));

	// test non number
	//jum.assertFalse("test25", dojo.validate.isInRange( 'a'));

}

function test_validate_isInteger(){
	//test default
	jum.assertTrue("test1", dojo.validate.isInteger('0'));
	jum.assertTrue("test2", dojo.validate.isInteger('+0'));
	jum.assertTrue("test3", dojo.validate.isInteger('-1'));
	jum.assertTrue("test4", dojo.validate.isInteger('123456789'));
	jum.assertFalse("test5", dojo.validate.isInteger('0123456789'));
	jum.assertFalse("test6", dojo.validate.isInteger('00'));
	jum.assertFalse("test7", dojo.validate.isInteger('1.0'));

	//test separator
	jum.assertTrue("test14", dojo.validate.isInteger( '10,000,000', {separator: ","} ));
	jum.assertTrue("test15", dojo.validate.isInteger( '100,000,000', {separator: ","} ));
	jum.assertTrue("test16", dojo.validate.isInteger( '1,000,000,000', {separator: ","} ));
	jum.assertTrue("test17", dojo.validate.isInteger( '1.000.000', {separator: "."} ));
	jum.assertTrue("test18", dojo.validate.isInteger( '10.000.000', {separator: "."} ));
	jum.assertTrue("test19", dojo.validate.isInteger( '100.000.000', {separator: "."} ));
	jum.assertFalse("test20", dojo.validate.isInteger('10.000.000.000', {} ));
	jum.assertTrue("test21", dojo.validate.isInteger( '10,000,000', {separator: ["", ","]} ));
	jum.assertTrue("test22", dojo.validate.isInteger( '10000000', {separator: ["", ","]} ));
	jum.assertFalse("test23", dojo.validate.isInteger( '10.000.000', {separator: ["", ","]} ));

	//test sign
	jum.assertFalse("test24", dojo.validate.isInteger( '+10000000', {signed: false} ));
	jum.assertFalse("test25", dojo.validate.isInteger( '10000000', {signed: true} ));
}

function test_validate_isRealNumber(){
	// test default
	jum.assertTrue("test1", dojo.validate.isRealNumber('0'));
	jum.assertTrue("test2", dojo.validate.isRealNumber('+0'));
	jum.assertTrue("test3", dojo.validate.isRealNumber('-1'));
	jum.assertTrue("test4", dojo.validate.isRealNumber('123456789'));
	jum.assertFalse("test5", dojo.validate.isRealNumber('0123456789'));
	jum.assertFalse("test6", dojo.validate.isRealNumber('00'));
	jum.assertTrue("test7", dojo.validate.isRealNumber('1.0'));
	jum.assertTrue("test8", dojo.validate.isRealNumber('0.0000'));
	jum.assertFalse("test9", dojo.validate.isRealNumber('1.'));
	jum.assertTrue("test10", dojo.validate.isRealNumber('1234.0012340e63'));
	jum.assertTrue("test11", dojo.validate.isRealNumber('1234.0012340e+63'));
	jum.assertTrue("test12", dojo.validate.isRealNumber('1234.0012340e-63'));
	jum.assertFalse("test13", dojo.validate.isRealNumber('1234.0012340e063'));
	jum.assertFalse("test14", dojo.validate.isRealNumber('1234.0012340e63.5'));
	jum.assertFalse("test15", dojo.validate.isRealNumber('01234.0012340e10'));

	//test separator
	jum.assertTrue("test25", dojo.validate.isRealNumber( '10,000,000.12345e-5', {separator: ","} ));

	//test decimal
	jum.assertTrue("test26", dojo.validate.isRealNumber( '10.000.000,12345e-5', {separator: ".", decimal: ","} ));

	//test places
	jum.assertTrue("test29", dojo.validate.isRealNumber( '100.25', {places: 2} ));
	jum.assertFalse("test30", dojo.validate.isRealNumber( '100.2', {places: 2} ));
	jum.assertFalse("test31", dojo.validate.isRealNumber( '100.250', {places: 2} ));

	//test exponent part
	jum.assertTrue("test32", dojo.validate.isRealNumber( '100.25e32', {exponent: true} ));
	jum.assertFalse("test33", dojo.validate.isRealNumber( '100.25e32', {exponent: false} ));
	jum.assertTrue("test34", dojo.validate.isRealNumber( '100.25', {exponent: false} ));
	jum.assertFalse("test35", dojo.validate.isRealNumber( '100.25e32', {eSigned: true} ));
	jum.assertFalse("test36", dojo.validate.isRealNumber( '100.25+e32', {eSigned: false} ));
}

function test_validate_isCurrency(){
	// Austria
	jum.assertTrue("test1", dojo.validate.isCurrency('\u20AC 123.456.789,00',  {separator: ".", decimal: ",", symbol:"\u20AC"} ));
	// Germany
	jum.assertTrue("test2", dojo.validate.isCurrency('123.456.789,00 \u20AC',  {separator: ".", decimal: ",", symbol:"\u20AC", placement:"after"} ));
	// Switzerland
	jum.assertTrue("test3", dojo.validate.isCurrency("SFr. 123'456'789.00",  {separator: "'", symbol:"SFr."} ));
	// Estonia
	jum.assertTrue("test4", dojo.validate.isCurrency('123 456 789.00 kr', {separator:" ", symbol:"kr", placement:"after"} ));
	// Hungary
	jum.assertTrue("test5", dojo.validate.isCurrency('123 456 789,00 Ft', {separator:" ", decimal: ",", symbol:"Ft", placement:"after"} ));
	// Iceland
	jum.assertTrue("test6", dojo.validate.isCurrency('123.456.789,00 kr.', {separator:".", decimal: ",", symbol:"kr.", placement:"after"} ));
	// Indoneasia
	jum.assertTrue("test7", dojo.validate.isCurrency('Rp123.456.789', {separator:".", cents: false, symbol:"Rp"} ));
	// Japan
	jum.assertTrue("test8", dojo.validate.isCurrency('\u00a5123,456,789', {cents: false, symbol:"\u00a5"} ));
	// Kazakh
	jum.assertTrue("test9", dojo.validate.isCurrency('-T123 456 789-00', {separator:" ", decimal: "-", symbol:"T"} ));
	// Peru
	jum.assertTrue("test10", dojo.validate.isCurrency('S/. 123,456,789.00', { symbol:"S/."} ));
}

function test_validate_us_isCurrency(){
	jum.assertTrue("test1", dojo.validate.us.isCurrency('$1,000'));
	jum.assertTrue("test2", dojo.validate.us.isCurrency('$1,000.25'));
	jum.assertTrue("test3", dojo.validate.us.isCurrency('+$1,000,000'));
	jum.assertTrue("test4", dojo.validate.us.isCurrency('- $10,000,000'));
	jum.assertTrue("test5", dojo.validate.us.isCurrency('$100,000,000'));
	jum.assertFalse("test6", dojo.validate.us.isCurrency('$1000.25', {}));
	jum.assertTrue("test7", dojo.validate.us.isCurrency('$1000.25', {separator: ""}));
	jum.assertFalse("test8", dojo.validate.us.isCurrency('1,000.25', {}));
	jum.assertTrue("test9", dojo.validate.us.isCurrency('1,000.25', {symbol: ["", "$"]}));
	jum.assertFalse("test10", dojo.validate.us.isCurrency('1,000.25', {symbol: ["?", "$"]})); //FIXME
	jum.assertTrue("test11", dojo.validate.us.isCurrency('1000.25', {symbol: "", separator: ""}));
	jum.assertFalse("test12", dojo.validate.us.isCurrency('$1,000.25', {cents: false}));
	jum.assertFalse("test13", dojo.validate.us.isCurrency('$1,000.25', {signed: true}));
	jum.assertFalse("test14", dojo.validate.us.isCurrency('-$1,000.25', {signed: false}));
}

function test_validate_isGermanCurrency(){
	jum.assertTrue("test1", dojo.validate.isGermanCurrency('1.000 \u20AC'));
	jum.assertTrue("test2", dojo.validate.isGermanCurrency('1.000,25 \u20AC'));
	jum.assertTrue("test3", dojo.validate.isGermanCurrency('+1.000.000 \u20AC'));
	jum.assertTrue("test4", dojo.validate.isGermanCurrency('-10.000.000 \u20AC'));
	jum.assertTrue("test5", dojo.validate.isGermanCurrency('100.000.000 \u20AC'));
	jum.assertFalse("test6", dojo.validate.isGermanCurrency('1000,25 \u20AC'));
	jum.assertFalse("test8", dojo.validate.isGermanCurrency('1.000,25'));
}

function test_validate_isJapaneseCurrency(){
	jum.assertTrue("test1", dojo.validate.isJapaneseCurrency('\u00a51,000'));
	jum.assertFalse("test2", dojo.validate.isJapaneseCurrency('\u00a51,000.25'));
	jum.assertTrue("test3", dojo.validate.isJapaneseCurrency('+\u00a51,000,000'));
	jum.assertTrue("test4", dojo.validate.isJapaneseCurrency('- \u00a510,000,000'));
	jum.assertTrue("test5", dojo.validate.isJapaneseCurrency('\u00a5100,000,000'));
	jum.assertFalse("test6", dojo.validate.isJapaneseCurrency('\u00a51000'));
}
function test_validate_datetime_isValidTime(){
	jum.assertTrue("test1", dojo.validate.isValidTime('5:15:05 pm'));
	jum.assertTrue("test2", dojo.validate.isValidTime('5:15:05 p.m.', {pmSymbol: "P.M."} ));
	jum.assertFalse("test3", dojo.validate.isValidTime('5:15:05 p.m.', {} ));
	jum.assertTrue("test4", dojo.validate.isValidTime('5:15 pm', {format: "h:mm t"} ) );
	jum.assertFalse("test5", dojo.validate.isValidTime('5:15 pm', {}) );
	jum.assertTrue("test6", dojo.validate.isValidTime('15:15:00', {format: "H:mm:ss"} ) );
	jum.assertFalse("test7", dojo.validate.isValidTime('15:15:00', {}) );
	jum.assertTrue("test8", dojo.validate.isValidTime('17:01:30', {format: "H:mm:ss"} ) );
	jum.assertFalse("test9", dojo.validate.isValidTime('17:1:30', {format: "H:mm:ss"} ) );
	jum.assertFalse("test10", dojo.validate.isValidTime('17:01:30', {format: "H:m:ss"} ) );
	// Greek
	jum.assertTrue("test11", dojo.validate.isValidTime('5:01:30 ��', {amSymbol: "p�", pmSymbol: "��"} ) ); //FIXME and use \u escapes to avoid encoding problems
	// Italian
	jum.assertTrue("test12", dojo.validate.isValidTime('17.01.30', {format: "H.mm.ss"} ) );
	// Mexico
	jum.assertTrue("test13", dojo.validate.isValidTime('05:01:30 p.m.', {format: "hh:mm:ss t", amSymbol: "a.m.", pmSymbol: "p.m."} ) );
}


function test_validate_datetime_is12HourTime(){
	jum.assertTrue("test1", dojo.validate.is12HourTime('5:15:05 pm'));
	jum.assertFalse("test2", dojo.validate.is12HourTime('05:15:05 pm'));
	jum.assertFalse("test3", dojo.validate.is12HourTime('5:5:05 pm'));
	jum.assertFalse("test4", dojo.validate.is12HourTime('5:15:5 pm'));
	jum.assertFalse("test5", dojo.validate.is12HourTime('13:15:05 pm'));
	jum.assertFalse("test6", dojo.validate.is12HourTime('5:60:05 pm'));
	jum.assertFalse("test7", dojo.validate.is12HourTime('5:15:60 pm'));
	jum.assertTrue("test8", dojo.validate.is12HourTime('5:59:05 pm'));
	jum.assertTrue("test9", dojo.validate.is12HourTime('5:15:59 pm'));
	jum.assertFalse("test10", dojo.validate.is12HourTime('5:15:05'));

	// optional seconds
	jum.assertTrue("test11", dojo.validate.is12HourTime('5:15 pm'));
	jum.assertFalse("test12", dojo.validate.is12HourTime('5:15: pm'));
}

function test_validate_datetime_is24HourTime(){
	jum.assertTrue("test1", dojo.validate.is24HourTime('00:03:59'));
	jum.assertTrue("test2", dojo.validate.is24HourTime('22:03:59'));
	jum.assertFalse("test3", dojo.validate.is24HourTime('22:03:59 pm'));
	jum.assertFalse("test4", dojo.validate.is24HourTime('2:03:59'));
	jum.assertFalse("test5", dojo.validate.is24HourTime('0:3:59'));
	jum.assertFalse("test6", dojo.validate.is24HourTime('00:03:5'));
	jum.assertFalse("test7", dojo.validate.is24HourTime('24:03:59'));
	jum.assertFalse("test8", dojo.validate.is24HourTime('02:60:59'));
	jum.assertFalse("test9", dojo.validate.is24HourTime('02:03:60'));

	// optional seconds
	jum.assertTrue("test10", dojo.validate.is24HourTime('22:53'));
	jum.assertFalse("test11", dojo.validate.is24HourTime('22:53:'));
}

function test_validate_datetime_isValidDate(){
	
	// Month date year
	jum.assertTrue("test1", dojo.validate.isValidDate("08/06/2005", "MM/DD/YYYY"));
	jum.assertTrue("test2", dojo.validate.isValidDate("08.06.2005", "MM.DD.YYYY"));
	jum.assertTrue("test3", dojo.validate.isValidDate("08-06-2005", "MM-DD-YYYY"));
	jum.assertTrue("test4", dojo.validate.isValidDate("8/6/2005", "M/D/YYYY"));
	jum.assertTrue("test5", dojo.validate.isValidDate("8/6", "M/D"));
	jum.assertFalse("test6", dojo.validate.isValidDate("09/31/2005", "MM/DD/YYYY"));
	jum.assertFalse("test7", dojo.validate.isValidDate("02/29/2005", "MM/DD/YYYY"));
	jum.assertTrue("test8", dojo.validate.isValidDate("02/29/2004", "MM/DD/YYYY"));

	// year month date
	jum.assertTrue("test9", dojo.validate.isValidDate("2005-08-06", "YYYY-MM-DD"));
	jum.assertTrue("test10", dojo.validate.isValidDate("20050806", "YYYYMMDD"));

	// year month
	jum.assertTrue("test11", dojo.validate.isValidDate("2005-08", "YYYY-MM"));
	jum.assertTrue("test12", dojo.validate.isValidDate("200508", "YYYYMM"));

	// year
	jum.assertTrue("test13", dojo.validate.isValidDate("2005", "YYYY"));

	// year week day
	jum.assertTrue("test14", dojo.validate.isValidDate("2005-W42-3", "YYYY-Www-d"));
	jum.assertTrue("test15", dojo.validate.isValidDate("2005W423", "YYYYWwwd"));
	jum.assertFalse("test16", dojo.validate.isValidDate("2005-W42-8", "YYYY-Www-d"));
	jum.assertFalse("test17", dojo.validate.isValidDate("2005-W54-3", "YYYY-Www-d"));

	// year week
	jum.assertTrue("test18", dojo.validate.isValidDate("2005-W42", "YYYY-Www"));
	jum.assertTrue("test19", dojo.validate.isValidDate("2005W42", "YYYYWww"));

	// year ordinal-day
	jum.assertTrue("test20", dojo.validate.isValidDate("2005-292", "YYYY-DDD"));
	jum.assertTrue("test21", dojo.validate.isValidDate("2005292", "YYYYDDD"));
	jum.assertFalse("test22", dojo.validate.isValidDate("2005-366", "YYYY-DDD"));
	jum.assertTrue("test23", dojo.validate.isValidDate("2004-366", "YYYY-DDD"));

	// date month year
	jum.assertTrue("test24", dojo.validate.isValidDate("19.10.2005", "DD.MM.YYYY"));
	jum.assertTrue("test25", dojo.validate.isValidDate("19-10-2005", "D-M-YYYY"));
}

function test_validate_us_datetime_isPhoneNumber(){
	//jum.assertEquals("test1", 1, dojo.validate.us.isPhoneNumber('(111) 111-1111'));
	jum.assertTrue("test2", dojo.validate.us.isPhoneNumber('(111) 111 1111'));
	jum.assertTrue("test3", dojo.validate.us.isPhoneNumber('111 111 1111'));
	jum.assertTrue("test4", dojo.validate.us.isPhoneNumber('111.111.1111'));
	jum.assertTrue("test5", dojo.validate.us.isPhoneNumber('111-111-1111'));
	jum.assertTrue("test6", dojo.validate.us.isPhoneNumber('111/111-1111'));
	jum.assertFalse("test7", dojo.validate.us.isPhoneNumber('111 111-1111'));
	jum.assertFalse("test8", dojo.validate.us.isPhoneNumber('111-1111'));
	jum.assertFalse("test9", dojo.validate.us.isPhoneNumber('(111)-111-1111'));

	// test extensions
	jum.assertTrue("test10", dojo.validate.us.isPhoneNumber('111-111-1111 x1'));
	jum.assertTrue("test11", dojo.validate.us.isPhoneNumber('111-111-1111 x12'));
	jum.assertTrue("test12", dojo.validate.us.isPhoneNumber('111-111-1111 x1234'));
}

function test_validate_us_isSocialSecurityNumber(){
	jum.assertTrue("test1", dojo.validate.us.isSocialSecurityNumber('123-45-6789'));
	jum.assertTrue("test2", dojo.validate.us.isSocialSecurityNumber('123 45 6789'));
	jum.assertTrue("test3", dojo.validate.us.isSocialSecurityNumber('123456789'));
	jum.assertFalse("test4", dojo.validate.us.isSocialSecurityNumber('123-45 6789'));
	jum.assertFalse("test5", dojo.validate.us.isSocialSecurityNumber('12345 6789'));
	jum.assertFalse("test6", dojo.validate.us.isSocialSecurityNumber('123-456789'));
}

function test_validate_us_isZipCode(){
	jum.assertTrue("test1", dojo.validate.us.isZipCode('12345-6789'));
	jum.assertTrue("test2", dojo.validate.us.isZipCode('12345 6789'));
	jum.assertTrue("test3", dojo.validate.us.isZipCode('123456789'));
	jum.assertTrue("test4", dojo.validate.us.isZipCode('12345'));
}

function test_validate_us_isState(){
	jum.assertTrue("test1", dojo.validate.us.isState('CA'));
	jum.assertTrue("test2", dojo.validate.us.isState('ne'));
	jum.assertTrue("test3", dojo.validate.us.isState('PR'));
	jum.assertFalse("test4", dojo.validate.us.isState('PR', {allowTerritories: false} ));
	jum.assertTrue("test5", dojo.validate.us.isState('AA'));
	jum.assertFalse("test6", dojo.validate.us.isState('AA', {allowMilitary: false} ));
}

function validateAlienSelected(elem){
	if (elem.length > 0) { return true; }
	return false;
}

function test_validate_check(){
	// A generic form
	var f = {
		// textboxes
		tx1: {type: "text", value: " 1001 ",  name: "tx1"},
		tx2: {type: "text", value: " x",  name: "tx2"},
		tx3: {type: "text", value: "10/19/2005",  name: "tx3"},
		tx4: {type: "text", value: "10/19/2005",  name: "tx4"},
		tx5: {type: "text", value: "Foo@Localhost",  name: "tx5"},
		tx6: {type: "text", value: "Foo@Localhost",  name: "tx6"},
		tx7: {type: "text", value: "<Foo@Gmail.Com>",  name: "tx7"},
		tx8: {type: "text", value: "   ",  name: "tx8"},
		tx9: {type: "text", value: "ca",  name: "tx9"},
		tx10: {type: "text", value: "homer SIMPSON",  name: "tx10"},
		tx11: {type: "text", value: "$1,000,000 (US)",  name: "tx11"},
		tx12: {type: "text", value: "as12.a13", name: "tx12"},
		tx13: {type: "text", value: "4.13", name: "tx13"},
		tx14: {type: "text", value: "15.681", name: "tx14"},
		tx15: {value: "1", name: "tx15"},
		cc_no: {type: "text", value: "5434 1111 1111 1111",  name: "cc_no"},
		cc_exp: {type: "text", value: "",  name: "cc_exp"},
		cc_type: {type: "text", value: "Visa",  name: "cc_type"},
		email: {type: "text", value: "foo@gmail.com",  name: "email"},
		email_confirm: {type: "text", value: "foo2@gmail.com",  name: "email_confirm"},
		// password
		pw1: {type: "password", value: "123456",  name: "pw1"},
		pw2: {type: "password", value: "123456",  name: "pw2"},
		// textarea - they have a type property, even though no html attribute
		ta1: {type: "textarea", value: "",  name: "ta1"},
		ta2: {type: "textarea", value: "",  name: "ta2"},
		// radio button groups
		rb1: [
			{type: "radio", value: "v0",  name: "rb1", checked: false},
			{type: "radio", value: "v1",  name: "rb1", checked: false},
			{type: "radio", value: "v2",  name: "rb1", checked: true}
		],
		rb2: [
			{type: "radio", value: "v0",  name: "rb2", checked: false},
			{type: "radio", value: "v1",  name: "rb2", checked: false},
			{type: "radio", value: "v2",  name: "rb2", checked: false}
		],
		rb3: [
			{type: "radio", value: "v0",  name: "rb3", checked: false},
			{type: "radio", value: "v1",  name: "rb3", checked: false},
			{type: "radio", value: "v2",  name: "rb3", checked: false}
		],
		// checkboxes
		cb1: {type: "checkbox", value: "cb1",  name: "cb1", checked: false},
		cb2: {type: "checkbox", value: "cb2",  name: "cb2", checked: false},
		// checkbox group with the same name
		cb3: [
			{type: "checkbox", value: "v0",  name: "cb3", checked: false},
			{type: "checkbox", value: "v1",  name: "cb3", checked: false},
			{type: "checkbox", value: "v2",  name: "cb3", checked: false}
		],
		doubledip: [
			{type: "checkbox", value: "vanilla",  name: "doubledip", checked: false},
			{type: "checkbox", value: "chocolate",  name: "doubledip", checked: false},
			{type: "checkbox", value: "chocolate chip",  name: "doubledip", checked: false},
			{type: "checkbox", value: "lemon custard",  name: "doubledip", checked: true},
			{type: "checkbox", value: "pistachio almond",  name: "doubledip", checked: false}
		],		
		// <select>
		s1: {
			type: "select-one", 
			name: "s1",
			selectedIndex: -1,
			options: [
				{text: "option 1", value: "v0", selected: false},
				{text: "option 2", value: "v1", selected: false},
				{text: "option 3", value: "v2", selected: false}
			]
		},
		// <select multiple>
		s2: {
			type: "select-multiple", 
			name: "s2",
			selectedIndex: 1,
			options: [
				{text: "option 1", value: "v0", selected: false},
				{text: "option 2", value: "v1", selected: true},
				{text: "option 3", value: "v2", selected: true}
			]
		},
		tripledip: {
			type: "select-multiple", 
			name: "tripledip",
			selectedIndex: 3,
			options: [
				{text: "option 1", value: "vanilla", selected: false},
				{text: "option 2", value: "chocolate", selected: false},
				{text: "option 3", value: "chocolate chip", selected: false},
				{text: "option 4", value: "lemon custard", selected: true},
				{text: "option 5", value: "pistachio almond", selected: true},
				{text: "option 6", value: "mocha almond chip", selected: false}
			]
		},
		doublea: {
			type: "select-multiple", 
			name: "doublea",
			selectedIndex: 2,
			options: [
				{text: "option 1", value: "vanilla", selected: false},
				{text: "option 2", value: "chocolate", selected: true},
				{text: "option 3", value: "", selected: true}
			]
		},
		// <select> null selection
		s3: {
			type: "select-one", 
			name: "s3",
			selectedIndex: 0,
			options: [
				{text: "option 1", value: "", selected: true},
				{text: "option 2", value: "v1", selected: false},
				{text: "option 3", value: "v2", selected: false}
			]
		},
		selectAlien: {
			name: "selectAlien",
			multiple: "multiple",
			id: "selectAlient",
			size: "10",
			length: 0,
			options: [],
			value:[]
		}
	};

	// Profile for form input
	var profile = {
		// filters
		trim: ["tx1", "tx2"],
		uppercase: ["tx9"],
		lowercase: ["tx5", "tx6", "tx7"],
		ucfirst: ["tx10"],
		digit: ["tx11"],
		// required fields
		required: ["tx2", "tx3", "tx4", "tx5", "tx6", "tx7", "tx8", "tx15", "pw1", "ta1", "rb1", "rb2", 
					"cb3", "s1", "s2", "s3",
			{"doubledip":2}, {"tripledip":3}, {"doublea":2} ],
		// dependant/conditional fields
		dependancies:	{
			cc_exp: "cc_no",
			cc_type: "cc_no"
		},
		// validated fields
		constraints: {
			tx1: dojo.validate.isInteger,
			tx2: dojo.validate.isInteger,
			tx3: [dojo.validate.isValidDate, "MM/DD/YYYY"],
			tx4: [dojo.validate.isValidDate, "YYYY.MM.DD"],
			tx5: [dojo.validate.isEmailAddress],
			tx6: [dojo.validate.isEmailAddress, {allowLocal: true}],
			tx7: [dojo.validate.isEmailAddress, {allowCruft: true}],
			tx8: dojo.validate.isURL,
			tx12: [[dojo.validate.isRealNumber],[dojo.validate.isInRange, {max:100.00,min:5.0}]],
			tx13: [[dojo.validate.isRealNumber],[dojo.validate.isInRange, {max:100.00,min:5.0}]],
			tx14: [[dojo.validate.isRealNumber],[dojo.validate.isInRange, {max:100.00,min:5.0}]],
			selectAlien: [[validateAlienSelected]]
		},
		// confirm fields
		confirm: {
			email_confirm: "email",	
			pw2: "pw1"
		}
	};

	// results object
	var results = dojo.validate.check(f, profile);

	// test filter stuff
	jum.assertEquals("trim_test1", "1001", f.tx1.value );
	jum.assertEquals("trim_test2", "x", f.tx2.value );
	jum.assertEquals("uc_test1", "CA", f.tx9.value );
	jum.assertEquals("lc_test1", "foo@localhost", f.tx5.value );
	jum.assertEquals("lc_test2", "foo@localhost", f.tx6.value );
	jum.assertEquals("lc_test3", "<foo@gmail.com>", f.tx7.value );
	jum.assertEquals("ucfirst_test1", "Homer Simpson", f.tx10.value );
	jum.assertEquals("digit_test1", "1000000", f.tx11.value );

	// test missing stuff
	jum.assertFalse("missing_test1", results.isSuccessful() );
	jum.assertTrue("missing_test2", results.hasMissing() );
	jum.assertFalse("missing_test3", results.isMissing("tx1") );
	jum.assertFalse("missing_test4", results.isMissing("tx2") );
	jum.assertFalse("missing_test5", results.isMissing("tx3") );
	jum.assertFalse("missing_test6", results.isMissing("tx4") );
	jum.assertFalse("missing_test7", results.isMissing("tx5") );
	jum.assertFalse("missing_test8", results.isMissing("tx6") );
	jum.assertFalse("missing_test9", results.isMissing("tx7") );
	jum.assertTrue("missing_test10", results.isMissing("tx8") );
	jum.assertFalse("missing_test11", results.isMissing("pw1") );
	jum.assertFalse("missing_test12", results.isMissing("pw2") );
	jum.assertTrue("missing_test13", results.isMissing("ta1") );
	jum.assertFalse("missing_test14", results.isMissing("ta2") );
	jum.assertFalse("missing_test15", results.isMissing("rb1") );
	jum.assertTrue("missing_test16", results.isMissing("rb2") );
	jum.assertFalse("missing_test17", results.isMissing("rb3") );
	jum.assertTrue("missing_test18", results.isMissing("cb3") );
	jum.assertTrue("missing_test17", results.isMissing("s1") );
	jum.assertFalse("missing_test20", results.isMissing("s2") );
	jum.assertTrue(results.isMissing("s3"));
	jum.assertTrue("missing_test21", results.isMissing("doubledip") );
	jum.assertTrue("missing_test22", results.isMissing("tripledip") );
	jum.assertTrue(results.isMissing("doublea"));
	jum.assertFalse("missing_test23", results.isMissing("cc_no") );
	jum.assertTrue("missing_test24", results.isMissing("cc_exp") );
	jum.assertFalse("missing_test25", results.isMissing("cc_type") );
	// missing: tx8, ta1, rb2, cb3, s1, s3, doubledip, tripledip, cc_exp
	jum.assertEquals(10, results.getMissing().length );

	// test constraint stuff
	jum.assertTrue(results.hasInvalid() );
	jum.assertFalse(results.isInvalid("tx1") );
	jum.assertTrue(results.isInvalid("tx2") );
	jum.assertFalse(results.isInvalid("tx3") );
	jum.assertTrue(results.isInvalid("tx4") );
	jum.assertTrue(results.isInvalid("tx5") );
	jum.assertFalse(results.isInvalid("tx6") );
	jum.assertFalse(results.isInvalid("tx7") );
	jum.assertFalse(results.isInvalid("tx8") );
	jum.assertFalse(results.isInvalid("pw1") );
	jum.assertFalse(results.isInvalid("pw2") );
	jum.assertFalse(results.isInvalid("ta1") );
	jum.assertFalse(results.isInvalid("ta2") );
	jum.assertFalse(results.isInvalid("email") );
	jum.assertTrue(results.isInvalid("email_confirm") );
	
	// invlaid: txt2, txt4, txt5, email_confirm, selectAlien
	
	jum.assertEquals(7, results.getInvalid().length);
	jum.assertTrue(results.isInvalid("tx12"));
	jum.assertTrue(results.isInvalid("tx13"));
	jum.assertFalse(results.isInvalid("tx14"));
	jum.assertTrue(results.isInvalid("selectAlien"));
}
