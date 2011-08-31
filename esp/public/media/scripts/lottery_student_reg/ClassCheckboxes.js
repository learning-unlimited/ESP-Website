ClassCheckboxes = Ext.extend(Ext.form.FieldSet, { 

    ESPClassInfo: {},
    timeblockId: "",

    getSectionId: function ()
    {
        var i;
        for(i = 0; i < this.ESPClassInfo.data.get_sections.length; i ++)
        {
            section = this.ESPClassInfo.data.get_sections[i];      
            if(section.get_meeting_times[0].id == this.timeblockId)
            {
                return section.id;
            }
        }
        //there should be error handling here
        return 0;
    },

    initComponent: function ()
    {
        section_id = this.getSectionId();
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
