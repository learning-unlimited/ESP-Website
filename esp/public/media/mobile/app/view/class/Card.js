Ext.define('LU.view.class.Card', {

    extend: 'Ext.NavigationView',
    xtype: 'classContainer',

    config: {
        navigationBar: false,
        title: 'Browse',
        iconCls: 'search',

        autoDestroy: false,

        items: [
            {
                xtype: 'titleBar'
            },
            {
                xtype: 'classList'
            }
        ]
    }
});

