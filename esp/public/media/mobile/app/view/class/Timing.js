Ext.define('LU.view.class.Timing', {
    extend: 'Ext.List',
    xtype: 'timingList',

    config: {
        disableSelection: true,
        scrollable: false,
        store: 'Timings',

        items: [
            {
                xtype: 'listitemheader',
                html: 'Time'
            }
        ],

        itemTpl: Ext.create('Ext.XTemplate',
            '{[this.formatStartTime(values.start)]} - {[this.formatEndTime(values.end)]}',
            {
                formatEndTime: function(time) {
                    return Ext.Date.format(time, 'g:i A');
                }
            },
            {
                formatStartTime: function(time) {
                    return Ext.Date.format(time, 'D j M Y, g:i');
                }
            }
        )
    }
});
