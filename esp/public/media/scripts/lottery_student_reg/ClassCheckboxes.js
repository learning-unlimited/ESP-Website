ClassCheckboxes = Ext.extend(Ext.form.FieldSet, { 

    ESPClassInfo: {},
    timeblockId: "",
    sectionId: 0,
    initialStatus: "",

    initComponent: function ()
    {
		//comes up with label for checkboxes
		classText = '';
		classText = classText + this.ESPClassInfo.data.category.symbol + this.ESPClassInfo.data.id + ': ' + this.ESPClassInfo.data.title;
        var config = 
        {
            id: this.timeblockId + this.ESPClassInfo.id,
            items: 
            [
                {
			       xtype: 'radio',
			       id: 'flag_'+section_id,
			       name: 'flag_'+this.timeblockId,
			       inputValue: section_id,
			       listeners: { //listener changes the flagged classes box at the top when the flagged class changes
			       }
                },
                {
        	       xtype: 'checkbox',
        	       name: section_id,
        	       id: section_id
                }, 
                { 
        	       xtype: 'displayfield',
            	   value: classText,
        	       autoHeight: true,
        	       id: 'title_'+ section_id 
                }
            ],
            width: 400,
            layout: 'column',
            sectionId: section_id,
            classFullTitle: classText,
        };

    	Ext.apply(this, Ext.apply(this.initialConfig, config));
        ClassCheckboxes.superclass.initComponent.apply(this, arguments); 

        if(this.initialStatus == "Priority/1")
        {
            console.log("Priority/1");
            this.items.items[0].checked = true;
        }
        else if(this.initialStatus == "Interested")
        {
            console.log("interested");
            this.items.items[1].checked = true;
        }
    },

    classNumber: function () 
    {
        return this.sectionId;
    },

    isChecked: function () 
    {
        return this.items.items[1].getValue();
    },

    isFlagged: function ()
    {
        return this.items.items[0].getValue();
    }
});

Ext.reg('class_checkboxes', ClassCheckboxes);
