
/*
 * general use functions
 */
ESP.Utilities = function(){
    var Utilities = {};
    
    Utilities.EventManager = function(){
	var evm = {};
	evm._jq_obj = $j(evm);
	evm.bind = function(type, data, fn) {
	    evm._jq_obj.bind(type, data, fn);
	};
	evm.fire = function(type, data) {
	    if (!$j.isArray(data)) var data = [data];
	    evm._jq_obj.triggerHandler(type, data);
	};
	evm.unbind = function(type, fn) {
	    evm._jq_obj.unbind(type, fn);
	};
	return evm;
    };
    
    Utilities.evm = Utilities.EventManager();
    
    return Utilities;
}();

/*
 * JQuery extensions
 */
$j.extend({
	check : function(variable) {
	    return typeof variable != 'undefined' && variable;
	},
	getDefault : function(dict, key, def) {
	    return ((typeof dict[key] != 'undefined') && dict[key]) || (dict[key] = def);
	}
});


/*
 * language extensions
 */
if (!Array.prototype.contains) {
    Array.prototype.contains = function(value){
	return $j.inArray(value, this) != -1;
    };
}
function cmp(one,two) {
    return one === two ? 0 : ( one > two ? 1 : -1 );
}
