/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.widget.ComboBox");
dojo.require("dojo.logging.Logger");

var comboData = [
	["Alabama","AL"],
	["Alaska","AK"],
	["American Samoa","AS"],
	["Arizona","AZ"],
	["Arkansas","AR"],
	["Armed Forces Europe","AE"],
	["Armed Forces Pacific","AP"],
	["Armed Forces the Americas","AA"],
	["California","CA"],
	["Colorado","CO"],
	["Connecticut","CT"],
	["Delaware","DE"],
	["District of Columbia","DC"],
	["Federated States of Micronesia","FM"],
	["Florida","FL"],
	["Georgia","GA"],
	["Guam","GU"],
	["Hawaii","HI"],
	["Idaho","ID"],
	["Illinois","IL"],
	["Indiana","IN"],
	["Iowa","IA"],
	["Kansas","KS"],
	["Kentucky","KY"],
	["Louisiana","LA"],
	["Maine","ME"],
	["Marshall Islands","MH"],
	["Maryland","MD"],
	["Massachusetts","MA"],
	["Michigan","MI"],
	["Minnesota","MN"],
	["Mississippi","MS"],
	["Missouri","MO"],
	["Montana","MT"],
	["Nebraska","NE"],
	["Nevada","NV"],
	["New Hampshire","NH"],
	["New Jersey","NJ"],
	["New Mexico","NM"],
	["New York","NY"],
	["North Carolina","NC"],
	["North Dakota","ND"],
	["Northern Mariana Islands","MP"],
	["Ohio","OH"],
	["Oklahoma","OK"],
	["Oregon","OR"],
	["Pennsylvania","PA"],
	["Puerto Rico","PR"],
	["Rhode Island","RI"],
	["South Carolina","SC"],
	["South Dakota","SD"],
	["Tennessee","TN"],
	["Texas","TX"],
	["Utah","UT"],
	["Vermont","VT"],
	["Virgin Islands, U.S.","VI"],
	["Virginia","VA"],
	["Washington","WA"],
	["West Virginia","WV"],
	["Wisconsin","WI"],
	["Wyoming","WY"]
];

function test_combobox_ctor(){
	var b1 = new dojo.widget.ComboBox();

	jum.assertEquals(typeof b1, "object");
	jum.assertEquals(b1.widgetType, "ComboBox");
	jum.assertEquals(typeof b1["attachProperty"], "undefined");
}

function test_combobox_dataprovider(){
	var box = new dojo.widget.ComboBox();

	jum.assertEquals(typeof dojo.widget.basicComboBoxDataProvider, "function");
	jum.assertTrue(comboData.length > 40);
	
	var provider = new dojo.widget.basicComboBoxDataProvider();
	provider.setData(comboData);
	
	jum.assertEquals(30, provider.searchLimit);

	// test the results of our search
	var searchTester = function(data){
		var expectedReturns = [
			["Washington","WA"],
			["West Virginia","WV"],
			["Wisconsin","WI"],
			["Wyoming","WY"]
		];

		var expectedLabels = [];
		for(var x=0; x<expectedReturns.length; x++){
			expectedLabels.push(expectedReturns[x][0]);
		}
		jum.assertEquals(4, data.length);
		for(var x=0; x<data.length; x++){
			jum.assertTrue(dojo.lang.find(expectedLabels, data[x][0]) != -1);
		}
	}
	
	provider.startSearch("W", searchTester);
}
