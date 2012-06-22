Ext.define('LU.view.program.List', {
    extend: 'Ext.List',
    xtype: 'programList',

    config: {
        layout: 'vbox',
        cls: 'program-list',
        ui: 'round',
        scrollable: true,
        store: 'Programs',
        itemTpl: '{title}',
        items: [
            {
                xtype: 'titlebar',
                docked: 'top',
                title: 'Program',
                items: [
                    {
                        align: 'right',
                        text: 'Go!'
                    }
                ]
            },
            {
                xtype: 'component',
                cls: 'description',
                styleHtmlContent: true,
                html: 'Select the program you are attending:'
            }
        ]
    }
});
