/*
	Copyright (c) 2004-2006, The Dojo Foundation
	All Rights Reserved.

	Licensed under the Academic Free License version 2.1 or above OR the
	modified BSD license. For more information on Dojo licensing, see:

		http://dojotoolkit.org/community/licensing.shtml
*/

dojo.provide("tests.MockXMLHttpRequest");

/* summary:
 *   MockXMLHttpRequest implements the XMLHttpRequest interface to allow testing 
 *   without having to run a server. It can work with dojo.io.bind and
 *   dojo.hostenv.getText by using the setMockXMLHttpRequest() function to 
 *   set dojo.hostenv.getXmlhttpObject use a MockXMLHTTPRequest.
 *   tests.MockXMLHttpRequest.restore() restores the original one.
 */
 
/*
examples:
	var responseText = "this is a test!";
	tests.MockXMLHttpRequest.set(responseText, 1000); //simulate a 1 sec response time
	dojo.hostenv.getText('urn:this_is_ignored', 
		function(data) { 
			jum.assertTrue(data == responseText);
		});	
	tests.MockXMLHttpRequest.restore(); 

	tests.MockXMLHttpRequest.set(function(xhr) { return xhr.data; }, 100);  
	var postData = "test post data";
	dojo.io.bind({
		url: "urn:ignore", 
		method :"post",
		postContent :  postData,
		mimetype: "text/plain" ,		
		handle: function(type, data, evt) {
			if(type == "load"){
				jum.assertTrue(data == postData);
			}
		}
	}); 
	tests.MockXMLHttpRequest.restore(); 
*/

dojo.require('dojo.event.*');

tests.MockXMLHttpRequest = function(responseText, /* milliseconds */ responseTime, responseXml) {
	if (typeof responseText == "function") {
		this._responseFunc = responseText; 
		this.responseText= null;
	} else {
		this.responseText=responseText;
		this._responseFunc = null;
	}	 
	this._responseHeaders = '';
	this.responseXml= responseXml; //note: this isn't used by BrowserIO
	this._delay = responseTime;
	this.readyState = 0; 
	this.onreadystatechange = null;
	this._timeout = null;
	this._timeoutFunc = null;
	this._aborted = false;

	this.open = function(method, url, async) { 
		this._async = async;
		this.readyState = 1; 
		this.url = url;
	};

	this._finish  = function() {
	    if (this._aborted)
	       return;
		this.readyState = 4;
		this.status = 200;
		this.statusText = "OK"; 
		if (this._responseFunc)
			this.responseText = this._responseFunc(this);
		if (this.onreadystatechange)
			 this.onreadystatechange(this);
	 };
		 
	this.send = function(data) { 
	    this._aborted = false;
		this.data = data;
		if (this._async !== undefined && !this._async)	{
			this._finish();
		 } else {
			this.readyState = 2;
			var self = this;
			this._timeout = setTimeout( function() { 
				self._timeout = null; self._finish(); 
			}, this._delay);

		}
	};

	this.abort = function() {
	    this._aborted = true;
		this.readyState = 0;
		if (this._timeout) {
			clearTimeout(this._timeout);
			this._timeout = null;
		}
	};

	this.getAllResponseHeaders = function() { return this._responseHeaders; }
	this.getResponseHeader = function(header) { return ""; }
	this.setRequestHeader = function(header, value) {  }

};

tests.MockXMLHttpRequest._originalXmlhttpObjectGetter = dojo.hostenv.getXmlhttpObject;

tests.MockXMLHttpRequest.set = function(responseTextOrFunc, /* milliseconds */responseTime,
	responseXml) {
	var oldFunc = dojo.hostenv.getXmlhttpObject;
	dojo.hostenv.getXmlhttpObject  = function() {
		return new tests.MockXMLHttpRequest(responseTextOrFunc, 
			responseTime, responseXml); 
	}
	return oldFunc;
}

tests.MockXMLHttpRequest.restore = function() {
	dojo.hostenv.getXmlhttpObject = tests.MockXMLHttpRequest._originalXmlhttpObjectGetter;
}

