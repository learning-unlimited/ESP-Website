ClassCheckboxes = Ext.extend(Ext.form.FieldSet, { 

    ESPClassInfo: {},
    timeblockId: "",

    initComponent: function ()
    {
        checkbox_id = this.ESPClassInfo.id;
        var config = 
        {
            items: 
            [
                {
			       xtype: 'radio',
			       id: 'flag_'+checkbox_id,
			       name: 'flag_'+this.timeblockId,
			       inputValue: checkbox_id,
			       listeners: { //listener changes the flagged classes box at the top when the flagged class changes
			       }
                },
                {
        	       xtype: 'checkbox',
        	       name: checkbox_id,
        	       id: checkbox_id
                }, 
                { 
        	       xtype: 'displayfield',
            	   value: text,
        	       autoHeight: true,
        	       id: 'title_'+ checkbox_id 
                }
            ],
            layout: 'column',
            id: this.timeblockId + checkbox_id,
            listeners: {
               // render: this.addCheckboxes
            }
        };
    	Ext.apply(this, Ext.apply(this.initialConfig, config));
        ClassCheckboxes.superclass.initComponent.apply(this, arguments); 
    },

    addCheckboxes: function ()
    {
        this.add(
);
    }

});

Ext.reg('class_checkboxes', ClassCheckboxes);
