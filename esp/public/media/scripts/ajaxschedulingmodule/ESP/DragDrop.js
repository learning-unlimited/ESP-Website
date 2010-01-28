ESP.declare('ESP.Scheduling.DragDrop', function(){
	var DragDrop = {};
	// create drag proxy
	DragDrop.drag_proxy_el = $j('<div/>').addClass('class-dd-proxy');
	
	DragDrop.get_drag_proxy = function(section) {
	    this.drag_proxy_el.text(section && section.code || '---');
	    this.drag_proxy_el.css('width',Math.round(50*section.length_hr)+'px');
	    return this.drag_proxy_el;
	}.bind(DragDrop);
	
	DragDrop.make_draggable = function(target, get_section) {
	    target.draggable({
		    helper: function(){ return this.get_drag_proxy(get_section()); }.bind(this),
		    revert: 'invalid', revertDuration: 350,
		    scroll: false, cursorAt: {left:25,top:25}, cursor: 'default',
		    opacity: 1.0, containment: 'window',
		    zIndex: 24, // Just enough
		    appendTo: 'body',
		    start: function(e,ui) {
			var blocks = ESP.Scheduling.data.blocks;
			var section = get_section();
			for (var i = 0; i < blocks.length; i++) {
			    var b = blocks[i];
			    b._temp_accept = (b.section == section) || ESP.Scheduling.validate_block_assignment(b, section);
			}
			target.data('section', section);
			ESP.Utilities.evm.fire('drag_started',{ event: e, ui: ui});
		    },
		    stop:  function(e,ui) { ESP.Utilities.evm.fire('drag_stopped',{ event: e, ui: ui}); }
		});
	    //target.data('section',get_section);
	};
	
	DragDrop.make_droppable = function(target, getBlock, options) {
	    var options = $j.extend({
		    hoverClass: 'dd-hover',
		    tolerance: 'pointer',
		    accept: function(d){
			var block = getBlock();
			// cache (accept is called on drag_start and on drag_end)
			if (block._temp_accept_flag) {
			    block._temp_accept_flag = false;
			    return true;
			}
			//block._temp_accept_flag = true; 
			
			var target_block = block;
			var blocks = [];
			
			var section = d.data('section');
			var t = section.length;
			while (t > 0) {
			    if (block == null || !block._temp_accept) {
				return target_block._temp_accept_flag = false;
			    }
			    blocks.push(block);
			    t -= block.time.length;
			    block = block.seq;
			}
			target_block._temp_glom = blocks;
			return target_block._temp_accept_flag = true;
		    },
		    drop: function(e, ui) {
			var blocks = getBlock()._temp_glom;
			for (var i = 0; i < blocks.length; i++) {
			    // grr.. stupid JQuery fail (deactivate isn't called on the drop target)
			    blocks[i].__td.removeClass('dd-highlight');
			}
			
			ESP.Utilities.evm.fire('drag_dropped',{
				event: e, ui: ui, draggable:ui.draggable, droppable:this,
				blocks:blocks, section:ui.draggable.data('section')
			    });
		    },
		    activate: function(e, ui) { target.addClass('dd-highlight'); },
		    deactivate: function(e, ui) { target.removeClass('dd-highlight'); }
		}, options || {});
	    target.droppable(options);
	};
	
	return DragDrop;
    }());