tests.MockXMLHttpRequest.wrap = function(scope, func, responseTextOrFunc, responseTime, responseXml) {
	 var disconnectHack = false;  
	 //disconnect is broken!: hasAdvice is doesn't find the advice 
	 //because "__0" != "__0$joinpoint$method"
     var aroundFunc = function(invocation) {
     	if (!disconnectHack)
        	tests.MockXMLHttpRequest.set(responseTextOrFunc, responseTime, responseXml);
        try {
            var result = invocation.proceed();
        } finally { 
            var ret = dojo.event.disconnect("around", scope, func, aroundFunc);
            if (!disconnectHack)
            	tests.MockXMLHttpRequest.restore();
            disconnectHack = true;
        }
        return result;
    };
    dojo.event.connect("around", scope, func, aroundFunc);
}

if (dojo.hostenv.name_ == 'rhino') {
	var _orginalRhinoIOBind = null;
	var _currentMockRequests = {};

	function _rhinoIOBind(kwArgs) {			
		var tid = java.lang.Thread.currentThread().toString();
		if (!_currentMockRequests[tid]) 
			return _orginalRhinoIOBind.call(this, kwArgs);
	
		var async = kwArgs["sync"] ? false : true;
		var http = dojo.hostenv.getXmlhttpObject(kwArgs);
		//dojo.debug('get mock ' + tid + ' ' + http.responseText);
			
		var query = "";
		if (kwArgs.postContent) 
			query = kwArgs.postContent
		query += dojo.io.argsFromMap(kwArgs["content"] || {},
							kwArgs.encoding);
		
		http.onreadystatechange = function() {
			if (http.readyState != 4)
				return;
			
			var ret;
			if (kwArgs.method.toLowerCase() == "head"){
				// TODO: return the headers
			}else{
				var text = http.responseText;
				if(kwArgs.mimetype == "text/javascript"){
					try{
						ret = dj_eval(text);
					}catch(e){
						dojo.debug(e);
						dojo.debug(text);
						ret = null;
					}
				}else if(kwArgs.mimetype == "text/json"){
					try{
						ret = dj_eval("("+text+")");
					}catch(e){
						dojo.debug(e);
						dojo.debug(text);
						ret = false;
					}
				}else{
					ret = text;
				}
				(kwArgs.load || kwArgs.handle)("load", ret, kwArgs);
			}
		}
		http.open('ignored', 'ignored', async);
		http.send(query);
		kwArgs.abort = function() { http.abort(); };
	}
	
	dojo.hostenv.getXmlhttpObject  = function() {
		var tid = java.lang.Thread.currentThread().toString();
		var mockRequest = _currentMockRequests[tid];
		if (mockRequest) { 
		 	return new MockXMLHTTPRequest(mockRequest[0],mockRequest[1],
		 			mockRequest[2]);
		}else{
			return null; //hostenv doesn't define getXmlhttpObject
		} 
	}

	var _setMockXMLHttpRequest = tests.MockXMLHttpRequest.set;
	tests.MockXMLHttpRequest.set = function(responseTextOrFunc, /* milliseconds */responseTime,
		responseXml) {
		if (!_orginalRhinoIOBind) {
			_orginalRhinoIOBind = dojo.io.RhinoHTTPTransport.bind;
			dojo.io.RhinoHTTPTransport.bind = _rhinoIOBind;
		}
		var tid = java.lang.Thread.currentThread().toString();
		//dojo.debug( 'set mock ' + tid + ' ' + responseTextOrFunc); 
		_currentMockRequests[tid] = arguments;
		_setMockXMLHttpRequest.apply(dj_global, arguments);
	}

	var _restoreXMLHttpRequest = tests.MockXMLHttpRequest.restore;
	tests.MockXMLHttpRequest.restore = function() {
		var tid = java.lang.Thread.currentThread().toString();
		if (_currentMockRequests[tid]) {
			//dojo.debug( 'delete mock ' + tid); 
			delete _currentMockRequests[tid];
		}
		_restoreXMLHttpRequest();
	}
} 



