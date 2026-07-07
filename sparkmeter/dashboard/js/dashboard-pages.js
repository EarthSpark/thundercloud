// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('dashboard', function() {
    var DashboardPage = require('dashboard/js/dashboard.js');
    new DashboardPage.DashboardPage();
});
