Ext.define('LU.view.schedule.Timing', {
    extend: 'Ext.List',
    xtype: 'scheduleTimingList',

    config: {
        disableSelection: true,
        scrollable: false,
        store: 'RegisteredTimings',

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
