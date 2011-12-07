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
            var thead = $j('<thead/>');
            this.table.append(thead);
            this.tbody = $j('<tbody/>');
            this.table.append(this.tbody);
        
            var header = this.header = $j('<tr/>').addClass('header');
            thead.append(header);
            $j.each(this.properties, function(key, prop){
                var td = $j('<td style="'+(prop.css||'')+'"><span>' + (prop.label || key) + '</span></td>');
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
                // use code instead of emailcode; that's how Scheduling.process_data names it
                var diff = x.section.class_id - y.section.class_id;
                return diff == 0 ? cmp(x.section.code, y.section.code) : diff;
            },
            css: 'width:100px;'
        },
        'Title': {
            get: function(x){ return x.text; },
            sort: function(x,y){
                return cmp(x.section.text, y.section.text);
            },
            css: 'width:400px;'
        },
        'Category': {
            get: function(x){ return x.category; },
            sort: function(x,y){
                return cmp(x.section.category, y.section.category);
            },
            css: 'width:100px;'
        },
        'Teacher': {
            get: function(x) { return ""+x.teachers.map(function(x){return x.block_contents;}); },
            sort: function(x,y){
                return cmp(""+x.section.teachers.map(function(z){return z.text;}), ""+y.section.teachers.map(function(z){return z.text;}));
            },
            css: 'width:200px;'
        },
        'Length': {
            get: function(x) { return x.length_hr; },
            sort: function(x,y) {
                return x.section.length - y.section.length;
            },
            css: 'width:50px;'
        }
        },
        
        // filter active rows
        filter: function(filter){
            var filter = filter || this.activeFilter || function(){ return true; };
            this.activeFilter = filter;
            var active_rows = [];
            $j.each(this.entries, function(i,entry){
                if (entry.section.blocks.length == 0 && filter(entry.section))
                    active_rows.push(entry);
            });
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
                    if (x.status == 10){ // skip non-Approved classes
                        this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, x));
                    }
                }.bind(this));
            } else {
                if (entry.status == 10) { // skip non-Approved classes
                    this.entries.push(new ESP.Scheduling.Widgets.Directory.Entry(this, entry));
                }
            }
            if (update) this.filter();
        },
        
        // update directory entries
        update: function(){
            this.tbody.hide();
            this.tbody[0].innerHTML = "";//.children().remove();  // The 'right' way here is vastly slower, sadly.  -- aseering 10/23/2010
            $j.each(this.active_rows, function (i,x){ this.tbody.append(x.update().el); x.draggable(); }.bind(this));
            this.tbody.show();
        }
    }));

ESP.declare('ESP.Scheduling.Widgets.Directory.Entry', Class.create({
        initialize: function(directory, section){
            this.directory = directory;
            this.section = section;
            this.el = $j('<tr/>').addClass('class-entry').data("controller",this);
            this.el.addClass('CLS_category_' + section.category);
            this.el.addClass('CLS_id_' + section.id);
            this.el.addClass('CLS_length_' + section.length_hr + '_hrs');
            this.el.addClass('CLS_status_' + section.status);
            this.el.addClass('CLS_grade_min_' + section.grade_min);
            this.el.addClass('CLS_grade_max_' + section.grade_max);
            for (var i = 0; i < section.resource_requests.length; i++) {
                if (section.resource_requests[i][0]) {
                    this.el.addClass('CLS_rsrc_req_' + section.resource_requests[i][0].text.replace(/[^a-zA-Z]+/g, '-'));
                }
            }

            this.tds = {};
            $j.each(this.directory.properties,function(index, prop){
                var td = $j('<td style="' + (prop.css||'') + '">' + prop.get(section) + '</td>');
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
        
            //this.textbox.bind('keyup',this.do_search.bind(this));
            this.textbox.bind('keypress',function(e){ if (e.which == 13) this.do_search(); }.bind(this));
        },
        do_search: function(){
            this.directory.filter(this.search_function(this.textbox.val()));
        },
        search_function: function(text){
            var regex = new RegExp(text,'i'); // case insensitive
            var fields = ['id','category','text', 'code'];
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
