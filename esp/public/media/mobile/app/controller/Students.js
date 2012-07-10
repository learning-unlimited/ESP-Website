Ext.define('LU.controller.Students', {
    extend: 'Ext.app.Controller',

    config: {
        refs: {
            studentContainer: 'studentContainer',
            navigationBarTitle: 'studentContainer title',
            studentList: 'studentList',
            studentProfile: 'studentProfile',
            studentInfo: 'studentProfile #namecard',
            searchField: 'studentSearchBar textfield',
            phoneField: 'studentProfile textareafield[name="phone"]',
            segmentedButton: 'studentContainer segmentedbutton',
            logout: 'studentContainer button[text="Logout"]'
        },

        control: {
            studentList: {
                show: 'onListShow',
                itemtap: 'onStudentTap'
            },
            searchField: {
                action: 'onSearch',
                keyup: 'onSearch',
                clearicontap: 'onSearchClear'
            },
            segmentedButton: {
                toggle: 'onToggle'
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

    clearFieldValues: function() {
        Ext.Array.each(this.getStudentProfile().query('textfield,textareafield,numberfield'), function(field) {
            field.setValue('');
        });
    },

    setFieldValue: function(itemId, property) {
        this.getStudentProfile().down('#'+itemId).setValue(this.profile.get(property));

        if (itemId == 'phone_field') {
            if (this.profile.get(property).indexOf('\n') > -1) {
                // adjust to double row
                this.getPhoneField().setHeight('4em');
            } else {
                this.getPhoneField().setHeight('2em');
            }
        }
    },

    proceedTo: function(view) {
        this.getStudentContainer().push(view);

        // setup the navigation bar with segmented buttons
        var navbar = this.getStudentContainer().getNavigationBar();
        if (!this.segmentedButton) {
            this.segmentedButton = new Ext.SegmentedButton({
                centered: true,
                align: 'center',
                allowDepress: false,
                items: [
                    {
                        iconCls: 'user',
                        iconMask: true,
                        itemId: 'profile-tab',
                        pressed: true
                    },
                    {
                        iconCls: 'note2',
                        itemId: 'schedule-tab',
                        iconMask: true
                    }
                ]
            });
        } else {
            this.segmentedButton.show();
        }
        navbar.rightBox.hide();
        navbar.spacer.hide();
        navbar.leftBox.setWidth('100%');
        navbar.add(this.segmentedButton);
    },

    loadProfile: function(id) {
        var profileStore = Ext.getStore('StudentProfiles'),
            profileUrl = LU.Util.getStudentProfileUrl(id);

        Ext.Viewport.setMasked({ xtype: 'loadmask' });
        profileStore.setProxy({
            type: 'ajax',
            url: profileUrl
        });
        profileStore.removeAll();
        profileStore.load({
            callback: function(records, operation, success) {
                this.profile = records[0];
                this.setFieldValue('email_field', 'email');
                this.setFieldValue('phone_field', 'phone');
                this.setFieldValue('address_field', 'address');
                this.setFieldValue('school_field', 'school');
                this.setFieldValue('grad_yr_field', 'graduation_year');
                this.setFieldValue('grade_field', 'grade');
                this.setFieldValue('dob_field', 'dob');
                Ext.Viewport.setMasked(false);
                this.proceedTo(this.studentDetail);
            },
            scope: this
        });
    },

    onListShow: function(list, opts) {
        // show Logout button
        this.getLogout().show();
        this.getNavigationBarTitle().show();

        var navbar = this.getStudentContainer().getNavigationBar();
        navbar.rightBox.show();
        navbar.spacer.show();
        navbar.leftBox.setWidth(null);
        if (this.segmentedButton) {
            this.segmentedButton.hide();
        }
    },

    onStudentTap: function(list, index, target, record, event, opts) {
        if (!this.studentDetail) {
            this.studentDetail = Ext.widget('studentDetail');
        }
        this.getStudentInfo().setData(record.data);
        this.loadProfile(record.get('id'));

        // hide Logout button
        this.getLogout().hide();
    },

    onSearch: function(searchField) {
        this.search(searchField.getValue(), Ext.getStore('Students'));
    },

    onSearchClear: function() {
        Ext.getStore('Students').clearFilter();
    },

    onToggle: function(segmentedButton, button, isPressed, opts) {
        if (button.getItemId() == 'profile-tab') {
            this.studentDetail.setActiveItem(0);
        } else if (button.getItemId() == 'schedule-tab') {
            this.studentDetail.setActiveItem(1);
        }
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
