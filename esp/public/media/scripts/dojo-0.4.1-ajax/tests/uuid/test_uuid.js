/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.uuid.*");
dojo.require("dojo.lang");

function OFF_test_uuid_performance() {
	var start = new Date();
	var startMS = start.valueOf();
	var nowMS = startMS;
	var i;
	var now;
	var numTrials = 100000;

	while (nowMS == startMS) {
		now = new Date();
		nowMS = now.valueOf();
	}
	
	startMS = nowMS;
	for (i = 0; i < numTrials; ++i) {
		var a = dojo.uuid.LightweightGenerator.generate();
	}
	now = new Date();
	nowMS = now.valueOf();
	var elapsedMS = nowMS - startMS;
	// dojo.log.debug("created " + numTrials + " UUIDs in " + elapsedMS + " milliseconds");
}

function test_uuid_capitalization() {
	var randomLowercaseString = "3b12f1df-5232-4804-897e-917bf397618a";
	var randomUppercaseString = "3B12F1DF-5232-4804-897E-917BF397618A";
	
	var timebasedLowercaseString = "b4308fb0-86cd-11da-a72b-0800200c9a66";
	var timebasedUppercaseString = "B4308FB0-86CD-11DA-A72B-0800200C9A66";
	
	var uuidRL = new dojo.uuid.Uuid(randomLowercaseString);
	var uuidRU = new dojo.uuid.Uuid(randomUppercaseString);
	
	var uuidTL = new dojo.uuid.Uuid(timebasedLowercaseString);
	var uuidTU = new dojo.uuid.Uuid(timebasedUppercaseString);
	
	jum.assertTrue("(uuidRL.isEqual(uuidRU))", uuidRL.isEqual(uuidRU));
	jum.assertTrue("(uuidRU.isEqual(uuidRL))", uuidRU.isEqual(uuidRL));
	
	jum.assertTrue("(uuidTL.isEqual(uuidTU))", uuidTL.isEqual(uuidTU));
	jum.assertTrue("(uuidTU.isEqual(uuidTL))", uuidTU.isEqual(uuidTL));
}

function test_uuid_constructor() {
	var uuid, uuidToo;
	
	var nilUuid = '00000000-0000-0000-0000-000000000000';
	uuid = new dojo.uuid.Uuid();
	jum.assertTrue("'new dojo.uuid.Uuid()' returns the Nil UUID", (uuid == nilUuid));
	
	var randomUuidString = "3b12f1df-5232-4804-897e-917bf397618a";
	uuid = new dojo.uuid.Uuid(randomUuidString);
	jum.assertTrue('"uuid.isValid()" returns true', uuid.isValid());
	jum.assertTrue('"uuid.getVariant()" returns DCE', (uuid.getVariant() == dojo.uuid.Uuid.Variant.DCE));
	jum.assertTrue('"uuid.getVersion()" returns RANDOM', (uuid.getVersion() == dojo.uuid.Uuid.Version.RANDOM));
	uuidToo = new dojo.uuid.Uuid(new String(randomUuidString));
	jum.assertTrue('"uuid.isEqual(uuidToo)" returns true', uuid.isEqual(uuidToo));	

	var timeBasedUuidString = "b4308fb0-86cd-11da-a72b-0800200c9a66";
	uuid = new dojo.uuid.Uuid(timeBasedUuidString);
	jum.assertTrue('"uuid.isValid()" returns true', uuid.isValid());
	jum.assertTrue('"uuid.getVariant()" returns DCE', (uuid.getVariant() == dojo.uuid.Uuid.Variant.DCE));
	jum.assertTrue('"uuid.getVersion()" returns TIME_BASED', (uuid.getVersion() == dojo.uuid.Uuid.Version.TIME_BASED));
	jum.assertTrue('"uuid.getNode()" returns "0800200c9a66"', (uuid.getNode() == "0800200c9a66"));
	var timestamp = uuid.getTimestamp();
	var date = uuid.getTimestamp(Date);
	var dateString = uuid.getTimestamp(String);
	var hexString = uuid.getTimestamp("hex");
	var now = new Date();
	jum.assertTrue('uuid.getTimestamp() == uuid.getTimestamp(Date)', (timestamp == date));
	jum.assertTrue('uuid.getTimestamp("hex") == "1da86cdb4308fb0"', (hexString == "1da86cdb4308fb0"));
	jum.assertTrue('uuid.getTimestamp() < new Date()', (timestamp < now));
}

