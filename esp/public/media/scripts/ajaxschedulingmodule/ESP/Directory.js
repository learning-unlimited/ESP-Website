ESP.declare('ESP.Scheduling.Widgets.Directory', Class.create({
	    initialize : function(sections){
		var directory = this;
		
		this.entries = [];
		this.active_entries = [];
		this.active_sort = null;
		this.active_filter = null;
		
		// set up display
		this.table = $j("<table/>").addClass('directory');
		this.el = $j("<div/>").addClass('directory-table-wrapper');
		this.el.append(this.table);
		
		// create header
		var header = this.header = $j('<tr/>').addClass('header');
		$j.each(this.properties, function(key, prop){
			var td = $j('<td><span>' + (prop.label || key) + '</span></td>');
			prop.header = td;
			if (prop.sort) {
			    td.addClass('sortable');
			    // enable onclick sorting
			    td.bind('click', function(e){
				    prop.reverse = (directory.active_sort != prop) ? prop.reverse : !prop.reverse;
				    directory.sort(prop);
				});
			}
			header.append(td);
		    });
		this.table.append(header);
		
		// add sections
		this.addEntry(sections, false);
		
		// refresh the representation
		this.filter();
	    },
		
	    // table columns
	    properties: {
		'ID': {
		    get: function(x){ return x.block_contents; },
		    //css: 'text-align:center; text-decoration:underline; font-weight:bold;',
		    sort: function(x,y){
			return x.section.id - y.section.id;
		    }
		},
		'Title': {
		    get: function(x){ return x.text; },
		},
		'Category': {
		    get: function(x){ return x.category; },
		    sort: function(x,y){
			return x.section.category == y.section.category ? this.properties['ID'].sort(x,y) :
			x.section.category > y.section.category ? 1 : -1;
		    }
		},
		'Teacher': {
		    get: function(x) { return ""+x.teachers.map(function(x){return x.block_contents;}); },
		},
		'Length': {
		    get: function(x) { return x.length_hr; },
		    sort: function(x,y) {
			var diff = x.section.length - y.section.length;
			return diff == 0 ? this.properties['ID'].sort(x,y) : diff;
		    }
		}
	    },
	    
	    // filter active rows
	    filter: function(filter){
		var filter = filter || this.activeFilter || function(){ return true; };
		this.activeFilter = filter;
		var active_rows = [];
		$j.each(this.entries, function(i,entry){ if (filter(entry.section)) active_rows.push(entry); });
		this.active_rows = active_rows;
		this.sort();
	    },
	    
	    // sort active rows
	    sort: function(prop){
		var prop = prop || this.active_sort;
		this.header.children().removeClass('sort-by asc desc');
		if (prop) {
		    prop.header.addClass('sort-by').addClass(prop.reverse ? 'asc' : 'desc');
		    this.active_sort = prop;
		    this.active_rows.sort(prop.sort.bind(this));
		    if (prop.reverse) this.active_rows.reverse();
		}
		this.update();
	    },
	    
	    // add an entry
	    addEntry: function(entry, update){
		var update = typeof update == 'undefined' ? true : update;
		if (Object.isArray(entry)) {
		    $j.each(entry, function(i,x){
			    this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, x));
			}.bind(this));
		} else {
		    this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, entry));
		}
		if (update) this.filter();
	    },
	    
	    // update directory entries
	    update: function(){
		this.table.find('.class-entry').remove();
		$j.each(this.active_rows, function (i,x){ this.table.append(x.update().el); x.draggable(); }.bind(this));
	}
	}));

ESP.declare('ESP.Scheduling.Widgets.Directory.Entry', Class.create({
	    initialize: function(directory, section){
		this.directory = directory;
		this.section = section;
		this.el = $j('<tr/>').addClass('class-entry').data("controller",this);
		
		this.tds = {};
		$j.each(this.directory.properties,function(index, prop){
			var td = $j('<td style="' + prop.css + '">' + prop.get(section) + '</td>');
			this.tds[prop] = td;
			this.el.append(td);
		    }.bind(this));
	    },
	    draggable: function(){
		ESP.Scheduling.DragDrop.make_draggable(this.el, function(){ return this.section; }.bind(this));
	    },
	    update: function(){
                $j.each(this.directory.properties,function(index, prop){
                        this.tds[prop].text(prop.get(this.section));
		    }.bind(this));
		return this;
	    }
	}));

ESP.declare('ESP.Scheduling.Widgets.SearchBox', Class.create({
	    initialize: function(directory) {
		this.directory = directory;
		
		this.el = $j('<div/>').addClass('searchbox');
		this.el.append($j('<span>filter: </span>'));
		this.textbox = $j('<input type="text"/>');
		this.el.append(this.textbox);
		
		this.textbox.bind('keyup',this.do_search.bind(this));
		//this.textbox.bind('keypress',function(e){ if (e.which == 13) this.do_search(); }.bind(this));
	    },
	    do_search: function(){
		this.directory.filter(this.search_function(this.textbox.val()));
	    },
	    search_function: function(text){
		var regex = new RegExp(text,'i'); // case insensitive
		var fields = ['id','category','text'];
		var pfields = ['Teacher'];
		return function(x){
		    for (var i = 0; i < fields.length; i++) {
			if (String(x[fields[i]]).search(regex) != -1) return true;
		    }
		    for (var i = 0; i < pfields.length; i++) {
			if (this.directory.properties[pfields[i]].get(x).search(regex) != -1) return true;
		    }
		    return false;
		}.bind(this);
	    }
	}));