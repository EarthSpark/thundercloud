// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('salesaccount-list', function() {
    var SalesAccountList = require('salesaccount/js/sales-account-list.js');
    new SalesAccountList.SalesAccountList({
        page: SalesAccountList.PAGE_SALES_ACCOUNT
    });
});

base.registerPageLoader('salesaccount-view', function() {
    var TransactionList = require('transaction/js/transaction-list.js');
    new TransactionList.TransactionList();
});