function test_uuid_generators() {
	var generators = [];
	generators.push(dojo.uuid.NilGenerator);
	generators.push(dojo.uuid.LightweightGenerator);
	generators.push(dojo.uuid.TimeBasedGenerator);
	
	for (var i in generators) {
		var generator = generators[i];
		
		var uuid, uuidString;
		uuidString = generator.generate();
		jum.assertTrue("generate() returns a string", ((typeof uuidString) == 'string'));
		checkValidityOfUuidString(uuidString);
		
		uuidString = generator.generate(String);
		jum.assertTrue("generate(String) returns a string", ((typeof uuidString) == 'string'));
		checkValidityOfUuidString(uuidString);

		uuid = generator.generate(dojo.uuid.Uuid);
		jum.assertTrue("generate(dojo.uuid.Uuid) returns a dojo.uuid.Uuid", (uuid instanceof dojo.uuid.Uuid));
		if (generator != dojo.uuid.NilGenerator) {
			jum.assertTrue('"uuid.getVariant()" returns DCE', (uuid.getVariant() == dojo.uuid.Uuid.Variant.DCE));
		}
		jum.assertTrue("uuid.isEqual(uuid)", uuid.isEqual(uuid));
		jum.assertTrue("uuid.compare(uuid) == 0", (uuid.compare(uuid) == 0));
		jum.assertTrue("dojo.uuid.Uuid.compare(uuid, uuid) == 0", (dojo.uuid.Uuid.compare(uuid, uuid) == 0));
		checkValidityOfUuidString(uuid.toString());
		jum.assertTrue("uuid.toString() works", uuid.toString().length == 36);
		jum.assertTrue("uuid.toString('{}') works", uuid.toString('{}').length == 38);
		jum.assertTrue("uuid.toString('()') works", uuid.toString('()').length == 38);
		jum.assertTrue("uuid.toString('\"\"') works", uuid.toString('""').length == 38);
		jum.assertTrue("uuid.toString(\"''\") works", uuid.toString("''").length == 38);
		jum.assertTrue("uuid.toString('!-') works", uuid.toString('!-').length == 32);
		jum.assertTrue("uuid.toString('urn') works", uuid.toString('urn').length == 45);

		if (generator != dojo.uuid.NilGenerator) {
			var uuidStringOne = generator.generate();
			var uuidStringTwo = generator.generate();
			jum.assertTrue("uuidStringOne != uuidStringTwo", uuidStringOne != uuidStringTwo);
			
			dojo.uuid.Uuid.setGenerator(generator);
			var uuidOne = new dojo.uuid.Uuid();
			var uuidTwo = new dojo.uuid.Uuid();
			jum.assertTrue("generator === dojo.uuid.Uuid.getGenerator()", generator === dojo.uuid.Uuid.getGenerator());
			dojo.uuid.Uuid.setGenerator(null);
			jum.assertTrue("uuidOne != uuidTwo", uuidOne != uuidTwo);
			jum.assertTrue("!uuidOne.isEqual(uuidTwo)", !uuidOne.isEqual(uuidTwo));
			jum.assertTrue("!uuidTwo.isEqual(uuidOne)", !uuidTwo.isEqual(uuidOne));
			
			var oneVsTwo = dojo.uuid.Uuid.compare(uuidOne, uuidTwo); // either 1 or -1
			var twoVsOne = dojo.uuid.Uuid.compare(uuidTwo, uuidOne); // either -1 or 1
			jum.assertTrue("oneVsTwo + twoVsOne == 0", (oneVsTwo + twoVsOne == 0));
			jum.assertTrue("oneVsTwo != 0", (oneVsTwo != 0));
			jum.assertTrue("twoVsOne != 0", (twoVsOne != 0));

			jum.assertTrue("!uuidTwo.isEqual(uuidOne)", !uuidTwo.isEqual(uuidOne));
		}
		
		if (generator == dojo.uuid.LightweightGenerator) {
			jum.assertTrue('"uuid.getVersion()" returns RANDOM', (uuid.getVersion() == dojo.uuid.Uuid.Version.RANDOM));
		}
		
		if (generator == dojo.uuid.TimeBasedGenerator) {
			checkValidityOfTimeBasedUuidString(uuid.toString());
			jum.assertTrue('"uuid.getVersion()" returns TIME_BASED', (uuid.getVersion() == dojo.uuid.Uuid.Version.TIME_BASED));
			jum.assertTrue('"uuid.getNode()" returns a string', dojo.lang.isString(uuid.getNode()));
			jum.assertTrue('"uuid.getNode()" returns a 12-character string', (uuid.getNode().length == 12));
			var timestamp = uuid.getTimestamp();
			var date = uuid.getTimestamp(Date);
			var dateString = uuid.getTimestamp(String);
			var hexString = uuid.getTimestamp("hex");
			jum.assertTrue('date instanceof Date', (date instanceof Date));
			jum.assertTrue('uuid.getTimestamp() == uuid.getTimestamp(Date)', (timestamp == date));
			jum.assertTrue('uuid.getTimestamp("hex").length == 15', (hexString.length == 15));
		}
	}
}

