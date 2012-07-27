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
        Ext.Viewport.setMasked({ xtype: 'loadmask' });

        // associates the program selected with the user model
        // (we need this to fetch the program catalog)
        var store = Ext.getStore('User');
        var user = store.first();
        user.setProgram(this.id);
        store.sync();

        if (user.get('role') === 'onsite') {

            // retrieves the list of users
            var studentStore = Ext.getStore('Students');

            studentStore.setProxy({
                type: 'ajax',
                url: LU.Util.getStudentListUrl()
            });

            studentStore.load({
                callback: function(records, operation, success) {
                    var next;
                    if (success) {
                        next = Ext.widget('onsite');
                    } else {
                        Ext.Msg.alert('Network Error', 'We are experiencing problems fetching the data from server. You may wish to try reloading again.');
                        next = Ext.widget('main');
                    }
                    Ext.Viewport.setActiveItem(next);
                    Ext.Viewport.setMasked(false);
                }
            });
        } else if (user.get('role') === 'student') {
            LU.Util.getRegisteredClasses(function(result) {
                var next;
                if (!result) {
                    next = Ext.widget('student');
                } else {
                    Ext.Msg.alert('Network Error', 'We are experiencing problems fetching the data from server. You may wish to try reloading again.');
                    next = Ext.widget('main');
                }
                Ext.Viewport.setActiveItem(next);
                Ext.Viewport.setMasked(false);
            });
        }
    }
});
