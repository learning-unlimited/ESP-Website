Ext.define('LU.controller.Classes', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            classList: 'classList',
            sortBy: 'classSortBar segmentedbutton',
            searchField: 'classSearchBar textfield',
            logout: 'titleBar button'
        },

        control: {
            sortBy: {
                toggle: 'onSortToggle'
            },
            searchField: {
                action: 'onSearch',
                keyup: 'onSearch',
                clearicontap: 'onSearchClear'
            },
            classList: {
                initialize: 'onListInit',
            },
            logout: {
                tap: 'onLogout'
            }
        },

        titleGrouper: {
            groupFn: function(record) {
                return record.get('title')[0];
            },
            sortProperty: 'title'               // sorts the grouped headers
        },

        difficultyGrouper: {
            groupFn: function(record) {
                return record.get('hardness_desc');
            },
            sortProperty: 'hardness_rating'
        }
    },

    onSortToggle: function(segBtn, btn) {
        var store = Ext.getStore('Classes');

        if (btn.getText() === 'Title') {
            store.setGrouper(this.getTitleGrouper());
        } else if (btn.getText() === 'Difficulty') {
            store.setGrouper(this.getDifficultyGrouper());
        } else if (btn.getText() === 'Time') {
            // not implemented yet
        }
        store.sort('title');                    // sorts items within the group
        this.getClassList().setStore(store);
        this.getClassList().deselectAll();
    },

    onListInit: function(list, opts) {
        list.getStore().load().clearFilter();
        list.getStore().setGrouper(this.getTitleGrouper());
    },

    onSearch: function(searchField) {
        this.getClassList().deselectAll();

        var store = Ext.getStore('Classes'),
            input = searchField.getValue();

        if (input != '') {
            store.clearFilter(true);
            store.filter('title', input, true);
        } else {
            store.clearFilter();
        }
    },

    onSearchClear: function() {
        Ext.getStore('Classes').clearFilter();
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
