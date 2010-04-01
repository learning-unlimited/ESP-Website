ESP.declare('ESP.Scheduling.Widgets.StatusBar', Class.create({
	    initialize: function(target) {
		this.target = $j(target);
	    },
	    type: {
		warning: 'yellow',
		error: 'red',
		none: ' ',
		success: 'green',
		info: ' ',
		hidden: 'hidden'
	    },
	    setStatus: function(type, text) {
		var text = text || type;
		var css = this.type[text ? type : type ? 'none' : 'hidden'];
		this.target.removeClass();
		this.target.addClass(css);
		this.target.text(text);
	    }
}));