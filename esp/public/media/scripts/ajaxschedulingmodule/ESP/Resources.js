
ESP.declare('ESP.Scheduling.Resources',function(){
	var Resources = {};
	var uid = 0;
	Resources.__cache__ = {};
	Resources.create = function(type, extra, id) {
	    var extra = extra || {};
	    var id = id || extra['id'] || extra['uid'] || type+(++uid);
	    extra['uid'] = id;
	    return $j.getDefault(this.__cache__,type,{})[id] = new this[type](extra);
	};
	Resources.get = function(type, id) {
	    return this.__cache__[type][id];
	}
	
	var RClass = Class.create({
	    type: "Resource",
	    initialize: function(extra){
		    // provide auto-configure of data
		    //this.__data__ = {};
		    //$j.extend(this.__data__, this.__defaults__);
		    //$j.extend(this.__data__, extra);
		    $j.extend(this, this.__defaults__);
		    $j.extend(this, extra);
		},
	    // manage access to data [edit - bypassed for now]
	    get: function(key){
		    return this.__data__[key];
		},
	    set: function(key, value){
		    var old_value = this.get(key);
		    this.__set__(key, value);
		    ESP.Utilities.evm.fire("property-changed", {
			    target: this,
				name: key,
				action: "set",
				old_value: old_value,
				new_value: value
			});
		},
	    __set__: function(key, value){
		    this.__data__[key] = value;
		},
	    append: function(key, value){
		    if (!this.__append__(key, value)) return;
		    ESP.Utilities.evm.fire("property-changed", {
			    target: this,
				name: key,
				action: "append",
				array: this.get(key),
				new_value: value
			});
		},
	    __append__: function(key, value){
		    var arr = this.__data__[key];
		    if (!arr) {
			this.__data__[key] = [value];
			return true;
		    }
		    else if (!arr.contains(value)) {
			this.__data__[key].push(value);
			return true;
		    }
		    return false;
		},
	    remove: function(key, value){
		    if (!this.__remove__(key, value)) return;
		    ESP.Utilities.evm.fire("property-changed", {
			    target: this,
				name: key,
				action: "append",
				array: this.get(key),
				new_value: value
			});
		},
	    __remove__: function(key, value){
		    var arr = this.__data__[key];
		    if (arr && arr.contains(value)) {
			this.__data__[key].remove(value);
			return true;
		    }
		    return false;
		}
	});
	
	Resources.Time = Class.create(RClass, {
		type: "Time",
		__defaults__: {
		    start: -1,
		    end: -1,
		    text: ""
		}
	    });
	Resources.Time.sequential = function(t1, t2) {
	    return t1.end <= t2.start && t2.start - t1.end < 11*60000; // account for +-5 min
	    //return t1.end == t2.start;
	};
	
	Resources.Room = Class.create(RClass, {
		type: "Room",
		__defaults__: {
		    location: "",
		    text: ""
		}
	    });
	
	Resources.BlockStatus = {
	    NOT_OURS: 1,
	    AVAILABLE: 2,
	    RESERVED: 4
	};
	
	Resources.Block = Class.create(RClass, {
		type: "Block",
		__defaults__: {
		    room: null,
		    time: null,
		    status: Resources.BlockStatus.NOT_OURS
		}
	    });
	
	Resources.Teacher = Class.create(RClass, {
		type: "Teacher",
		__defaults__: {
		    sections: [],
		    available_times: [],
		}
	    });
	
	Resources.Section = Class.create(RClass, {
		type: "Section",
		__defaults__: {
		    teachers: [],
		    blocks: [],
		    length: -1
		}
	    });
	
	Resources.RoomResource = Class.create(RClass, {
	        type: "RoomResource",
	        __defaults__: {
	            attributes: []
	        }
	    });
	
	Resources.Generic = Class.create(RClass, {
		type: "Generic",
		__defaults__: {
		    // not implemented yet
		}
	    });

	return Resources;
    }());
