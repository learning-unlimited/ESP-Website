/*
 * the matrix class
 */
ESP.declare('ESP.Scheduling.Widgets.Matrix', Class.create({
    initialize: function(times, rooms, blocks){
        this.matrix = $j("<div/>").addClass('matrix');
        this.el = this.matrix;

        var Matrix = ESP.Scheduling.Widgets.Matrix;
        
        this.times = times;
        this.rooms = rooms;
        var time_cells = this.time_cells = {};
        var room_cells = this.room_cells = {};
        var block_cells = this.block_cells = {};
        
        // set up header
        var header = $j('<div/>').addClass('matrix-header');
        this.matrix.append(header);
        header.append($j('<div/>').addClass('matrix-corner-box'));
        
        var col_header = $j('<table/>').addClass('matrix-column-header-box');
        header.append(col_header);
        var tr = $j('<tr/>').addClass('matrix-row-body');
        col_header.append(tr);
        for (var i = 0; i < times.length; i++) {
            var c = new Matrix.TimeCell(times[i]);
            time_cells[times[i].uid] = c;
            if (!times[i].seq) c.td.addClass('non-sequential');
            tr.append(c.td);
        }
        
        var body = $j('<div/>').addClass('matrix-body');
        this.matrix.append(body);
        var row_header = $j('<table/>').addClass('matrix-row-header-box');
        var cell_body = $j('<table/>').addClass('matrix-cell-body');
        body.append(row_header);
        body.append(cell_body);
        
        // create rows
        for (var i = 0; i < rooms.length; i++) {
            var room = rooms[i];
            
            var rc = new Matrix.RoomCell(room);
            room_cells[room.uid] = rc;
            
            block_cells[room.uid] = {};
            var tr = $j('<tr/>');
            tr.append(rc.td);
            row_header.append(tr);
            cell_body.append(rc.tr);
        }
        
        // create individual blocks
        for (var i = 0; i < blocks.length; i++){
            var block = blocks[i];
            block_cells[block.room.uid][block.time.uid] = new Matrix.BlockCell(block);
        }
        
        // add blocks in correct order
        for (var i = 0; i < rooms.length; i++) {
            var row = block_cells[rooms[i].uid];
            var tr = room_cells[rooms[i].uid].tr;
            var lt = false, t = false, td = null;
            for (var j = 0; j < times.length; j++) {
                t = times[j];
                td = (row[t.uid] || new Matrix.InvalidCell()).td;
                tr.append(td);
                //if (lt && !ESP.Scheduling.Resources.Time.sequential(lt,t)) td.addClass('non-sequential');
                if (!t.seq) td.addClass('non-sequential');
                lt = t;
            }
        }
        
        // set up scrolling
        cell_body.scroll(function(evt){
            row_header.css('top','-'+cell_body.attr('scrollTop')+'px');
            col_header.children('tbody').css('left','-'+cell_body.attr('scrollLeft')+'px');
        });
        
        var BlockStatus = ESP.Scheduling.Resources.BlockStatus;
        // listen for assignments
        ESP.Utilities.evm.bind('block_section_assignment', function(e, data) {
            if (!(data.nowriteback)) {
                if (data.blocks.length > 0) {
                    //Refresh the csrf token
                    refresh_csrf_cookie();
                    var req = { action: 'assignreg',
                            csrfmiddlewaretoken: csrf_token(),
                            cls: data.section.uid,
                            block_room_assignments: data.blocks.map(function(x) { return x.time.uid + "," + x.room.uid; } ).join("\n") };

                    $j.post('ajax_schedule_class', req, "json")
                    .success(function(ajax_data, status) {
                        if (ajax_data.ret == true) {
                            ESP.version_uuid = data.val;
                            ESP.Utilities.evm.fire('block_section_assignment_local', data);
                        } else {
			    ESP.Scheduling.directory.filter();
                            ESP.Scheduling.status('error', "Failed to assign " + data.section.code + ": " + ajax_data.msg);
                        }
                    })
                    .error(function(ajax_data, status) {
                        alert("Assignment failure!");
                    });
                } else {
                    ESP.Utilities.evm.fire('block_section_assignment_local', data);
                }
            }
            else {
                ESP.Utilities.evm.fire('block_section_assignment_local', data);
            }
        }.bind(this));
        ESP.Utilities.evm.bind('block_section_assignment_local', function(e, data) {
            //Some checking
            var block_status;
            for (var i = 0; i < data.blocks.length; i++) {
                if (!((block_status = ESP.Scheduling.validate_block_assignment(data.blocks[i], data.section, true)) == "OK")) {
                    console.log("Error:  Conflict when adding block " + data.blocks[i].room.text + " (" + data.blocks[i].time.text + ") to section " + data.section.code + ": [" + block_status + "]");
                }
            }
            //Actually set the data
            data.section.blocks = data.blocks;
            for (var i = 0; i < data.blocks.length; i++) {
                data.blocks[i].section = data.section;
            }
            //Set the CSS
            var blocks = data.blocks;
            for (var i = 0; i < blocks.length; i++) {
                var block = blocks[i];
                var cell = this.block_cells[block.room.uid][block.time.uid];
                //  cell.td.text(data.section.class_id);
                cell.td.html(data.section.block_contents.clone(true));
		if(data.section.status == 10) {
                    cell.status(BlockStatus.RESERVED);
		}
		else {
		    cell.status(BlockStatus.UNREVIEWED);
		}
                var section = data.section;
                cell.td.addClass('CLS_category_' + section.category);
                cell.td.addClass('CLS_id_' + section.id);
                cell.td.addClass('CLS_length_' + section.length_hr + '_hrs');
                cell.td.addClass('CLS_status_' + section.status);
                cell.td.addClass('CLS_grade_min_' + section.grade_min);
                cell.td.addClass('CLS_grade_max_' + section.grade_max);               
		/*
                for (var j = 0; j < section.resource_requests.length; j++) {
                    if (section.resource_requests[j][0]) {
                        cell.td.addClass('CLS_rsrc_req_' + section.resource_requests[j][0].text.replace(/[^a-zA-Z]+/g, '-'));
                    }
                }
		*/
                for (var j = 0; j < block.processed_room.resources.length; j++) {
                    if (block.processed_room.resources[j]) {
                        cell.td.addClass('CLS_ROOM_rsrc_' + block.processed_room.resources[j].replace(/[^a-zA-Z]+/g, '-'));
                    }
                }
            }

            ESP.Utilities.evm.fire('block_section_assignment_success', data);
        }.bind(this));
        ESP.Utilities.evm.bind('block_section_unassignment', function(e, data) {
            if (!(data.nowriteback)) {
                //Refresh the csrf token
                refresh_csrf_cookie();
                var req = { action: 'deletereg',
                    csrfmiddlewaretoken: csrf_token(),
                    cls: data.section.uid };

                $j.post('ajax_schedule_class', req)
                .success(function(ajax_data, status) {
                    ESP.version_uuid = data.val;
                    ESP.Utilities.evm.fire('block_section_unassignment_local', data);
                })
                .error(function(ajax_data, status) {
                    alert("Unassignment failure!");
                });
            }
            else {
                ESP.Utilities.evm.fire('block_section_unassignment_local', data);
            }
        }.bind(this));
        ESP.Utilities.evm.bind('block_section_unassignment_local', function(e, data) {
            //Update the actual data
            data.section.blocks = [];
            for (var i = 0; i < data.blocks.length; i++) {
                data.blocks[i].section = null;
            }
            //Update the CSS
            var old_blocks = data.blocks;
            for (var i = 0; i < old_blocks.length; i++) {
                var block = old_blocks[i];
                var cell = this.block_cells[block.room.uid][block.time.uid];
                cell.td.text('');
                cell.status(BlockStatus.AVAILABLE);
                var css_cls = cell.td.attr('class').split(/\s+/);
                for (var j = 0; j < css_cls.length; j++) {
                    if (css_cls[j].indexOf("CLS_") == 0) {
                        cell.td.removeClass(css_cls[j]);
                    }
                }
            }
        }.bind(this));
    },
    
    hideRoom:function(uid){
        var rc=this.room_cells[uid];
        rc.tr.hide();
        rc.td.parent().hide();
    },
    
    showRoom:function(uid){
        var rc=this.room_cells[uid];
        rc.tr.show();
        rc.td.parent().show();
    },
    
    showAll:function(){
        this.filter(function(){return true;});
    },
    
    filter:function(filter){
        for(var i=0; i<this.rooms.length; i++){
            if(filter(this.rooms[i]))
                this.showRoom(this.rooms[i].uid);
            else
                this.hideRoom(this.rooms[i].uid);
        }
    },
    
    sortBy:function(val){
        var sorted=this.rooms.sortBy(val);
        
        function moveToEnd(node){
            var parent=node.parentNode;
            parent.removeChild(node);
            parent.appendChild(node);
        }
        
        for(var i=0; i<sorted.length; i++){
            var rc=this.room_cells[sorted[i].uid];
            moveToEnd(rc.tr[0]);
            moveToEnd(rc.td.parent()[0]);
        }
    }
    
}));

