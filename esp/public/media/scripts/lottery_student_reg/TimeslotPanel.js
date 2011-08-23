TimeslotPanel = Ext.extend(Ext.FormPanel, {

   /* items:
    {
	    xtype: 'fieldset',
	    layout: 'column',
	    id: this.id+'no_class',
	    name: this.id+'no_class',
	    items: 
	    [
	        {
	            xtype: 'radio',
		        id: 'flag_'+this.id,
		        name: 'flag_'+this.id
            },{ 
		        xtype: 'displayfield',
		        value: "I would not like to flag a priority class for this timeblock."
            }
        ]
    },*/

    listeners: { 
        render: this.makeCheckBoxes,
        //beforehide: this.checkPriorities
    },
 
    initComponent: function() {
        alert("initComponent");
        var config = {
            height: 800,
            priorityLimit: 1,
            autoScroll: true,
            monitorResize: true,
        }

    	Ext.apply(this, Ext.apply(this.initialConfig, config));
        TimeslotPanel.superclass.initComponent.apply(this, arguments); 
    },

    makeCheckBoxes: function() {
        alert("makeCheckBoxes");
    }
});

Ext.reg('timeslotpanel', TimeslotPanel)
