dojo.provide("nong.widget.NongSelect");
dojo.provide("nong.widget.html.NongSelect");

dojo.require("dojo.widget.Select");
dojo.require("dojo.widget.*");

dojo.widget.defineWidget(
	"nong.widget.html.NongSelect",
	dojo.widget.html.Select,
	{
		widgetType: "NongSelect",
		size: 30,
		id: "",
		fadeTime: 50,
		searchDelay: 500,
		templatePath: dojo.uri.dojoUri("../nong/widget/templates/NongComboBox.html"),
		templateCssPath: dojo.uri.dojoUri("../nong/widget/templates/NongComboBox.css"),
		inactiveImage: dojo.uri.dojoUri("../nong/widget/templates/combo-arrowdown.gif"),
		activeImage: dojo.uri.dojoUri("../nong/widget/templates/combo-arrowdown-over.gif"),

		arrowActive: function(){
			this._setImage(this.activeImage);
		},

		arrowInactive: function(){
			this._setImage(this.inactiveImage);
		},

		_setImage: function(src){
			this.downArrowNode.src=src;
		},

		showResultList: function(){
			// Our dear friend IE doesnt take max-height so we need to calculate that on our own every time
			var childs = this.optionsListNode.childNodes;
			if(childs.length){
				var visibleCount = this.maxListLength;
				if(childs.length < visibleCount){
					visibleCount = childs.length;
				}

				with(this.optionsListNode.style){
					display = "";
					height = ((visibleCount) ? (dojo.style.getOuterHeight(childs[0]) * visibleCount) : 0)+"px";
					width = dojo.html.getOuterWidth(this.textInputNode)-2+"px";
				}
				// only fadein once (flicker)
				if(!this._result_list_open){
					dojo.html.setOpacity(this.optionsListNode, 0);
					dojo.lfx.fadeIn(this.optionsListNode, this.fadeTime).play();
				}

				// prevent IE bleed through
				this._iframeTimer = dojo.lang.setTimeout(this, "sizeBackgroundIframe", 200);
				this._result_list_open = true;
			}else{
				this.hideResultList();
			}
		}
});
