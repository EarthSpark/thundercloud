// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('transaction-form', function() {
    var TransactionForm = require('transaction/js/transaction-form.js');
    TransactionForm.transaction_form();
});

base.registerPageLoader('transaction-transfer-form', function() {
    var TransactionForm = require('transaction/js/transaction-form.js');
    new TransactionForm.TransactionTransferForm();
});

base.registerPageLoader('transaction-list', function() {
    var TransactionList = require('transaction/js/transaction-list.js');
    new TransactionList.TransactionList();
});
