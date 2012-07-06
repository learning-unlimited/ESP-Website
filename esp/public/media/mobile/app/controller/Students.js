Ext.define('LU.controller.Students', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            studentContainer: 'studentContainer',
            studentList: 'studentList',
            searchField: 'studentSearchBar textfield',
            logout: 'studentContainer button[text="Logout"]'
        },

        control: {
            searchField: {
                action: 'onSearch',
                keyup: 'onSearch',
                clearicontap: 'onSearchClear'
            },
            logout: {
                tap: 'onLogout'
            }
        }
    },

    search: function(input, store) {
        store.clearFilter();
        if (input != '') {
            var regex = new RegExp('^' + input, 'i');
            store.filter([
                {
                    filterFn: function(record) {
                        return record.get('last_name').match(regex) ||
                               record.get('first_name').match(regex) ||
                               record.get('username').match(regex) ||
                               record.get('email').match(regex);
                    }
                }
            ]);
        }
    },

    onSearch: function(searchField) {
        this.search(searchField.getValue(), Ext.getStore('Students'));
    },

    onSearchClear: function() {
        Ext.getStore('Students').clearFilter();
    },

    onLogout: function() {
        Ext.Ajax.request({
            url: '/myesp/ajax_signout/',
            success: function(result) {
                Ext.Viewport.getActiveItem().destroy();
                Ext.Viewport.setActiveItem(Ext.widget('main'));
            },
            failure: function(result) {
                Ext.Msg.alert('Logout Error', 'An unknown error has occurred. You may wish to try logging out later.');
            }
        });
    }
});
