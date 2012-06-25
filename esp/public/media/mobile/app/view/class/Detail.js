Ext.define('LU.view.class.Detail', {
    extend: 'Ext.Container',
    xtype: 'classDetail',

    config: {
        layout: 'vbox',
        scrollable: 'vertical',
        items: [
            {
                xtype: 'classInfo'
            },
            {
                xtype: 'prereqList',
                scrollable: false,

                items: [
                    {
                        xtype: 'listitemheader',
                        html: 'Prerequisites'
                    }
                ]
            },
            {
                xtype: 'timingList',
                scrollable: false,

                items: [
                    {
                        xtype: 'listitemheader',
                        html: 'Time'
                    }
                ]
            }
        ]
    }
});
