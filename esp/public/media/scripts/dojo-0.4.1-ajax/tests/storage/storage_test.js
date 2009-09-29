/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.require("dojo.dom");
dojo.require("dojo.io.*");
dojo.require("dojo.event.*");
dojo.require("dojo.html.*");
dojo.require("dojo.lfx.*");
dojo.require("dojo.storage.*");

var TestStorage = {
	currentProvider: "default",
	
	initialize: function(){
		//dojo.debug("test_storage.initialize()");
		
		// clear out old values and enable input forms
		dojo.byId("storageKey").value = "";
		dojo.byId("storageKey").disabled = false;
		dojo.byId("storageValue").value = "";
		dojo.byId("storageValue").disabled = false;
		
		// write out our available keys
		this._printAvailableKeys();
		
		// initialize our event handlers
		var directory = dojo.byId("directory");
		dojo.event.connect(directory, "onchange", this, this.directoryChange);
		var storageValueElem = dojo.byId("storageValue");
		dojo.event.connect(storageValueElem, "onkeyup", this, this.printValueSize);
		
		// make the directory be unselected if the key name field gets focus
		var keyNameField = dojo.byId("storageKey");
		dojo.event.connect(keyNameField, "onfocus", function(evt){
			directory.selectedIndex = -1;
		}); 		
											 
		// add onclick listeners to all of our buttons
		var buttonContainer = dojo.byId("buttonContainer");
		var currentChild = buttonContainer.firstChild;
		while (currentChild.nextSibling != null){
			if (currentChild.nodeType == dojo.dom.ELEMENT_NODE){
				var buttonName = currentChild.id;
				var functionName = buttonName.match(/^(.*)Button$/)[1];
				dojo.event.connect(currentChild, "onclick", this, this[functionName]);
				currentChild.disabled = false;
			}		
			
			currentChild = currentChild.nextSibling;
		}
		
		// print out metadata
		this._printProviderMetadata();
		
		// disable the configuration button if none is supported for this provider
		if(dojo.storage.hasSettingsUI() == false){
			dojo.byId("configureButton").disabled = true;	
		}
	},
	
	directoryChange: function(evt){
		var key = evt.target.value;
		
		// add this value into the form
		var keyNameField = dojo.byId("storageKey");
		keyNameField.value = key;
		
		this._handleLoad(key);		
	},
	
	load: function(evt){
		// cancel the button's default behavior
		evt.preventDefault();
		evt.stopPropagation();
		
		// get the key to load
		var key = dojo.byId("storageKey").value;
		
		if(key == null || typeof key == "undefined" || key == ""){
			alert("Please enter a key name");
			return;
		}
		
		this._handleLoad(key);
	},
	
	save: function(evt){
		// cancel the button's default behavior
		evt.preventDefault();
		evt.stopPropagation();
		
		// get the new values
		var key = dojo.byId("storageKey").value;
		var value = dojo.byId("storageValue").value;
		
		if(key == null || typeof key == "undefined" || key == ""){
			alert("Please enter a key name");
			return;
		}
		
		if(value == null || typeof value == "undefined" || value == ""){
			alert("Please enter a key value");
			return;
		}
		
		// print out the size of the value
		this.printValueSize(); 
		
		// do the save
		this._save(key, value)
	},
	
	clear: function(evt){
		// cancel the button's default behavior
		evt.preventDefault();
		evt.stopPropagation();
		
		dojo.storage.clear();
		
		this._printStatus("Cleared");
		this._printAvailableKeys();
	},
	
	configure: function(evt){
		// cancel the button's default behavior
		evt.preventDefault();
		evt.stopPropagation();
		
		if(dojo.storage.hasSettingsUI()){
			// redraw our keys after the dialog is closed, in
			// case they have all been erased
			var self = this;
			dojo.storage.onHideSettingsUI = function(){
				self._printAvailableKeys();
			}
			
			// show the dialog
			dojo.storage.showSettingsUI();
		}
	},
	
	remove: function(evt){
		// cancel the button's default behavior
		evt.preventDefault();
		evt.stopPropagation();
		
		// determine what key to delete; if the directory has a selected value,
		// use that; otherwise, use the key name field
		var directory = dojo.byId("directory");
		var keyNameField = dojo.byId("storageKey");
		var keyValueField = dojo.byId("storageValue");
		var key;
		if(directory.selectedIndex != -1){
			key = directory.value;
			// delete this option
			var options = directory.childNodes;
			for(var i = 0; i < options.length; i++){
				if(options[i].nodeType == dojo.dom.ELEMENT_NODE &&
					 options[i].value == key){
					directory.removeChild(options[i]);
					break;
				}
			}
		}else{
			key = keyNameField.value;
		}
		
		keyNameField.value = "";
		keyValueField.value = "";
		
		// now delete the value
		this._printStatus("Removing '" + key + "'...");
		dojo.storage.remove(key);
		this._printStatus("Removed '" + key);
	},
	
	printValueSize: function(){
		var storageValue = dojo.byId("storageValue").value;
		var size = 0;
		if(storageValue != null && !dojo.lang.isUndefined(storageValue)){
			size = storageValue.length;
		}
		
		// determine the units we are dealing with
		var units;
		if(size < 1024)
			units = " bytes";
		else{
			units = " K";
			size = size / 1024;
			size = Math.round(size);
		}
		
		size = size + units;
		
		var valueSize = dojo.byId("valueSize");
		valueSize.innerHTML = size;
	},
	
	saveBook: function(evt){
		this._printStatus("Loading book...");
		var self = this;
		dojo.io.bind({
				url: "resources/testBook.txt",
				load: function(type, data, evt){
					self._printStatus("Book loaded");
					self._save("testBook", data);
				},
				error: function(type, error){ 
					alert("Unable to load testBook.txt");
				},
				mimetype: "text/plain"
		});
		
		if(!dojo.lang.isUndefined(evt) && evt != null){
			evt.preventDefault();
			evt.stopPropagation();
		}
		
		return false;
	},
	
	saveXML: function(evt){
		this._printStatus("Loading XML...");
		var self = this;
		dojo.io.bind({
				url: "../flash/resources/test.xml",
				load: function(type, data, evt){
					self._printStatus("XML loaded");
					self._save("testXML", data);
				},
				error: function(type, error){ 
					alert("Unable to load test.XML");
				},
				mimetype: "text/plain"
		});
		
		if(!dojo.lang.isUndefined(evt) && evt != null){
			evt.preventDefault();
			evt.stopPropagation();
		}
		
		return false;
	},
	
	_save: function(key, value){
		this._printStatus("Saving '" + key + "'...");
		var self = this;
		var saveHandler = function(status, keyName){
			if(status == dojo.storage.FAILED){
				alert("You do not have permission to store data for this web site. "
			        + "Press the Configure button to grant permission.");
			}else if(status == dojo.storage.SUCCESS){
				// clear out the old value
				dojo.byId("storageKey").value = "";
				dojo.byId("storageValue").value = "";
				self._printStatus("Saved '" + key + "'");
				
				// update the list of available keys
				// put this on a slight timeout, because saveHandler is called back
				// from Flash, which can cause problems in Flash 8 communication
				// which affects Safari
				// FIXME: Find out what is going on in the Flash 8 layer and fix it
				// there
				window.setTimeout(function(){ self._printAvailableKeys() }, 1);
			}
		};
		try{
			dojo.storage.put(key, value, saveHandler);
		}catch(exp){
			alert(exp);
		}
	},
	
	_printAvailableKeys: function(){
		var directory = dojo.byId("directory");
		
		// clear out any old keys
		directory.innerHTML = "";
		
		// add new ones
		var availableKeys = dojo.storage.getKeys();
		for (var i = 0; i < availableKeys.length; i++){
			var optionNode = document.createElement("option");
			optionNode.appendChild(document.createTextNode(availableKeys[i]));
			optionNode.value = availableKeys[i];
			directory.appendChild(optionNode);
		}
	},
	
	_handleLoad: function(key){
		this._printStatus("Loading '" + key + "'...");
		
		// get the value
		var results = dojo.storage.get(key);
		
		// print out its value
		this._printStatus("Loaded '" + key + "'");
		dojo.byId("storageValue").value = results;
		
		// print out the size of the value
		this.printValueSize(); 
	},
	
	_printProviderMetadata: function(){
		var storageType = dojo.storage.getType();
		var isSupported = dojo.storage.isAvailable();
		var maximumSize = dojo.storage.getMaximumSize();
		var permanent = dojo.storage.isPermanent();
		var uiConfig = dojo.storage.hasSettingsUI();
		var moreInfo = "";
		if(dojo.storage.getType() == "dojo.storage.FlashStorageProvider"){
			moreInfo = "Flash Comm Version " + dojo.flash.info.commVersion;
		}
		
		dojo.byId("currentStorageProvider").innerHTML = storageType;
		dojo.byId("isSupported").innerHTML = isSupported;
		dojo.byId("isPersistent").innerHTML = permanent;
		dojo.byId("hasUIConfig").innerHTML = uiConfig;
		dojo.byId("maximumSize").innerHTML = maximumSize;
		dojo.byId("moreInfo").innerHTML = moreInfo;
	},
	
	_printStatus: function(message){
		// remove the old status
		var top = dojo.byId("top");
		for (var i = 0; i < top.childNodes.length; i++){
			var currentNode = top.childNodes[i];
			if (currentNode.nodeType == dojo.dom.ELEMENT_NODE &&
					currentNode.className == "status"){
				top.removeChild(currentNode);
			}		
		}
		
		var status = document.createElement("span");
		status.className = "status";
		status.innerHTML = message;
		
		top.appendChild(status);
		dojo.lfx.fadeOut(status, 2000).play();
	}
};

// wait until the storage system is finished loading
if(dojo.storage.manager.isInitialized() == false){ // storage might already be loaded when we get here
	dojo.event.connect(dojo.storage.manager, "loaded", TestStorage, 
	                  TestStorage.initialize);
}else{
	dojo.event.connect(dojo, "loaded", TestStorage, TestStorage.initialize);
}