function test_uuid_nilGenerator() {
	var nilUuidString = '00000000-0000-0000-0000-000000000000';
	var uuidString = dojo.uuid.NilGenerator.generate();
	jum.assertTrue("nilUuidString == '00000000-0000-0000-0000-000000000000'", (uuidString == nilUuidString));
}

function test_uuid_timeBasedGenerator() {
	var uuid;   // an instance of dojo.uuid.Uuid
	var string; // a simple string literal
	var generate = dojo.uuid.TimeBasedGenerator.generate;
	
	var string01 = generate();
	var string02 = generate(String);
	var uuid1    = generate(dojo.uuid.Uuid);
	var string03 = generate("017bf397618a");
	var string04 = generate(new String("017BF397618A"));
	var string05 = generate({node: "017bf397618a"});         // hardwareNode
	var string06 = generate({node: "f17bf397618a"});         // pseudoNode
	var string07 = generate({hardwareNode: "017bf397618a"});
	var string08 = generate({pseudoNode:   "f17bf397618a"});
	var string09 = generate({node: "017bf397618a", returnType: String});
	var uuid2    = generate({node: "017bf397618a", returnType: dojo.uuid.Uuid});
	dojo.uuid.TimeBasedGenerator.setNode("017bf397618a");
	var string10 = generate(); // the generated UUID has node == "017bf397618a"
	var uuid3   = generate(dojo.uuid.Uuid); // the generated UUID has node == "017bf397618a"
	var returnedNode = dojo.uuid.TimeBasedGenerator.getNode();
	jum.assertTrue('returnedNode == "017bf397618a"', (returnedNode == "017bf397618a"));

	function getNode(string) {
		var arrayOfStrings = string.split('-');
		return arrayOfStrings[4];
	}

	checkForPseudoNodeBitInTimeBasedUuidString(string01);
	checkForPseudoNodeBitInTimeBasedUuidString(string02);
	checkForPseudoNodeBitInTimeBasedUuidString(uuid1.toString());
	jum.assertTrue('getNode(string03) == "017bf397618a"', (getNode(string03) == "017bf397618a"));
	jum.assertTrue('getNode(string04) == "017bf397618a"', (getNode(string04) == "017bf397618a"));
	jum.assertTrue('getNode(string05) == "017bf397618a"', (getNode(string05) == "017bf397618a"));
	jum.assertTrue('getNode(string06) == "f17bf397618a"', (getNode(string06) == "f17bf397618a"));
	jum.assertTrue('getNode(string07) == "017bf397618a"', (getNode(string07) == "017bf397618a"));
	jum.assertTrue('getNode(string08) == "f17bf397618a"', (getNode(string08) == "f17bf397618a"));
	jum.assertTrue('getNode(string09) == "017bf397618a"', (getNode(string09) == "017bf397618a"));
	jum.assertTrue('getNode(string10) == "017bf397618a" ~~~~ ' + getNode(string10), (getNode(string10) == "017bf397618a"));
	
	jum.assertTrue('uuid2.getNode() == "017bf397618a"', (uuid2.getNode() == "017bf397618a"));
	jum.assertTrue('uuid3.getNode() == "017bf397618a"', (uuid3.getNode() == "017bf397618a"));
	
	checkValidityOfTimeBasedUuidString(string01);
	checkValidityOfTimeBasedUuidString(string02);
	checkValidityOfTimeBasedUuidString(string03);
	checkValidityOfTimeBasedUuidString(string04);
	checkValidityOfTimeBasedUuidString(string05);
	checkValidityOfTimeBasedUuidString(string06);
	checkValidityOfTimeBasedUuidString(string07);
	checkValidityOfTimeBasedUuidString(string08);
	checkValidityOfTimeBasedUuidString(string09);
	checkValidityOfTimeBasedUuidString(string10);
	checkValidityOfTimeBasedUuidString(uuid1.toString());
	checkValidityOfTimeBasedUuidString(uuid2.toString());
	checkValidityOfTimeBasedUuidString(uuid3.toString());
}

