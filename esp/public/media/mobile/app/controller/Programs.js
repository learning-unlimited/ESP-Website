Ext.define('LU.controller.Programs', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            goBtn: 'programList titlebar button'
        },
        control: {
            programList: {
                itemtap: 'onProgramTap',
                show: 'onListShow'
            },
            goBtn: {
                tap: 'onGoBtnTap'
            }
        }
    },

    onProgramTap: function(list, index, target, record, event, opts) {
        this.id = record.get('id');
    },

    onListShow: function(list, opts) {
        list.getStore().load();
    },

    onGoBtnTap: function(btn, event, opts) {
        Ext.Viewport.getActiveItem().destroy();

        // associates the program selected with the user model
        // (we need this to fetch the program catalog)
        var store = Ext.getStore('User');
        var user = store.first();
        user.setProgram(this.id);
        store.sync();

        if (user.get('role') === 'onsite') {
            Ext.Viewport.setActiveItem(Ext.widget('onsite'));
        } else if (user.get('role') === 'student') {
            Ext.Viewport.setMasked({ xtype: 'loadmask' });

            LU.Util.getClasses(function(result) {
                if (!result) {
                    Ext.Viewport.setActiveItem(Ext.widget('student'));
                    Ext.Viewport.setMasked(false);
                } else {
                    Ext.Msg.alert('Network Error', 'We are experiencing problems fetching the data from server. You may wish to try reloading again.');
                }
            });
        }
    }
});
