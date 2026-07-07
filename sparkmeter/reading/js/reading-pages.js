// -*- coding: utf-8 -*-
// Copyright © 2013-2016 SparkMeter, Inc.
// All Rights Reserved.
//

var base = require('base.js');

base.registerPageLoader('latest-readings', function() {
    var LatestReadings = require('reading/js/latest-readings.js');
    new LatestReadings.LatestReadings();
});