function test_uuid_invalidUuids() {
	var uuidStrings = [];
	uuidStrings.push("Hello world!");                          // not a UUID
	uuidStrings.push("3B12F1DF-5232-1804-897E-917BF39761");    // too short
	uuidStrings.push("3B12F1DF-5232-1804-897E-917BF39761-8A"); // extra '-'
	uuidStrings.push("3B12F1DF-5232-1804-897E917BF39761-8A");  // last '-' in wrong place
	uuidStrings.push("HB12F1DF-5232-1804-897E-917BF397618A");  // "HB12F1DF" is not a hex string

	var numberOfFailures = 0;
	for (var i in uuidStrings) {
		var uuidString = uuidStrings[i];
		try {
			new dojo.uuid.Uuid(uuidString);
		} catch (e) {
			++numberOfFailures;
		}
	}
	jum.assertTrue('All of the "new dojo.uuid.Uuid()" calls failed', (numberOfFailures == uuidStrings.length));
}

// -------------------------------------------------------------------
// Helper functions
// -------------------------------------------------------------------

function checkValidityOfUuidString(uuidString) {
	var NIL_UUID = "00000000-0000-0000-0000-000000000000";
	if (uuidString == NIL_UUID) {
		// We'll consider the Nil UUID to be valid, so now 
		// we can just return, with not further checks.
		return;
	}
	
	jum.assertTrue('UUIDs have 36 characters', (uuidString.length == 36));

	var validCharacters = "0123456789abcedfABCDEF-";
	var character;
	var position;
	for (var i = 0; i < 36; ++i) {
		character = uuidString.charAt(i);
		position = validCharacters.indexOf(character);
		jum.assertTrue('UUIDs have only valid characters', (position != -1));
	}

	var arrayOfParts = uuidString.split("-");
	jum.assertTrue('UUIDs have 5 sections separated by 4 hyphens', (arrayOfParts.length == 5));
	jum.assertTrue('Section 0 has 8 characters', (arrayOfParts[0].length == 8));
	jum.assertTrue('Section 1 has 4 characters', (arrayOfParts[1].length == 4));
	jum.assertTrue('Section 2 has 4 characters', (arrayOfParts[2].length == 4));
	jum.assertTrue('Section 3 has 4 characters', (arrayOfParts[3].length == 4));
	jum.assertTrue('Section 4 has 8 characters', (arrayOfParts[4].length == 12));

	// check to see that the "UUID variant code" starts with the binary bits '10'
	var section3 = arrayOfParts[3];
	var hex3 = parseInt(section3, dojo.uuid.Uuid.HEX_RADIX);
	var binaryString = hex3.toString(2);
	// alert("section3 = " + section3 + "\n binaryString = " + binaryString);
	jum.assertTrue('section 3 has 16 bits', binaryString.length == 16);
	jum.assertTrue("first bit of section 3 is 1", binaryString.charAt(0) == '1');
	jum.assertTrue("second bit of section 3 is 0", binaryString.charAt(1) == '0');
}

function checkValidityOfTimeBasedUuidString(uuidString) {
	checkValidityOfUuidString(uuidString);
	var arrayOfParts = uuidString.split("-");
	var section2 = arrayOfParts[2];
	jum.assertTrue('Section 2 starts with a 1', (section2.charAt(0) == "1"));
}

function checkForPseudoNodeBitInTimeBasedUuidString(uuidString) {
	var arrayOfParts = uuidString.split("-");
	var section4 = arrayOfParts[4];
	var firstChar = section4.charAt(0);
	var hexFirstChar = parseInt(firstChar, dojo.uuid.Uuid.HEX_RADIX);
	var binaryString = hexFirstChar.toString(2);
	var firstBit;
	if (binaryString.length == 4) {
		firstBit = binaryString.charAt(0);
	} else {
		firstBit = '0';
	}
	jum.assertTrue("first bit of section 4 is 1", firstBit == '1');
}

