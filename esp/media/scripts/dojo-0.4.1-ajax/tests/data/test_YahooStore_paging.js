/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.lang.type");
dojo.require("dojo.data.YahooStore");

gui = {
	runSearch: function() {
		var searchTermField = document.getElementById("searchTermField");
		this.queryString = searchTermField.value;
		this.currentItem = 1;
		this.itemsPerPage = 5;
		this.store = new dojo.data.YahooStore();
		//the query just fetches 1 item, used to get total size
		var self = this;
		this.result = this.store.find({
			query: this.queryString,
			sync: false,
			scope: this,
			oncompleted:
				function(result) { self.result = result; self.displayPage(); }
		}); 
		
		//this.result.setOnFindCompleted(this.displayPage, this);
	},
	showPreviousPage: function() {
		this.currentItem -= this.itemsPerPage;
		if (this.currentItem < 0) {this.currentItem = 0; };
		this.displayPage();
	},
	showNextPage: function() {
		this.currentItem += this.itemsPerPage;
		this.displayPage();
	},
	
	displayPage: function() {
		//this.result.setOnFindCompleted(null);
		//dojo.debug("displayPage " +dojo.json.serialize( this.result.resultMetadata) );
		var min = this.currentItem;
		var max = min + this.itemsPerPage - 1;
		var total = this.result.resultMetadata.totalResultsAvailable;
		this.textArray = [];
		this.textArray.push('<p>Showing results ' + min + ' to ' + max + ' of ' + total + '</p>');
		this.textArray.push('<table style="background-color:#EEEEEE; border-collapse:collapse">');
		this.textArray.push('<tr>');
		this.textArray.push('<td>');
		this.textArray.push('<input type="button" value="Previous Page" ');
		if (min == 1) {
			this.textArray.push('disabled>');
		} else {
			this.textArray.push('onclick="gui.showPreviousPage();">');
		}
		this.textArray.push('</td>');
		this.textArray.push('</tr>');
				
		this.result.start = this.currentItem;
		this.result.count = this.itemsPerPage
		this.result.onnext = this.displayItem,
		this.result.oncompleted = null;
		this.result = this.store.find( this.result );
				//this.result.forEach(this.displayItem, this, {start:this.currentItem, count:this.itemsPerPage})
	},
	
	displayItem: function(item, result) {
		var url = this.store.get(item, 'Url');
		var title = this.store.get(item, 'Title');
		var summary = this.store.get(item, 'Summary');
		//dojo.debug( dojo.json.serialize(item));
		//var identity = this.store.getIdentity(item);
		this.textArray.push('<tr style="border: 2px #FFFFFF solid">');
		this.textArray.push('<td>' + (parseInt(item)+1) + '</td>');
		this.textArray.push('<td width="25%"><a href="' + url + '">' + title + '</a></td>');
		this.textArray.push('<td width="70%">' + summary + '</td>');
		this.textArray.push('</tr>');
		var output = this.textArray.join('\n');
		if (!this.tailEndText) {
			this.tailEndText = '<tr>';
			this.tailEndText += '<td colspan="2">';
			this.tailEndText += '<input type="button" value="Next Page" onclick="gui.showNextPage();">';
			this.tailEndText += '</td>';
			this.tailEndText += '</tr>';
			this.tailEndText += '</table>';
		}
		output += this.tailEndText; 
		var outputDiv = document.getElementById("outputDiv");
		outputDiv.innerHTML = output;
	}
};


