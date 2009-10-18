/*
 * the matrix class
 */
ESP.declare('ESP.Scheduling.Widgets.Matrix', Class.create({
	initialize: function(times, rooms, blocks){
		this.table = $j("<div/>").addClass('matrix');

		var Matrix = ESP.Scheduling.Widgets.Matrix;
		
		this.times = times;
		this.rooms = rooms;
		var time_cells = this.time_cells = {};
		var room_cells = this.room_cells = {};
		var block_cells = this.block_cells = {};
		
		// set up header
		var th = $j('<div/>').addClass('matrix-header')
		th.append((new Matrix.InvalidCell()).td.addClass('corner-cell')); // do we want to keep a ref?
		var tr = $j('<div/>').addClass('matrix-row-body');
		th.append(tr);
		for (var i = 0; i < times.length; i++) {
			var c = new Matrix.TimeCell(times[i]);
			time_cells[times[i].uid] = c;
			if (!times[i].seq) c.td.addClass('non-sequential');
			tr.append(c.td);
		}
		this.table.append(th);
		
		var tb = $j('<div/>').addClass('matrix-body');
		th = $j('<div/>').addClass('matrix-row-header-box');
		tr = $j('<div/>').addClass('matrix-cell-body');
		this.table.append(tb);
		tb.append(th);
		tb.append(tr);
		
		// create rows
		for (var i = 0; i < rooms.length; i++) {
		    var room = rooms[i];
		    
		    var rc = new Matrix.RoomCell(room);
		    room_cells[room.uid] = rc;
		    
		    block_cells[room.uid] = {};
		    th.append(rc.td);
		    tr.append(rc.tr);
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
		var BlockStatus = ESP.Scheduling.Resources.BlockStatus;
		// listen for assignments
		ESP.Utilities.evm.bind('block_section_assignment', function(e, data) {
			var blocks = data.blocks;
			for (var i = 0; i < blocks.length; i++) {
			    var block = blocks[i];
			    var cell = this.block_cells[block.room.uid][block.time.uid];
			    cell.td.text(data.section.uid);
			    cell.status(BlockStatus.RESERVED);
			}
		    }.bind(this));
		ESP.Utilities.evm.bind('block_section_assignment', function(e, data) {
			if (!(data.nowriteback)) {
			    var req = { action: 'assignreg',
					cls: data.section.uid,
					block_room_assignments: data.blocks.map(function(x) { return x.time.uid + "," + x.room.uid; } ).join("\n") };

			    $j.post('ajax_schedule_class', req, function(data, status) {
				    if (status == "success") {
					ESP.version_uuid = data.val;
					ESP.tmp_data = data;
				    }
			        }, "json");
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
					ESP.tmp_data = data;
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
		        this.td = $j('<div/>').addClass('matrix-cell');
			this.td.data(Matrix.CELL_CACHE, this);
		}
	});
	Matrix.HeaderCell = Class.create(Matrix.Cell,{
		initialize: function($super){
			$super();
			this.td.addClass('header-cell');
		}
	});
	Matrix.InvalidCell = Class.create(Matrix.HeaderCell,{
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
			this.tr = $j('<div/>').addClass('matrix-row-body');
			this.td.text(room.text);
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