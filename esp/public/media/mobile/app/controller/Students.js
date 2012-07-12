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
            gradeField: 'studentProfile #grade_field',
            segmentedButton: 'studentContainer segmentedbutton',
            checkInButton: 'studentProfile #checkin_button',
            changeGradeButton: 'studentProfile #change_grade_button',
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
            checkInButton: {
                tap: 'onCheckIn'
            },
            changeGradeButton: {
                tap: 'onChangeGrade'
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

    checkIn: function(button, isCheckedIn) {
        button.setDisabled(isCheckedIn);

        if (isCheckedIn) {
            button.setText('Checked-in');
            button.setStyle({
                'background-image': '-webkit-linear-gradient(#3E5702,#507003 10%,#628904 65%,#648C04)',
                'color': '#eee'
            });
        } else {
            button.setText('Check-in');
            button.setStyle({
                'background-image': '-webkit-linear-gradient(#C2FA3B,#85BB05 2%,#547503)',
                'color': '#fff'
            });
        }
    },

    clearFieldValues: function() {
        Ext.Array.each(this.getStudentProfile().query('textfield,textareafield,numberfield'), function(field) {
            field.setValue('');
        });
    },

    setFieldValue: function(itemId, property) {

        var object = this.getStudentProfile().down('#'+itemId);

        if (itemId == 'checkin_button') {
            this.checkIn(object, this.profile.get(property));
            return;
        } else {
            object.setValue(this.profile.get(property));
        }

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
                this.setFieldValue('checkin_button', 'checkin_status');
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

    onCheckIn: function(button, event, opts) {

        // show checked in button first
        this.checkIn(button, true);

        LU.Util.ajaxPost({
            url: LU.Util.getRapidCheckInUrl(),
            params: {
                'user': this.profile.get('id')
            },
            success: function(result) {
                // do nothing
            },
            failure: function(result) {
                this.checkIn(button, false);
                Ext.Msg.alert('Network Error', 'Try checking-in again later.');
            },
            scope: this
        });
    },

    onChangeGrade: function() {
        Ext.Viewport.setMasked({ xtype: 'loadmask' });

        var new_grade = parseInt(this.getGradeField().getValue());
        LU.Util.ajaxPost({
            url: LU.Util.getChangeGradeUrl(),
            params: {
                'user': this.profile.get('id'),
                'grade': new_grade
            },
            success: function(result) {
                var grad_yr_field = this.getStudentProfile().down('#grad_yr_field'),
                    old_grade = parseInt(this.profile.get('grade')),
                    old_grad_yr = parseInt(grad_yr_field.getValue()),
                    new_grad_yr = old_grad_yr + old_grade - new_grade;

                // update the graduation year based on new grade
                grad_yr_field.setValue(new_grad_yr.toString().replace(',', ''));

                // update local storage
                this.profile.set('grade', new_grade);

                Ext.Viewport.setMasked(false);
            },
            failure: function(result) {
                // restores the old value
                this.setFieldValue('grade_field', 'grade');
                Ext.Viewport.setMasked(false);
            },
            scope: this
        });
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