ESP.declare('ESP.Scheduling.Widgets.RoomFilter', Class.create({
    initialize: function(matrix) {
        this.matrix = matrix;
        this.el=$j("<div/>").addClass('room-filter');
        this.el.append(
            $j("<input/>").attr({type: "button", value: "Filter/sort\nrooms"}).click((function(e){
                if(!this.dialog){
                    
                    this.dialog=$j("<div/>").css({
                        "background-color": "white",
                        "position": "relative",
                        "left": "10px",
                        "top": "10px",
                          "border": "solid black 1px",
                          "padding": "5px",
                          "width": "150px"
                    });
                    
                    this.resources={};
                    for(var i=0; i<this.matrix.rooms.length; i++)
                        for(var j=0; j<this.matrix.rooms[i].resources.length; j++)
                            this.resources[this.matrix.rooms[i].resources[j]]={};
                    
                    this.dialog.append("<b>Resources:</b><br/>");
                    for(var res in this.resources){
                        this.resources[res].name=res;
                        this.resources[res].checkbox=$j("<input type='checkbox'/>");
                        this.dialog.append(this.resources[res].checkbox, res, "<br/>");
                    }
                    this.dialog.append("<hr/>");
                    
                    this.dialog.append("<b>Min size:</b> ", this.minsize=$j("<input type='text' value='0' size='2'/>"), "<br/>",
                                 "<b>Max size:</b> ", this.maxsize=$j("<input type='text' value='1000' size='2'/>"), "<br/>");
                    $j([this.minsize[0], this.maxsize[0]]).focus(function(e){e.target.select()});
                    this.dialog.append("<hr/>");
                    
                    this.dialog.append("<b>Sort by:</b><br/>");
                    this.dialog.append(
                        $j("<input type='button' value='Room number'>").click((function(){
                            this.sort(function(r){return r.uid});
                            this.dialog.hide();
                        }).bind(this)),
                        $j("<input type='button' value='Size ascending'>").click((function(){
                            this.sort(function(r){return r.size});
                            this.dialog.hide();
                        }).bind(this)),
                        $j("<input type='button' value='Size descending'>").click((function(){
                            this.sort(function(r){return -r.size});
                            this.dialog.hide();
                        }).bind(this)));
                    
                    this.dialog.click(function(e){
                        e.stopPropagation();
                    }).change((function(){
                        this.filter();
                    }).bind(this));
                    
                    $j("body").click((function(){
                        this.filter();
                        this.dialog.hide();
                    }).bind(this));
                    
                    this.el.append(this.dialog);
                    this.dialog.hide();
                    
                }
                this.dialog.toggle(100);
                e.stopPropagation();
            }).bind(this))
        );
        $j('.matrix-corner-box').append(this.el);
    },
        
    filter: function(){
        this.matrix.filter((function(room){
            for(var res in this.resources)
                if(this.resources[res].checkbox[0].checked && 
                            !room.resources.contains(res))
                    return false;
            if (this.minsize && this.maxsize)
                if(room.size<this.minsize.val() || 
                room.size>this.maxsize.val())
                    return false;
            return true;
        }).bind(this));
    },
        
    sort: function(valFunc){
        if(!valFunc)
            valFunc=this.lastValFunc;
        this.lastValFunc=valFunc;
        if(typeof valFunc == "function")
            this.matrix.sortBy(valFunc);
    },
        
    save: function(){
        this.el[0].parentNode.removeChild(this.el[0]);
    },
        
    restore: function(matrix){
        this.matrix=matrix;
        $j('.matrix-corner-box').append(this.el);
        this.filter();
    }
}));

