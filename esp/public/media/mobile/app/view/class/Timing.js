Ext.define('LU.view.class.Timing', {
    extend: 'Ext.List',
    xtype: 'timingList',

    config: {
        disableSelection: true,
        store: 'Timings',
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
