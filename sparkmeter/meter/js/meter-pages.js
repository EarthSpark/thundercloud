// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('meter-chart', function() {
    var MeterChart = require('meter/js/meter-chart.js');
    new MeterChart.MeterChart();
});

base.registerPageLoader('meter-view', function() {
    var MeterView = require('meter/js/meter-view.js');
    new MeterView.MeterView();

    var TransactionList = require('transaction/js/transaction-list.js');
    new TransactionList.TransactionList();
});