/*
 * Helper Classes
 */
(function(){
    var Matrix = ESP.Scheduling.Widgets.Matrix;
    var Resources = ESP.Scheduling.Resources;
    
    /*
     * object caches (mapping from table cells to other stuff)
     */
    Matrix.CELL_CACHE = 'ESP.SCHEDULING.WIDGET.MATRIX.CELL_DATA',
    
    /*
     * accessibility classes (make it easy to manipulate table / data)
     */
    Matrix.Cell = Class.create({
        initialize: function(){
            this.td = $j('<td/>').addClass('matrix-cell');
            this.td.data(Matrix.CELL_CACHE, this);
        }
    });
    Matrix.HeaderCell = Class.create(Matrix.Cell,{
        initialize: function($super){
            $super();
        }
    });
    Matrix.InvalidCell = Class.create(Matrix.Cell,{
        initialize: function($super){
            $super();
            this.td.addClass('invalid-cell');
        }
    });
    Matrix.TimeCell = Class.create(Matrix.HeaderCell,{
        initialize: function($super, time){
            $super()
            this.time = time;
            this.td.text(time.text);
            this.td.addClass('column-header');
        }
    });
    Matrix.RoomCell = Class.create(Matrix.HeaderCell,{
        initialize: function($super, room){
            $super()
            this.room = room;
            this.tr = $j('<tr/>').addClass('matrix-row-body');
            this.td.html(room.block_contents);
            this.td.addClass('matrix-row-header');
            for (var j = 0; j < room.resources.length; j++) {
                if (room.resources[j]) {
                    this.td.addClass('ROOM_rsrc_' + room.resources[j].replace(/[^a-zA-Z]+/g, '-'));
                }
            }
            this.td.addClass('');
            //this.tr.append(this.td);
        }
    });
    
    var BlockStatus = ESP.Scheduling.Resources.BlockStatus;
    var StatusClasses = {};
    StatusClasses[BlockStatus.NOT_OURS] = 'inactive';
    StatusClasses[BlockStatus.AVAILABLE] = 'active';
    StatusClasses[BlockStatus.RESERVED] = 'filled';
    StatusClasses[BlockStatus.UNREVIEWED] = 'unreviewed';
    
    Matrix.BlockCell = Class.create(Matrix.Cell,{
        initialize: function($super,block){
            $super();
            this.block = block;
            this.td.addClass('data-cell')
            this.block.__td = this.td;
            ESP.Scheduling.DragDrop.make_draggable(this.td, function(){
                if (this.block.section == null){
                    console.log('null section on block [' + this.block.uid + ']');
                }
                return this.block.section;
            }.bind(this));
            ESP.Scheduling.DragDrop.make_droppable(this.td,
                function(){ return this.block; }.bind(this));
            this.status(block.status);
        },
        status: function(status) {
            var BlockStatus = ESP.Scheduling.Resources.BlockStatus;
            if (status) {
                this.td.removeClass(StatusClasses[this.block.status]);
                this.block.status = status;
                this.td.addClass(StatusClasses[status]);
                this.td.draggable(status == BlockStatus.RESERVED || status == BlockStatus.UNREVIEWED ? 'enable' : 'disable');
            } else {
                return this.block.status;
            }
        }
    });
})();

ESP.declare('ESP.Scheduling.Widgets.GarbageBin', Class.create({
        initialize: function(){
            this.el = $j('<div>Drag here to unschedule</div>').addClass('garbage');
            var target = this.el;
            var activeClass = 'dd-highlight';
            var options = $j.extend({
                hoverClass: 'dd-hover',
                tolerance: 'pointer',
                accept: function(d){ return true; },
                drop: function(e, ui) {
                    target.removeClass(activeClass);
                    ESP.Utilities.evm.fire('drag_dropped',{
                        event: e,
                        ui: ui,
                        draggable:ui.draggable,
                        droppable:this,
                        blocks:[],
                        section:ui.draggable.data('section')
                    });
                },
                activate: function(e, ui) { target.addClass(activeClass); },
                deactivate: function(e, ui) { target.removeClass(activeClass); }
            }, options || {});
            target.droppable(options);
        }
    }));

