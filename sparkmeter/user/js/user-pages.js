// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('user-form', function() {
    var UserForm = require('user/js/user-form.js');
    new UserForm.UserForm();
});

base.registerPageLoader('user-list', function() {
    var UserList = require('user/js/user-list.js');
    new UserList.UserList();
});

base.registerPageLoader('user-view', function() {
    var UserView = require('user/js/user-view.js');
    new UserView.UserView();

    var SalesAccountList = require('salesaccount/js/sales-account-list.js');
    new SalesAccountList.SalesAccountList({
        page: SalesAccountList.PAGE_USER_VIEW
    });
});
