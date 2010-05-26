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
		var header = $j('<div/>').addClass('matrix-header')
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
			var blocks = data.blocks;
			for (var i = 0; i < blocks.length; i++) {
			    var block = blocks[i];
			    var cell = this.block_cells[block.room.uid][block.time.uid];
                //  cell.td.text(data.section.class_id);
			    cell.td.html(data.section.block_contents);
			    cell.status(BlockStatus.RESERVED);
			}
		    }.bind(this));
		ESP.Utilities.evm.bind('block_section_assignment', function(e, data) {
			if (!(data.nowriteback)) {
			    if (data.blocks.length > 0) {
				var req = { action: 'assignreg',
					    cls: data.section.uid,
					    block_room_assignments: data.blocks.map(function(x) { return x.time.uid + "," + x.room.uid; } ).join("\n") };

				$j.post('ajax_schedule_class', req, function(data, status) {
					if (status == "success") {
					    ESP.version_uuid = data.val;
					    ESP.Utilities.evm.fire('block_section_assignment_success', data);
					}
				    }, "json");
			    } else {
				ESP.Utilities.evm.fire('block_section_assignment_success', data);
			    }
			}
		    }.bind(this));
		ESP.Utilities.evm.bind('block_section_unassignment', function(e, data) {
			var old_blocks = data.blocks;
			for (var i = 0; i < old_blocks.length; i++) {
			    var block = old_blocks[i];
			    var cell = this.block_cells[block.room.uid][block.time.uid];
			    cell.td.text('');
			    cell.status(BlockStatus.AVAILABLE);
			}
		    }.bind(this))
		ESP.Utilities.evm.bind('block_section_unassignment', function(e, data) {
			if (!(data.nowriteback)) {
			    var req = { action: 'deletereg',
					cls: data.section.uid };

			    $j.post('ajax_schedule_class', req, function(data, status) {
				    if (status == "success") {
					ESP.version_uuid = data.val;
				    }
			        }, "json");
			}
		    }.bind(this));
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
			this.td.addClass('header-cell');
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
			//this.tr.append(this.td);
		}
	});
	
	var BlockStatus = ESP.Scheduling.Resources.BlockStatus;
	var StatusClasses = {};
	StatusClasses[BlockStatus.NOT_OURS] = 'inactive';
	StatusClasses[BlockStatus.AVAILABLE] = 'active';
	StatusClasses[BlockStatus.RESERVED] = 'filled';
	
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
			this.td.draggable(status == BlockStatus.RESERVED ? 'enable' : 'disable');
		    } else {
			return this.block.status;
		    }
		}
	});
})();

ESP.declare('ESP.Scheduling.Widgets.GarbageBin', Class.create({
	    initialize: function(){
		this.el = $j('<div/>').addClass('garbage');
		var target = this.el;
		var activeClass = 'dd-highlight';
		var options = $j.extend({
		    hoverClass: 'dd-hover',
		    tolerance: 'pointer',
		    accept: function(d){ return true; },
		    drop: function(e, ui) {
			    target.removeClass(activeClass);
			    ESP.Utilities.evm.fire('drag_dropped',{
				event: e, ui: ui, draggable:ui.draggable, droppable:this,
				blocks:[], section:ui.draggable.data('section')
			    });
		    },
		    activate: function(e, ui) { target.addClass(activeClass); },
		    deactivate: function(e, ui) { target.removeClass(activeClass); }
		}, options || {});
		target.droppable(options);
	    }
	}));