/*
function test_uuid_get64bitArrayFromFloat() {
	var x = Math.pow(2, 63) + Math.pow(2, 15);
	var result = dojo.uuid.TimeBasedUuid._get64bitArrayFromFloat(x);
	jum.assertTrue("result[0] == 0x8000", result[0] === 0x8000);
	jum.assertTrue("result[1] == 0x0000", result[1] === 0x0000);
	jum.assertTrue("result[2] == 0x0000", result[2] === 0x0000);
	jum.assertTrue("result[3] == 0x8000", result[3] === 0x8000);

	var date = new Date();
	x = date.valueOf();
	result = dojo.uuid.TimeBasedUuid._get64bitArrayFromFloat(x);
	var reconstructedFloat = result[0];
	reconstructedFloat *= 0x10000;
	reconstructedFloat += result[1];
	reconstructedFloat *= 0x10000;
	reconstructedFloat += result[2];
	reconstructedFloat *= 0x10000;
	reconstructedFloat += result[3];

	jum.assertTrue("reconstructedFloat === x", reconstructedFloat === x);
	// dojo.log.debug("leaving test_uuid_get64bitArrayFromFloat()");
}

function test_uuid_addTwo64bitArrays() {
	var a = [0x0000, 0x0000, 0x0000, 0x0001];
	var b = [0x0FFF, 0xFFFF, 0xFFFF, 0xFFFF];
	var result = dojo.uuid.TimeBasedUuid._addTwo64bitArrays(a, b);
	jum.assertTrue("20", result[0] === 0x1000);
	jum.assertTrue("21", result[1] === 0x0000);
	jum.assertTrue("22", result[2] === 0x0000);
	jum.assertTrue("23", result[3] === 0x0000);

	a = [0x4000, 0x8000, 0x8000, 0x8000];
	b = [0x8000, 0x8000, 0x8000, 0x8000];
	result = dojo.uuid.TimeBasedUuid._addTwo64bitArrays(a, b);
	jum.assertTrue("24", result[0] === 0xC001);
	jum.assertTrue("25", result[1] === 0x0001);
	jum.assertTrue("26", result[2] === 0x0001);
	jum.assertTrue("27", result[3] === 0x0000);

	a = [7, 6, 2, 5];
	b = [1, 0, 3, 4];
	result = dojo.uuid.TimeBasedUuid._addTwo64bitArrays(a, b);
	jum.assertTrue("28", result[0] === 8);
	jum.assertTrue("29", result[1] === 6);
	jum.assertTrue("30", result[2] === 5);
	jum.assertTrue("31", result[3] === 9);
	// dojo.log.debug("leaving test_uuid_addTwo64bitArrays()");
}

function test_uuid_multiplyTwo64bitArrays() {
	var a = [     0, 0x0000, 0x0000, 0x0003];
	var b = [0x1111, 0x1234, 0x0000, 0xFFFF];
	var result = dojo.uuid.TimeBasedUuid._multiplyTwo64bitArrays(a, b);
	jum.assertTrue("40", result[0] === 0x3333);
	jum.assertTrue("41", result[1] === 0x369C);
	jum.assertTrue("42", result[2] === 0x0002);
	jum.assertTrue("43", result[3] === 0xFFFD);

	a = [0, 0, 0, 5];
	b = [0, 0, 0, 4];
	result = dojo.uuid.TimeBasedUuid._multiplyTwo64bitArrays(a, b);
	jum.assertTrue("44", result[0] === 0);
	jum.assertTrue("45", result[1] === 0);
	jum.assertTrue("46", result[2] === 0);
	jum.assertTrue("47", result[3] === 20);

	a = [0, 0, 2, 5];
	b = [0, 0, 3, 4];
	result = dojo.uuid.TimeBasedUuid._multiplyTwo64bitArrays(a, b);
	jum.assertTrue("48", result[0] === 0);
	jum.assertTrue("49", result[1] === 6);
	jum.assertTrue("50", result[2] === 23);
	jum.assertTrue("51", result[3] === 20);
	// dojo.log.debug("leaving test_uuid_multiplyTwo64bitArrays()");
}
*/
